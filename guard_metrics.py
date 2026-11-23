"""Print descriptive Guard FPR for a benign experiment run."""
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
