"""
Data integrity checking and validation.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import time
from ..utils.logger import get_logger


class IntegrityViolation(Exception):
    """Exception raised when data integrity is violated."""
    pass


class DataIntegrityChecker:
    """
    Validates data integrity and consistency.
    """
    
    def __init__(self):
        self.logger = get_logger("agentic_redteam.reliability.data_integrity")
        self.checksums: Dict[str, str] = {}
        
    def compute_checksum(self, data: Any) -> str:
        """Compute checksum for data."""
        if isinstance(data, dict):
            data_str = json.dumps(data, sort_keys=True)
        else:
            data_str = str(data)
        
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def validate_integrity(self, key: str, data: Any) -> bool:
        """Validate data integrity against stored checksum."""
        current_checksum = self.compute_checksum(data)
        
        if key in self.checksums:
            expected_checksum = self.checksums[key]
            if current_checksum != expected_checksum:
                self.logger.error(f"Data integrity violation for {key}")
                raise IntegrityViolation(f"Checksum mismatch for {key}")
        
        self.checksums[key] = current_checksum
        return True