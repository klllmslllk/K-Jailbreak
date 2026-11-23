from datetime import datetime
import sqlite3

from config import DB_PATH


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("BEGIN")
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
            created_at TEXT,
            defense_module TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS experiment_runs (
            run_id TEXT PRIMARY KEY,
            defense TEXT
        )
    """)
    # 이전 버전의 NOT NULL 제약과 'none' 표기를 NULL로 전환한다.
    columns = conn.execute("PRAGMA table_info(experiment_runs)").fetchall()
    if any(column[1] == "defense" and column[3] for column in columns):
        conn.execute("ALTER TABLE experiment_runs RENAME TO experiment_runs_old")
        conn.execute("CREATE TABLE experiment_runs (run_id TEXT PRIMARY KEY, defense TEXT)")
        conn.execute("""
            INSERT INTO experiment_runs (run_id, defense)
            SELECT run_id, NULLIF(defense, 'none') FROM experiment_runs_old
        """)
        conn.execute("DROP TABLE experiment_runs_old")
    else:
        conn.execute("UPDATE experiment_runs SET defense = NULL WHERE defense = 'none'")
    result_columns = conn.execute("PRAGMA table_info(results)").fetchall()
    if not any(column[1] == "defense_module" for column in result_columns):
        conn.execute("ALTER TABLE results ADD COLUMN defense_module TEXT")
        conn.execute("""
            UPDATE results SET defense_module = (
                SELECT defense FROM experiment_runs WHERE experiment_runs.run_id = results.run_id
            )
        """)
    conn.commit()
    return conn


def register_run(conn, run_id, defense_module):
    """Record the defense for a run and reject incompatible resumptions."""
    defense = defense_module
    existing = conn.execute(
        "SELECT defense FROM experiment_runs WHERE run_id = ?", (run_id,)
    ).fetchone()
    if existing is None:
        legacy = conn.execute(
            "SELECT 1 FROM results WHERE run_id = ? LIMIT 1", (run_id,)
        ).fetchone()
        if legacy and defense is not None:
            raise ValueError("Existing results have no recorded defense; resume without --defense or use a new run ID.")
        conn.execute(
            "INSERT INTO experiment_runs (run_id, defense) VALUES (?, ?)",
            (run_id, defense),
        )
        conn.commit()
    elif existing[0] != defense:
        raise ValueError(f"Run {run_id} uses defense {existing[0]!r}; requested {defense!r}.")


def completed_results(conn, run_id):
    return set(conn.execute(
        "SELECT model, attack_id FROM results WHERE run_id = ?", (run_id,)
    ).fetchall())


def save_result(conn, run_id, model, attack, answer, defense_module=None, success=None):
    conn.execute("""
        INSERT INTO results (
            run_id, attack_id, original_id, model, language,
            prompt, goal, response, created_at, defense_module, success
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run_id, attack["attack_id"], attack["original_id"], model,
        attack["language"], attack["prompt"], attack["goal"], answer,
        datetime.now().isoformat(timespec="seconds"), defense_module, success,
    ))
    conn.commit()
