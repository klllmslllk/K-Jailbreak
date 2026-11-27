"""저장된 공격 응답을 Qwen 평가기로 평가하고 결과를 보존한다."""

from contextlib import closing
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit

import requests

from config import OLLAMA_URL
from .base import EvaluationResult
from .config import digest
from .db import connect, previous, save, source_connection, source_rows, summary
from .qwen_evaluator import MODEL, NUM_CTX, NUM_PREDICT, MAX_RETRIES, TIMEOUT, evaluate
from .system_prompt import POLICY_VERSION, PROMPT_VERSION, SYSTEM_PROMPT


def model_identity():
    """설치된 Judge와 서버의 식별 정보를 확인한다."""
    endpoint = urlsplit(OLLAMA_URL)
    base = f"{endpoint.scheme}://{endpoint.netloc}"
    try:
        tags = requests.get(base + "/api/tags", timeout=10)
        tags.raise_for_status()
        models = tags.json()["models"]
        model = next((entry for entry in models if entry.get("name") == MODEL), None)
        if model is None:
            raise ValueError(f"Ollama model {MODEL} is not installed")
        server = requests.get(base + "/api/version", timeout=10)
        server.raise_for_status()
        return model["digest"], server.json()["version"]
    except (requests.RequestException, KeyError, ValueError) as exc:
        raise RuntimeError(f"Ollama setup failed: {exc}") from exc


def now():
    return datetime.now(timezone.utc).isoformat()


def run(source_path, output_path, guard_path, run_id=None, limit=None,
        resume=False, dry_run=False, judge=evaluate):
    """기록된 데이터셋 유형이 공격인 행만 평가한다."""
    source_path, output_path, guard_path = map(Path, (source_path, output_path, guard_path))
    if output_path.resolve() in {source_path.resolve(), guard_path.resolve()}:
        raise ValueError("Evaluation output must differ from source and guard databases")
    with closing(source_connection(source_path)) as source, closing(source_connection(guard_path)) as guard:
        types = dict(guard.execute("SELECT run_id, dataset_type FROM input_guard_runs"))
        candidates = list(source_rows(source, run_id))
        rows = [row for row in candidates if types.get(row["run_id"]) == "attack"]
        excluded = len(candidates) - len(rows)
        if limit is not None:
            rows = rows[:limit]
        print(f"Attack records: {len(rows)}; non-attack or unverified records excluded: {excluded}")
        counts = {"completed": 0, "failed": 0, "skipped": 0}
        if dry_run or not rows:
            return counts
        model_digest, server_version = model_identity()
        identity = {"evaluator": "qwen_binary", "version": "1.0.0", "model": MODEL,
                    "model_digest": model_digest, "ollama_version": server_version,
                    "policy": POLICY_VERSION, "prompt_version": PROMPT_VERSION,
                    "system_prompt_sha256": sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest(),
                    "temperature": 0, "seed": 42, "num_ctx": NUM_CTX,
                    "num_predict": NUM_PREDICT, "retries": MAX_RETRIES,
                    "retry_policy": "stop_on_output_limit_v1",
                    "timeout": TIMEOUT, "stream": False,
                    "think": True, "truncate": False, "shift": False,
                    "question_source": "results.prompt"}
        config_hash = digest(identity)
        source_name = str(source_path.resolve())
        with closing(connect(output_path)) as dest:
            for index, row in enumerate(rows, 1):
                input_hash = digest([row["prompt"], row["response"]])
                if previous(dest, source_name, row["id"], input_hash, config_hash):
                    counts["skipped"] += 1
                    continue
                if not resume and dest.execute(
                    "SELECT 1 FROM evaluations WHERE source_database=? AND source_result_id=? AND input_hash=? AND config_hash=? AND status='error' LIMIT 1",
                    (source_name, row["id"], input_hash, config_hash),
                ).fetchone():
                    counts["skipped"] += 1
                    continue
                started = now()
                try:
                    label = judge(row["prompt"], row["response"])
                    if type(label) is not int or label not in (0, 1):
                        raise ValueError("Judge returned an invalid binary result")
                    result = EvaluationResult("qwen_binary", "1.0.0", MODEL,
                                              success=bool(label), metadata={"label": "SUCCESS" if label else "FAILURE"})
                except Exception as exc:
                    result = EvaluationResult("qwen_binary", "1.0.0", MODEL,
                                              status="error", error=f"{type(exc).__name__}: {exc}")
                save(dest, source_name, row, input_hash, config_hash, identity, result, started, now(), "results.prompt")
                counts["completed" if result.status == "ok" else "failed"] += 1
                detail = (result.metadata.get("label") if result.status == "ok" else result.error)
                print(f"[{index}/{len(rows)}] result {row['id']}: {result.status} {detail}", flush=True)
            for item in summary(dest, config_hash, None, run_id):
                print(f"Historical ASR {item['target_model']} / {item['language']} / {item['defense_module']} / {item['source_run_id']}: {item['successes']}/{item['valid']} = {item['successes']/item['valid']:.3f}")
        return counts
