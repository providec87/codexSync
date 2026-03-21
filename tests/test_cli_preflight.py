from __future__ import annotations

from unittest.mock import patch
import unittest

from codexsync.app import PreflightCheckResult, PreflightReport
from codexsync.cli import main


class CliPreflightTests(unittest.TestCase):
    @patch("codexsync.cli.run_preflight", return_value=PreflightReport(checks=[PreflightCheckResult("x", "PASS", "ok")]))
    @patch("codexsync.cli.print_preflight_report")
    def test_doctor_returns_ok_on_success(self, print_report, _run_preflight) -> None:
        code = main(["-c", "config.toml", "doctor"])
        self.assertEqual(code, 0)
        print_report.assert_called_once()

    @patch("codexsync.cli.run_preflight", return_value=PreflightReport(checks=[PreflightCheckResult("x", "FAIL", "bad")]))
    @patch("codexsync.cli.print_preflight_report")
    def test_preflight_returns_failsafe_code_on_failure(self, print_report, _run_preflight) -> None:
        code = main(["-c", "config.toml", "preflight"])
        self.assertEqual(code, 5)
        print_report.assert_called_once()


if __name__ == "__main__":
    unittest.main()
