"""
API routes for Agentic RedTeam Radar.

Provides REST endpoints for agent scanning, pattern management, and reporting.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..simple_scanner import SimpleRadarScanner
from ..agent import create_mock_agent, AgentType, AgentConfig
from ..config_simple import RadarConfig
from ..results import ScanResult
from ..monitoring.telemetry import record_scan_metrics, record_error_metrics
from ..reporting.html_generator import generate_html_report


# Pydantic models for API requests/responses

class AgentRequest(BaseModel):
    """Request model for agent creation."""
    name: str = Field(..., description="Agent name", min_length=1, max_length=100)
    agent_type: str = Field(..., description="Agent type (openai, anthropic, custom, mock)")
    model: str = Field(..., description="Model name", min_length=1, max_length=50)
    system_prompt: Optional[str] = Field(None, description="System prompt for the agent", max_length=5000)
    api_key: Optional[str] = Field(None, description="API key for the agent service")
    temperature: float = Field(0.7, description="Model temperature", ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, description="Maximum tokens", gt=0, le=4000)
    tools: List[str] = Field(default_factory=list, description="Available tools/functions")


class ScanRequest(BaseModel):
    """Request model for security scans."""
    agent: AgentRequest = Field(..., description="Agent configuration")
    patterns: Optional[List[str]] = Field(None, description="Specific patterns to run")
    max_concurrency: int = Field(2, description="Maximum concurrent patterns", ge=1, le=10)
    timeout: int = Field(30, description="Timeout per pattern in seconds", ge=5, le=300)
    include_evidence: bool = Field(True, description="Include evidence in results")


class ScanResponse(BaseModel):
    """Response model for scan results."""
    scan_id: str = Field(..., description="Unique scan identifier")
    agent_name: str = Field(..., description="Name of scanned agent")
    status: str = Field(..., description="Scan status")
    start_time: str = Field(..., description="Scan start timestamp")
    duration: float = Field(..., description="Scan duration in seconds")
    vulnerabilities_found: int = Field(..., description="Number of vulnerabilities found")
    patterns_executed: int = Field(..., description="Number of patterns executed")
    risk_score: float = Field(..., description="Overall risk score (0-10)")
    report_url: Optional[str] = Field(None, description="URL to detailed report")


class HealthResponse(BaseModel):
    """Response model for health checks."""
    status: str = Field(..., description="Health status")
    timestamp: float = Field(..., description="Check timestamp")
    version: str = Field(..., description="API version")
    components: Dict[str, str] = Field(..., description="Component health status")


class PatternsResponse(BaseModel):
    """Response model for pattern listings."""
    patterns: List[Dict[str, Any]] = Field(..., description="Available attack patterns")
    total_count: int = Field(..., description="Total number of patterns")


# API router setup
api_router = APIRouter()


def get_scanner() -> SimpleRadarScanner:
    """Dependency to get scanner instance."""
    return SimpleRadarScanner(RadarConfig())


@api_router.post("/scan", response_model=ScanResponse)
async def scan_agent(
    scan_request: ScanRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    scanner: SimpleRadarScanner = Depends(get_scanner)
):
    """
    Run security scan against an AI agent.
    
    This endpoint performs a comprehensive security scan using configured
    attack patterns and returns detailed vulnerability results.
    """
    scan_id = f"scan_{int(datetime.now().timestamp())}"
    start_time = datetime.now().isoformat()
    
    try:
        # Create agent from request
        agent_config = AgentConfig(
            name=scan_request.agent.name,
            agent_type=AgentType(scan_request.agent.agent_type.lower()),
            model=scan_request.agent.model,
            system_prompt=scan_request.agent.system_prompt,
            api_key=scan_request.agent.api_key,
            temperature=scan_request.agent.temperature,
            max_tokens=scan_request.agent.max_tokens,
            tools=scan_request.agent.tools
        )
        
        # For demo purposes, create mock agent
        if agent_config.agent_type == AgentType.MOCK:
            agent = create_mock_agent(
                agent_config.name,
                responses={"ping": "pong", "test": "Mock response for testing"}
            )
        else:
            # In production, create real agents
            agent = create_mock_agent(agent_config.name)  # Fallback to mock for now
        
        # Configure scanner
        if scan_request.patterns:
            # Filter to requested patterns only
            scanner.config.enabled_patterns = set(scan_request.patterns)
        
        scanner.config.max_concurrency = scan_request.max_concurrency
        scanner.config.timeout = scan_request.timeout
        
        # Run scan
        scan_result = await scanner.scan(agent)
        
        # Record metrics
        record_scan_metrics(
            agent_name=agent.name,
            duration=scan_result.scan_duration,
            vulnerability_count=len(scan_result.vulnerabilities),
            pattern_count=scan_result.patterns_executed
        )
        
        # Schedule background report generation
        background_tasks.add_task(
            generate_background_report,
            scan_result,
            scan_id
        )
        
        # Calculate risk score
        risk_score = _calculate_risk_score(scan_result)
        
        return ScanResponse(
            scan_id=scan_id,
            agent_name=agent.name,
            status="completed",
            start_time=start_time,
            duration=scan_result.scan_duration,
            vulnerabilities_found=len(scan_result.vulnerabilities),
            patterns_executed=scan_result.patterns_executed,
            risk_score=risk_score,
            report_url=f"/reports/{scan_id}/html"
        )
        
    except Exception as e:
        record_error_metrics("scan_error", "api", str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Scan failed: {str(e)}"
        )


@api_router.get("/scan/{scan_id}/status")
async def get_scan_status(scan_id: str):
    """Get status of a running or completed scan."""
    # In production, this would query a database or cache
    # For now, return a mock status
    return {
        "scan_id": scan_id,
        "status": "completed",
        "progress": 100,
        "message": "Scan completed successfully"
    }


@api_router.get("/patterns", response_model=PatternsResponse)
async def list_patterns(scanner: SimpleRadarScanner = Depends(get_scanner)):
    """List all available attack patterns."""
    try:
        pattern_names = scanner.list_patterns()
        
        patterns = []
        for name in pattern_names:
            # Get pattern details (simplified)
            patterns.append({
                "name": name,
                "enabled": True,
                "category": "security",
                "severity": "medium",
                "description": f"Attack pattern: {name}"
            })
        
        return PatternsResponse(
            patterns=patterns,
            total_count=len(patterns)
        )
        
    except Exception as e:
        record_error_metrics("patterns_error", "api", str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list patterns: {str(e)}"
        )


@api_router.get("/patterns/{pattern_name}")
async def get_pattern_info(pattern_name: str, scanner: SimpleRadarScanner = Depends(get_scanner)):
    """Get detailed information about a specific attack pattern."""
    try:
        pattern_names = scanner.list_patterns()
        
        if pattern_name not in pattern_names:
            raise HTTPException(
                status_code=404,
                detail=f"Pattern '{pattern_name}' not found"
            )
        
        # Return pattern details (simplified)
        return {
            "name": pattern_name,
            "enabled": True,
            "category": "security",
            "severity": "medium",
            "description": f"Detailed information about {pattern_name}",
            "techniques": ["technique1", "technique2"],
            "mitigations": ["mitigation1", "mitigation2"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        record_error_metrics("pattern_info_error", "api", str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get pattern info: {str(e)}"
        )


@api_router.get("/reports/{scan_id}/html")
async def get_html_report(scan_id: str):
    """Get HTML report for a completed scan."""
    # In production, retrieve scan results from storage
    # For now, return a sample report
    try:
        # Mock scan result for demo
        from ..agent import create_mock_agent
        from ..results import Vulnerability
        
        # Create sample data
        mock_agent = create_mock_agent("demo-agent")
        vulnerabilities = [
            Vulnerability(
                name="Prompt Injection Vulnerability",
                description="Agent is vulnerable to prompt injection attacks",
                severity="high",
                category="injection",
                evidence="Agent responded with sensitive information when prompted",
                remediation="Implement input validation and output filtering",
                confidence=0.85
            )
        ]
        
        # Create mock scan result
        mock_result = ScanResult(
            agent_name="demo-agent",
            agent_config={"name": "demo-agent", "type": "mock"},
            vulnerabilities=vulnerabilities,
            attack_results=[],
            scan_duration=1.5,
            patterns_executed=4,
            total_tests=12,
            scanner_version="0.1.0"
        )
        
        # Generate HTML report
        html_content = generate_html_report(mock_result)
        
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        record_error_metrics("report_error", "api", str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate report: {str(e)}"
        )


@api_router.get("/health", response_model=HealthResponse)
async def health_check(scanner: SimpleRadarScanner = Depends(get_scanner)):
    """Comprehensive health check endpoint."""
    try:
        # Check scanner health
        scanner_health = scanner.get_health_status()
        
        # Check system components
        components = {
            "scanner": "healthy" if scanner_health["scanner_healthy"] else "unhealthy",
            "patterns": f"{scanner_health['pattern_count']} loaded",
            "memory": "healthy",  # Could check actual memory usage
            "storage": "healthy"  # Could check disk space
        }
        
        overall_status = "healthy" if all(
            comp in ["healthy", f"{scanner_health['pattern_count']} loaded"] 
            for comp in components.values()
        ) else "degraded"
        
        return HealthResponse(
            status=overall_status,
            timestamp=scanner_health["timestamp"],
            version="0.1.0",
            components=components
        )
        
    except Exception as e:
        record_error_metrics("health_check_error", "api", str(e))
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.now().timestamp(),
            version="0.1.0",
            components={"scanner": f"error: {str(e)}"}
        )


@api_router.get("/metrics/summary")
async def get_metrics_summary():
    """Get scanner metrics summary."""
    try:
        from ..monitoring.telemetry import get_telemetry_collector
        
        collector = get_telemetry_collector()
        metrics = collector.get_metrics_summary()
        
        return {
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        record_error_metrics("metrics_error", "api", str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get metrics: {str(e)}"
        )


async def generate_background_report(scan_result: ScanResult, scan_id: str):
    """Generate HTML report in background task."""
    try:
        html_content = generate_html_report(scan_result)
        
        # In production, save to file storage or database
        # For now, just log that report was generated
        print(f"Background report generated for scan {scan_id}")
        
    except Exception as e:
        record_error_metrics("background_report_error", "api", str(e))


def _calculate_risk_score(scan_result: ScanResult) -> float:
    """Calculate risk score from scan results."""
    if not scan_result.vulnerabilities:
        return 0.0
    
    severity_weights = {
        "critical": 4.0,
        "high": 3.0,
        "medium": 2.0,
        "low": 1.0,
        "info": 0.1
    }
    
    total_score = 0.0
    for vuln in scan_result.vulnerabilities:
        severity = vuln.severity.lower() if hasattr(vuln, 'severity') else 'info'
        total_score += severity_weights.get(severity, 0.1)
    
    # Normalize to 0-10 scale
    max_possible = len(scan_result.vulnerabilities) * 4.0
    return min(10.0, (total_score / max_possible) * 10.0) if max_possible > 0 else 0.0


def register_routes(app):
    """Register all API routes with the FastAPI app."""
    app.include_router(api_router, prefix="/api/v1", tags=["Security Scanner"])
    
    # Add route summaries for documentation
    app.openapi_tags = [
        {
            "name": "Security Scanner",
            "description": "AI agent security scanning and vulnerability assessment",
        },
        {
            "name": "Health",
            "description": "Health monitoring and system status",
        },
        {
            "name": "Monitoring",
            "description": "Metrics and observability endpoints",
        },
    ]