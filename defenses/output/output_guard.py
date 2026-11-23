"""사용자 질문을 참고해 모델 응답의 안전성을 검사한다."""

from defenses.guard_client import classify_messages


def classify(prompt, response):
    return classify_messages(
        [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response},
        ]
    )
