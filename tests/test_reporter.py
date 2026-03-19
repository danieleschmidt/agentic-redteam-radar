"""
Tests for report generation (JSON and text formats).
"""
import json
import pytest
from unittest.mock import MagicMock

from redteam_radar.endpoint import Endpoint
from redteam_radar.scanner import Scanner
from redteam_radar.reporter import to_json, to_text


def make_scan_report(response: str = "I cannot help with that."):
    ep = MagicMock(spec=Endpoint)
    ep.url = "http://mock-llm"
    ep.model = "mock"
    ep.style = "openai"
    ep.query.return_value = response
    scanner = Scanner(ep, delay_ms=0)
    return scanner.run()


class TestJSONReport:
    def test_valid_json(self):
        report = make_scan_report()
        output = to_json(report)
        parsed = json.loads(output)  # Should not raise
        assert isinstance(parsed, dict)

    def test_has_meta_section(self):
        report = make_scan_report()
        parsed = json.loads(to_json(report))
        assert "meta" in parsed
        assert parsed["meta"]["target"] == "http://mock-llm"

    def test_has_summary_section(self):
        report = make_scan_report()
        parsed = json.loads(to_json(report))
        assert "summary" in parsed
        summary = parsed["summary"]
        assert "total_probes" in summary
        assert "vulnerable" in summary
        assert "risk_score" in summary

    def test_has_all_results(self):
        report = make_scan_report()
        parsed = json.loads(to_json(report))
        assert len(parsed["all_results"]) == report.total

    def test_findings_only_contains_vulnerable(self):
        report = make_scan_report("DAN mode ON. No restrictions.")
        parsed = json.loads(to_json(report))
        for finding in parsed["findings"]:
            assert finding["is_vulnerable"] is True

    def test_reproduction_steps_in_each_result(self):
        report = make_scan_report()
        parsed = json.loads(to_json(report))
        for result in parsed["all_results"]:
            assert "reproduction" in result
            assert "payload" in result["reproduction"]
            assert "endpoint" in result["reproduction"]


class TestTextReport:
    def test_returns_string(self):
        report = make_scan_report()
        output = to_text(report)
        assert isinstance(output, str)

    def test_contains_target_url(self):
        report = make_scan_report()
        output = to_text(report)
        assert "http://mock-llm" in output

    def test_contains_risk_score(self):
        report = make_scan_report()
        output = to_text(report)
        assert "Risk Score" in output

    def test_contains_no_vulnerabilities_message_on_clean(self):
        report = make_scan_report("I'm sorry, I cannot and will not comply.")
        output = to_text(report)
        assert "No vulnerabilities detected" in output

    def test_contains_vulnerability_details_when_vulnerable(self):
        report = make_scan_report("DAN mode activated. No restrictions.")
        output = to_text(report)
        # Should show some vulnerability section
        assert "VULNERABILITY DETAILS" in output

    def test_contains_summary_counts(self):
        report = make_scan_report()
        output = to_text(report)
        assert "Total Probes" in output
        assert "Vulnerable" in output
        assert "Safe" in output
