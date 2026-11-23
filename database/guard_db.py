"""Guard run configuration, evaluation records and descriptive FPR."""
import json
import sqlite3
from datetime import datetime, timezone
from config import GUARD_DB_PATH


def connect_guard(path=None):
    path = path or GUARD_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        # 기존 입력 Guard 테이블을 트랜잭션으로 이름 변경한다.
        with conn:
            conn.execute('BEGIN IMMEDIATE')
            existing = {row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )}
            for old, new in (('guard_runs', 'input_guard_runs'),
                             ('guard_results', 'input_guard_results')):
                if old in existing and new in existing:
                    raise RuntimeError(f'Both {old} and {new} exist; resolve the conflict before continuing.')
            for old, new in (('guard_runs', 'input_guard_runs'),
                             ('guard_results', 'input_guard_results')):
                if old in existing:
                    conn.execute(f'ALTER TABLE "{old}" RENAME TO "{new}"')
    except Exception:
        conn.close()
        raise
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS input_guard_runs (
        run_id TEXT PRIMARY KEY, enabled INTEGER NOT NULL CHECK(enabled IN (0,1)),
        dataset_type TEXT NOT NULL CHECK(dataset_type IN ('attack','benign')),
        dataset_hash TEXT NOT NULL, guard_model TEXT, model_digest TEXT, guard_options TEXT
    );
    CREATE TABLE IF NOT EXISTS input_guard_results (
        id INTEGER PRIMARY KEY, run_id TEXT NOT NULL, attack_id TEXT NOT NULL,
        original_id INTEGER NOT NULL, target_model TEXT NOT NULL,
        dataset_type TEXT NOT NULL CHECK(dataset_type IN ('attack','benign')),
        language TEXT NOT NULL, prompt TEXT NOT NULL, guard_model TEXT NOT NULL,
        model_digest TEXT NOT NULL, guard_options TEXT NOT NULL,
        guard_verdict TEXT NOT NULL CHECK(guard_verdict IN ('safe','unsafe','error')),
        hazard_categories TEXT NOT NULL, raw_guard_response TEXT NOT NULL,
        error TEXT NOT NULL, was_blocked INTEGER NOT NULL CHECK(was_blocked IN (0,1)),
        defense_enabled INTEGER NOT NULL CHECK(defense_enabled IN (0,1)), created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_guard_link ON input_guard_results(run_id, target_model, attack_id);
    CREATE INDEX IF NOT EXISTS idx_guard_metrics ON input_guard_results(run_id, dataset_type, language, guard_verdict);
    CREATE TABLE IF NOT EXISTS output_guard_runs (
        run_id TEXT PRIMARY KEY, guard_model TEXT NOT NULL,
        model_digest TEXT NOT NULL, guard_options TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS output_guard_results (
        id INTEGER PRIMARY KEY, run_id TEXT NOT NULL, attack_id TEXT NOT NULL,
        original_id INTEGER NOT NULL, target_model TEXT NOT NULL,
        dataset_type TEXT NOT NULL CHECK(dataset_type IN ('attack','benign')),
        language TEXT NOT NULL, prompt TEXT NOT NULL, target_response TEXT NOT NULL,
        guard_model TEXT NOT NULL, model_digest TEXT NOT NULL, guard_options TEXT NOT NULL,
        guard_verdict TEXT NOT NULL CHECK(guard_verdict IN ('safe','unsafe','error')),
        hazard_categories TEXT NOT NULL, raw_guard_response TEXT NOT NULL, error TEXT NOT NULL,
        was_blocked INTEGER NOT NULL CHECK(was_blocked IN (0,1)), created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_output_guard_link
        ON output_guard_results(run_id, target_model, attack_id);
    ''')
    return conn


def register_guard_run(conn, run_id, enabled, dataset_type, dataset_hash, model, digest, options, legacy_results):
    values = (int(enabled), dataset_type, dataset_hash, model if enabled else None,
              digest if enabled else None, json.dumps(options, sort_keys=True) if enabled else None)
    existing = conn.execute('SELECT enabled,dataset_type,dataset_hash,guard_model,model_digest,guard_options FROM input_guard_runs WHERE run_id=?', (run_id,)).fetchone()
    if existing is None:
        if legacy_results and (enabled or dataset_type != 'attack'):
            raise ValueError('Existing run has no Guard configuration; use a new run ID.')
        with conn:
            conn.execute('INSERT INTO input_guard_runs VALUES (?,?,?,?,?,?,?)', (run_id, *values))
    elif existing != values:
        raise ValueError('Run configuration, dataset, or Guard model digest changed; use a new run ID.')


def save_guard(conn, run_id, attack, model, dataset_type, guard_model, digest, options, result):
    with conn:
        conn.execute('''INSERT INTO input_guard_results
        (run_id,attack_id,original_id,target_model,dataset_type,language,prompt,guard_model,
         model_digest,guard_options,guard_verdict,hazard_categories,raw_guard_response,error,
         was_blocked,defense_enabled,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
        (run_id, attack['attack_id'], attack['original_id'], model, dataset_type, attack['language'],
         attack['prompt'], guard_model, digest, json.dumps(options, sort_keys=True), result.verdict,
         json.dumps(result.categories), result.raw, result.error, int(result.verdict == 'unsafe'), 1,
         datetime.now(timezone.utc).isoformat()))


def register_output_guard_run(conn, run_id, model, digest, options, legacy_results):
    values = (model, digest, json.dumps(options, sort_keys=True))
    existing = conn.execute('SELECT guard_model, model_digest, guard_options FROM output_guard_runs WHERE run_id=?', (run_id,)).fetchone()
    if existing is None:
        if legacy_results:
            raise ValueError('Existing run has no output Guard configuration; use a new run ID.')
        with conn:
            conn.execute('INSERT INTO output_guard_runs VALUES (?,?,?,?)', (run_id, *values))
    elif existing != values:
        raise ValueError('Output Guard model digest or options changed; use a new run ID.')


def save_output_guard(conn, run_id, attack, model, dataset_type, guard_model, digest, options, response, result):
    with conn:
        conn.execute('''INSERT INTO output_guard_results
        (run_id,attack_id,original_id,target_model,dataset_type,language,prompt,target_response,
         guard_model,model_digest,guard_options,guard_verdict,hazard_categories,raw_guard_response,
         error,was_blocked,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
        (run_id, attack['attack_id'], attack['original_id'], model, dataset_type, attack['language'],
         attack['prompt'], response, guard_model, digest, json.dumps(options, sort_keys=True),
         result.verdict, json.dumps(result.categories), result.raw, result.error,
         int(result.verdict == 'unsafe'), datetime.now(timezone.utc).isoformat()))


def fpr(conn, run_id):
    """Latest evaluation per prompt within the run; errors excluded from denominator."""
    rows = conn.execute('''SELECT language,
       SUM(guard_verdict='unsafe'), SUM(guard_verdict='safe'), SUM(guard_verdict='error')
       FROM input_guard_results g WHERE run_id=? AND dataset_type='benign'
       AND id=(SELECT MAX(id) FROM input_guard_results x WHERE x.run_id=g.run_id
               AND x.attack_id=g.attack_id)
       GROUP BY language ORDER BY language''', (run_id,)).fetchall()
    def entry(language, fp, tn, errors):
        return dict(language=language, fp=fp, tn=tn, errors=errors,
                    fpr_percent=100 * fp / (fp + tn) if fp + tn else None)
    result = [entry(*row) for row in rows]
    result.insert(0, entry('overall', sum(r[1] for r in rows), sum(r[2] for r in rows), sum(r[3] for r in rows)))
    return result
