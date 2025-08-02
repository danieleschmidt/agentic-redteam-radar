"""Testing utilities and helper functions."""

import json
import time
import asyncio
from typing import Dict, List, Any, Optional, Callable
from unittest.mock import Mock, AsyncMock
from pathlib import Path


class MockResponse:
    """Mock response object for API calls."""
    
    def __init__(self, content: str, status_code: int = 200, headers: Optional[Dict] = None):
        self.content = content
        self.text = content
        self.status_code = status_code
        self.headers = headers or {}
        
    def json(self):
        """Return JSON response."""
        return json.loads(self.content)


class AgentTestHelper:
    """Helper class for agent testing utilities."""
    
    @staticmethod
    def create_mock_agent(name: str = "test-agent", **kwargs) -> Mock:
        """Create a mock agent with standard methods."""
        agent = Mock()
        agent.name = name
        agent.model = kwargs.get("model", "gpt-4")
        agent.system_prompt = kwargs.get("system_prompt", "You are a test agent.")
        agent.tools = kwargs.get("tools", [])
        
        # Mock the query method
        agent.query = AsyncMock()
        agent.query.return_value = "Mock response from test agent"
        
        return agent
    
    @staticmethod
    def create_mock_scanner(**kwargs) -> Mock:
        """Create a mock scanner with standard methods."""
        scanner = Mock()
        scanner.scan = AsyncMock()
        scanner.patterns = kwargs.get("patterns", [])
        
        return scanner
    
    @staticmethod
    def assert_vulnerability_detected(results: Dict, vulnerability_type: str) -> bool:
        """Assert that a specific vulnerability type was detected."""
        if "vulnerabilities" not in results:
            return False
            
        for vuln in results["vulnerabilities"]:
            if vuln.get("type") == vulnerability_type:
                return True
                
        return False
    
    @staticmethod
    def count_vulnerabilities(results: Dict, severity: Optional[str] = None) -> int:
        """Count vulnerabilities, optionally filtered by severity."""
        if "vulnerabilities" not in results:
            return 0
            
        vulns = results["vulnerabilities"]
        if severity:
            vulns = [v for v in vulns if v.get("severity") == severity]
            
        return len(vulns)


class PerformanceTestHelper:
    """Helper class for performance testing."""
    
    @staticmethod
    def measure_execution_time(func: Callable, *args, **kwargs) -> tuple:
        """Measure execution time of a function."""
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        return result, end_time - start_time
    
    @staticmethod
    async def measure_async_execution_time(func: Callable, *args, **kwargs) -> tuple:
        """Measure execution time of an async function."""
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        
        return result, end_time - start_time
    
    @staticmethod
    def run_concurrent_tests(func: Callable, test_data: List, max_workers: int = 5) -> List:
        """Run tests concurrently and return results."""
        async def run_tests():
            semaphore = asyncio.Semaphore(max_workers)
            
            async def run_single_test(data):
                async with semaphore:
                    return await func(data)
            
            tasks = [run_single_test(data) for data in test_data]
            return await asyncio.gather(*tasks)
        
        return asyncio.run(run_tests())


class ReportTestHelper:
    """Helper class for testing report generation."""
    
    @staticmethod
    def validate_report_structure(report: Dict) -> bool:
        """Validate that a report has the expected structure."""
        required_fields = [
            "scan_id",
            "timestamp", 
            "agent_info",
            "vulnerabilities",
            "summary",
            "recommendations"
        ]
        
        return all(field in report for field in required_fields)
    
    @staticmethod
    def validate_vulnerability_entry(vuln: Dict) -> bool:
        """Validate that a vulnerability entry has required fields."""
        required_fields = [
            "id",
            "type",
            "severity",
            "description",
            "evidence",
            "remediation"
        ]
        
        return all(field in vuln for field in required_fields)
    
    @staticmethod
    def create_test_report(num_vulnerabilities: int = 3) -> Dict:
        """Create a test report with specified number of vulnerabilities."""
        return {
            "scan_id": "test-scan-123",
            "timestamp": "2025-01-01T00:00:00Z",
            "agent_info": {
                "name": "test-agent",
                "model": "gpt-4",
                "version": "1.0.0"
            },
            "vulnerabilities": [
                {
                    "id": f"vuln-{i}",
                    "type": "prompt_injection",
                    "severity": "high",
                    "description": f"Test vulnerability {i}",
                    "evidence": f"Test evidence {i}",
                    "remediation": f"Test remediation {i}"
                }
                for i in range(num_vulnerabilities)
            ],
            "summary": {
                "total_vulnerabilities": num_vulnerabilities,
                "high_severity": num_vulnerabilities,
                "medium_severity": 0,
                "low_severity": 0
            },
            "recommendations": [
                "Implement input validation",
                "Add output filtering",
                "Review system prompts"
            ]
        }


class FileTestHelper:
    """Helper class for file-based testing."""
    
    @staticmethod
    def create_temp_config(tmp_path: Path, config: Dict) -> Path:
        """Create a temporary configuration file."""
        config_file = tmp_path / "test_config.json"
        config_file.write_text(json.dumps(config, indent=2))
        return config_file
    
    @staticmethod
    def create_temp_report(tmp_path: Path, report: Dict) -> Path:
        """Create a temporary report file."""
        report_file = tmp_path / "test_report.json"
        report_file.write_text(json.dumps(report, indent=2))
        return report_file
    
    @staticmethod
    def validate_json_file(file_path: Path) -> bool:
        """Validate that a file contains valid JSON."""
        try:
            json.loads(file_path.read_text())
            return True
        except (json.JSONDecodeError, FileNotFoundError):
            return False


def wait_for_condition(condition_func: Callable, timeout: float = 10.0, interval: float = 0.1) -> bool:
    """Wait for a condition to become true within a timeout."""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if condition_func():
            return True
        time.sleep(interval)
    
    return False


async def wait_for_async_condition(condition_func: Callable, timeout: float = 10.0, interval: float = 0.1) -> bool:
    """Wait for an async condition to become true within a timeout."""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if await condition_func():
            return True
        await asyncio.sleep(interval)
    
    return False