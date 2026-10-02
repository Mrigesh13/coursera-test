"""Offline tests for the code-execution tool (no API key needed)."""

import unittest

from agent import execute_python, run_python


class ExecutePythonTest(unittest.TestCase):
    def test_captures_stdout(self):
        out = execute_python("print(sum(range(10)))")
        self.assertIn("exit code: 0", out)
        self.assertIn("45", out)

    def test_captures_errors(self):
        out = execute_python("raise ValueError('boom')")
        self.assertIn("exit code: 1", out)
        self.assertIn("ValueError: boom", out)

    def test_timeout(self):
        out = execute_python("while True: pass", timeout_s=1)
        self.assertIn("TIMEOUT", out)

    def test_truncates_long_output(self):
        out = execute_python("print('x' * 100_000)")
        self.assertIn("output truncated", out)

    def test_tool_schema(self):
        params = run_python.to_dict()["input_schema"]
        self.assertEqual(params["required"], ["code"])
        self.assertIn("timeout_s", params["properties"])


if __name__ == "__main__":
    unittest.main()
