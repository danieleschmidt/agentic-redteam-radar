"""
Configuration management for Agentic RedTeam Radar.

This module provides configuration loading, validation, and management
for the security testing framework.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

try:
    import yaml
except ImportError:
    yaml = None

try:
    from pydantic import BaseModel, Field, validator
except ImportError:
    # Provide minimal compatibility without pydantic
    class BaseModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
        
        def dict(self):
            return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
    
    def Field(**kwargs):
        return kwargs.get('default')
    
    def validator(field):
        def decorator(func):
            return func
        return decorator


class ScannerConfig(BaseModel):
    """Scanner engine configuration."""
    
    max_concurrency: int = Field(default=5, ge=1, le=50, description="Maximum concurrent attack patterns")
    max_agent_concurrency: int = Field(default=3, ge=1, le=20, description="Maximum concurrent agents")
    timeout: int = Field(default=30, ge=5, le=300, description="Default timeout in seconds")
    retry_attempts: int = Field(default=3, ge=0, le=10, description="Retry attempts for failed requests")
    retry_delay: float = Field(default=1.0, ge=0.1, le=10.0, description="Delay between retries")
    scanner_version: str = Field(default="0.1.0", description="Scanner version")


class PatternConfig(BaseModel):
    """Attack pattern configuration."""
    
    enabled: bool = Field(default=True, description="Whether pattern is enabled")
    severity_threshold: str = Field(default="low", description="Minimum severity to report")
    max_attempts: int = Field(default=10, ge=1, le=100, description="Maximum test attempts per pattern")
    timeout: int = Field(default=15, ge=5, le=120, description="Pattern-specific timeout")
    
    @validator('severity_threshold')
    def validate_severity(cls, v):
        valid_severities = {'low', 'medium', 'high', 'critical'}
        if v.lower() not in valid_severities:
            raise ValueError(f"severity_threshold must be one of {valid_severities}")
        return v.lower()


class DatabaseConfig(BaseModel):
    """Database configuration."""
    
    url: str = Field(default="sqlite:///radar_results.db", description="Database URL")
    echo: bool = Field(default=False, description="Enable SQL query logging")
    pool_size: int = Field(default=10, ge=1, le=100, description="Connection pool size")
    max_overflow: int = Field(default=20, ge=0, le=100, description="Max overflow connections")
    timeout: int = Field(default=30, ge=5, le=300, description="Connection timeout")


class CacheConfig(BaseModel):
    """Cache configuration."""
    
    backend: str = Field(default="memory", description="Cache backend type")
    url: Optional[str] = Field(default=None, description="Cache backend URL (for Redis)")
    default_ttl: int = Field(default=3600, ge=60, le=86400, description="Default TTL in seconds")
    max_size: int = Field(default=1000, ge=10, le=100000, description="Maximum cache entries")
    
    @validator('backend')
    def validate_backend(cls, v):
        valid_backends = {'memory', 'redis', 'file'}
        if v.lower() not in valid_backends:
            raise ValueError(f"backend must be one of {valid_backends}")
        return v.lower()


class ReportingConfig(BaseModel):
    """Reporting configuration."""
    
    format: str = Field(default="json", description="Default report format")
    output_dir: str = Field(default="./reports", description="Output directory for reports")
    include_payloads: bool = Field(default=False, description="Include attack payloads in reports")
    include_responses: bool = Field(default=False, description="Include agent responses in reports")
    compress: bool = Field(default=True, description="Compress large reports")
    
    @validator('format')
    def validate_format(cls, v):
        valid_formats = {'json', 'yaml', 'html', 'csv', 'xml'}
        if v.lower() not in valid_formats:
            raise ValueError(f"format must be one of {valid_formats}")
        return v.lower()


class LoggingConfig(BaseModel):
    """Logging configuration."""
    
    level: str = Field(default="INFO", description="Log level")
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", description="Log format")
    file: Optional[str] = Field(default=None, description="Log file path")
    max_size: str = Field(default="10MB", description="Maximum log file size")
    backup_count: int = Field(default=5, ge=1, le=20, description="Number of backup files")
    
    @validator('level')
    def validate_level(cls, v):
        valid_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
        if v.upper() not in valid_levels:
            raise ValueError(f"level must be one of {valid_levels}")
        return v.upper()


class SecurityConfig(BaseModel):
    """Security configuration."""
    
    enable_input_sanitization: bool = Field(default=True, description="Enable input sanitization")
    max_payload_size: int = Field(default=10000, ge=100, le=1000000, description="Maximum payload size")
    allowed_domains: List[str] = Field(default_factory=list, description="Allowed domains for external requests")
    blocked_patterns: List[str] = Field(default_factory=list, description="Blocked payload patterns")
    audit_logging: bool = Field(default=True, description="Enable security audit logging")


class RadarConfig(BaseModel):
    """Main configuration class for Agentic RedTeam Radar."""
    
    # Core configuration sections
    scanner: ScannerConfig = Field(default_factory=ScannerConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    reporting: ReportingConfig = Field(default_factory=ReportingConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    
    # Pattern configurations
    patterns: Dict[str, PatternConfig] = Field(default_factory=dict)
    
    # Global settings
    enabled_patterns: Set[str] = None
    
    def __post_init__(self):
        """Post-initialization setup."""
        if self.enabled_patterns is None:
            self.enabled_patterns = {
                "prompt_injection", 
                "info_disclosure", 
                "policy_bypass", 
                "chain_of_thought"
            }
    
    # Convenience properties
    @property
    def max_concurrency(self) -> int:
        """Get scanner max concurrency."""
        return self.scanner.max_concurrency
    
    @property
    def max_agent_concurrency(self) -> int:
        """Get max agent concurrency."""
        return self.scanner.max_agent_concurrency
    
    @property
    def timeout(self) -> int:
        """Get default timeout."""
        return self.scanner.timeout
    
    @property
    def log_level(self) -> str:
        """Get log level."""
        return self.logging.level
    
    @property
    def scanner_version(self) -> str:
        """Get scanner version."""
        return self.scanner.scanner_version
    
    def get_pattern_config(self, pattern_name: str) -> PatternConfig:
        """Get configuration for specific pattern."""
        return self.patterns.get(pattern_name, PatternConfig())
    
    def enable_pattern(self, pattern_name: str) -> None:
        """Enable an attack pattern."""
        self.enabled_patterns.add(pattern_name)
        if pattern_name not in self.patterns:
            self.patterns[pattern_name] = PatternConfig(enabled=True)
        else:
            self.patterns[pattern_name].enabled = True
    
    def disable_pattern(self, pattern_name: str) -> None:
        """Disable an attack pattern."""
        self.enabled_patterns.discard(pattern_name)
        if pattern_name in self.patterns:
            self.patterns[pattern_name].enabled = False
    
    def is_pattern_enabled(self, pattern_name: str) -> bool:
        """Check if pattern is enabled."""
        return (pattern_name in self.enabled_patterns and 
                self.get_pattern_config(pattern_name).enabled)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.dict()
    
    def to_json(self, indent: int = 2) -> str:
        """Convert configuration to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)
    
    def to_yaml(self) -> str:
        """Convert configuration to YAML string."""
        if yaml is None:
            raise ImportError("PyYAML not available. Install with: pip install pyyaml")
        return yaml.dump(self.to_dict(), default_flow_style=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RadarConfig":
        """Create configuration from dictionary."""
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> "RadarConfig":
        """Create configuration from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    @classmethod
    def from_yaml(cls, yaml_str: str) -> "RadarConfig":
        """Create configuration from YAML string."""
        if yaml is None:
            raise ImportError("PyYAML not available. Install with: pip install pyyaml")
        data = yaml.safe_load(yaml_str)
        return cls.from_dict(data)
    
    @classmethod
    def from_file(cls, file_path: Union[str, Path]) -> "RadarConfig":
        """Load configuration from file."""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if file_path.suffix.lower() in ['.yml', '.yaml']:
            return cls.from_yaml(content)
        elif file_path.suffix.lower() == '.json':
            return cls.from_json(content)
        else:
            raise ValueError(f"Unsupported configuration file format: {file_path.suffix}")
    
    def save_to_file(self, file_path: Union[str, Path]) -> None:
        """Save configuration to file."""
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            if file_path.suffix.lower() in ['.yml', '.yaml']:
                f.write(self.to_yaml())
            elif file_path.suffix.lower() == '.json':
                f.write(self.to_json())
            else:
                raise ValueError(f"Unsupported configuration file format: {file_path.suffix}")


def load_config(
    config_file: Optional[Union[str, Path]] = None,
    env_prefix: str = "RADAR_",
    merge_env: bool = True
) -> RadarConfig:
    """
    Load configuration from file and environment variables.
    
    Args:
        config_file: Path to configuration file
        env_prefix: Prefix for environment variables
        merge_env: Whether to merge environment variables
        
    Returns:
        Loaded and validated configuration
    """
    # Start with default configuration
    config_data = {}
    
    # Load from file if provided
    if config_file:
        config_file = Path(config_file)
        if config_file.exists():
            config = RadarConfig.from_file(config_file)
            config_data = config.to_dict()
    
    # Merge environment variables if requested
    if merge_env:
        env_config = _load_from_env(env_prefix)
        config_data = _deep_merge(config_data, env_config)
    
    # Create and validate final configuration
    return RadarConfig.from_dict(config_data)


def _load_from_env(prefix: str) -> Dict[str, Any]:
    """Load configuration from environment variables."""
    env_config = {}
    
    # Map environment variables to config paths
    env_mappings = {
        f"{prefix}MAX_CONCURRENCY": ["scanner", "max_concurrency"],
        f"{prefix}MAX_AGENT_CONCURRENCY": ["scanner", "max_agent_concurrency"],
        f"{prefix}TIMEOUT": ["scanner", "timeout"],
        f"{prefix}LOG_LEVEL": ["logging", "level"],
        f"{prefix}DATABASE_URL": ["database", "url"],
        f"{prefix}CACHE_BACKEND": ["cache", "backend"],
        f"{prefix}CACHE_URL": ["cache", "url"],
        f"{prefix}REPORT_FORMAT": ["reporting", "format"],
        f"{prefix}REPORT_DIR": ["reporting", "output_dir"],
        f"{prefix}ENABLED_PATTERNS": ["enabled_patterns"],
    }
    
    for env_var, config_path in env_mappings.items():
        value = os.getenv(env_var)
        if value is not None:
            # Parse value based on type
            if env_var.endswith("_CONCURRENCY") or env_var.endswith("_TIMEOUT"):
                value = int(value)
            elif env_var.endswith("_PATTERNS"):
                value = set(value.split(","))
            elif value.lower() in ["true", "false"]:
                value = value.lower() == "true"
            
            # Set value in config dictionary
            _set_nested_value(env_config, config_path, value)
    
    return env_config


def _set_nested_value(dictionary: Dict[str, Any], path: List[str], value: Any) -> None:
    """Set a nested value in a dictionary."""
    for key in path[:-1]:
        if key not in dictionary:
            dictionary[key] = {}
        dictionary = dictionary[key]
    dictionary[path[-1]] = value


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries."""
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result


def create_default_config() -> RadarConfig:
    """Create a default configuration with sensible defaults."""
    return RadarConfig()


def validate_config(config: RadarConfig) -> List[str]:
    """
    Validate configuration and return list of issues.
    
    Args:
        config: Configuration to validate
        
    Returns:
        List of validation error messages
    """
    errors = []
    
    # Validate scanner configuration
    if config.scanner.max_concurrency <= 0:
        errors.append("scanner.max_concurrency must be positive")
    
    if config.scanner.timeout <= 0:
        errors.append("scanner.timeout must be positive")
    
    # Validate database configuration
    if not config.database.url:
        errors.append("database.url is required")
    
    # Validate output directory
    try:
        output_dir = Path(config.reporting.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        errors.append(f"Cannot create output directory: {e}")
    
    # Validate enabled patterns
    if not config.enabled_patterns:
        errors.append("At least one attack pattern must be enabled")
    
    return errors


# Configuration file templates
DEFAULT_CONFIG_YAML = """
# Agentic RedTeam Radar Configuration

scanner:
  max_concurrency: 5
  max_agent_concurrency: 3
  timeout: 30
  retry_attempts: 3
  retry_delay: 1.0

database:
  url: "sqlite:///radar_results.db"
  echo: false
  pool_size: 10

cache:
  backend: "memory"
  default_ttl: 3600
  max_size: 1000

reporting:
  format: "json"
  output_dir: "./reports"
  include_payloads: false
  include_responses: false

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

security:
  enable_input_sanitization: true
  max_payload_size: 10000
  audit_logging: true

enabled_patterns:
  - prompt_injection
  - info_disclosure
  - policy_bypass
  - chain_of_thought

patterns:
  prompt_injection:
    enabled: true
    severity_threshold: "low"
    max_attempts: 10
  
  info_disclosure:
    enabled: true
    severity_threshold: "medium"
    max_attempts: 15
"""


def generate_config_template(file_path: Union[str, Path]) -> None:
    """Generate a configuration template file."""
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(DEFAULT_CONFIG_YAML.strip())