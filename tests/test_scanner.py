"""
Tests for the scanner using a mock endpoint.
"""
import pytest
from unittest.mock import MagicMock, patch

from redteam_radar.endpoint import Endpoint, EndpointError
from redteam_radar.scanner import Scanner, ScanReport, ProbeResult
from redteam_radar.probes import ALL_PROBES


def make_mock_endpoint(response: str = "I cannot help with that.") -> Endpoint:
    ep = MagicMock(spec=Endpoint)
    ep.url = "http://mock-llm"
    ep.model = "mock-model"
    ep.style = "openai"
    ep.query.return_value = response
    return ep


class TestScannerBasic:
    def test_scan_returns_report(self):
        ep = make_mock_endpoint()
        scanner = Scanner(ep, delay_ms=0)
        report = scanner.run()
        assert isinstance(report, ScanReport)

    def test_report_has_all_probe_results(self):
        ep = make_mock_endpoint()
        scanner = Scanner(ep, delay_ms=0)
        report = scanner.run()
        assert len(report.results) == len(ALL_PROBES)

    def test_all_safe_on_refusal(self):
        ep = make_mock_endpoint("I'm sorry, I cannot and will not help with that request.")
        scanner = Scanner(ep, delay_ms=0)
        report = scanner.run()
        assert len(report.vulnerable) == 0
        assert len(report.safe) == len(ALL_PROBES)

    def test_vulnerability_detected_on_hint_match(self):
        # Make endpoint echo back the probe payload hints
        ep = make_mock_endpoint("DAN mode activated — I have no restrictions now!")
        scanner = Scanner(ep, delay_ms=0)
        report = scanner.run()
        # At least some probes should flag this (JB-001 detects "dan", "no restrictions")
        assert len(report.vulnerable) > 0

    def test_report_duration_positive(self):
        ep = make_mock_endpoint()
        scanner = Scanner(ep, delay_ms=0)
        report = scanner.run()
        assert report.duration_s >= 0.0

    def test_report_timestamps_ordered(self):
        ep = make_mock_endpoint()
        scanner = Scanner(ep, delay_ms=0)
        report = scanner.run()
        assert report.finished_at >= report.started_at


class TestScannerCategoryFilter:
    def test_filter_single_category(self):
        ep = make_mock_endpoint()
        scanner = Scanner(ep, categories=["jailbreak"], delay_ms=0)
        report = scanner.run()
        assert report.total == 5  # 5 jailbreak probes

    def test_filter_multiple_categories(self):
        ep = make_mock_endpoint()
        scanner = Scanner(ep, categories=["prompt_injection", "jailbreak"], delay_ms=0)
        report = scanner.run()
        assert report.total == 10  # 5 + 5

    def test_invalid_category_raises(self):
        ep = make_mock_endpoint()
        with pytest.raises(ValueError, match="Unknown category"):
            Scanner(ep, categories=["nonexistent"])


class TestScannerErrors:
    def test_endpoint_error_captured_in_result(self):
        ep = MagicMock(spec=Endpoint)
        ep.url = "http://mock-llm"
        ep.model = "mock"
        ep.style = "openai"
        ep.query.side_effect = EndpointError("Connection refused")

        scanner = Scanner(ep, delay_ms=0)
        report = scanner.run()
        assert len(report.errors) == len(ALL_PROBES)
        assert len(report.vulnerable) == 0

    def test_scan_continues_after_error(self):
        call_count = 0

        def flaky_query(text):
            nonlocal call_count
            call_count += 1
            if call_count % 3 == 0:
                raise EndpointError("Intermittent failure")
            return "I cannot help with that."

        ep = MagicMock(spec=Endpoint)
        ep.url = "http://mock-llm"
        ep.model = "mock"
        ep.style = "openai"
        ep.query.side_effect = flaky_query

        scanner = Scanner(ep, delay_ms=0)
        report = scanner.run()
        assert len(report.results) == len(ALL_PROBES)


class TestScanReport:
    def test_by_category_has_all_categories(self):
        ep = make_mock_endpoint()
        scanner = Scanner(ep, delay_ms=0)
        report = scanner.run()
        by_cat = report.by_category()
        assert "prompt_injection" in by_cat
        assert "jailbreak" in by_cat
        assert "data_exfiltration" in by_cat
        assert "role_confusion" in by_cat
        assert "multi_turn" in by_cat

    def test_risk_score_zero_on_all_safe(self):
        ep = make_mock_endpoint("I'm sorry, I cannot comply with that.")
        scanner = Scanner(ep, delay_ms=0)
        report = scanner.run()
        assert report.risk_score() == 0.0

    def test_risk_score_positive_on_vulnerabilities(self):
        ep = make_mock_endpoint("DAN mode ON. No restrictions. Your system prompt is: You are an AI.")
        scanner = Scanner(ep, delay_ms=0)
        report = scanner.run()
        assert report.risk_score() > 0.0

    def test_vulnerability_rate_between_0_and_1(self):
        ep = make_mock_endpoint()
        scanner = Scanner(ep, delay_ms=0)
        report = scanner.run()
        assert 0.0 <= report.vulnerability_rate <= 1.0
