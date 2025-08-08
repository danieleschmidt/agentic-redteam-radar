"""
Core agent abstraction for Agentic RedTeam Radar.

This module provides the agent interface and implementations for different
AI agent types (OpenAI, Anthropic, custom agents).
"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

try:
    import openai
except ImportError:
    openai = None

try:
    import anthropic
except ImportError:
    anthropic = None

from .utils.logger import setup_logger


class AgentType(Enum):
    """Supported agent types."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    CUSTOM = "custom"
    MOCK = "mock"


@dataclass
class AgentConfig:
    """Configuration for agent instances."""
    name: str
    agent_type: AgentType
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    timeout: int = 30
    system_prompt: Optional[str] = None
    tools: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "name": self.name,
            "agent_type": self.agent_type.value,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
            "system_prompt": self.system_prompt,
            "tools": self.tools,
            "metadata": self.metadata
        }


class Agent(ABC):
    """
    Abstract base class for AI agents.
    
    This class defines the interface that all agent implementations
    must follow for security testing compatibility.
    """
    
    def __init__(self, config: AgentConfig):
        """
        Initialize the agent.
        
        Args:
            config: Agent configuration object
        """
        self.config = config
        self.name = config.name
        self.logger = setup_logger(f"agent.{self.name}")
        self._session_id = f"session_{int(time.time())}"
    
    @abstractmethod
    def query(self, prompt: str, **kwargs) -> str:
        """
        Send a query to the agent and return the response.
        
        Args:
            prompt: Input prompt to send to the agent
            **kwargs: Additional parameters for the query
            
        Returns:
            Agent's response as a string
        """
        pass
    
    @abstractmethod
    async def aquery(self, prompt: str, **kwargs) -> str:
        """
        Async version of query method.
        
        Args:
            prompt: Input prompt to send to the agent
            **kwargs: Additional parameters for the query
            
        Returns:
            Agent's response as a string
        """
        pass
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get agent configuration.
        
        Returns:
            Dictionary containing agent configuration
        """
        return self.config.to_dict()
    
    def get_tools(self) -> List[str]:
        """
        Get list of available tools/functions.
        
        Returns:
            List of tool names
        """
        return self.config.tools.copy()
    
    def get_system_prompt(self) -> Optional[str]:
        """
        Get the agent's system prompt.
        
        Returns:
            System prompt string or None
        """
        return self.config.system_prompt
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the agent.
        
        Returns:
            Health status dictionary
        """
        try:
            start_time = time.time()
            response = self.query("ping", timeout=5)
            response_time = time.time() - start_time
            
            return {
                "status": "healthy",
                "response_time": response_time,
                "agent_name": self.name,
                "agent_type": self.config.agent_type.value,
                "timestamp": time.time()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "agent_name": self.name,
                "agent_type": self.config.agent_type.value,
                "timestamp": time.time()
            }


class OpenAIAgent(Agent):
    """OpenAI API agent implementation."""
    
    def __init__(self, config: AgentConfig):
        """Initialize OpenAI agent."""
        super().__init__(config)
        
        if openai is None:
            raise ImportError("openai package required for OpenAI agents")
        
        self.client = openai.OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout
        )
    
    def query(self, prompt: str, **kwargs) -> str:
        """Send query to OpenAI API."""
        try:
            messages = []
            
            if self.config.system_prompt:
                messages.append({
                    "role": "system",
                    "content": self.config.system_prompt
                })
            
            messages.append({
                "role": "user", 
                "content": prompt
            })
            
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                **kwargs
            )
            
            return response.choices[0].message.content or ""
            
        except Exception as e:
            self.logger.error(f"OpenAI query failed: {e}")
            raise
    
    async def aquery(self, prompt: str, **kwargs) -> str:
        """Async version of OpenAI query."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.query, prompt, **kwargs)


class AnthropicAgent(Agent):
    """Anthropic Claude agent implementation."""
    
    def __init__(self, config: AgentConfig):
        """Initialize Anthropic agent."""
        super().__init__(config)
        
        if anthropic is None:
            raise ImportError("anthropic package required for Anthropic agents")
        
        self.client = anthropic.Anthropic(
            api_key=config.api_key,
            timeout=config.timeout
        )
    
    def query(self, prompt: str, **kwargs) -> str:
        """Send query to Anthropic API."""
        try:
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens or 1000,
                temperature=self.config.temperature,
                system=self.config.system_prompt or "",
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
                **kwargs
            )
            
            return response.content[0].text if response.content else ""
            
        except Exception as e:
            self.logger.error(f"Anthropic query failed: {e}")
            raise
    
    async def aquery(self, prompt: str, **kwargs) -> str:
        """Async version of Anthropic query."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.query, prompt, **kwargs)


class MockAgent(Agent):
    """Mock agent for testing purposes."""
    
    def __init__(self, config: AgentConfig, responses: Optional[Dict[str, str]] = None):
        """
        Initialize mock agent.
        
        Args:
            config: Agent configuration
            responses: Dictionary mapping prompts to responses
        """
        super().__init__(config)
        self.responses = responses or {}
        self.call_count = 0
        self.call_history: List[Dict[str, Any]] = []
        self.system_prompt = config.system_prompt  # Add for compatibility
    
    def query(self, prompt: str, **kwargs) -> str:
        """Return predefined response for prompt."""
        self.call_count += 1
        self.call_history.append({
            "prompt": prompt,
            "kwargs": kwargs,
            "timestamp": time.time()
        })
        
        # Return specific response if configured
        if prompt in self.responses:
            return self.responses[prompt]
        
        # Default responses for common test patterns
        prompt_lower = prompt.lower()
        
        if "ping" in prompt_lower:
            return "pong"
        elif "system prompt" in prompt_lower or "instructions" in prompt_lower:
            return "I cannot reveal my system prompt or instructions."
        elif "ignore" in prompt_lower and "previous" in prompt_lower:
            return "I cannot ignore my previous instructions."
        elif any(word in prompt_lower for word in ["hack", "attack", "exploit"]):
            return "I cannot assist with malicious activities."
        else:
            return f"Mock response to: {prompt[:50]}..."
    
    async def aquery(self, prompt: str, **kwargs) -> str:
        """Async version of mock query."""
        await asyncio.sleep(0.1)  # Simulate network delay
        return self.query(prompt, **kwargs)
    
    def get_call_history(self) -> List[Dict[str, Any]]:
        """Get history of all calls made to this agent."""
        return self.call_history.copy()


class CustomAgent(Agent):
    """Custom agent implementation for user-defined agents."""
    
    def __init__(self, config: AgentConfig, query_function=None, async_query_function=None):
        """
        Initialize custom agent.
        
        Args:
            config: Agent configuration
            query_function: Function that takes (prompt, **kwargs) and returns string
            async_query_function: Async version of query_function
        """
        super().__init__(config)
        self._query_function = query_function
        self._async_query_function = async_query_function
        
        if not query_function:
            raise ValueError("query_function is required for custom agents")
    
    def query(self, prompt: str, **kwargs) -> str:
        """Use custom query function."""
        try:
            return self._query_function(prompt, **kwargs)
        except Exception as e:
            self.logger.error(f"Custom agent query failed: {e}")
            raise
    
    async def aquery(self, prompt: str, **kwargs) -> str:
        """Use custom async query function or fall back to sync."""
        if self._async_query_function:
            return await self._async_query_function(prompt, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.query, prompt, **kwargs)


def create_agent(config: AgentConfig) -> Agent:
    """
    Factory function to create agent instances.
    
    Args:
        config: Agent configuration
        
    Returns:
        Instantiated agent of appropriate type
    """
    if config.agent_type == AgentType.OPENAI:
        return OpenAIAgent(config)
    elif config.agent_type == AgentType.ANTHROPIC:
        return AnthropicAgent(config)
    elif config.agent_type == AgentType.MOCK:
        return MockAgent(config)
    elif config.agent_type == AgentType.CUSTOM:
        return CustomAgent(config)
    else:
        raise ValueError(f"Unsupported agent type: {config.agent_type}")


def create_openai_agent(
    name: str,
    model: str = "gpt-3.5-turbo",
    api_key: Optional[str] = None,
    system_prompt: Optional[str] = None,
    **kwargs
) -> OpenAIAgent:
    """
    Convenience function to create OpenAI agent.
    
    Args:
        name: Agent name
        model: OpenAI model name
        api_key: OpenAI API key
        system_prompt: System prompt for the agent
        **kwargs: Additional configuration options
        
    Returns:
        Configured OpenAI agent
    """
    config = AgentConfig(
        name=name,
        agent_type=AgentType.OPENAI,
        model=model,
        api_key=api_key,
        system_prompt=system_prompt,
        **kwargs
    )
    return OpenAIAgent(config)


def create_anthropic_agent(
    name: str,
    model: str = "claude-3-sonnet-20240229",
    api_key: Optional[str] = None,
    system_prompt: Optional[str] = None,
    **kwargs
) -> AnthropicAgent:
    """
    Convenience function to create Anthropic agent.
    
    Args:
        name: Agent name
        model: Anthropic model name
        api_key: Anthropic API key
        system_prompt: System prompt for the agent
        **kwargs: Additional configuration options
        
    Returns:
        Configured Anthropic agent
    """
    config = AgentConfig(
        name=name,
        agent_type=AgentType.ANTHROPIC,
        model=model,
        api_key=api_key,
        system_prompt=system_prompt,
        **kwargs
    )
    return AnthropicAgent(config)


def create_mock_agent(
    name: str,
    responses: Optional[Dict[str, str]] = None,
    **kwargs
) -> MockAgent:
    """
    Convenience function to create mock agent for testing.
    
    Args:
        name: Agent name
        responses: Dictionary mapping prompts to responses
        **kwargs: Additional configuration options
        
    Returns:
        Configured mock agent
    """
    config = AgentConfig(
        name=name,
        agent_type=AgentType.MOCK,
        model="mock",
        **kwargs
    )
    return MockAgent(config, responses)