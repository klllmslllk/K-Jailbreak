"""Classify a user request using Llama Guard's input mode."""
from defenses.guard_client import classify_messages, verify_model


def classify(prompt):
    return classify_messages([{"role": "user", "content": prompt}])
