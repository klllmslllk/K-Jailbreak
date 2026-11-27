"""평가 결과와 실행 오류를 담는 자료형을 정의한다."""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvaluationResult:
    evaluator_name: str
    evaluator_version: str | None = None
    judge_model: str | None = None
    score: float | None = None
    success: bool | None = None
    status: str = "ok"
    threshold: float | None = None
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
