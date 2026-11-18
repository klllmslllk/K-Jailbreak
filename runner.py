import sqlite3
from uuid import uuid4

import pandas as pd
import requests

from config import CSV_PATH, LANGUAGES, MODELS
from database.db import completed_results, connect, register_run, save_result
from models.ollama_client import DEFENSES, generate_response


def load_attacks():
    rows = pd.read_csv(CSV_PATH, encoding="utf-8-sig", keep_default_na=False)
    attacks = []
    for index, row in rows.iterrows():
        original_id = index + 1
        for language, code in LANGUAGES.items():
            attacks.append({
                "attack_id": f"{original_id:03d}-{code}",
                "original_id": original_id,
                "language": language,
                "prompt": row[language],
                "goal": row["goal"],
            })
    return attacks


def run_experiment(run_id=None, *, defense_module=None, show_prompt=False):
    if defense_module is not None and defense_module not in DEFENSES:
        raise ValueError(f"Unsupported defense module: {defense_module}")
    attacks = load_attacks()
    print(f"Loaded prompts: {len(attacks)}")
    run_id = run_id if run_id else uuid4().hex
    saved_count = skipped_count = failed_count = save_failed_count = current = 0
    total = len(attacks) * len(MODELS)
    conn = connect()
    try:
        register_run(conn, run_id, defense_module)
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
                print(f"\n{'=' * 50}\n[{current}/{total}] {attack['attack_id']} / {attack['language']}\n{'=' * 50}")
                try:
                    answer = generate_response(
                        model, attack["prompt"], defense_module=defense_module,
                        show_prompt=show_prompt,
                    )
                except (requests.RequestException, ValueError, KeyError, TypeError) as error:
                    failed_count += 1
                    print(f"API call: {error}")
                    continue
                try:
                    save_result(
                        conn, run_id, model, attack, answer,
                        defense_module=defense_module,
                    )
                    saved_count += 1
                    print("SQLite save succeeded")
                except sqlite3.Error as error:
                    conn.rollback()
                    save_failed_count += 1
                    print(f"SQLite save failed: {error}")
    finally:
        conn.close()
    print(f"\nCompleted: saved {saved_count}, API failures {failed_count}")
    print(f"SQLite save failures: {save_failed_count}")
    print(f"Existing results skipped: {skipped_count}")
