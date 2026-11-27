"""평가 결과와 실행 오류를 담는 자료형을 정의한다."""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvaluationResult:
    evaluator_name: str
    evaluator_version: str | None = None
    judge_model: str | None = None
    success: bool | None = None
    status: str = "ok"
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
