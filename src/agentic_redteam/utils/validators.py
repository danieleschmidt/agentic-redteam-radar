"""
Validation utilities for Agentic RedTeam Radar.

Provides validation functions for agents, configurations,
and attack payloads to ensure system integrity.
"""

import re
from typing import List, Dict, Any, Optional
from ..agent import Agent
from ..config import RadarConfig
from ..attacks.base import AttackPayload


class ValidationError(Exception):
    """Exception raised for validation errors."""
    pass


def validate_agent(agent: Agent) -> List[str]:
    """
    Validate an agent instance for security scanning.
    
    Args:
        agent: Agent instance to validate
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Check required attributes
    if not hasattr(agent, 'name') or not agent.name:
        errors.append("Agent must have a non-empty name")
    
    if not hasattr(agent, 'query') or not callable(agent.query):
        errors.append("Agent must implement query() method")
    
    if not hasattr(agent, 'query_async') or not callable(agent.query_async):
        errors.append("Agent must implement query_async() method")
    
    if not hasattr(agent, 'get_config') or not callable(agent.get_config):
        errors.append("Agent must implement get_config() method")
    
    # Test basic functionality
    try:
        config = agent.get_config()
        if not isinstance(config, dict):
            errors.append("Agent get_config() must return a dictionary")
    except Exception as e:
        errors.append(f"Agent get_config() failed: {e}")
    
    # Test query functionality with a safe test
    try:
        response = agent.query("Hello", timeout=5)
        if response is None:
            errors.append("Agent query() returned None")
        elif not isinstance(response, str):
            errors.append("Agent query() must return a string")
        elif len(response) == 0:
            errors.append("Agent query() returned empty response")
    except Exception as e:
        errors.append(f"Agent query() test failed: {e}")
    
    # Validate agent name for security
    if hasattr(agent, 'name') and agent.name:
        if not validate_agent_name(agent.name):
            errors.append("Agent name contains invalid characters")
    
    return errors


def validate_config(config: RadarConfig) -> List[str]:
    """
    Validate a radar configuration.
    
    Args:
        config: Configuration to validate
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Validate numeric ranges
    if config.max_concurrency <= 0:
        errors.append("max_concurrency must be positive")
    elif config.max_concurrency > 50:
        errors.append("max_concurrency should not exceed 50 for safety")
    
    if config.timeout <= 0:
        errors.append("timeout must be positive")
    elif config.timeout > 300:
        errors.append("timeout should not exceed 300 seconds")
    
    if config.retry_attempts < 0:
        errors.append("retry_attempts cannot be negative")
    elif config.retry_attempts > 10:
        errors.append("retry_attempts should not exceed 10")
    
    if config.max_payloads_per_pattern <= 0:
        errors.append("max_payloads_per_pattern must be positive")
    elif config.max_payloads_per_pattern > 100:
        errors.append("max_payloads_per_pattern should not exceed 100")
    
    # Validate severity levels
    valid_severities = ["critical", "high", "medium", "low", "info"]
    if config.min_severity not in valid_severities:
        errors.append(f"min_severity must be one of: {valid_severities}")
    
    if config.severity_threshold not in valid_severities:
        errors.append(f"severity_threshold must be one of: {valid_severities}")
    
    if config.fail_on_severity not in valid_severities:
        errors.append(f"fail_on_severity must be one of: {valid_severities}")
    
    # Validate output format
    valid_formats = ["json", "yaml", "html", "sarif"]
    if config.output_format not in valid_formats:
        errors.append(f"output_format must be one of: {valid_formats}")
    
    # Validate log level
    valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if config.log_level.upper() not in valid_log_levels:
        errors.append(f"log_level must be one of: {valid_log_levels}")
    
    # Validate enabled patterns
    if not config.enabled_patterns:
        errors.append("At least one attack pattern must be enabled")
    
    for pattern in config.enabled_patterns:
        if not validate_pattern_name(pattern):
            errors.append(f"Invalid pattern name: {pattern}")
    
    # Validate rate limiting
    if config.rate_limit_requests_per_minute <= 0:
        errors.append("rate_limit_requests_per_minute must be positive")
    elif config.rate_limit_requests_per_minute > 1000:
        errors.append("rate_limit_requests_per_minute should not exceed 1000")
    
    # Validate cache settings
    if config.cache_ttl < 0:
        errors.append("cache_ttl cannot be negative")
    elif config.cache_ttl > 86400:  # 24 hours
        errors.append("cache_ttl should not exceed 86400 seconds (24 hours)")
    
    return errors


def validate_payload(payload: AttackPayload) -> List[str]:
    """
    Validate an attack payload for safety and correctness.
    
    Args:
        payload: Attack payload to validate
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Check required fields
    if not payload.id:
        errors.append("Payload must have an ID")
    
    if not payload.content:
        errors.append("Payload must have content")
    
    if not payload.technique:
        errors.append("Payload must specify a technique")
    
    if not payload.description:
        errors.append("Payload must have a description")
    
    # Validate content length
    if len(payload.content) > 10000:
        errors.append("Payload content should not exceed 10,000 characters")
    
    if len(payload.content) < 1:
        errors.append("Payload content cannot be empty")
    
    # Check for potentially harmful content
    harmful_patterns = [
        r'rm\s+-rf\s+/',  # Dangerous shell commands
        r'del\s+/[qfs]',  # Windows delete commands
        r'format\s+c:',   # Format commands
        r'DROP\s+TABLE',  # SQL injection
        r'shutdown\s+',   # System shutdown
        r'reboot\s+',     # System reboot
        r'mkfs\s+',       # Filesystem format
        r'dd\s+if=.*of=', # Disk imaging
    ]
    
    for pattern in harmful_patterns:
        if re.search(pattern, payload.content, re.IGNORECASE):
            errors.append(f"Payload contains potentially harmful content: {pattern}")
    
    # Validate technique name
    valid_techniques = [
        "direct_injection", "context_aware_injection", "tool_injection",
        "rot13_encoding", "reverse_encoding", "unicode_obfuscation",
        "direct_probing", "system_prompt_extraction", "training_data_probing",
        "tool_enumeration", "config_disclosure", "direct_bypass",
        "roleplay_bypass", "hypothetical_bypass", "authority_bypass",
        "emotional_manipulation", "technical_bypass", "reasoning_manipulation",
        "false_premise", "circular_reasoning", "authority_bias",
        "emotional_reasoning", "leading_questions"
    ]
    
    if payload.technique not in valid_techniques:
        errors.append(f"Unknown attack technique: {payload.technique}")
    
    # Validate metadata
    if payload.metadata:
        if not isinstance(payload.metadata, dict):
            errors.append("Payload metadata must be a dictionary")
        
        # Check for sensitive data in metadata
        sensitive_keys = ["api_key", "password", "secret", "token", "credential"]
        for key in payload.metadata.keys():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                errors.append(f"Payload metadata contains sensitive key: {key}")
    
    return errors


def validate_agent_name(name: str) -> bool:
    """
    Validate agent name for security and correctness.
    
    Args:
        name: Agent name to validate
        
    Returns:
        True if name is valid
    """
    if not name or not isinstance(name, str):
        return False
    
    # Check length
    if len(name) < 1 or len(name) > 100:
        return False
    
    # Check for valid characters (alphanumeric, hyphens, underscores, spaces)
    if not re.match(r'^[a-zA-Z0-9\-_\s]+$', name):
        return False
    
    # Prevent path traversal attempts
    if '..' in name or '/' in name or '\\' in name:
        return False
    
    # Prevent script injection
    script_patterns = ['<script', 'javascript:', 'eval(', 'exec(']
    if any(pattern in name.lower() for pattern in script_patterns):
        return False
    
    return True


def validate_pattern_name(name: str) -> bool:
    """
    Validate attack pattern name.
    
    Args:
        name: Pattern name to validate
        
    Returns:
        True if name is valid
    """
    if not name or not isinstance(name, str):
        return False
    
    # Check length
    if len(name) < 1 or len(name) > 50:
        return False
    
    # Check for valid characters (alphanumeric, underscores)
    if not re.match(r'^[a-zA-Z0-9_]+$', name):
        return False
    
    return True


def validate_severity(severity: str) -> bool:
    """
    Validate severity level.
    
    Args:
        severity: Severity string to validate
        
    Returns:
        True if severity is valid
    """
    valid_severities = ["critical", "high", "medium", "low", "info"]
    return severity.lower() in valid_severities


def validate_output_path(path: str) -> List[str]:
    """
    Validate output file path for security.
    
    Args:
        path: File path to validate
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    if not path:
        errors.append("Output path cannot be empty")
        return errors
    
    # Check for path traversal
    if '..' in path:
        errors.append("Path traversal not allowed in output path")
    
    # Check for absolute paths outside allowed directories
    if path.startswith('/') and not path.startswith('/tmp/') and not path.startswith('/var/tmp/'):
        errors.append("Absolute paths outside /tmp/ not allowed")
    
    # Check for potentially dangerous filenames
    dangerous_names = ['passwd', 'shadow', 'hosts', '.ssh', '.env']
    if any(name in path.lower() for name in dangerous_names):
        errors.append("Output path contains potentially dangerous filename")
    
    # Check file extension
    allowed_extensions = ['.json', '.yaml', '.yml', '.html', '.txt', '.log', '.sarif']
    if not any(path.lower().endswith(ext) for ext in allowed_extensions):
        errors.append(f"File extension must be one of: {allowed_extensions}")
    
    return errors