"""
Logging utilities for Agentic RedTeam Radar.

Provides centralized logging configuration with security-aware features.
"""

import logging
import logging.handlers
import sys
import os
import json
from pathlib import Path
from typing import Optional, Dict, Any, Union
from datetime import datetime


class SecurityAwareFormatter(logging.Formatter):
    """Custom formatter that sanitizes sensitive information."""
    
    SENSITIVE_PATTERNS = [
        'api_key', 'password', 'token', 'secret', 'auth',
        'Authorization', 'X-API-Key', 'Bearer'
    ]
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with security sanitization."""
        # Create a copy to avoid modifying the original
        record_dict = record.__dict__.copy()
        
        # Sanitize message
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            record_dict['msg'] = self._sanitize_text(record.msg)
        
        # Sanitize args
        if hasattr(record, 'args') and record.args:
            sanitized_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    sanitized_args.append(self._sanitize_text(arg))
                elif isinstance(arg, dict):
                    sanitized_args.append(self._sanitize_dict(arg))
                else:
                    sanitized_args.append(arg)
            record_dict['args'] = tuple(sanitized_args)
        
        # Create new record with sanitized data
        sanitized_record = logging.LogRecord(
            name=record_dict['name'],
            level=record_dict['levelno'],
            pathname=record_dict['pathname'],
            lineno=record_dict['lineno'],
            msg=record_dict['msg'],
            args=record_dict.get('args', ()),
            exc_info=record_dict.get('exc_info')
        )
        
        # Copy other attributes
        for key, value in record_dict.items():
            if not hasattr(sanitized_record, key):
                setattr(sanitized_record, key, value)
        
        return super().format(sanitized_record)
    
    def _sanitize_text(self, text: str) -> str:
        """Sanitize sensitive information from text."""
        for pattern in self.SENSITIVE_PATTERNS:
            if pattern.lower() in text.lower():
                # Simple masking - replace with asterisks
                import re
                pattern_re = re.compile(
                    f'({pattern}["\']?\\s*[:=]\\s*["\']?)([^\\s,"\'}}]+)',
                    re.IGNORECASE
                )
                text = pattern_re.sub(r'\1***REDACTED***', text)
        return text
    
    def _sanitize_dict(self, data: dict) -> dict:
        """Sanitize sensitive information from dictionary."""
        sanitized = {}
        for key, value in data.items():
            if any(pattern.lower() in key.lower() for pattern in self.SENSITIVE_PATTERNS):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_dict(value)
            elif isinstance(value, str):
                sanitized[key] = self._sanitize_text(value)
            else:
                sanitized[key] = value
        return sanitized


class StructuredFormatter(SecurityAwareFormatter):
    """JSON structured logging formatter."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format record as structured JSON."""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add extra fields
        if hasattr(record, 'agent_name'):
            log_entry['agent_name'] = record.agent_name
        if hasattr(record, 'scan_id'):
            log_entry['scan_id'] = record.scan_id
        if hasattr(record, 'pattern_name'):
            log_entry['pattern_name'] = record.pattern_name
        if hasattr(record, 'vulnerability_type'):
            log_entry['vulnerability_type'] = record.vulnerability_type
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, default=str)


def setup_logger(
    name: str,
    level: str = "INFO",
    log_format: Optional[str] = None,
    log_file: Optional[Union[str, Path]] = None,
    structured: bool = False,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Setup a logger with security-aware formatting.
    
    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Custom log format string
        log_file: Path to log file (optional)
        structured: Use structured JSON logging
        max_bytes: Maximum log file size before rotation
        backup_count: Number of backup files to keep
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Set log level
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # Choose formatter
    if structured:
        formatter = StructuredFormatter()
    else:
        if log_format is None:
            log_format = (
                '%(asctime)s - %(name)s - %(levelname)s - '
                '[%(filename)s:%(lineno)d] - %(message)s'
            )
        formatter = SecurityAwareFormatter(log_format)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger with default configuration.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    # Check if logger already exists
    logger = logging.getLogger(name)
    
    # If logger has no handlers, set it up with defaults
    if not logger.handlers:
        # Get configuration from environment
        log_level = os.getenv('LOG_LEVEL', 'INFO')
        log_file = os.getenv('LOG_FILE')
        structured = os.getenv('LOG_STRUCTURED', 'false').lower() == 'true'
        
        logger = setup_logger(
            name=name,
            level=log_level,
            log_file=log_file,
            structured=structured
        )
    
    return logger


class LogContext:
    """Context manager for adding contextual information to logs."""
    
    def __init__(self, logger: logging.Logger, **context):
        """
        Initialize log context.
        
        Args:
            logger: Logger instance
            **context: Context key-value pairs
        """
        self.logger = logger
        self.context = context
        self.old_factory = None
    
    def __enter__(self):
        """Enter context and modify logger factory."""
        self.old_factory = logging.getLogRecordFactory()
        
        def context_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record
        
        logging.setLogRecordFactory(context_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and restore original factory."""
        logging.setLogRecordFactory(self.old_factory)


def log_scan_event(
    logger: logging.Logger,
    event_type: str,
    scan_id: str,
    details: Optional[Dict[str, Any]] = None,
    level: str = "INFO"
):
    """
    Log a scan-related event with structured context.
    
    Args:
        logger: Logger instance
        event_type: Type of event (scan_started, pattern_executed, etc.)
        scan_id: Scan session ID
        details: Additional event details
        level: Log level
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    with LogContext(logger, scan_id=scan_id, event_type=event_type):
        message = f"Scan event: {event_type}"
        if details:
            message += f" - {details}"
        logger.log(log_level, message)


def log_vulnerability_found(
    logger: logging.Logger,
    vulnerability_type: str,
    severity: str,
    scan_id: str,
    pattern_name: str,
    agent_name: str,
    details: Optional[str] = None
):
    """
    Log vulnerability discovery with full context.
    
    Args:
        logger: Logger instance
        vulnerability_type: Type of vulnerability
        severity: Severity level
        scan_id: Scan session ID
        pattern_name: Attack pattern name
        agent_name: Target agent name
        details: Additional details
    """
    with LogContext(
        logger,
        scan_id=scan_id,
        pattern_name=pattern_name,
        agent_name=agent_name,
        vulnerability_type=vulnerability_type,
        severity=severity
    ):
        message = f"Vulnerability found: {vulnerability_type} ({severity})"
        if details:
            message += f" - {details}"
        logger.warning(message)


def log_security_event(
    logger: logging.Logger,
    event_type: str,
    severity: str = "INFO",
    details: Optional[Dict[str, Any]] = None
):
    """
    Log security-related events for audit purposes.
    
    Args:
        logger: Logger instance
        event_type: Type of security event
        severity: Event severity
        details: Additional event details
    """
    log_level = getattr(logging, severity.upper(), logging.INFO)
    
    security_event = {
        'event_type': event_type,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'severity': severity,
        'details': details or {}
    }
    
    logger.log(log_level, f"Security event: {json.dumps(security_event)}")


# Configure root logger with security defaults
def configure_root_logger():
    """Configure the root logger with security-aware defaults."""
    root_logger = logging.getLogger()
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set up with security formatter
    setup_logger(
        name='',  # Root logger
        level=os.getenv('LOG_LEVEL', 'INFO'),
        structured=os.getenv('LOG_STRUCTURED', 'false').lower() == 'true'
    )


# Auto-configure on import if not in test environment
if 'pytest' not in sys.modules and not os.getenv('TESTING'):
    configure_root_logger()