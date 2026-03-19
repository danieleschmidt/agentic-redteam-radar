"""
Core scanner — runs all probes against an endpoint and collects results.
"""

import time
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict

from .endpoint import Endpoint, EndpointError
from .probes import Probe, ALL_PROBES, CATEGORIES
from .detector import DetectionResult, detect

logger = logging.getLogger("redteam_radar")


@dataclass
class ProbeResult:
    probe: Probe
    response: str
    detection: DetectionResult
    elapsed_ms: int
    error: Optional[str] = None

    @property
    def status(self) -> str:
        if self.error:
            return "ERROR"
        return "VULNERABLE" if self.detection.is_vulnerable else "SAFE"


@dataclass
class ScanReport:
    target_url: str
    model: str
    style: str
    started_at: float
    finished_at: float
    results: List[ProbeResult] = field(default_factory=list)

    @property
    def duration_s(self) -> float:
        return self.finished_at - self.started_at

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def vulnerable(self) -> List[ProbeResult]:
        return [r for r in self.results if r.detection.is_vulnerable and not r.error]

    @property
    def safe(self) -> List[ProbeResult]:
        return [r for r in self.results if not r.detection.is_vulnerable and not r.error]

    @property
    def errors(self) -> List[ProbeResult]:
        return [r for r in self.results if r.error]

    @property
    def vulnerability_rate(self) -> float:
        tested = self.total - len(self.errors)
        return len(self.vulnerable) / tested if tested > 0 else 0.0

    def by_category(self) -> Dict[str, Dict]:
        cats: Dict[str, Dict] = {}
        for r in self.results:
            cat = r.probe.category
            if cat not in cats:
                cats[cat] = {"total": 0, "vulnerable": 0, "safe": 0, "errors": 0}
            cats[cat]["total"] += 1
            if r.error:
                cats[cat]["errors"] += 1
            elif r.detection.is_vulnerable:
                cats[cat]["vulnerable"] += 1
            else:
                cats[cat]["safe"] += 1
        return cats

    def by_severity(self) -> Dict[str, int]:
        sev: Dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for r in self.vulnerable:
            sev[r.probe.severity] = sev.get(r.probe.severity, 0) + 1
        return sev

    def risk_score(self) -> float:
        """Weighted risk score 0–100."""
        weights = {"CRITICAL": 40, "HIGH": 20, "MEDIUM": 10, "LOW": 5}
        max_possible = sum(weights[p.severity] for p in ALL_PROBES)
        score = sum(weights[r.probe.severity] for r in self.vulnerable)
        return round(min(100.0, score / max_possible * 100), 1)


class Scanner:
    """
    Runs adversarial probes against a single LLM endpoint.

    Args:
        endpoint: Endpoint instance (URL, style, model, etc.)
        categories: Optional list of category names to limit scanning
        delay_ms: Milliseconds to wait between probes (avoids rate-limiting)
        verbose: Log each probe result
    """

    def __init__(
        self,
        endpoint: Endpoint,
        categories: Optional[List[str]] = None,
        delay_ms: int = 200,
        verbose: bool = False,
    ):
        self.endpoint = endpoint
        self.delay_ms = delay_ms
        self.verbose = verbose

        if categories:
            self.probes: List[Probe] = []
            for cat in categories:
                if cat not in CATEGORIES:
                    raise ValueError(f"Unknown category: {cat!r}. Valid: {list(CATEGORIES)}")
                self.probes.extend(CATEGORIES[cat])
        else:
            self.probes = ALL_PROBES

    def run(self) -> ScanReport:
        """Execute all probes and return a ScanReport."""
        report = ScanReport(
            target_url=self.endpoint.url,
            model=self.endpoint.model,
            style=self.endpoint.style,
            started_at=time.time(),
            finished_at=0.0,
        )

        logger.info(
            f"Starting scan: {len(self.probes)} probes against {self.endpoint.url} "
            f"(style={self.endpoint.style}, model={self.endpoint.model})"
        )

        for i, probe in enumerate(self.probes, 1):
            logger.debug(f"[{i}/{len(self.probes)}] {probe.id} — {probe.name}")

            t0 = time.perf_counter()
            error = None
            response = ""

            try:
                response = self.endpoint.query(probe.payload)
            except EndpointError as e:
                error = str(e)
                logger.warning(f"  Probe {probe.id} endpoint error: {e}")

            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            detection = detect(probe, response) if not error else DetectionResult(
                probe_id=probe.id,
                is_vulnerable=False,
                confidence=0.0,
                evidence=["Endpoint error — could not evaluate"],
            )

            result = ProbeResult(
                probe=probe,
                response=response,
                detection=detection,
                elapsed_ms=elapsed_ms,
                error=error,
            )
            report.results.append(result)

            if self.verbose:
                status_icon = "🔴" if result.status == "VULNERABLE" else ("⚠️" if result.status == "ERROR" else "✅")
                logger.info(
                    f"  {status_icon} [{result.status}] {probe.id}: {probe.name} "
                    f"(conf={detection.confidence:.2f}, {elapsed_ms}ms)"
                )

            if i < len(self.probes) and self.delay_ms > 0:
                time.sleep(self.delay_ms / 1000.0)

        report.finished_at = time.time()
        logger.info(
            f"Scan complete in {report.duration_s:.1f}s — "
            f"{len(report.vulnerable)} vulnerable / {report.total} total "
            f"(risk score: {report.risk_score()}/100)"
        )
        return report
