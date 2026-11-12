import argparse
from datetime import datetime
from pathlib import Path
import sqlite3
from uuid import uuid4

import pandas as pd
import requests


parser = argparse.ArgumentParser(description="LLM 응답 수집")
parser.add_argument("--run-id", help="재개할 실험 ID. 생략하면 새 실험을 시작합니다.")
args = parser.parse_args()

url = "http://localhost:11434/api/chat"
# 실제 설치된 모델 이름을 사용한다.
models = ["qwen3:8b", "llama3.1:8b", "exaone3.5:7.8b"]
options = {"temperature": 0, "seed": 42, "num_ctx": 4096, "num_predict": 2048}

folder = Path(__file__).parent
csv_path = folder / "Data" / "data.csv"
db_path = folder / "results.db"

languages = {
    "평어체": "PLAIN",
    "경어체": "HONOR",
    "충청도 방언": "CHUNG",
    "경상도 방언": "GYEONG",
    "은어": "SLANG"
}

# CSV 한 행을 언어 변형별 공격 5개로 나눈다.
rows = pd.read_csv(csv_path, encoding="utf-8-sig", keep_default_na=False)
attacks = []

for index, row in rows.iterrows():
    original_id = index + 1
    for language, code in languages.items():
        attack = {
            "attack_id": f"{original_id:03d}-{code}",
            "original_id": original_id,
            "language": language,
            "prompt": row[language],
            "goal": row["goal"]
        }
        attacks.append(attack)

print(f"불러온 공격 데이터: {len(attacks)}개")
conn = sqlite3.connect(db_path)
conn.execute("""
    CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT,
        attack_id TEXT,
        original_id INTEGER,
        model TEXT,
        language TEXT,
        prompt TEXT,
        goal TEXT,
        response TEXT,
        success INTEGER,
        created_at TEXT
    )
""")
conn.commit()

# ID를 지정하면 해당 실험을 재개하고, 생략하면 새 실험을 시작한다.
run_id = args.run_id if args.run_id else uuid4().hex

completed = conn.execute(
    "SELECT model, attack_id FROM results WHERE run_id = ?",
    (run_id,)
).fetchall()
print(f"실험 실행 ID: {run_id}")

saved_count = 0
skipped_count = 0
failed_count = 0
save_failed_count = 0
current = 0
total = len(attacks) * len(models)

try:
    for model in models:
        print(f"\n현재 모델: {model}")

        for attack in attacks:
            current += 1
            if (model, attack["attack_id"]) in completed:
                skipped_count += 1
                continue

            prompt = attack["prompt"]
            print(f"[{current}/{total}] {attack['attack_id']} / {attack['language']}")

            data = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "stream": False,
                "options": options
            }

            try:
                response = requests.post(url, json=data, timeout=600)
                response.raise_for_status()
                result = response.json()
                answer = result["message"]["content"]
                if not isinstance(answer, str):
                    raise ValueError("LLM 응답이 문자열이 아닙니다.")
            except (requests.RequestException, ValueError, KeyError, TypeError) as error:
                failed_count += 1
                print(f"API 호출 실패: {error}")
                continue

            try:
                conn.execute("""
                    INSERT INTO results (
                        run_id, attack_id, original_id, model, language,
                        prompt, goal, response, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    run_id, attack["attack_id"], attack["original_id"],
                    model, attack["language"], prompt, attack["goal"],
                    answer, datetime.now().isoformat(timespec="seconds")
                ))
                conn.commit()
                saved_count += 1
                print("SQLite 저장 성공")
            except sqlite3.Error as error:
                conn.rollback()
                save_failed_count += 1
                print(f"SQLite 저장 실패: {error}")
finally:
    conn.close()

print(f"\n전체 실험 완료: 저장 성공 {saved_count}개, API 호출 실패 {failed_count}개")
print(f"SQLite 저장 실패: {save_failed_count}개")
print(f"기존 저장 결과 건너뜀: {skipped_count}개")
