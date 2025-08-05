"""
Logging utilities for Agentic RedTeam Radar.

Provides structured logging with security-aware output handling.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

try:
    from rich.logging import RichHandler
    from rich.console import Console
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    RichHandler = None
    Console = None


class SecurityAwareFormatter(logging.Formatter):
    """Custom formatter that redacts sensitive information from logs."""
    
    SENSITIVE_PATTERNS = [
        "api_key", "password", "secret", "token", "credential",
        "auth", "bearer", "jwt", "private_key"
    ]
    
    def format(self, record):
        """Format log record with sensitive data redaction."""
        formatted = super().format(record)
        
        # Redact sensitive patterns
        for pattern in self.SENSITIVE_PATTERNS:
            if pattern in formatted.lower():
                # Simple redaction - replace with asterisks
                import re
                pattern_regex = rf"{pattern}['\"]?\s*[:=]\s*['\"]?[\w\-]+"
                formatted = re.sub(pattern_regex, f"{pattern}=***", formatted, flags=re.IGNORECASE)
        
        return formatted


def setup_logger(
    name: str,
    level: str = "INFO",
    log_file: Optional[str] = None,
    enable_rich: bool = True
) -> logging.Logger:
    """
    Setup a logger with security-aware formatting.
    
    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file to write logs to
        enable_rich: Whether to use rich formatting for console output
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Set level
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # Create formatter
    formatter = SecurityAwareFormatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler
    if enable_rich and RICH_AVAILABLE:
        console = Console(stderr=True)
        console_handler = RichHandler(
            console=console,
            show_path=False,
            rich_tracebacks=True,
            tracebacks_show_locals=False  # Security: don't show local variables
        )
    else:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Prevent propagation to avoid duplicate logs
    logger.propagate = False
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get an existing logger or create a basic one.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        # Setup basic logger if none exists
        return setup_logger(name)
    
    return logger


class AuditLogger:
    """
    Specialized logger for security audit events.
    
    Maintains detailed logs of security testing activities
    for compliance and analysis purposes.
    """
    
    def __init__(self, audit_file: str = "audit.log"):
        """
        Initialize audit logger.
        
        Args:
            audit_file: Path to audit log file
        """
        self.audit_file = audit_file
        self.logger = setup_logger(
            "agentic_redteam.audit",
            level="INFO",
            log_file=audit_file,
            enable_rich=False
        )
    
    def log_scan_start(self, agent_name: str, patterns: list, config: dict) -> None:
        """Log scan initialization."""
        self.logger.info(
            f"SCAN_START: agent={agent_name}, patterns={patterns}, "
            f"concurrency={config.get('max_concurrency', 'unknown')}"
        )
    
    def log_scan_complete(self, agent_name: str, duration: float, results: dict) -> None:
        """Log scan completion."""
        self.logger.info(
            f"SCAN_COMPLETE: agent={agent_name}, duration={duration:.2f}s, "
            f"vulnerabilities={results.get('total_vulnerabilities', 0)}, "
            f"risk_score={results.get('risk_score', 0):.2f}"
        )
    
    def log_vulnerability_found(self, agent_name: str, vuln_name: str, severity: str) -> None:
        """Log vulnerability discovery."""
        self.logger.warning(
            f"VULNERABILITY: agent={agent_name}, name={vuln_name}, severity={severity}"
        )
    
    def log_attack_executed(self, agent_name: str, attack_name: str, success: bool) -> None:
        """Log attack pattern execution."""
        status = "SUCCESS" if success else "FAILED"
        self.logger.info(
            f"ATTACK_EXECUTED: agent={agent_name}, attack={attack_name}, status={status}"
        )
    
    def log_error(self, component: str, error: str, context: dict = None) -> None:
        """Log error events."""
        context_str = f", context={context}" if context else ""
        self.logger.error(f"ERROR: component={component}, error={error}{context_str}")
    
    def log_security_event(self, event_type: str, details: dict) -> None:
        """Log general security events."""
        self.logger.info(f"SECURITY_EVENT: type={event_type}, details={details}")


class PerformanceLogger:
    """
    Logger for performance monitoring and optimization.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize performance logger.
        
        Args:
            logger: Optional logger instance to use
        """
        self.logger = logger or get_logger("agentic_redteam.performance")
    
    def log_timing(self, operation: str, duration: float, context: dict = None) -> None:
        """
        Log operation timing.
        
        Args:
            operation: Name of the operation
            duration: Duration in seconds
            context: Additional context information
        """
        context_str = f" {context}" if context else ""
        self.logger.info(f"TIMING: {operation} took {duration:.3f}s{context_str}")
    
    def log_concurrency(self, active_tasks: int, max_concurrency: int) -> None:
        """Log concurrency metrics."""
        utilization = (active_tasks / max_concurrency) * 100 if max_concurrency > 0 else 0
        self.logger.debug(
            f"CONCURRENCY: active={active_tasks}, max={max_concurrency}, "
            f"utilization={utilization:.1f}%"
        )
    
    def log_rate_limit(self, requests_per_minute: int, limit: int) -> None:
        """Log rate limiting metrics."""
        usage = (requests_per_minute / limit) * 100 if limit > 0 else 0
        self.logger.debug(
            f"RATE_LIMIT: current={requests_per_minute}/min, limit={limit}/min, "
            f"usage={usage:.1f}%"
        )