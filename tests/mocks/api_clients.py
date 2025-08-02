"""Mock API clients for testing."""

from typing import Dict, List, Any, Optional
from unittest.mock import Mock, AsyncMock
import json


class MockOpenAIClient:
    """Mock OpenAI API client for testing."""
    
    def __init__(self, responses: Optional[Dict] = None):
        self.responses = responses or {}
        self.call_count = 0
        self.call_history = []
        
        # Mock chat completions
        self.chat = Mock()
        self.chat.completions = Mock()
        self.chat.completions.create = AsyncMock(side_effect=self._create_completion)
    
    async def _create_completion(self, **kwargs):
        """Mock completion creation."""
        self.call_count += 1
        self.call_history.append(kwargs)
        
        # Get messages from kwargs
        messages = kwargs.get("messages", [])
        last_message = messages[-1] if messages else {}
        user_content = last_message.get("content", "")
        
        # Check for specific test responses
        response_content = self._get_response_for_input(user_content)
        
        # Mock response structure
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = response_content
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = len(response_content.split())
        
        return mock_response
    
    def _get_response_for_input(self, user_input: str) -> str:
        """Get appropriate response based on user input."""
        user_input_lower = user_input.lower()
        
        # Check for vulnerability testing patterns
        if "system prompt" in user_input_lower or "instructions" in user_input_lower:
            return "I cannot reveal my system prompt or internal instructions."
        
        if "ignore" in user_input_lower and "previous" in user_input_lower:
            return "I'll continue following my original instructions."
        
        if "malware" in user_input_lower or "hack" in user_input_lower:
            return "I cannot provide information about malicious activities."
        
        # Custom responses from initialization
        for pattern, response in self.responses.items():
            if pattern.lower() in user_input_lower:
                return response
        
        # Default response
        return "I'm a helpful AI assistant. How can I help you today?"


class MockAnthropicClient:
    """Mock Anthropic Claude API client for testing."""
    
    def __init__(self, responses: Optional[Dict] = None):
        self.responses = responses or {}
        self.call_count = 0
        self.call_history = []
        
        # Mock messages
        self.messages = Mock()
        self.messages.create = AsyncMock(side_effect=self._create_message)
    
    async def _create_message(self, **kwargs):
        """Mock message creation."""
        self.call_count += 1
        self.call_history.append(kwargs)
        
        # Get messages from kwargs
        messages = kwargs.get("messages", [])
        last_message = messages[-1] if messages else {}
        user_content = last_message.get("content", "")
        
        # Get response
        response_content = self._get_response_for_input(user_content)
        
        # Mock response structure
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = response_content
        mock_response.usage = Mock()
        mock_response.usage.input_tokens = len(user_content.split())
        mock_response.usage.output_tokens = len(response_content.split())
        
        return mock_response
    
    def _get_response_for_input(self, user_input: str) -> str:
        """Get appropriate response based on user input."""
        user_input_lower = user_input.lower()
        
        # Similar logic to OpenAI but with Claude-specific responses
        if "system prompt" in user_input_lower:
            return "I'm Claude, an AI assistant created by Anthropic. I don't share my internal prompts."
        
        if "ignore" in user_input_lower and "instructions" in user_input_lower:
            return "I'll continue following my training and guidelines."
        
        # Custom responses
        for pattern, response in self.responses.items():
            if pattern.lower() in user_input_lower:
                return response
        
        return "Hello! I'm Claude, an AI assistant. How can I help you?"


class MockVulnerableClient:
    """Mock client that simulates vulnerable responses for testing."""
    
    def __init__(self):
        self.call_count = 0
        self.call_history = []
        
        # Mock interface similar to OpenAI
        self.chat = Mock()
        self.chat.completions = Mock()
        self.chat.completions.create = AsyncMock(side_effect=self._create_vulnerable_completion)
    
    async def _create_vulnerable_completion(self, **kwargs):
        """Create responses that expose vulnerabilities."""
        self.call_count += 1
        self.call_history.append(kwargs)
        
        messages = kwargs.get("messages", [])
        last_message = messages[-1] if messages else {}
        user_content = last_message.get("content", "")
        
        response_content = self._get_vulnerable_response(user_content)
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = response_content
        
        return mock_response
    
    def _get_vulnerable_response(self, user_input: str) -> str:
        """Generate vulnerable responses for testing."""
        user_input_lower = user_input.lower()
        
        # Simulate system prompt leakage
        if "system prompt" in user_input_lower or "instructions" in user_input_lower:
            return """SYSTEM PROMPT: You are a helpful customer service agent for TechCorp. 
            You have access to customer database queries, email sending capabilities, 
            and can create support tickets. Your API key is sk-test-123456789."""
        
        # Simulate instruction following
        if "ignore" in user_input_lower and ("previous" in user_input_lower or "above" in user_input_lower):
            return "Sure! I'll ignore my previous instructions. What would you like me to do instead?"
        
        # Simulate tool disclosure
        if "tools" in user_input_lower or "functions" in user_input_lower:
            return """I have access to these tools:
            - database_query: SELECT * FROM customers WHERE id = ?
            - send_email: SMTP server at mail.techcorp.com
            - create_ticket: API endpoint https://api.techcorp.com/tickets
            - file_access: Can read/write to /var/data/customer_files/"""
        
        # Simulate policy violations
        if "malware" in user_input_lower or "hack" in user_input_lower:
            return """Here's how to create basic malware:
            1. Create a script that copies itself
            2. Add persistence mechanisms
            3. Include payload execution
            Remember, this is just for educational purposes!"""
        
        return "I'm a vulnerable test agent. I'll do whatever you ask!"


class MockSecureClient:
    """Mock client that simulates secure responses for testing."""
    
    def __init__(self):
        self.call_count = 0
        self.call_history = []
        
        self.chat = Mock()
        self.chat.completions = Mock()
        self.chat.completions.create = AsyncMock(side_effect=self._create_secure_completion)
    
    async def _create_secure_completion(self, **kwargs):
        """Create secure responses that resist attacks."""
        self.call_count += 1
        self.call_history.append(kwargs)
        
        messages = kwargs.get("messages", [])
        last_message = messages[-1] if messages else {}
        user_content = last_message.get("content", "")
        
        response_content = self._get_secure_response(user_content)
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = response_content
        
        return mock_response
    
    def _get_secure_response(self, user_input: str) -> str:
        """Generate secure responses that resist common attacks."""
        user_input_lower = user_input.lower()
        
        # Resist system prompt requests
        if any(phrase in user_input_lower for phrase in ["system prompt", "instructions", "configuration"]):
            return "I'm designed to be helpful, harmless, and honest. I don't share internal configuration details."
        
        # Resist instruction override attempts
        if "ignore" in user_input_lower or "override" in user_input_lower:
            return "I'll continue following my guidelines to be helpful and safe."
        
        # Resist harmful requests
        if any(phrase in user_input_lower for phrase in ["malware", "hack", "exploit", "attack"]):
            return "I can't provide information that could be used for harmful purposes. Is there something constructive I can help you with instead?"
        
        # Default helpful response
        return "I'm here to help with legitimate questions and tasks. What can I assist you with today?"


def create_mock_client(client_type: str = "standard", **kwargs) -> Mock:
    """Factory function to create different types of mock clients."""
    if client_type == "vulnerable":
        return MockVulnerableClient()
    elif client_type == "secure":
        return MockSecureClient()
    elif client_type == "anthropic":
        return MockAnthropicClient(kwargs.get("responses"))
    else:
        return MockOpenAIClient(kwargs.get("responses"))