"""데이터를 불러와 방어 모듈을 적용하고 모델 실험을 실행한다."""

import hashlib
import sqlite3
from uuid import uuid4

import pandas as pd
import requests

from config import CSV_PATH, LANGUAGES, MODELS
from database.guard_db import (
    connect_guard,
    register_guard_run,
    save_guard,
    register_output_guard_run,
    save_output_guard,
)
from defenses.registry import AVAILABLE_DEFENSES, INPUT_DEFENSES, SYSTEM_DEFENSES, OUTPUT_DEFENSES
from database.db import completed_results, connect, register_run, save_result
from models.ollama_client import generate_response


def load_attacks(csv_path=CSV_PATH):
    """CSV 행을 원본 ID를 공유하는 언어별 요청으로 펼친다."""
    rows = pd.read_csv(csv_path, encoding="utf-8-sig", keep_default_na=False)
    attacks = []

    # 같은 CSV 행의 언어 변형은 원본 ID를 공유한다.
    for index, row in rows.iterrows():
        original_id = index + 1
        for language, code in LANGUAGES.items():
            attacks.append(
                {
                    "attack_id": f"{original_id:03d}-{code}",
                    "original_id": original_id,
                    "language": "영어" if language == "goal" else language,
                    "prompt": row[language],
                    "goal": row["goal"],
                }
            )

    return attacks


def run_experiment(
    run_id=None, *, defense_module=None, show_prompt=False, dataset_type="attack", csv_path=CSV_PATH
):
    """선택한 방어를 적용하며 모델 응답과 Guard 판정을 수집한다."""
    selected = [defense_module] if isinstance(defense_module, str) else list(defense_module or [])

    if len(selected) != len(set(selected)) or set(selected) - AVAILABLE_DEFENSES:
        raise ValueError(f"Unsupported or duplicate defense modules: {selected}")
    # 방어는 입력·시스템·출력 단계별로 최대 하나씩 선택한다.
    stages = (INPUT_DEFENSES, SYSTEM_DEFENSES, OUTPUT_DEFENSES)
    stage_selections = [[name for name in selected if name in stage] for stage in stages]
    if any(len(names) > 1 for names in stage_selections):
        raise ValueError("Only one defense can be selected per stage.")

    input_defense, system_defense, output_defense = (
        names[0] if names else None for names in stage_selections
    )
    input_module = INPUT_DEFENSES[input_defense] if input_defense else None
    output_module = OUTPUT_DEFENSES[output_defense] if output_defense else None
    defense_module = ",".join(sorted(selected)) or None
    if dataset_type not in ("attack", "benign"):
        raise ValueError("dataset_type must be attack or benign")

    attacks = load_attacks(csv_path)
    # 재개 시 다른 데이터셋이 같은 실험에 섞이지 않도록 해시를 기록한다.
    dataset_hash = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    digest = input_module.verify_model() if input_module else None

    # 같은 Guard 모델과 확인 함수를 사용하면 모델 확인 결과를 공유한다.
    output_digest = (
        digest
        if input_module
        and output_module
        and input_module.model == output_module.model
        and input_module.verify_model == output_module.verify_model
        else output_module.verify_model() if output_module else None
    )

    print(f"Loaded prompts: {len(attacks)}")
    run_id = run_id if run_id else uuid4().hex
    saved_count = skipped_count = failed_count = save_failed_count = current = 0
    total = len(attacks) * len(MODELS)
    conn = connect()
    guard_conn = None

    try:
        guard_conn = connect_guard()
        legacy = bool(completed_results(conn, run_id))
        register_guard_run(
            guard_conn,
            run_id,
            bool(input_module),
            dataset_type,
            dataset_hash,
            input_module.model if input_module else None,
            digest,
            input_module.options if input_module else None,
            legacy,
        )
        register_run(conn, run_id, defense_module)
        if output_module:
            register_output_guard_run(
                guard_conn,
                run_id,
                output_module.model,
                output_digest,
                output_module.options,
                legacy,
            )
        # 이미 저장된 모델·질문 조합은 재개 시 건너뛴다.
        completed = completed_results(conn, run_id)
        print(f"Run ID: {run_id}")
        print(f"Defense: {defense_module or 'none'}")

        for model in MODELS:
            print(f"\nExperiment: {model}")
            for attack in attacks:
                current += 1
                if (model, attack["attack_id"]) in completed:
                    skipped_count += 1
                    continue

                print(
                    f"\n{'=' * 50}\n[{current}/{total}] {attack['attack_id']} / {attack['language']}\n{'=' * 50}"
                )
                success = None

                try:
                    blocked = False
                    if input_module:
                        # 입력 판정을 저장한 뒤 오류라면 대상 모델을 호출하지 않는다.
                        verdict = input_module.classify(attack["prompt"])
                        save_guard(
                            guard_conn,
                            run_id,
                            attack,
                            model,
                            dataset_type,
                            input_module.model,
                            digest,
                            input_module.options,
                            verdict,
                        )
                        if verdict.verdict == "error":
                            failed_count += 1
                            print(f"Guard error (request skipped): {verdict.error}")
                            continue
                        blocked = verdict.verdict == "unsafe"

                    if blocked:
                        answer = "안전 정책에 따라 해당 요청을 처리할 수 없습니다."
                        # 정상 요청 차단은 공격 실패가 아닌 오탐 분석 대상이다.
                        if dataset_type == "attack":
                            success = 0
                    else:
                        messages = [{"role": "user", "content": attack["prompt"]}]
                        if system_defense is not None:
                            messages = SYSTEM_DEFENSES[system_defense](messages)

                        answer = generate_response(
                            model,
                            messages,
                            show_prompt=show_prompt,
                        )
                        if output_module:
                            # 최종 거절문과 구분하도록 차단 전 모델 응답을 보존한다.
                            verdict = output_module.classify(attack["prompt"], answer)
                            save_output_guard(
                                guard_conn,
                                run_id,
                                attack,
                                model,
                                dataset_type,
                                output_module.model,
                                output_digest,
                                output_module.options,
                                answer,
                                verdict,
                            )
                            if verdict.verdict == "error":
                                failed_count += 1
                                print(f"Output Guard error (request skipped): {verdict.error}")
                                continue
                            if verdict.verdict == "unsafe":
                                answer = "안전 정책에 따라 해당 요청을 처리할 수 없습니다."
                                if dataset_type == "attack":
                                    success = 0
                except (requests.RequestException, ValueError, KeyError, TypeError) as error:
                    failed_count += 1
                    print(f"API call: {error}")
                    continue

                try:
                    save_result(
                        conn,
                        run_id,
                        model,
                        attack,
                        answer,
                        defense_module=defense_module,
                        success=success,
                    )
                    saved_count += 1
                    print("SQLite save succeeded")
                except sqlite3.Error as error:
                    conn.rollback()
                    save_failed_count += 1
                    print(f"SQLite save failed: {error}")
    finally:
        if guard_conn is not None:
            guard_conn.close()
        conn.close()

    print(f"\nCompleted: saved {saved_count}, API failures {failed_count}")
    print(f"SQLite save failures: {save_failed_count}")
    print(f"Existing results skipped: {skipped_count}")
