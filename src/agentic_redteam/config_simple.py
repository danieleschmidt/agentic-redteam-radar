"""
Simple configuration for Agentic RedTeam Radar without external dependencies.

Provides basic configuration classes using only standard library.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union


@dataclass
class ScannerConfig:
    """Scanner engine configuration."""
    max_concurrency: int = 5
    max_agent_concurrency: int = 3
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0
    scanner_version: str = "0.1.0"


@dataclass
class PatternConfig:
    """Attack pattern configuration."""
    enabled: bool = True
    severity_threshold: str = "low"
    max_attempts: int = 10
    timeout: int = 15
    max_payloads_per_pattern: int = 20


@dataclass
class DatabaseConfig:
    """Database configuration."""
    url: str = "sqlite:///radar_results.db"
    echo: bool = False
    pool_size: int = 10
    max_overflow: int = 20
    timeout: int = 30


@dataclass
class CacheConfig:
    """Cache configuration."""
    backend: str = "memory"
    url: Optional[str] = None
    default_ttl: int = 3600
    max_size: int = 1000


@dataclass
class ReportingConfig:
    """Reporting configuration."""
    format: str = "json"
    output_dir: str = "./reports"
    include_payloads: bool = False
    include_responses: bool = False
    compress: bool = True


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Optional[str] = None
    max_size: str = "10MB"
    backup_count: int = 5


@dataclass
class SecurityConfig:
    """Security configuration."""
    enable_input_sanitization: bool = True
    max_payload_size: int = 10000
    allowed_domains: List[str] = field(default_factory=list)
    blocked_patterns: List[str] = field(default_factory=list)
    audit_logging: bool = True


@dataclass
class RadarConfig:
    """Main configuration class for Agentic RedTeam Radar."""
    
    # Core configuration sections
    scanner: ScannerConfig = field(default_factory=ScannerConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    reporting: ReportingConfig = field(default_factory=ReportingConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    
    # Pattern configurations
    patterns: Dict[str, PatternConfig] = field(default_factory=dict)
    
    # Global settings
    enabled_patterns: Set[str] = field(default_factory=lambda: {
        "prompt_injection", 
        "info_disclosure", 
        "policy_bypass", 
        "chain_of_thought"
    })
    
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
    
    @property  
    def max_payloads_per_pattern(self) -> int:
        """Get max payloads per pattern."""
        return 20
        
    @property
    def pattern_concurrency(self) -> int:
        """Get pattern concurrency limit."""
        return 3
        
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
        def dataclass_to_dict(obj):
            if hasattr(obj, '__dataclass_fields__'):
                return {k: dataclass_to_dict(v) for k, v in obj.__dict__.items()}
            elif isinstance(obj, (list, tuple)):
                return [dataclass_to_dict(item) for item in obj]
            elif isinstance(obj, dict):
                return {k: dataclass_to_dict(v) for k, v in obj.items()}
            elif isinstance(obj, set):
                return list(obj)
            else:
                return obj
        
        return dataclass_to_dict(self)
    
    def to_json(self, indent: int = 2) -> str:
        """Convert configuration to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RadarConfig":
        """Create configuration from dictionary."""
        # Convert nested dictionaries to dataclass instances
        config_data = {}
        
        for key, value in data.items():
            if key == "scanner" and isinstance(value, dict):
                config_data[key] = ScannerConfig(**value)
            elif key == "database" and isinstance(value, dict):
                config_data[key] = DatabaseConfig(**value)
            elif key == "cache" and isinstance(value, dict):
                config_data[key] = CacheConfig(**value)
            elif key == "reporting" and isinstance(value, dict):
                config_data[key] = ReportingConfig(**value)
            elif key == "logging" and isinstance(value, dict):
                config_data[key] = LoggingConfig(**value)
            elif key == "security" and isinstance(value, dict):
                config_data[key] = SecurityConfig(**value)
            elif key == "patterns" and isinstance(value, dict):
                patterns = {}
                for pattern_name, pattern_data in value.items():
                    if isinstance(pattern_data, dict):
                        patterns[pattern_name] = PatternConfig(**pattern_data)
                    else:
                        patterns[pattern_name] = pattern_data
                config_data[key] = patterns
            elif key == "enabled_patterns" and isinstance(value, list):
                config_data[key] = set(value)
            else:
                config_data[key] = value
        
        return cls(**config_data)
    
    @classmethod
    def from_json(cls, json_str: str) -> "RadarConfig":
        """Create configuration from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


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
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if config_file.suffix.lower() == '.json':
                config = RadarConfig.from_json(content)
                config_data = config.to_dict()
    
    # Merge environment variables if requested
    if merge_env:
        env_config = _load_from_env(env_prefix)
        config_data = _deep_merge(config_data, env_config)
    
    # Create and return final configuration
    if config_data:
        return RadarConfig.from_dict(config_data)
    else:
        return RadarConfig()


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
    }
    
    for env_var, config_path in env_mappings.items():
        value = os.getenv(env_var)
        if value is not None:
            # Parse value based on type
            if env_var.endswith("_CONCURRENCY") or env_var.endswith("_TIMEOUT"):
                try:
                    value = int(value)
                except ValueError:
                    continue
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