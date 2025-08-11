"""
Advanced input sanitization for Agentic RedTeam Radar.

Provides comprehensive input validation, sanitization, and security controls
to prevent injection attacks and ensure safe operation.
"""

import re
import html
import json
import base64
import logging
from typing import Any, Dict, List, Optional, Union, Tuple
from urllib.parse import urlparse, unquote
from pathlib import Path


class SecurityPolicy:
    """Security policy configuration for input sanitization."""
    
    def __init__(
        self,
        max_input_length: int = 10000,
        max_payload_count: int = 100,
        allow_html: bool = False,
        allow_javascript: bool = False,
        allow_sql: bool = False,
        allow_shell_commands: bool = False,
        allow_file_paths: bool = False,
        blocked_patterns: Optional[List[str]] = None,
        allowed_protocols: Optional[List[str]] = None
    ):
        """
        Initialize security policy.
        
        Args:
            max_input_length: Maximum length for input strings
            max_payload_count: Maximum number of payloads per request
            allow_html: Whether to allow HTML content
            allow_javascript: Whether to allow JavaScript content
            allow_sql: Whether to allow SQL-like content
            allow_shell_commands: Whether to allow shell commands
            allow_file_paths: Whether to allow file system paths
            blocked_patterns: List of regex patterns to block
            allowed_protocols: List of allowed URL protocols
        """
        self.max_input_length = max_input_length
        self.max_payload_count = max_payload_count
        self.allow_html = allow_html
        self.allow_javascript = allow_javascript
        self.allow_sql = allow_sql
        self.allow_shell_commands = allow_shell_commands
        self.allow_file_paths = allow_file_paths
        self.blocked_patterns = blocked_patterns or []
        self.allowed_protocols = allowed_protocols or ['http', 'https']


class InputSanitizer:
    """
    Advanced input sanitizer with configurable security policies.
    
    Provides comprehensive protection against various injection attacks
    while maintaining usability for legitimate security testing.
    """
    
    # Dangerous patterns that should be blocked by default
    DANGEROUS_PATTERNS = {
        'javascript': [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'eval\s*\(',
            r'setTimeout\s*\(',
            r'setInterval\s*\(',
            r'document\.',
            r'window\.',
            r'alert\s*\(',
            r'confirm\s*\(',
            r'prompt\s*\('
        ],
        'sql': [
            r';\s*DROP\s+TABLE',
            r';\s*DELETE\s+FROM',
            r';\s*INSERT\s+INTO',
            r';\s*UPDATE\s+\w+\s+SET',
            r'UNION\s+SELECT',
            r'OR\s+1\s*=\s*1',
            r'AND\s+1\s*=\s*1',
            r';\s*EXEC\s*\(',
            r'xp_cmdshell',
            r'sp_executesql'
        ],
        'shell': [
            r'rm\s+-rf\s*/',
            r'del\s+/[qfs]',
            r'format\s+c:',
            r'shutdown\s+',
            r'reboot\s+',
            r'halt\s+',
            r'init\s+[06]',
            r'kill\s+-9',
            r'killall\s+',
            r'mkfs\s+',
            r'dd\s+if=.*of=',
            r'>\s*/dev/(null|zero)',
            r'\|\s*nc\s+',
            r'\|\s*netcat\s+'
        ],
        'path_traversal': [
            r'\.\./',
            r'\.\.\\',
            r'/etc/passwd',
            r'/etc/shadow',
            r'/proc/self/',
            r'\\windows\\system32',
            r'%SYSTEMROOT%',
            r'~/.ssh/',
            r'/root/',
            r'C:\\\\Users'
        ],
        'code_injection': [
            r'import\s+os',
            r'import\s+subprocess',
            r'import\s+sys',
            r'__import__\s*\(',
            r'exec\s*\(',
            r'eval\s*\(',
            r'compile\s*\(',
            r'globals\s*\(',
            r'locals\s*\(',
            r'vars\s*\(',
            r'dir\s*\(',
            r'getattr\s*\(',
            r'setattr\s*\(',
            r'hasattr\s*\('
        ]
    }
    
    def __init__(self, policy: Optional[SecurityPolicy] = None):
        """
        Initialize input sanitizer with security policy.
        
        Args:
            policy: Security policy configuration
        """
        self.policy = policy or SecurityPolicy()
        self._compile_patterns()
    
    def _compile_patterns(self) -> None:
        """Compile regex patterns for performance."""
        self.compiled_patterns = {}
        
        for category, patterns in self.DANGEROUS_PATTERNS.items():
            self.compiled_patterns[category] = [
                re.compile(pattern, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                for pattern in patterns
            ]
        
        # Compile custom blocked patterns
        if self.policy.blocked_patterns:
            self.compiled_patterns['custom'] = [
                re.compile(pattern, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                for pattern in self.policy.blocked_patterns
            ]
    
    def sanitize_string(self, text: str, context: str = "general") -> Tuple[str, List[str]]:
        """
        Sanitize a string input with context-aware filtering.
        
        Args:
            text: Input text to sanitize
            context: Context for sanitization (attack_payload, config, general)
            
        Returns:
            Tuple of (sanitized_text, warnings)
        """
        if not text or not isinstance(text, str):
            return "", []
        
        warnings = []
        sanitized = text
        # Length check
        if len(text) > self.policy.max_input_length:
            sanitized = text[:self.policy.max_input_length]
            warnings.append(f"Input truncated to {self.policy.max_input_length} characters")
        
        # HTML sanitization
        if not self.policy.allow_html:
            if '<' in sanitized and '>' in sanitized:
                sanitized = html.escape(sanitized)
                warnings.append("HTML tags escaped")
        
        # Remove null bytes and control characters
        sanitized = sanitized.replace('\\x00', '').replace('\\0', '')
        sanitized = re.sub(r'[\\x00-\\x08\\x0B\\x0C\\x0E-\\x1F\\x7F]', '', sanitized)
        
        # Check for dangerous patterns
        for category, compiled_patterns in self.compiled_patterns.items():
            if self._should_check_category(category, context):
                for pattern in compiled_patterns:
                    if pattern.search(sanitized):
                        warnings.append(f"Potentially dangerous {category} pattern detected")
                        # For attack payloads, we might allow these patterns but log them
                        if context != "attack_payload":
                            sanitized = pattern.sub('[BLOCKED]', sanitized)
        
        # Unicode normalization
        try:
            import unicodedata
            sanitized = unicodedata.normalize('NFKC', sanitized)
        except ImportError:
            pass  # unicodedata should be available in standard library
        
        return sanitized, warnings
    
    def _should_check_category(self, category: str, context: str) -> bool:
        """Determine if a category should be checked based on context."""
        if context == "attack_payload":
            # For attack payloads, we're more permissive but still log
            return category in ['shell', 'path_traversal', 'code_injection']
        
        # Map categories to policy settings
        category_map = {
            'javascript': not self.policy.allow_javascript,
            'sql': not self.policy.allow_sql,
            'shell': not self.policy.allow_shell_commands,
            'path_traversal': not self.policy.allow_file_paths,
            'code_injection': True,  # Always check
            'custom': True  # Always check custom patterns
        }
        
        return category_map.get(category, True)
    
    def sanitize_url(self, url: str) -> Tuple[str, List[str]]:
        """
        Sanitize and validate URL input.
        
        Args:
            url: URL to sanitize
            
        Returns:
            Tuple of (sanitized_url, warnings)
        """
        if not url:
            return "", []
        
        warnings = []
        
        try:
            # Parse URL
            parsed = urlparse(url)
            
            # Check protocol
            if parsed.scheme and parsed.scheme not in self.policy.allowed_protocols:
                warnings.append(f"Protocol {parsed.scheme} not allowed")
                return "", warnings
            
            # Check for dangerous hosts
            dangerous_hosts = ['localhost', '127.0.0.1', '0.0.0.0', '::1']
            if parsed.netloc.lower() in dangerous_hosts:
                warnings.append("Localhost/loopback URLs not allowed")
                return "", warnings
            
            # Check for private IP ranges
            if self._is_private_ip(parsed.netloc):
                warnings.append("Private IP addresses not allowed")
                return "", warnings
            
            # URL decode and check for injection
            decoded_url = unquote(url)
            if decoded_url != url:
                sanitized_decoded, decode_warnings = self.sanitize_string(decoded_url, "general")
                warnings.extend(decode_warnings)
                if '[BLOCKED]' in sanitized_decoded:
                    return "", warnings
            
            return url, warnings
            
        except Exception as e:
            warnings.append(f"URL parsing error: {e}")
            return "", warnings
    
    def _is_private_ip(self, hostname: str) -> bool:
        """Check if hostname is a private IP address."""
        try:
            import ipaddress
            ip = ipaddress.ip_address(hostname)
            return ip.is_private
        except (ValueError, ImportError):
            return False
    
    def sanitize_json(self, json_data: Union[str, Dict, List]) -> Tuple[Any, List[str]]:
        """
        Sanitize JSON data recursively.
        
        Args:
            json_data: JSON data to sanitize
            
        Returns:
            Tuple of (sanitized_data, warnings)
        """
        warnings = []
        
        if isinstance(json_data, str):
            try:
                parsed = json.loads(json_data)
                return self.sanitize_json(parsed)
            except json.JSONDecodeError as e:
                warnings.append(f"Invalid JSON: {e}")
                return {}, warnings
        
        elif isinstance(json_data, dict):
            sanitized = {}
            for key, value in json_data.items():
                # Sanitize key
                clean_key, key_warnings = self.sanitize_string(str(key), "general")
                warnings.extend(key_warnings)
                
                # Sanitize value
                clean_value, value_warnings = self._sanitize_json_value(value)
                warnings.extend(value_warnings)
                
                sanitized[clean_key] = clean_value
            
            return sanitized, warnings
        
        elif isinstance(json_data, list):
            sanitized = []
            for item in json_data:
                clean_item, item_warnings = self._sanitize_json_value(item)
                warnings.extend(item_warnings)
                sanitized.append(clean_item)
            
            return sanitized, warnings
        
        else:
            return self._sanitize_json_value(json_data)
    
    def _sanitize_json_value(self, value: Any) -> Tuple[Any, List[str]]:
        """Sanitize individual JSON values."""
        warnings = []
        
        if isinstance(value, str):
            sanitized, str_warnings = self.sanitize_string(value, "general")
            warnings.extend(str_warnings)
            return sanitized, warnings
        
        elif isinstance(value, (dict, list)):
            return self.sanitize_json(value)
        
        elif isinstance(value, (int, float, bool)) or value is None:
            return value, warnings
        
        else:
            # Convert unknown types to string and sanitize
            sanitized, str_warnings = self.sanitize_string(str(value), "general")
            warnings.extend(str_warnings)
            return sanitized, warnings
    
    def sanitize_file_path(self, path: str) -> Tuple[str, List[str]]:
        """
        Sanitize file path input.
        
        Args:
            path: File path to sanitize
            
        Returns:
            Tuple of (sanitized_path, warnings)
        """
        if not path:
            return "", []
        
        warnings = []
        
        # Resolve path to prevent traversal
        try:
            resolved_path = Path(path).resolve()
            
            # Check if path escapes allowed directories
            allowed_dirs = ['/tmp', '/var/tmp', './reports', './data']
            is_allowed = any(
                str(resolved_path).startswith(str(Path(allowed_dir).resolve()))
                for allowed_dir in allowed_dirs
            )
            
            if not is_allowed:
                warnings.append("Path outside allowed directories")
                return "", warnings
            
            # Check for dangerous filenames
            dangerous_names = [
                'passwd', 'shadow', 'hosts', '.ssh', '.env', 'id_rsa',
                'config', 'secrets', 'keys', 'credentials'
            ]
            
            if any(dangerous in path.lower() for dangerous in dangerous_names):
                warnings.append("Potentially dangerous filename")
                return "", warnings
            
            return str(resolved_path), warnings
            
        except Exception as e:
            warnings.append(f"Path resolution error: {e}")
            return "", warnings
    
    def validate_attack_payload(self, payload: str) -> Tuple[bool, List[str]]:
        """
        Validate attack payload for safety while allowing test content.
        
        Args:
            payload: Attack payload to validate
            
        Returns:
            Tuple of (is_valid, warnings)
        """
        if not payload:
            return False, ["Empty payload"]
        
        warnings = []
        
        # Length check
        if len(payload) > self.policy.max_input_length:
            warnings.append(f"Payload exceeds maximum length of {self.policy.max_input_length}")
            return False, warnings
        
        # Check for extremely dangerous patterns that should never be allowed
        forbidden_patterns = [
            r'rm\s+-rf\s*/',  # Recursive delete
            r'format\s+c:',   # Format system drive
            r'del\s+/[qfs]\s+\\*',  # Windows recursive delete
            r'shutdown\s+-[fhr]',  # System shutdown
            r':(){ :|:& };:',  # Fork bomb
            r'chmod\s+777\s+/',  # Dangerous permissions
            r'dd\s+if=/dev/random\s+of=',  # Disk destruction
        ]
        
        for pattern in forbidden_patterns:
            if re.search(pattern, payload, re.IGNORECASE):
                warnings.append(f"Payload contains forbidden destructive pattern: {pattern}")
                return False, warnings
        
        # Log potentially dangerous but allowed patterns
        _, sanitize_warnings = self.sanitize_string(payload, "attack_payload")
        warnings.extend(sanitize_warnings)
        
        return True, warnings
    
    def get_security_headers(self) -> Dict[str, str]:
        """
        Get recommended security headers for HTTP responses.
        
        Returns:
            Dictionary of security headers
        """
        return {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self'; script-src 'none'; object-src 'none';",
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
            'Cache-Control': 'no-store, no-cache, must-revalidate',
            'Pragma': 'no-cache'
        }


class SecurityAuditLog:
    """Security audit logging for input sanitization events."""
    
    def __init__(self, logger=None):
        """Initialize security audit log."""
        if logger is None:
            import logging
            logger = logging.getLogger("agentic_redteam.security")
        self.logger = logger
    
    def log_sanitization(self, input_type: str, warnings: List[str], 
                        sanitized: bool = True, blocked: bool = False) -> None:
        """Log sanitization events."""
        level = logging.WARNING if blocked else logging.INFO
        action = "BLOCKED" if blocked else "SANITIZED" if sanitized else "ALLOWED"
        
        self.logger.log(level, 
            f"INPUT_{action}: type={input_type}, warnings={len(warnings)}, "
            f"details={'; '.join(warnings[:3])}")
    
    def log_security_violation(self, violation_type: str, details: str, 
                             source: str = "unknown") -> None:
        """Log security violations."""
        self.logger.error(
            f"SECURITY_VIOLATION: type={violation_type}, source={source}, "
            f"details={details[:200]}")
    
    def log_attack_attempt(self, attack_type: str, payload_hash: str,
                          blocked: bool = True) -> None:
        """Log potential attack attempts."""
        level = logging.WARNING
        status = "BLOCKED" if blocked else "ALLOWED"
        
        self.logger.log(level,
            f"ATTACK_ATTEMPT_{status}: type={attack_type}, "
            f"payload_hash={payload_hash}")