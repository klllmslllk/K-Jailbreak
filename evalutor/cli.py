"""저장된 공격 응답에 대한 Qwen 평가 명령을 제공한다."""

import argparse
import sqlite3
from pathlib import Path

from .config import ROOT
from .runner import run


def main(argv=None):
    parser = argparse.ArgumentParser(description="Evaluate stored attack responses")
    parser.add_argument("--run-id")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--source-db", type=Path, default=ROOT / "results/results.db")
    parser.add_argument("--guard-db", type=Path, default=ROOT / "results/guard_results.db")
    parser.add_argument("--output-db", type=Path, default=ROOT / "results/evaluation_results.db")
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    protected = {args.source_db.resolve(), args.guard_db.resolve(),
                 (ROOT / "results/results.db").resolve(), (ROOT / "results/guard_results.db").resolve()}
    if args.output_db.resolve() in protected:
        parser.error("Evaluation output must differ from experiment and guard databases")
    try:
        counts = run(args.source_db, args.output_db, args.guard_db, args.run_id,
                     args.limit, args.resume, args.dry_run)
        print("Summary: " + ", ".join(f"{key}={value}" for key, value in counts.items()))
        return 1 if counts["failed"] else 0
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
        print(f"Evaluation setup failed: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
