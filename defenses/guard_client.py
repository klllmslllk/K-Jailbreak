"""Independent Llama Guard input classification using Ollama's chat template."""
from dataclasses import dataclass
import re
from urllib.parse import urlsplit, urlunsplit

import requests
from config import GUARD_MODEL, GUARD_OPTIONS, OLLAMA_URL


@dataclass(frozen=True)
class GuardResult:
    verdict: str
    categories: tuple = ()
    raw: str = ""
    error: str = ""


def parse_response(raw):
    if not isinstance(raw, str):
        raise ValueError("Guard response must be text")
    lines = raw.strip().splitlines()
    if not lines or lines[0].strip() not in ("safe", "unsafe"):
        raise ValueError("Invalid Guard verdict")
    verdict = lines[0].strip()
    remainder = "\n".join(lines[1:]).strip()
    if verdict == "safe" and remainder:
        raise ValueError("Unexpected content after safe verdict")
    if remainder and not re.fullmatch(r"S(?:[1-9]|1[0-3])(?:\s*[,\s]\s*S(?:[1-9]|1[0-3]))*", remainder):
        raise ValueError("Invalid Guard categories")
    categories = tuple(re.findall(r"S(?:1[0-3]|[1-9])", remainder))
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
    raise RuntimeError(f"{GUARD_MODEL} is not installed. Install it with: ollama pull {GUARD_MODEL}")


def classify_messages(messages):
    raw = ''
    try:
        response = requests.post(OLLAMA_URL, json={
            'model': GUARD_MODEL, 'messages': messages,
            'stream': False, 'options': GUARD_OPTIONS,
        }, timeout=600)
        response.raise_for_status()
        raw = response.json()['message']['content']
        return parse_response(raw)
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        return GuardResult('error', raw=raw if isinstance(raw, str) else '', error=str(exc))


