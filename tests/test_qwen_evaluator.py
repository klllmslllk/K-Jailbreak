"""Qwen 평가기의 응답 검증과 요청 구성을 검증한다."""

import json
import sys
import types
import unittest
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from evalutor.qwen_evaluator import EvaluationError, evaluate, parse_result
from evalutor.runner import run


class QwenEvaluatorTest(unittest.TestCase):
    def test_output_validation(self):
        self.assertEqual(parse_result(" SUCCESS\n"), 1)
        self.assertEqual(parse_result("FAILURE"), 0)
        for value in ("", "success", "SUCCESS FAILURE", "SUCCESS 이유", "{}"):
            with self.subTest(value=value), self.assertRaises(EvaluationError):
                parse_result(value)

    def test_request_and_retry(self):
        prompt = types.ModuleType("evalutor.system_prompt")
        prompt.SYSTEM_PROMPT = "test policy"
        bad = Mock(status_code=200, json=lambda: {"done": True, "message": {"content": "invalid"}})
        good = Mock(status_code=200, json=lambda: {"done": True, "message": {"content": "FAILURE", "thinking": "ignored"}})
        with patch.dict(sys.modules, {"evalutor.system_prompt": prompt}), patch("evalutor.qwen_evaluator.requests.post", side_effect=[bad, good]) as post:
            self.assertEqual(evaluate('한국어 "\n', "응답 [RESPONSE]"), 0)
            self.assertEqual(post.call_count, 2)
            payload = post.call_args.kwargs["json"]
            self.assertEqual(payload["model"], "qwen3.5:9b")
            self.assertEqual(payload["messages"][0]["content"], "test policy")
            self.assertEqual(json.loads(payload["messages"][1]["content"]), {"attack_prompt": '한국어 "\n', "response": "응답 [RESPONSE]"})
            self.assertEqual(payload["options"]["seed"], 42)
            self.assertEqual(payload["options"]["temperature"], 0)
            self.assertFalse(payload["stream"])
            self.assertTrue(payload["think"])
            self.assertEqual(payload["options"]["num_predict"], 4096)

    def test_timeout_retries_and_error(self):
        prompt = types.ModuleType("evalutor.system_prompt")
        prompt.SYSTEM_PROMPT = "test policy"
        with patch.dict(sys.modules, {"evalutor.system_prompt": prompt}), patch("evalutor.qwen_evaluator.requests.post", side_effect=requests.Timeout("timeout")) as post:
            with self.assertRaises(EvaluationError):
                evaluate("q", "r")
            self.assertEqual(post.call_count, 3)

    def test_non_retryable_api_error(self):
        prompt = types.ModuleType("evalutor.system_prompt")
        prompt.SYSTEM_PROMPT = "test policy"
        missing = Mock(status_code=404, text="model not found")
        with patch.dict(sys.modules, {"evalutor.system_prompt": prompt}), patch("evalutor.qwen_evaluator.requests.post", return_value=missing) as post:
            with self.assertRaisesRegex(EvaluationError, "404"):
                evaluate("q", "r")
            self.assertEqual(post.call_count, 1)

    def test_invalid_response_retries_and_length_error(self):
        prompt = types.ModuleType("evalutor.system_prompt")
        prompt.SYSTEM_PROMPT = "test policy"
        replies = [
            Mock(status_code=200, json=lambda: {"done": True, "message": {"content": "SUCCESS FAILURE"}}),
            Mock(status_code=200, json=lambda: {"done": True, "message": {"content": ""}}),
            Mock(status_code=200, json=lambda: {"done": True, "done_reason": "length", "message": {"content": "SUCCESS"}}),
        ]
        with patch.dict(sys.modules, {"evalutor.system_prompt": prompt}), patch("evalutor.qwen_evaluator.requests.post", side_effect=replies) as post:
            with self.assertRaisesRegex(EvaluationError, "done_reason='length'"):
                evaluate("q", "r")
            self.assertEqual(post.call_count, 3)
            self.assertEqual(post.call_args_list[0].kwargs["json"], post.call_args_list[-1].kwargs["json"])

    def test_system_prompt_identity(self):
        from hashlib import sha256
        from evalutor.system_prompt import SYSTEM_PROMPT
        self.assertEqual(sha256(SYSTEM_PROMPT.encode('utf-8')).hexdigest(), '8a825b2db66eb20016aa9a7b91622d5e65956fe50c89e192fbead11faea82a94')

    def test_output_limit_is_not_retried(self):
        prompt = types.ModuleType("evalutor.system_prompt")
        prompt.SYSTEM_PROMPT = "test policy"
        reply = Mock(status_code=200, json=lambda: {
            "done": True, "done_reason": "length", "eval_count": 4096,
            "message": {"content": ""},
        })
        with patch.dict(sys.modules, {"evalutor.system_prompt": prompt}), patch("evalutor.qwen_evaluator.requests.post", return_value=reply) as post:
            with self.assertRaisesRegex(EvaluationError, "done_reason='length'"):
                evaluate("q", "r")
            self.assertEqual(post.call_count, 1)

    def test_retryable_http_error_then_success(self):
        prompt = types.ModuleType("evalutor.system_prompt")
        prompt.SYSTEM_PROMPT = "test policy"
        bad = Mock(status_code=503)
        bad.raise_for_status.side_effect = requests.HTTPError("unavailable")
        good = Mock(status_code=200, json=lambda: {"done": True, "message": {"content": " SUCCESS \n"}})
        with patch.dict(sys.modules, {"evalutor.system_prompt": prompt}), patch("evalutor.qwen_evaluator.requests.post", side_effect=[bad, good]) as post:
            self.assertEqual(evaluate("q", "r"), 1)
            self.assertEqual(post.call_count, 2)


    def test_database_resume_and_dataset_filter(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, guard, output = root / 'source.db', root / 'guard.db', root / 'eval.db'
            with closing(sqlite3.connect(source)) as conn, conn:
                conn.execute('CREATE TABLE results (id INTEGER PRIMARY KEY, run_id TEXT, attack_id TEXT, original_id INTEGER, model TEXT, language TEXT, prompt TEXT, goal TEXT, response TEXT, defense_module TEXT)')
                conn.executemany('INSERT INTO results VALUES (?,?,?,?,?,?,?,?,?,?)', [
                    (1, 'attack', 'a', 1, 'target', '한국어', '공격 원문', '원본 목표', '응답', None),
                    (2, 'benign', 'b', 2, 'target', '한국어', '정상 질문', '목표', '정상 응답', None),
                    (3, 'unknown', 'c', 3, 'target', '한국어', '미확인', '목표', '응답', None),
                ])
            with closing(sqlite3.connect(guard)) as conn, conn:
                conn.execute('CREATE TABLE input_guard_runs (run_id TEXT PRIMARY KEY, dataset_type TEXT)')
                conn.executemany('INSERT INTO input_guard_runs VALUES (?,?)', [('attack', 'attack'), ('benign', 'benign')])
            calls = []
            def judge(question, response):
                calls.append((question, response))
                return 1
            with patch('evalutor.runner.model_identity', return_value=('digest', 'version')):
                self.assertEqual(run(source, output, guard, judge=judge)['completed'], 1)
                self.assertEqual(run(source, output, guard, judge=judge)['skipped'], 1)
            self.assertEqual(calls, [('공격 원문', '응답')])
            with closing(sqlite3.connect(output)) as conn:
                self.assertEqual(conn.execute('SELECT evaluator_name, question_source, score, success, status FROM evaluations').fetchall(), [('qwen_binary', 'results.prompt', None, 1, 'ok')])

    def test_database_failure_is_retried_only_with_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, guard, output = root / 'source.db', root / 'guard.db', root / 'eval.db'
            with closing(sqlite3.connect(source)) as conn, conn:
                conn.execute('CREATE TABLE results (id INTEGER PRIMARY KEY, run_id TEXT, attack_id TEXT, original_id INTEGER, model TEXT, language TEXT, prompt TEXT, goal TEXT, response TEXT, defense_module TEXT)')
                conn.execute('INSERT INTO results VALUES (1,?,?,?,?,?,?,?,?,?)', ('r', 'a', 1, 'model', 'en', 'question', 'goal', 'answer', None))
            with closing(sqlite3.connect(guard)) as conn, conn:
                conn.execute('CREATE TABLE input_guard_runs (run_id TEXT PRIMARY KEY, dataset_type TEXT)')
                conn.execute('INSERT INTO input_guard_runs VALUES (?,?)', ('r', 'attack'))
            def broken(*args):
                raise EvaluationError('offline')
            with patch('evalutor.runner.model_identity', return_value=('digest', 'version')):
                self.assertEqual(run(source, output, guard, judge=broken)['failed'], 1)
                self.assertEqual(run(source, output, guard, judge=lambda *a: 0)['skipped'], 1)
                self.assertEqual(run(source, output, guard, resume=True, judge=lambda *a: 0)['completed'], 1)
            with closing(sqlite3.connect(output)) as conn:
                self.assertEqual(conn.execute('SELECT status,success FROM evaluations ORDER BY id').fetchall(), [('error', None), ('ok', 0)])


if __name__ == "__main__":
    unittest.main()
