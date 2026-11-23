"""정상 데이터 실험의 입력 Guard 오탐률을 출력한다."""

import argparse
import json
from database.guard_db import connect_guard, fpr

parser = argparse.ArgumentParser()
parser.add_argument('run_id')
args = parser.parse_args()
conn = connect_guard()
try:
    print(json.dumps(fpr(conn, args.run_id), ensure_ascii=False, indent=2))
finally:
    conn.close()
