"""
Output sanitization utilities for Agentic RedTeam Radar.

Provides functions to sanitize outputs and redact sensitive information
from scan results and logs for security purposes.
"""

import re
import json
from typing import Any, Dict, List, Union


class SensitiveDataPattern:
    """Patterns for detecting sensitive data."""
    
    # API Keys and tokens
    API_KEY_PATTERNS = [
        r'[Aa][Pp][Ii]_?[Kk][Ee][Yy]\s*[:=]\s*["\']?([A-Za-z0-9\-_]{20,})["\']?',
        r'[Tt][Oo][Kk][Ee][Nn]\s*[:=]\s*["\']?([A-Za-z0-9\-_]{20,})["\']?',
        r'[Aa][Cc][Cc][Ee][Ss][Ss]_?[Tt][Oo][Kk][Ee][Nn]\s*[:=]\s*["\']?([A-Za-z0-9\-_]{20,})["\']?',
        r'[Bb][Ee][Aa][Rr][Ee][Rr]\s+([A-Za-z0-9\-_\+/]{20,})',
        r'sk-[A-Za-z0-9]{20,}',  # OpenAI API keys
        r'anthropic_[A-Za-z0-9]{20,}',  # Anthropic API keys
    ]
    
    # Passwords and secrets
    PASSWORD_PATTERNS = [
        r'[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]\s*[:=]\s*["\']?([^\s"\']{8,})["\']?',
        r'[Ss][Ee][Cc][Rr][Ee][Tt]\s*[:=]\s*["\']?([^\s"\']{8,})["\']?',
        r'[Cc][Rr][Ee][Dd][Ee][Nn][Tt][Ii][Aa][Ll]\s*[:=]\s*["\']?([^\s"\']{8,})["\']?',
    ]
    
    # Personal Identifiable Information
    PII_PATTERNS = [
        r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
        r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',  # Credit card numbers
        r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',  # IP addresses
    ]
    
    # Database connection strings
    DB_CONNECTION_PATTERNS = [
        r'[Cc][Oo][Nn][Nn][Ee][Cc][Tt][Ii][Oo][Nn]_?[Ss][Tt][Rr][Ii][Nn][Gg]\s*[:=]\s*["\']?([^"\']+)["\']?',
        r'mongodb://[^\s"\']+',
        r'postgresql://[^\s"\']+',
        r'mysql://[^\s"\']+',
    ]


def sanitize_output(
    data: Union[str, Dict, List], 
    redact_patterns: bool = True,
    max_length: int = 10000
) -> Union[str, Dict, List]:
    """
    Sanitize output data by removing or redacting sensitive information.
    
    Args:
        data: Data to sanitize (string, dict, or list)
        redact_patterns: Whether to redact sensitive patterns
        max_length: Maximum length for string outputs
        
    Returns:
        Sanitized data
    """
    if isinstance(data, str):
        return _sanitize_string(data, redact_patterns, max_length)
    elif isinstance(data, dict):
        return _sanitize_dict(data, redact_patterns, max_length)
    elif isinstance(data, list):
        return _sanitize_list(data, redact_patterns, max_length)
    else:
        return data


def _sanitize_string(text: str, redact_patterns: bool, max_length: int) -> str:
    """Sanitize a string value."""
    if not isinstance(text, str):
        return text
    
    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length] + "... [TRUNCATED]"
    
    if redact_patterns:
        text = redact_sensitive_data(text)
    
    return text


def _sanitize_dict(data: Dict, redact_patterns: bool, max_length: int) -> Dict:
    """Sanitize a dictionary."""
    sanitized = {}
    
    for key, value in data.items():
        # Check if key itself is sensitive
        if _is_sensitive_key(key):
            sanitized[key] = "[REDACTED]"
        else:
            sanitized[key] = sanitize_output(value, redact_patterns, max_length)
    
    return sanitized


def _sanitize_list(data: List, redact_patterns: bool, max_length: int) -> List:
    """Sanitize a list."""
    return [sanitize_output(item, redact_patterns, max_length) for item in data]


def _is_sensitive_key(key: str) -> bool:
    """Check if a dictionary key indicates sensitive data."""
    sensitive_keys = [
        'api_key', 'apikey', 'api-key',
        'password', 'passwd', 'pwd',
        'secret', 'private_key', 'privatekey',
        'token', 'access_token', 'refresh_token',
        'credential', 'auth', 'authorization',
        'connection_string', 'conn_str',
        'database_url', 'db_url'
    ]
    
    return key.lower() in sensitive_keys


def redact_sensitive_data(text: str) -> str:
    """
    Redact sensitive data patterns from text.
    
    Args:
        text: Text to redact
        
    Returns:
        Text with sensitive data redacted
    """
    if not isinstance(text, str):
        return text
    
    redacted_text = text
    
    # Redact API keys and tokens
    for pattern in SensitiveDataPattern.API_KEY_PATTERNS:
        redacted_text = re.sub(pattern, '[API_KEY_REDACTED]', redacted_text, flags=re.IGNORECASE)
    
    # Redact passwords and secrets
    for pattern in SensitiveDataPattern.PASSWORD_PATTERNS:
        redacted_text = re.sub(pattern, '[PASSWORD_REDACTED]', redacted_text, flags=re.IGNORECASE)
    
    # Redact PII
    for pattern in SensitiveDataPattern.PII_PATTERNS:
        redacted_text = re.sub(pattern, '[PII_REDACTED]', redacted_text)
    
    # Redact database connection strings
    for pattern in SensitiveDataPattern.DB_CONNECTION_PATTERNS:
        redacted_text = re.sub(pattern, '[DB_CONNECTION_REDACTED]', redacted_text, flags=re.IGNORECASE)
    
    return redacted_text


def sanitize_payload_content(content: str) -> str:
    """
    Sanitize attack payload content for safe storage and display.
    
    Args:
        content: Payload content to sanitize
        
    Returns:
        Sanitized content safe for storage
    """
    if not isinstance(content, str):
        return content
    
    # Remove potentially harmful shell commands
    harmful_commands = [
        r'rm\s+-rf\s+/',
        r'del\s+/[qfs]',
        r'format\s+c:',
        r'shutdown\s+',
        r'reboot\s+',
        r'mkfs\s+',
        r'dd\s+if=.*of=',
    ]
    
    sanitized = content
    for pattern in harmful_commands:
        sanitized = re.sub(pattern, '[HARMFUL_COMMAND_REDACTED]', sanitized, flags=re.IGNORECASE)
    
    # Redact other sensitive patterns
    sanitized = redact_sensitive_data(sanitized)
    
    # Limit length
    if len(sanitized) > 1000:
        sanitized = sanitized[:1000] + "... [TRUNCATED]"
    
    return sanitized


def sanitize_response_content(response: str) -> str:
    """
    Sanitize agent response content for safe storage and display.
    
    Args:
        response: Agent response to sanitize
        
    Returns:
        Sanitized response safe for storage
    """
    if not isinstance(response, str):
        return response
    
    sanitized = response
    
    # Redact sensitive data
    sanitized = redact_sensitive_data(sanitized)
    
    # Remove potential HTML/script content for safety
    sanitized = re.sub(r'<script[^>]*>.*?</script>', '[SCRIPT_REMOVED]', sanitized, flags=re.IGNORECASE | re.DOTALL)
    sanitized = re.sub(r'<[^>]+>', '', sanitized)  # Remove HTML tags
    
    # Limit length for storage efficiency
    if len(sanitized) > 5000:
        sanitized = sanitized[:5000] + "... [TRUNCATED]"
    
    return sanitized


def create_redacted_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a redacted summary suitable for sharing or logging.
    
    Args:
        data: Original data dictionary
        
    Returns:
        Redacted summary dictionary
    """
    summary = {}
    
    # Safe fields to include
    safe_fields = [
        'agent_name', 'scan_duration', 'patterns_executed', 'total_tests',
        'scanner_version', 'timestamp', 'total_vulnerabilities',
        'vulnerabilities_by_severity', 'vulnerabilities_by_category'
    ]
    
    for field in safe_fields:
        if field in data:
            summary[field] = data[field]
    
    # Include vulnerability names but not details
    if 'vulnerabilities' in data:
        summary['vulnerability_names'] = [
            vuln.get('name', 'Unknown') for vuln in data['vulnerabilities']
        ]
        summary['vulnerability_count'] = len(data['vulnerabilities'])
    
    # Include agent type but not full config
    if 'agent_config' in data and isinstance(data['agent_config'], dict):
        agent_config = data['agent_config']
        summary['agent_type'] = agent_config.get('type', 'Unknown')
        summary['agent_model'] = agent_config.get('model', 'Unknown')
    
    return summary


def validate_sanitized_output(data: Union[str, Dict, List]) -> bool:
    """
    Validate that output has been properly sanitized.
    
    Args:
        data: Data to validate
        
    Returns:
        True if data appears properly sanitized
    """
    # Convert to string for pattern checking
    if isinstance(data, (dict, list)):
        text = json.dumps(data, default=str)
    else:
        text = str(data)
    
    # Check for common sensitive patterns
    sensitive_indicators = [
        r'sk-[A-Za-z0-9]{20,}',  # OpenAI keys
        r'anthropic_[A-Za-z0-9]{20,}',  # Anthropic keys
        r'password\s*[:=]\s*[^\s]{8,}',  # Passwords
        r'\d{3}-\d{2}-\d{4}',  # SSN
        r'\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}',  # Credit cards
    ]
    
    for pattern in sensitive_indicators:
        if re.search(pattern, text, re.IGNORECASE):
            return False
    
    return True