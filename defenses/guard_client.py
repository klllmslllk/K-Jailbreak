"""입력·출력 Guard가 공유하는 Ollama 호출과 판정 파서."""

from dataclasses import dataclass
import re
from urllib.parse import urlsplit, urlunsplit

import requests
from config import GUARD_MODEL, GUARD_OPTIONS, OLLAMA_URL


@dataclass(frozen=True)
class GuardResult:
    """Guard의 판정, 범주, 원본 응답과 오류를 함께 보관한다."""
    verdict: str
    categories: tuple = ()
    raw: str = ""
    error: str = ""


def parse_response(raw):
    """Guard 응답의 판정과 선택적 위험 범주를 해석한다."""
    if not isinstance(raw, str):
        raise ValueError("Guard response must be text")
    # 첫 줄 전체가 판정이어야 하며 문장 중간의 단어는 인정하지 않는다.
    lines = raw.strip().splitlines()
    if not lines or lines[0].strip() not in ("safe", "unsafe"):
        raise ValueError("Invalid Guard verdict")
    verdict = lines[0].strip()
    remainder = "\n".join(lines[1:]).strip()
    if verdict == "safe" and remainder:
        raise ValueError("Unexpected content after safe verdict")
    if remainder and not re.fullmatch(
        r"S(?:[1-9]|1[0-4])(?:\s*[,\s]\s*S(?:[1-9]|1[0-4]))*", remainder
    ):
        raise ValueError("Invalid Guard categories")
    categories = tuple(re.findall(r"S(?:1[0-4]|[1-9])", remainder))
    return GuardResult(verdict, categories, raw)


def verify_model():
    parts = urlsplit(OLLAMA_URL)
    url = urlunsplit((parts.scheme, parts.netloc, '/api/tags', '', ''))
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        for model in response.json()['models']:
            if model.get('name') == GUARD_MODEL or model.get('model') == GUARD_MODEL:
                digest = model.get('digest')
                if not digest:
                    raise ValueError('Guard model digest is missing from Ollama')
                return digest
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        raise RuntimeError(f"Cannot verify {GUARD_MODEL} in Ollama: {exc}") from exc
    raise RuntimeError(
        f"{GUARD_MODEL} is not installed. Install it with: ollama pull {GUARD_MODEL}"
    )


def classify_messages(messages):
    raw = ''
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                'model': GUARD_MODEL,
                'messages': messages,
                'stream': False,
                'options': GUARD_OPTIONS,
            },
            timeout=600,
        )
        response.raise_for_status()
        raw = response.json()['message']['content']
        return parse_response(raw)
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        # 호출이나 파싱 실패는 안전 판정이 아닌 오류로 전달한다.
        return GuardResult('error', raw=raw if isinstance(raw, str) else '', error=str(exc))
