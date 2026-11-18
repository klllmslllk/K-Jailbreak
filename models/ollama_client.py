import requests

from config import OLLAMA_URL, OPTIONS
from defenses.prompt.combined_prompt import apply_defense

DEFENSES = {"combined_prompt": apply_defense}


def generate_response(model, prompt, *, defense_module=None, show_prompt=False):
    messages = [{"role": "user", "content": prompt}]
    if defense_module is not None:
        if defense_module not in DEFENSES:
            raise ValueError(f"Unsupported defense module: {defense_module}")
        messages = DEFENSES[defense_module](messages)
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
