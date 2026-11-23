"""Llama Guard로 사용자 입력의 안전성을 검사한다."""

from defenses.guard_client import classify_messages, verify_model


def classify(prompt):
    return classify_messages([{"role": "user", "content": prompt}])
