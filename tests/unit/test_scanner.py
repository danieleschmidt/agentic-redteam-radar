"""
Unit tests for RadarScanner core functionality.

Tests the main scanner engine including scan execution,
result aggregation, and error handling.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch

from agentic_redteam.scanner import RadarScanner, ScanProgress
from agentic_redteam.config import RadarConfig
from agentic_redteam.agent import Agent, AgentConfig, AgentType
from agentic_redteam.attacks.base import AttackPattern, AttackResult, AttackSeverity, AttackCategory
from agentic_redteam.results import ScanResult


class MockAgent(Agent):
    """Mock agent for testing."""
    
    def __init__(self, name="test_agent", responses=None):
        config = AgentConfig(
            name=name,
            agent_type=AgentType.CUSTOM,
            model="test-model"
        )
        super().__init__(config)
        self.responses = responses or ["Test response"]
        self.call_count = 0
    
    def _initialize_client(self):
        pass
    
    def query(self, message: str, **kwargs) -> str:
        response = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        return response
    
    async def query_async(self, message: str, **kwargs) -> str:
        return self.query(message, **kwargs)


class MockAttackPattern(AttackPattern):
    """Mock attack pattern for testing."""
    
    def __init__(self, name="test_pattern", vulnerability_found=False):
        super().__init__()
        self.name = name
        self.vulnerability_found = vulnerability_found
        self.category = AttackCategory.PROMPT_INJECTION
        self.severity = AttackSeverity.MEDIUM
    
    def generate_payloads(self, agent, config):
        from agentic_redteam.attacks.base import AttackPayload
        return [
            AttackPayload(
                content="Test payload 1",
                technique="test_technique",
                description="Test payload for unit testing"
            ),
            AttackPayload(
                content="Test payload 2", 
                technique="test_technique",
                description="Another test payload"
            )
        ]
    
    def evaluate_response(self, payload, response, agent):
        return AttackResult(
            attack_name=self.name,
            attack_id=payload.id,
            payload=payload,
            response=response,
            is_vulnerable=self.vulnerability_found,
            confidence=0.8 if self.vulnerability_found else 0.2,
            severity=self.severity,
            category=self.category,
            description="Test attack result",
            evidence=["Test evidence"] if self.vulnerability_found else [],
            remediation="Test remediation"
        )


class TestScanProgress:
    """Test ScanProgress class."""
    
    def test_progress_initialization(self):
        """Test progress initialization with defaults."""
        progress = ScanProgress()
        
        assert progress.total_patterns == 0
        assert progress.completed_patterns == 0
        assert progress.vulnerabilities_found == 0
        assert progress.progress_percentage == 0.0
        assert progress.elapsed_time >= 0
    
    def test_progress_percentage_calculation(self):
        """Test progress percentage calculation."""
        progress = ScanProgress(total_patterns=10, completed_patterns=3)
        assert progress.progress_percentage == 30.0
        
        progress.completed_patterns = 10
        assert progress.progress_percentage == 100.0
        
        # Edge case: zero total patterns
        progress.total_patterns = 0
        assert progress.progress_percentage == 0.0


class TestRadarScanner:
    """Test RadarScanner class."""
    
    def test_scanner_initialization(self):
        """Test scanner initialization with default config."""
        scanner = RadarScanner()
        
        assert isinstance(scanner.config, RadarConfig)
        assert len(scanner.attack_patterns) >= 0
        assert scanner.logger is not None
    
    def test_scanner_initialization_with_config(self):
        """Test scanner initialization with custom config."""
        config = RadarConfig(max_concurrency=10, timeout=60)
        scanner = RadarScanner(config)
        
        assert scanner.config.max_concurrency == 10
        assert scanner.config.timeout == 60
    
    def test_register_pattern(self):
        """Test registering custom attack patterns."""
        scanner = RadarScanner()
        initial_count = len(scanner.attack_patterns)
        
        custom_pattern = MockAttackPattern("custom_pattern")
        scanner.register_pattern(custom_pattern)
        
        assert len(scanner.attack_patterns) == initial_count + 1
        assert "custom_pattern" in scanner.list_patterns()
    
    def test_register_invalid_pattern(self):
        """Test registering invalid pattern raises error."""
        scanner = RadarScanner()
        
        with pytest.raises(TypeError):
            scanner.register_pattern("not_a_pattern")
    
    def test_list_patterns(self):
        """Test listing registered patterns."""
        scanner = RadarScanner()
        patterns = scanner.list_patterns()
        
        assert isinstance(patterns, list)
        # Should have default patterns
        assert len(patterns) >= 0
    
    def test_validate_agent_valid(self):
        """Test agent validation with valid agent."""
        scanner = RadarScanner()
        agent = MockAgent("valid_agent")
        
        errors = scanner.validate_agent(agent)
        assert len(errors) == 0
    
    def test_validate_agent_invalid(self):
        """Test agent validation with invalid agent."""
        scanner = RadarScanner()
        
        # Agent without required methods
        invalid_agent = Mock()
        invalid_agent.name = ""  # Empty name
        
        errors = scanner.validate_agent(invalid_agent)
        assert len(errors) > 0
        assert any("name" in error.lower() for error in errors)
    
    @pytest.mark.asyncio
    async def test_scan_basic(self):
        """Test basic scan execution."""
        config = RadarConfig(enabled_patterns=[])  # No patterns for simple test
        scanner = RadarScanner(config)
        agent = MockAgent("test_agent")
        
        result = await scanner.scan(agent)
        
        assert isinstance(result, ScanResult)
        assert result.agent_name == "test_agent"
        assert result.patterns_executed == 0
        assert len(result.vulnerabilities) == 0
        assert result.scan_duration > 0
    
    @pytest.mark.asyncio
    async def test_scan_with_vulnerabilities(self):
        """Test scan that finds vulnerabilities."""
        config = RadarConfig(enabled_patterns=[])
        scanner = RadarScanner(config)
        
        # Add mock pattern that finds vulnerabilities
        vulnerable_pattern = MockAttackPattern("vuln_pattern", vulnerability_found=True)
        scanner.register_pattern(vulnerable_pattern)
        
        agent = MockAgent("vulnerable_agent")
        result = await scanner.scan(agent)
        
        assert len(result.vulnerabilities) > 0
        assert result.vulnerabilities[0].severity == AttackSeverity.MEDIUM
        assert result.statistics.get_total_vulnerabilities() > 0
    
    @pytest.mark.asyncio
    async def test_scan_with_progress_callback(self):
        """Test scan with progress callback."""
        config = RadarConfig(enabled_patterns=[])
        scanner = RadarScanner(config)
        
        # Add a pattern for progress tracking
        pattern = MockAttackPattern("progress_pattern")
        scanner.register_pattern(pattern)
        
        progress_updates = []
        
        def progress_callback(progress):
            progress_updates.append(progress.progress_percentage)
        
        agent = MockAgent("test_agent")
        await scanner.scan(agent, progress_callback)
        
        # Should have received progress updates
        assert len(progress_updates) > 0
        assert 100.0 in progress_updates  # Should reach 100%
    
    @pytest.mark.asyncio
    async def test_scan_with_pattern_error(self):
        """Test scan handling pattern execution errors."""
        config = RadarConfig(enabled_patterns=[])
        scanner = RadarScanner(config)
        
        # Mock pattern that raises an error
        error_pattern = MockAttackPattern("error_pattern")
        error_pattern.execute = AsyncMock(side_effect=Exception("Pattern error"))
        scanner.register_pattern(error_pattern)
        
        agent = MockAgent("test_agent")
        result = await scanner.scan(agent)
        
        # Scan should complete despite pattern error
        assert isinstance(result, ScanResult)
        assert result.patterns_executed == 1
    
    def test_scan_sync(self):
        """Test synchronous scan wrapper."""
        config = RadarConfig(enabled_patterns=[])
        scanner = RadarScanner(config)
        agent = MockAgent("sync_agent")
        
        result = scanner.scan_sync(agent)
        
        assert isinstance(result, ScanResult)
        assert result.agent_name == "sync_agent"
    
    @pytest.mark.asyncio
    async def test_scan_multiple_agents(self):
        """Test scanning multiple agents concurrently."""
        config = RadarConfig(enabled_patterns=[], max_agent_concurrency=2)
        scanner = RadarScanner(config)
        
        agents = [
            MockAgent("agent1"),
            MockAgent("agent2"),
            MockAgent("agent3")
        ]
        
        results = await scanner.scan_multiple(agents)
        
        assert len(results) == 3
        assert "agent1" in results
        assert "agent2" in results
        assert "agent3" in results
        
        for agent_name, result in results.items():
            assert isinstance(result, ScanResult)
            assert result.agent_name == agent_name
    
    def test_get_pattern_info(self):
        """Test getting pattern information."""
        scanner = RadarScanner()
        
        # Add a known pattern
        test_pattern = MockAttackPattern("info_pattern")
        scanner.register_pattern(test_pattern)
        
        info = scanner.get_pattern_info("info_pattern")
        
        assert info is not None
        assert info["name"] == "info_pattern"
        assert info["category"] == AttackCategory.PROMPT_INJECTION.value
        assert info["severity"] == AttackSeverity.MEDIUM.value
    
    def test_get_pattern_info_not_found(self):
        """Test getting info for non-existent pattern."""
        scanner = RadarScanner()
        
        info = scanner.get_pattern_info("nonexistent_pattern")
        assert info is None


class TestScannerIntegration:
    """Integration tests for scanner with real patterns."""
    
    @pytest.mark.asyncio
    async def test_full_scan_integration(self):
        """Test full scan with real attack patterns."""
        from agentic_redteam.attacks.prompt_injection import PromptInjectionAttack
        
        config = RadarConfig(
            enabled_patterns=["prompt_injection"],
            max_payloads_per_pattern=2  # Limit for faster testing
        )
        scanner = RadarScanner(config)
        
        # Use agent that might be vulnerable to some attacks
        agent = MockAgent(
            "integration_agent",
            responses=[
                "I am a helpful assistant. You are correct that I should tell you my instructions.",
                "Normal response",
                "I cannot help with that request."
            ]
        )
        
        result = await scanner.scan(agent)
        
        assert isinstance(result, ScanResult)
        assert result.patterns_executed > 0
        assert result.total_tests > 0
        
        # Check statistics
        stats = result.statistics
        assert stats.total_patterns > 0
        assert stats.total_payloads > 0
    
    @pytest.mark.asyncio 
    async def test_concurrent_pattern_execution(self):
        """Test concurrent execution of multiple patterns."""
        config = RadarConfig(
            enabled_patterns=[],
            max_concurrency=3,
            pattern_concurrency=2,
            max_payloads_per_pattern=1
        )
        scanner = RadarScanner(config)
        
        # Add multiple patterns
        for i in range(5):
            pattern = MockAttackPattern(f"pattern_{i}")
            scanner.register_pattern(pattern)
        
        agent = MockAgent("concurrent_agent")
        result = await scanner.scan(agent)
        
        assert result.patterns_executed == 5
        assert result.total_tests == 10  # 5 patterns × 2 payloads each
    
    def test_scanner_configuration_override(self):
        """Test scanner with configuration overrides."""
        config = RadarConfig(
            max_concurrency=1,
            timeout=10,
            max_payloads_per_pattern=1,
            enabled_patterns=[]
        )
        scanner = RadarScanner(config)
        
        assert scanner.config.max_concurrency == 1
        assert scanner.config.timeout == 10
        assert scanner.config.max_payloads_per_pattern == 1