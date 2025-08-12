"""
Input validation for ensuring data integrity and security.
"""

import re
import json
from typing import Any, Dict, List, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum

from ..utils.logger import get_logger


class ValidationSeverity(Enum):
    """Validation error severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationResult:
    """Result of validation check."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    sanitized_data: Any = None
    metadata: Dict[str, Any] = None


class ValidationError(Exception):
    """Exception raised for validation failures."""
    
    def __init__(self, message: str, errors: List[str] = None, severity: ValidationSeverity = ValidationSeverity.ERROR):
        super().__init__(message)
        self.errors = errors or []
        self.severity = severity


class InputValidator:
    """
    Comprehensive input validator for security and data integrity.
    """
    
    def __init__(self):
        self.logger = get_logger("agentic_redteam.validation")
        
        # Security patterns to detect
        self.security_patterns = {
            'sql_injection': [
                r"(?i)(union|select|insert|update|delete|drop|create|alter)\s+",
                r"(?i)(or|and)\s+\d+\s*=\s*\d+",
                r"(?i)exec\s*\(",
                r"(?i)script\s*:",
            ],
            'xss': [
                r"<script[^>]*>.*?</script>",
                r"javascript:",
                r"on\w+\s*=",
                r"<iframe[^>]*>",
            ],
            'command_injection': [
                r"[;&|`$]",
                r"(?i)(rm|del|format|shutdown|reboot)\s+",
                r"\.\./",
                r"eval\s*\(",
            ],
            'path_traversal': [
                r"\.\./",
                r"\.\.\\",
                r"/etc/passwd",
                r"windows/system32",
            ]
        }
    
    def validate_string(self, 
                       value: str, 
                       max_length: int = 10000,
                       min_length: int = 0,
                       allowed_chars: Optional[str] = None,
                       check_security: bool = True) -> ValidationResult:
        """
        Validate string input with security and length checks.
        
        Args:
            value: String to validate
            max_length: Maximum allowed length
            min_length: Minimum required length
            allowed_chars: Regex pattern of allowed characters
            check_security: Whether to perform security checks
            
        Returns:
            ValidationResult with validation outcome
        """
        errors = []
        warnings = []
        
        # Basic type check
        if not isinstance(value, str):
            errors.append(f"Expected string, got {type(value).__name__}")
            return ValidationResult(False, errors, warnings)
        
        # Length validation
        if len(value) > max_length:
            errors.append(f"String too long: {len(value)} > {max_length}")
        
        if len(value) < min_length:
            errors.append(f"String too short: {len(value)} < {min_length}")
        
        # Character validation
        if allowed_chars and not re.match(allowed_chars, value):
            errors.append("String contains invalid characters")
        
        # Security validation
        if check_security:
            security_issues = self._check_security_patterns(value)
            for issue_type, matches in security_issues.items():
                if matches:
                    if issue_type in ['sql_injection', 'command_injection']:
                        errors.append(f"Potential {issue_type} detected: {matches[:3]}")
                    else:
                        warnings.append(f"Potential {issue_type} detected: {matches[:3]}")
        
        # Sanitize if needed
        sanitized = self._sanitize_string(value) if warnings or errors else value
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            sanitized_data=sanitized,
            metadata={'original_length': len(value), 'sanitized_length': len(sanitized)}
        )
    
    def validate_json(self, 
                     value: Union[str, Dict], 
                     max_depth: int = 10,
                     max_size: int = 1000000) -> ValidationResult:
        """
        Validate JSON input for structure and security.
        
        Args:
            value: JSON string or dictionary
            max_depth: Maximum nesting depth
            max_size: Maximum JSON size in bytes
            
        Returns:
            ValidationResult with validation outcome
        """
        errors = []
        warnings = []
        parsed_data = None
        
        # Parse if string
        if isinstance(value, str):
            if len(value.encode('utf-8')) > max_size:
                errors.append(f"JSON too large: {len(value)} bytes > {max_size}")
                return ValidationResult(False, errors, warnings)
            
            try:
                parsed_data = json.loads(value)
            except json.JSONDecodeError as e:
                errors.append(f"Invalid JSON: {e}")
                return ValidationResult(False, errors, warnings)
        elif isinstance(value, dict):
            parsed_data = value
        else:
            errors.append(f"Expected JSON string or dict, got {type(value).__name__}")
            return ValidationResult(False, errors, warnings)
        
        # Depth validation
        depth = self._get_json_depth(parsed_data)
        if depth > max_depth:
            errors.append(f"JSON too deep: {depth} > {max_depth}")
        
        # Security validation for JSON values
        security_issues = self._check_json_security(parsed_data)
        for issue in security_issues:
            warnings.append(f"Security concern in JSON: {issue}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            sanitized_data=parsed_data,
            metadata={'depth': depth, 'keys': list(parsed_data.keys()) if isinstance(parsed_data, dict) else None}
        )
    
    def validate_agent_config(self, config: Dict[str, Any]) -> ValidationResult:
        """
        Validate agent configuration for completeness and security.
        
        Args:
            config: Agent configuration dictionary
            
        Returns:
            ValidationResult with validation outcome
        """
        errors = []
        warnings = []
        
        # Required fields
        required_fields = ['name', 'model']
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")
            elif not config[field]:
                errors.append(f"Empty required field: {field}")
        
        # Validate agent name
        if 'name' in config:
            name_result = self.validate_string(
                config['name'], 
                max_length=100, 
                min_length=1,
                allowed_chars=r'^[a-zA-Z0-9_-]+$'
            )
            if not name_result.is_valid:
                errors.extend([f"Agent name: {e}" for e in name_result.errors])
        
        # Validate model
        if 'model' in config:
            allowed_models = [
                'gpt-4', 'gpt-3.5-turbo', 'claude-3-sonnet', 'claude-3-haiku',
                'gemini-pro', 'llama-2', 'custom'
            ]
            if config['model'] not in allowed_models:
                warnings.append(f"Unknown model: {config['model']}")
        
        # Validate system prompt
        if 'system_prompt' in config and config['system_prompt']:
            prompt_result = self.validate_string(
                config['system_prompt'],
                max_length=50000,
                check_security=True
            )
            if not prompt_result.is_valid:
                errors.extend([f"System prompt: {e}" for e in prompt_result.errors])
            warnings.extend([f"System prompt: {w}" for w in prompt_result.warnings])
        
        # Validate tools
        if 'tools' in config:
            if not isinstance(config['tools'], list):
                errors.append("Tools must be a list")
            else:
                dangerous_tools = ['exec', 'eval', 'system', 'shell', 'file_system', 'network']
                for tool in config['tools']:
                    if any(dangerous in str(tool).lower() for dangerous in dangerous_tools):
                        warnings.append(f"Potentially dangerous tool: {tool}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            sanitized_data=config,
            metadata={'field_count': len(config)}
        )
    
    def _check_security_patterns(self, text: str) -> Dict[str, List[str]]:
        """Check text against security patterns."""
        findings = {}
        
        for pattern_type, patterns in self.security_patterns.items():
            matches = []
            for pattern in patterns:
                found = re.findall(pattern, text, re.IGNORECASE)
                matches.extend(found)
            findings[pattern_type] = matches[:5]  # Limit to 5 matches
        
        return findings
    
    def _sanitize_string(self, text: str) -> str:
        """Basic string sanitization."""
        # Remove potential script tags
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove potential XSS vectors
        text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
        text = re.sub(r'on\w+\s*=', '', text, flags=re.IGNORECASE)
        
        # Limit length
        return text[:10000]
    
    def _get_json_depth(self, obj: Any, current_depth: int = 0) -> int:
        """Calculate JSON nesting depth."""
        if isinstance(obj, dict):
            return max([self._get_json_depth(v, current_depth + 1) for v in obj.values()], default=current_depth)
        elif isinstance(obj, list):
            return max([self._get_json_depth(item, current_depth + 1) for item in obj], default=current_depth)
        else:
            return current_depth
    
    def _check_json_security(self, obj: Any) -> List[str]:
        """Check JSON object for security issues."""
        issues = []
        
        def check_recursive(item, path=""):
            if isinstance(item, str):
                security_findings = self._check_security_patterns(item)
                for pattern_type, matches in security_findings.items():
                    if matches:
                        issues.append(f"{pattern_type} in {path}: {matches[0]}")
            elif isinstance(item, dict):
                for key, value in item.items():
                    check_recursive(value, f"{path}.{key}")
            elif isinstance(item, list):
                for i, value in enumerate(item):
                    check_recursive(value, f"{path}[{i}]")
        
        check_recursive(obj)
        return issues


def validate_agent_input(agent_name: str, user_input: str, context: str = "general") -> ValidationResult:
    """
    Convenience function to validate agent input.
    
    Args:
        agent_name: Name of the agent
        user_input: User input to validate
        context: Context for validation
        
    Returns:
        ValidationResult with validation outcome
    """
    validator = InputValidator()
    
    # Validate agent name
    name_result = validator.validate_string(
        agent_name,
        max_length=100,
        allowed_chars=r'^[a-zA-Z0-9_-]+$'
    )
    
    if not name_result.is_valid:
        return ValidationResult(
            False, 
            [f"Invalid agent name: {e}" for e in name_result.errors], 
            []
        )
    
    # Validate user input
    input_result = validator.validate_string(
        user_input,
        max_length=50000,
        check_security=True
    )
    
    return ValidationResult(
        input_result.is_valid,
        input_result.errors,
        input_result.warnings,
        input_result.sanitized_data,
        {
            'agent_name': agent_name,
            'context': context,
            'input_length': len(user_input)
        }
    )