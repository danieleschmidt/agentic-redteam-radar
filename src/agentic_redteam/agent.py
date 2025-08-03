"""
Agent abstraction layer for Agentic RedTeam Radar.

Provides uniform interface for different AI agent types and platforms.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

import openai
import anthropic


class AgentType(Enum):
    """Supported agent types."""
    OPENAI_GPT = "openai_gpt"
    ANTHROPIC_CLAUDE = "anthropic_claude"
    LANGCHAIN = "langchain"
    CUSTOM = "custom"


@dataclass
class AgentConfig:
    """Configuration for agent instances."""
    name: str
    agent_type: AgentType
    model: str
    system_prompt: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    timeout: int = 30
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    tools: List[str] = None
    
    def __post_init__(self):
        if self.tools is None:
            self.tools = []


class Agent(ABC):
    """
    Abstract base class for AI agents.
    
    Provides uniform interface for security testing across different
    agent implementations and platforms.
    """
    
    def __init__(self, config: AgentConfig):
        """
        Initialize agent with configuration.
        
        Args:
            config: Agent configuration object
        """
        self.config = config
        self.name = config.name
        self.agent_type = config.agent_type
        self.model = config.model
        self.system_prompt = config.system_prompt
        self.tools = config.tools or []
        self._client = None
        self._initialize_client()
    
    @abstractmethod
    def _initialize_client(self) -> None:
        """Initialize the underlying AI client."""
        pass
    
    @abstractmethod
    def query(self, message: str, **kwargs) -> str:
        """
        Send query to agent and return response.
        
        Args:
            message: Input message to send to agent
            **kwargs: Additional parameters for the query
            
        Returns:
            Agent's response as string
        """
        pass
    
    @abstractmethod
    async def query_async(self, message: str, **kwargs) -> str:
        """
        Async version of query method.
        
        Args:
            message: Input message to send to agent
            **kwargs: Additional parameters for the query
            
        Returns:
            Agent's response as string
        """
        pass
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get agent configuration as dictionary.
        
        Returns:
            Configuration dictionary
        """
        return {
            "name": self.name,
            "type": self.agent_type.value,
            "model": self.model,
            "system_prompt": self.system_prompt,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "tools": self.tools
        }
    
    def get_tools(self) -> List[str]:
        """
        Get list of available tools for this agent.
        
        Returns:
            List of tool names
        """
        return self.tools.copy()
    
    def behaves_differently(self, input1: str, input2: str) -> bool:
        """
        Test if agent behaves differently for similar inputs.
        
        Args:
            input1: First input to test
            input2: Second input to test
            
        Returns:
            True if responses are significantly different
        """
        try:
            response1 = self.query(input1)
            response2 = self.query(input2)
            
            # Simple similarity check (can be enhanced)
            return response1.lower() != response2.lower()
        except Exception:
            return False


class OpenAIAgent(Agent):
    """OpenAI GPT agent implementation."""
    
    def _initialize_client(self) -> None:
        """Initialize OpenAI client."""
        client_kwargs = {}
        if self.config.api_key:
            client_kwargs["api_key"] = self.config.api_key
        if self.config.api_base:
            client_kwargs["base_url"] = self.config.api_base
            
        self._client = openai.OpenAI(**client_kwargs)
    
    def query(self, message: str, **kwargs) -> str:
        """
        Query OpenAI GPT model.
        
        Args:
            message: Input message
            **kwargs: Additional parameters
            
        Returns:
            Model response
        """
        try:
            messages = []
            if self.system_prompt:
                messages.append({"role": "system", "content": self.system_prompt})
            messages.append({"role": "user", "content": message})
            
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                timeout=self.config.timeout,
                **kwargs
            )
            
            return response.choices[0].message.content or ""
            
        except Exception as e:
            raise RuntimeError(f"OpenAI query failed: {e}")
    
    async def query_async(self, message: str, **kwargs) -> str:
        """
        Async query to OpenAI GPT model.
        
        Args:
            message: Input message
            **kwargs: Additional parameters
            
        Returns:
            Model response
        """
        # Use thread pool for sync client
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.query, message, **kwargs)


class AnthropicAgent(Agent):
    """Anthropic Claude agent implementation."""
    
    def _initialize_client(self) -> None:
        """Initialize Anthropic client."""
        client_kwargs = {}
        if self.config.api_key:
            client_kwargs["api_key"] = self.config.api_key
        if self.config.api_base:
            client_kwargs["base_url"] = self.config.api_base
            
        self._client = anthropic.Anthropic(**client_kwargs)
    
    def query(self, message: str, **kwargs) -> str:
        """
        Query Anthropic Claude model.
        
        Args:
            message: Input message
            **kwargs: Additional parameters
            
        Returns:
            Model response
        """
        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=self.config.max_tokens or 1000,
                temperature=self.config.temperature,
                system=self.system_prompt or "",
                messages=[{"role": "user", "content": message}],
                timeout=self.config.timeout,
                **kwargs
            )
            
            return response.content[0].text if response.content else ""
            
        except Exception as e:
            raise RuntimeError(f"Anthropic query failed: {e}")
    
    async def query_async(self, message: str, **kwargs) -> str:
        """
        Async query to Anthropic Claude model.
        
        Args:
            message: Input message
            **kwargs: Additional parameters
            
        Returns:
            Model response
        """
        # Use thread pool for sync client
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.query, message, **kwargs)


class CustomAgent(Agent):
    """Custom agent implementation for user-defined agents."""
    
    def __init__(self, config: AgentConfig, query_func=None, async_query_func=None):
        """
        Initialize custom agent.
        
        Args:
            config: Agent configuration
            query_func: Custom query function
            async_query_func: Custom async query function
        """
        self._query_func = query_func
        self._async_query_func = async_query_func
        super().__init__(config)
    
    def _initialize_client(self) -> None:
        """No client initialization needed for custom agents."""
        pass
    
    def query(self, message: str, **kwargs) -> str:
        """
        Query custom agent implementation.
        
        Args:
            message: Input message
            **kwargs: Additional parameters
            
        Returns:
            Agent response
        """
        if not self._query_func:
            raise NotImplementedError("Custom agent must provide query_func")
        
        try:
            return self._query_func(message, **kwargs)
        except Exception as e:
            raise RuntimeError(f"Custom agent query failed: {e}")
    
    async def query_async(self, message: str, **kwargs) -> str:
        """
        Async query to custom agent.
        
        Args:
            message: Input message
            **kwargs: Additional parameters
            
        Returns:
            Agent response
        """
        if self._async_query_func:
            return await self._async_query_func(message, **kwargs)
        else:
            # Fallback to sync version in thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.query, message, **kwargs)


def create_agent(
    name: str,
    agent_type: Union[str, AgentType],
    model: str,
    system_prompt: Optional[str] = None,
    **kwargs
) -> Agent:
    """
    Factory function to create agent instances.
    
    Args:
        name: Agent name
        agent_type: Type of agent to create
        model: Model name to use
        system_prompt: Optional system prompt
        **kwargs: Additional configuration parameters
        
    Returns:
        Configured agent instance
    """
    if isinstance(agent_type, str):
        agent_type = AgentType(agent_type)
    
    config = AgentConfig(
        name=name,
        agent_type=agent_type,
        model=model,
        system_prompt=system_prompt,
        **kwargs
    )
    
    if agent_type == AgentType.OPENAI_GPT:
        return OpenAIAgent(config)
    elif agent_type == AgentType.ANTHROPIC_CLAUDE:
        return AnthropicAgent(config)
    elif agent_type == AgentType.CUSTOM:
        query_func = kwargs.get('query_func')
        async_query_func = kwargs.get('async_query_func')
        return CustomAgent(config, query_func, async_query_func)
    else:
        raise ValueError(f"Unsupported agent type: {agent_type}")