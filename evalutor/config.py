"""평가 경로와 설정 식별용 해시를 정의한다."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def digest(value):
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()
