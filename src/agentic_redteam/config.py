"""
Configuration management for Agentic RedTeam Radar.

Handles scanner settings, attack pattern configuration,
and runtime parameters.
"""

import os
import logging
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union


@dataclass
class RadarConfig:
    """
    Configuration class for the RadarScanner.
    
    Manages all scanner settings including concurrency,
    timeouts, enabled patterns, and reporting options.
    """
    
    # Core scanner settings
    max_concurrency: int = 5
    max_agent_concurrency: int = 3
    pattern_concurrency: int = 2
    timeout: int = 30
    retry_attempts: int = 3
    max_payloads_per_pattern: int = 20
    
    # Logging configuration
    log_level: str = "INFO"
    log_file: Optional[str] = None
    enable_debug: bool = False
    
    # Pattern configuration
    enabled_patterns: List[str] = field(default_factory=lambda: [
        "prompt_injection",
        "info_disclosure", 
        "policy_bypass",
        "chain_of_thought"
    ])
    
    pattern_settings: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Severity filtering
    min_severity: str = "low"
    severity_threshold: str = "medium"
    fail_on_severity: str = "high"
    
    # Output configuration
    output_format: str = "json"
    output_dir: str = "./reports"
    include_payloads: bool = False
    include_responses: bool = True
    save_artifacts: bool = True
    
    # Performance settings
    rate_limit_requests_per_minute: int = 60
    cache_results: bool = True
    cache_ttl: int = 3600  # 1 hour
    
    # Security settings
    sanitize_output: bool = True
    redact_sensitive_data: bool = True
    allowed_domains: List[str] = field(default_factory=list)
    blocked_domains: List[str] = field(default_factory=list)
    
    # Scanner metadata
    scanner_version: str = "0.1.0"
    user_agent: str = "Agentic-RedTeam-Radar/0.1.0"
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_config()
        self._setup_defaults()
    
    def _validate_config(self) -> None:
        """Validate configuration values."""
        if self.max_concurrency <= 0:
            raise ValueError("max_concurrency must be positive")
        
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
        
        if self.retry_attempts < 0:
            raise ValueError("retry_attempts cannot be negative")
        
        valid_severities = ["critical", "high", "medium", "low", "info"]
        if self.min_severity not in valid_severities:
            raise ValueError(f"min_severity must be one of: {valid_severities}")
        
        valid_formats = ["json", "yaml", "html", "sarif"]
        if self.output_format not in valid_formats:
            raise ValueError(f"output_format must be one of: {valid_formats}")
        
        if self.rate_limit_requests_per_minute <= 0:
            raise ValueError("rate_limit_requests_per_minute must be positive")
    
    def _setup_defaults(self) -> None:
        """Setup default pattern settings."""
        if not self.pattern_settings:
            self.pattern_settings = {
                "prompt_injection": {
                    "enabled": True,
                    "severity_threshold": "medium",
                    "max_payloads": 15
                },
                "info_disclosure": {
                    "enabled": True,
                    "severity_threshold": "medium", 
                    "max_payloads": 10
                },
                "policy_bypass": {
                    "enabled": True,
                    "severity_threshold": "high",
                    "max_payloads": 12
                },
                "chain_of_thought": {
                    "enabled": True,
                    "severity_threshold": "medium",
                    "max_payloads": 8
                }
            }
    
    @classmethod
    def from_file(cls, config_path: Union[str, Path]) -> "RadarConfig":
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            RadarConfig instance
        """
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        if yaml is None:
            raise ImportError("PyYAML not installed. Install with: pip install pyyaml")
        
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        return cls.from_dict(config_data)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "RadarConfig":
        """
        Create configuration from dictionary.
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            RadarConfig instance
        """
        # Extract nested configurations
        scanner_config = config_dict.get("scanner", {})
        pattern_config = config_dict.get("patterns", {})
        output_config = config_dict.get("output", {})
        security_config = config_dict.get("security", {})
        
        # Build configuration arguments
        config_args = {}
        
        # Scanner settings
        if "max_concurrency" in scanner_config:
            config_args["max_concurrency"] = scanner_config["max_concurrency"]
        if "timeout" in scanner_config:
            config_args["timeout"] = scanner_config["timeout"]
        if "retry_attempts" in scanner_config:
            config_args["retry_attempts"] = scanner_config["retry_attempts"]
        
        # Pattern settings
        if "enabled" in pattern_config:
            config_args["enabled_patterns"] = pattern_config["enabled"]
        if "settings" in pattern_config:
            config_args["pattern_settings"] = pattern_config["settings"]
        
        # Output settings
        if "format" in output_config:
            config_args["output_format"] = output_config["format"]
        if "directory" in output_config:
            config_args["output_dir"] = output_config["directory"]
        if "include_payloads" in output_config:
            config_args["include_payloads"] = output_config["include_payloads"]
        
        # Security settings
        if "sanitize_output" in security_config:
            config_args["sanitize_output"] = security_config["sanitize_output"]
        if "allowed_domains" in security_config:
            config_args["allowed_domains"] = security_config["allowed_domains"]
        
        return cls(**config_args)
    
    @classmethod
    def from_env(cls) -> "RadarConfig":
        """
        Create configuration from environment variables.
        
        Returns:
            RadarConfig instance
        """
        config_args = {}
        
        # Map environment variables to config fields
        env_mapping = {
            "RADAR_MAX_CONCURRENCY": ("max_concurrency", int),
            "RADAR_TIMEOUT": ("timeout", int),
            "RADAR_RETRY_ATTEMPTS": ("retry_attempts", int),
            "RADAR_LOG_LEVEL": ("log_level", str),
            "RADAR_OUTPUT_FORMAT": ("output_format", str),
            "RADAR_OUTPUT_DIR": ("output_dir", str),
            "RADAR_INCLUDE_PAYLOADS": ("include_payloads", bool),
            "RADAR_MIN_SEVERITY": ("min_severity", str),
            "RADAR_FAIL_ON_SEVERITY": ("fail_on_severity", str),
            "RADAR_RATE_LIMIT": ("rate_limit_requests_per_minute", int),
            "RADAR_SANITIZE_OUTPUT": ("sanitize_output", bool)
        }
        
        for env_var, (config_key, config_type) in env_mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                if config_type == bool:
                    config_args[config_key] = value.lower() in ("true", "1", "yes", "on")
                elif config_type == int:
                    config_args[config_key] = int(value)
                else:
                    config_args[config_key] = value
        
        # Handle list environment variables
        if "RADAR_ENABLED_PATTERNS" in os.environ:
            patterns = os.environ["RADAR_ENABLED_PATTERNS"].split(",")
            config_args["enabled_patterns"] = [p.strip() for p in patterns]
        
        if "RADAR_ALLOWED_DOMAINS" in os.environ:
            domains = os.environ["RADAR_ALLOWED_DOMAINS"].split(",")
            config_args["allowed_domains"] = [d.strip() for d in domains]
        
        return cls(**config_args)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.
        
        Returns:
            Configuration dictionary
        """
        return {
            "scanner": {
                "max_concurrency": self.max_concurrency,
                "max_agent_concurrency": self.max_agent_concurrency,
                "pattern_concurrency": self.pattern_concurrency,
                "timeout": self.timeout,
                "retry_attempts": self.retry_attempts,
                "max_payloads_per_pattern": self.max_payloads_per_pattern
            },
            "logging": {
                "log_level": self.log_level,
                "log_file": self.log_file,
                "enable_debug": self.enable_debug
            },
            "patterns": {
                "enabled": self.enabled_patterns,
                "settings": self.pattern_settings
            },
            "severity": {
                "min_severity": self.min_severity,
                "severity_threshold": self.severity_threshold,
                "fail_on_severity": self.fail_on_severity
            },
            "output": {
                "format": self.output_format,
                "directory": self.output_dir,
                "include_payloads": self.include_payloads,
                "include_responses": self.include_responses,
                "save_artifacts": self.save_artifacts
            },
            "performance": {
                "rate_limit_requests_per_minute": self.rate_limit_requests_per_minute,
                "cache_results": self.cache_results,
                "cache_ttl": self.cache_ttl
            },
            "security": {
                "sanitize_output": self.sanitize_output,
                "redact_sensitive_data": self.redact_sensitive_data,
                "allowed_domains": self.allowed_domains,
                "blocked_domains": self.blocked_domains
            }
        }
    
    def to_yaml(self) -> str:
        """
        Convert configuration to YAML string.
        
        Returns:
            YAML configuration string
        """
        if yaml is None:
            raise ImportError("PyYAML not installed. Install with: pip install pyyaml")
        return yaml.dump(self.to_dict(), default_flow_style=False, indent=2)
    
    def save_to_file(self, config_path: Union[str, Path]) -> None:
        """
        Save configuration to YAML file.
        
        Args:
            config_path: Path to save configuration file
        """
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w') as f:
            f.write(self.to_yaml())
    
    def get_pattern_config(self, pattern_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific pattern.
        
        Args:
            pattern_name: Name of the pattern
            
        Returns:
            Pattern configuration dictionary
        """
        return self.pattern_settings.get(pattern_name, {})
    
    def is_pattern_enabled(self, pattern_name: str) -> bool:
        """
        Check if a pattern is enabled.
        
        Args:
            pattern_name: Name of the pattern
            
        Returns:
            True if pattern is enabled
        """
        return pattern_name.lower() in [p.lower() for p in self.enabled_patterns]
    
    def should_fail_on_result(self, severity: str) -> bool:
        """
        Check if scan should fail based on result severity.
        
        Args:
            severity: Vulnerability severity
            
        Returns:
            True if scan should fail
        """
        severity_levels = {
            "info": 0,
            "low": 1, 
            "medium": 2,
            "high": 3,
            "critical": 4
        }
        
        result_level = severity_levels.get(severity.lower(), 0)
        fail_level = severity_levels.get(self.fail_on_severity.lower(), 4)
        
        return result_level >= fail_level