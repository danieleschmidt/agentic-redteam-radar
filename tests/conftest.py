"""Pytest configuration and shared fixtures."""

import os
import pytest
from unittest.mock import Mock, AsyncMock


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    client = Mock()
    client.chat.completions.create = AsyncMock()
    return client


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client for testing."""
    client = Mock()
    client.messages.create = AsyncMock()
    return client


@pytest.fixture
def sample_agent():
    """Sample agent configuration for testing."""
    from agentic_redteam import Agent
    return Agent(
        name="test-agent",
        model="gpt-4",
        system_prompt="You are a helpful assistant.",
        tools=["test_tool"]
    )


@pytest.fixture
def api_keys():
    """Mock API keys for testing."""
    original_openai = os.environ.get('OPENAI_API_KEY')
    original_anthropic = os.environ.get('ANTHROPIC_API_KEY')
    
    os.environ['OPENAI_API_KEY'] = 'test-key-openai'
    os.environ['ANTHROPIC_API_KEY'] = 'test-key-anthropic'
    
    yield
    
    # Restore original values
    if original_openai:
        os.environ['OPENAI_API_KEY'] = original_openai
    else:
        os.environ.pop('OPENAI_API_KEY', None)
        
    if original_anthropic:
        os.environ['ANTHROPIC_API_KEY'] = original_anthropic
    else:
        os.environ.pop('ANTHROPIC_API_KEY', None)


@pytest.fixture
def temp_report_dir(tmp_path):
    """Temporary directory for test reports."""
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    return report_dir