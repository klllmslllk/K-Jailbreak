from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "datasets" / "data.csv"
DB_PATH = BASE_DIR / "results" / "results.db"
OLLAMA_URL = "http://localhost:11434/api/chat"
MODELS = ["qwen3:8b", "llama3.1:8b", "exaone3.5:7.8b"]
OPTIONS = {"temperature": 0, "seed": 42, "num_ctx": 4096, "num_predict": 2048}
LANGUAGES = {
    "goal": "EN",
    "평어체": "PLAIN",
    "경어체": "HONOR",
    "충청도 방언": "CHUNG",
    "경상도 방언": "GYEONG",
    "은어": "SLANG",
}

GUARD_MODEL = "llama-guard3:8b"
GUARD_DB_PATH = BASE_DIR / "results" / "guard_results.db"
GUARD_OPTIONS = {"temperature": 0, "seed": 42, "num_predict": 128}
