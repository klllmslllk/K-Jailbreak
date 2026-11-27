"""Ollama의 Qwen 모델로 응답을 이진 평가한다."""

import json

import requests

from config import OLLAMA_URL


MODEL = "qwen3.5:9b"
TIMEOUT = 600
MAX_RETRIES = 2
NUM_CTX = 16384
NUM_PREDICT = 4096


class EvaluationError(RuntimeError):
    """평가 실행이 완료되지 않았음을 나타낸다."""


class OutputLimitError(EvaluationError):
    """생성 한도에 도달해 판정이 완료되지 않았다."""


def parse_result(content: str) -> int:
    """허용된 두 출력만 정수 판정으로 변환한다."""
    if not isinstance(content, str):
        raise EvaluationError("Judge response content must be a string")
    result = content.strip()
    if result == "SUCCESS":
        return 1
    if result == "FAILURE":
        return 0
    raise EvaluationError("Judge response must be exactly SUCCESS or FAILURE")


def evaluate(attack_prompt: str, response: str) -> int:
    """공격 프롬프트와 최종 응답을 모델에 전달하여 평가한다."""
    if not isinstance(attack_prompt, str) or not isinstance(response, str):
        raise TypeError("attack_prompt and response must be strings")

    try:
        from .system_prompt import SYSTEM_PROMPT
    except ImportError as exc:
        raise EvaluationError("System prompt is not installed; evaluator setup is incomplete") from exc

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(
                {"attack_prompt": attack_prompt, "response": response},
                ensure_ascii=False,
            )},
        ],
        "stream": False,
        "think": True,
        "truncate": False,
        "shift": False,
        "options": {"temperature": 0, "seed": 42, "num_ctx": NUM_CTX,
                    "num_predict": NUM_PREDICT},
    }
    last_error = None
    for _ in range(MAX_RETRIES + 1):
        try:
            reply = requests.post(OLLAMA_URL, json=payload, timeout=TIMEOUT)
            if 400 <= reply.status_code < 500:
                raise EvaluationError(f"Ollama API error {reply.status_code}: {reply.text}")
            reply.raise_for_status()
            data = reply.json()
            if not isinstance(data, dict):
                raise EvaluationError("Ollama response must be an object")
            if data.get("done") is not True or data.get("done_reason") == "length":
                error_type = OutputLimitError if data.get("done_reason") == "length" else EvaluationError
                raise error_type(
                    "Judge response incomplete "
                    f"(done={data.get('done')!r}, "
                    f"done_reason={data.get('done_reason')!r}, "
                    f"eval_count={data.get('eval_count')!r}, "
                    f"num_predict={NUM_PREDICT})"
                )
            return parse_result(data["message"]["content"])
        except (requests.RequestException, KeyError, TypeError, ValueError, EvaluationError) as exc:
            last_error = exc
            # 동일한 길이 한도에 도달한 요청을 반복해 기다리지 않는다.
            if isinstance(exc, OutputLimitError):
                break
            if isinstance(exc, EvaluationError) and str(exc).startswith("Ollama API error 4"):
                break
    raise EvaluationError(f"Qwen evaluation failed: {last_error}") from last_error
