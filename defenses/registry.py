"""입력·시스템·출력 단계별 방어 모듈을 등록한다."""

from dataclasses import dataclass
from typing import Callable

from config import GUARD_MODEL, GUARD_OPTIONS
from defenses.input.input_guard import classify, verify_model
from defenses.output.output_guard import classify as classify_output
from defenses.system.combined_prompt import apply_defense


@dataclass(frozen=True)
class InputDefense:
    """입력 검사에 필요한 분류 함수와 모델 설정."""

    classify: Callable
    verify_model: Callable
    model: str
    options: dict


@dataclass(frozen=True)
class OutputDefense:
    """출력 검사에 필요한 분류 함수와 모델 설정."""

    classify: Callable
    verify_model: Callable
    model: str
    options: dict


# 각 단계의 이름을 실제 방어 구현에 연결한다.
INPUT_DEFENSES = {
    "input-guard": InputDefense(classify, verify_model, GUARD_MODEL, GUARD_OPTIONS),
}
SYSTEM_DEFENSES = {"combined_prompt": apply_defense}
OUTPUT_DEFENSES = {
    "output-guard": OutputDefense(classify_output, verify_model, GUARD_MODEL, GUARD_OPTIONS),
}

AVAILABLE_DEFENSES = set(INPUT_DEFENSES) | set(SYSTEM_DEFENSES) | set(OUTPUT_DEFENSES)
