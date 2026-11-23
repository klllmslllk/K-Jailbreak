"""Classify the target model's response in the context of the user request."""
from defenses.guard_client import classify_messages


def classify(prompt, response):
    return classify_messages([
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": response},
    ])
