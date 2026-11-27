"""원본 응답을 읽고 평가 결과를 SQLite에 저장하고 집계한다."""
import json
import sqlite3
from pathlib import Path


def source_connection(path):
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    conn = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def connect(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS evaluations (
      id INTEGER PRIMARY KEY, source_database TEXT NOT NULL, source_result_id INTEGER NOT NULL,
      source_run_id TEXT, attack_id TEXT, original_id INTEGER, target_model TEXT, language TEXT,
      defense_module TEXT, evaluator_name TEXT NOT NULL, evaluator_version TEXT,
      judge_model TEXT, judge_configuration TEXT NOT NULL, question_source TEXT NOT NULL,
      response_source TEXT NOT NULL, input_hash TEXT NOT NULL, config_hash TEXT NOT NULL,
      threshold REAL, score REAL, success INTEGER, status TEXT NOT NULL, reason TEXT,
      raw_result TEXT, error TEXT, started_at TEXT NOT NULL, completed_at TEXT NOT NULL
    );
    CREATE UNIQUE INDEX IF NOT EXISTS unique_success ON evaluations
      (source_database, source_result_id, input_hash, config_hash, threshold)
      WHERE status = 'ok';
    CREATE UNIQUE INDEX IF NOT EXISTS unique_qwen_success ON evaluations
      (source_database, source_result_id, input_hash, config_hash)
      WHERE status = 'ok' AND evaluator_name = 'qwen_binary';
    """)
    return conn


def source_rows(conn, run_id=None):
    query = "SELECT id, run_id, attack_id, original_id, model, language, prompt, goal, response, defense_module FROM results"
    params = []
    if run_id is not None:
        query += " WHERE run_id = ?"
        params.append(run_id)
    query += " ORDER BY id"
    return conn.execute(query, params)


def previous(conn, source, row_id, input_hash, config_hash, threshold=None):
    sql = "SELECT * FROM evaluations WHERE source_database=? AND source_result_id=? AND input_hash=? AND config_hash=? AND status='ok'"
    args = [source, row_id, input_hash, config_hash]
    if threshold is not None:
        sql += " AND threshold=?"
        args.append(threshold)
    return conn.execute(sql + " ORDER BY id DESC LIMIT 1", args).fetchone()


def save(conn, source, row, input_hash, config_hash, config, result, started, completed, question_source='results.prompt'):
    with conn:
        conn.execute("""INSERT INTO evaluations (source_database,source_result_id,source_run_id,attack_id,original_id,target_model,language,defense_module,evaluator_name,evaluator_version,judge_model,judge_configuration,question_source,response_source,input_hash,config_hash,threshold,score,success,status,reason,raw_result,error,started_at,completed_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
          source, row['id'], row['run_id'], row['attack_id'], row['original_id'], row['model'], row['language'], row['defense_module'], result.evaluator_name, result.evaluator_version, result.judge_model, json.dumps(config, ensure_ascii=False, sort_keys=True), question_source, 'results.response (final; defense state not inferred)', input_hash, config_hash, result.threshold, result.score, None if result.success is None else int(result.success), result.status, result.reason, json.dumps(result.metadata, ensure_ascii=False), result.error, started, completed))


def summary(conn, config_hash, threshold, run_id=None):
    sql = """SELECT evaluator_name,target_model,language,defense_module,source_run_id, COUNT(*) valid, SUM(success) successes FROM evaluations WHERE status='ok' AND config_hash=? AND threshold IS ?"""
    args = [config_hash, threshold]
    if run_id is not None:
        sql += " AND source_run_id=?"
        args.append(run_id)
    return conn.execute(sql + " GROUP BY evaluator_name,target_model,language,defense_module,source_run_id", args).fetchall()
