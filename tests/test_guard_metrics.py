"""Guard 오탐률 집계가 기존 최신 판정 규칙을 유지하는지 검증한다."""

import random
import sqlite3
import unittest

from database.guard_db import fpr


class GuardMetricsTest(unittest.TestCase):
    def test_latest_verdict_matches_previous_query(self):
        conn = sqlite3.connect(":memory:")
        self.addCleanup(conn.close)
        conn.execute(
            "CREATE TABLE input_guard_results (id INTEGER PRIMARY KEY, run_id TEXT, "
            "attack_id TEXT, dataset_type TEXT, language TEXT, guard_verdict TEXT)"
        )
        rng = random.Random(42)
        conn.executemany(
            "INSERT INTO input_guard_results VALUES (?, ?, ?, ?, ?, ?)",
            (
                (i, rng.choice(("run", "other")), rng.choice(("a", "b", "c", None)),
                 rng.choice(("attack", "benign")), rng.choice(("ko", "en")),
                 rng.choice(("safe", "unsafe", "error")))
                for i in range(1, 501)
            ),
        )
        query = """SELECT language, SUM(guard_verdict='unsafe'),
                   SUM(guard_verdict='safe'), SUM(guard_verdict='error')
                   FROM input_guard_results g WHERE run_id=? AND dataset_type='benign'
                   AND id=(SELECT MAX(id) FROM input_guard_results x
                           WHERE x.run_id=g.run_id AND x.attack_id=g.attack_id)
                   GROUP BY language ORDER BY language"""
        for run_id in ("run", "other", "missing", None):
            with self.subTest(run_id=run_id):
                rows = conn.execute(query, (run_id,)).fetchall()
                actual = fpr(conn, run_id)
                self.assertEqual(
                    [(r["language"], r["fp"], r["tn"], r["errors"]) for r in actual[1:]],
                    rows,
                )
                fp, tn, errors = (sum(row[i] for row in rows) for i in (1, 2, 3))
                self.assertEqual(actual[0], {
                    "language": "overall", "fp": fp, "tn": tn, "errors": errors,
                    "fpr_percent": 100 * fp / (fp + tn) if fp + tn else None,
                })


if __name__ == "__main__":
    unittest.main()
