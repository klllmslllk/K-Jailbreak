"""Ollama 대상 모델에 메시지를 보내고 응답을 받는다."""

import requests

from config import OLLAMA_URL, OPTIONS


def generate_response(model, messages, *, show_prompt=False):
    if show_prompt:
        print("Messages sent to Ollama:")
        for message in messages:
            print(f"\n[{message['role']}]\n{message['content']}")
    data = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": OPTIONS,
    }
    response = requests.post(OLLAMA_URL, json=data, timeout=600)
    response.raise_for_status()
    answer = response.json()["message"]["content"]
    if not isinstance(answer, str):
        raise ValueError("LLM response must be a string.")
    return answer
