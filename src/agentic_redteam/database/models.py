"""
Database models for Agentic RedTeam Radar.

Defines data models for scan sessions, vulnerabilities, attack patterns,
and agent configurations with validation and serialization.
"""

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from enum import Enum

from ..attacks.base import AttackSeverity, AttackCategory


class ScanStatus(Enum):
    """Scan session status values."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ScanSession:
    """
    Model for scan session records.
    
    Represents a complete security scanning session against an agent.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    agent_config: Dict[str, Any] = field(default_factory=dict)
    status: ScanStatus = ScanStatus.PENDING
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Set default timestamps."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        data = asdict(self)
        
        # Convert enums and complex types
        data['status'] = self.status.value
        data['agent_config'] = json.dumps(self.agent_config)
        data['metadata'] = json.dumps(self.metadata)
        
        # Convert datetime objects
        for field_name in ['created_at', 'updated_at', 'started_at', 'completed_at']:
            if data[field_name]:
                data[field_name] = data[field_name].isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScanSession':
        """Create instance from dictionary."""
        # Parse JSON fields
        if isinstance(data.get('agent_config'), str):
            data['agent_config'] = json.loads(data['agent_config'])
        if isinstance(data.get('metadata'), str):
            data['metadata'] = json.loads(data['metadata'])
        
        # Parse status
        if isinstance(data.get('status'), str):
            data['status'] = ScanStatus(data['status'])
        
        # Parse datetime fields
        for field_name in ['created_at', 'updated_at', 'started_at', 'completed_at']:
            if data.get(field_name):
                if isinstance(data[field_name], str):
                    data[field_name] = datetime.fromisoformat(data[field_name])
        
        return cls(**data)
    
    def start(self):
        """Mark scan as started."""
        self.status = ScanStatus.RUNNING
        self.started_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def complete(self):
        """Mark scan as completed."""
        self.status = ScanStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def fail(self, error_message: str):
        """Mark scan as failed."""
        self.status = ScanStatus.FAILED
        self.error_message = error_message
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()


@dataclass
class Vulnerability:
    """
    Model for vulnerability records.
    
    Represents a security vulnerability found during scanning.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    scan_session_id: str = ""
    pattern_name: str = ""
    vulnerability_type: str = ""
    severity: AttackSeverity = AttackSeverity.MEDIUM
    title: str = ""
    description: str = ""
    evidence: List[str] = field(default_factory=list)
    remediation: str = ""
    confidence_score: float = 0.0
    false_positive: bool = False
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Set default timestamp."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        data = asdict(self)
        
        # Convert enums and complex types
        data['severity'] = self.severity.value
        data['evidence'] = json.dumps(self.evidence)
        data['metadata'] = json.dumps(self.metadata)
        data['false_positive'] = int(self.false_positive)  # SQLite compatibility
        
        # Convert datetime
        if data['created_at']:
            data['created_at'] = data['created_at'].isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Vulnerability':
        """Create instance from dictionary."""
        # Parse JSON fields
        if isinstance(data.get('evidence'), str):
            data['evidence'] = json.loads(data['evidence'])
        if isinstance(data.get('metadata'), str):
            data['metadata'] = json.loads(data['metadata'])
        
        # Parse severity
        if isinstance(data.get('severity'), str):
            data['severity'] = AttackSeverity(data['severity'])
        
        # Parse boolean (SQLite compatibility)
        if 'false_positive' in data:
            data['false_positive'] = bool(data['false_positive'])
        
        # Parse datetime
        if data.get('created_at') and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        
        return cls(**data)
    
    def mark_false_positive(self, reason: str = ""):
        """Mark vulnerability as false positive."""
        self.false_positive = True
        if reason:
            self.metadata['false_positive_reason'] = reason


@dataclass
class AttackPattern:
    """
    Model for attack pattern records.
    
    Represents a reusable attack pattern for vulnerability testing.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    category: AttackCategory = AttackCategory.PROMPT_INJECTION
    description: str = ""
    technique: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    severity: AttackSeverity = AttackSeverity.MEDIUM
    active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    version: int = 1
    
    def __post_init__(self):
        """Set default timestamps."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        data = asdict(self)
        
        # Convert enums and complex types
        data['category'] = self.category.value
        data['severity'] = self.severity.value
        data['technique'] = json.dumps(self.technique)
        data['tags'] = json.dumps(self.tags)
        data['active'] = int(self.active)  # SQLite compatibility
        
        # Convert datetime
        for field_name in ['created_at', 'updated_at']:
            if data[field_name]:
                data[field_name] = data[field_name].isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AttackPattern':
        """Create instance from dictionary."""
        # Parse JSON fields
        if isinstance(data.get('technique'), str):
            data['technique'] = json.loads(data['technique'])
        if isinstance(data.get('tags'), str):
            data['tags'] = json.loads(data['tags'])
        
        # Parse enums
        if isinstance(data.get('category'), str):
            data['category'] = AttackCategory(data['category'])
        if isinstance(data.get('severity'), str):
            data['severity'] = AttackSeverity(data['severity'])
        
        # Parse boolean (SQLite compatibility)
        if 'active' in data:
            data['active'] = bool(data['active'])
        
        # Parse datetime
        for field_name in ['created_at', 'updated_at']:
            if data.get(field_name) and isinstance(data[field_name], str):
                data[field_name] = datetime.fromisoformat(data[field_name])
        
        return cls(**data)
    
    def update_version(self):
        """Increment version and update timestamp."""
        self.version += 1
        self.updated_at = datetime.utcnow()


@dataclass
class AgentConfig:
    """
    Model for agent configuration records.
    
    Represents a saved agent configuration for reuse in scans.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    model: str = ""
    system_prompt: Optional[str] = None
    tools: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Set default timestamps."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        data = asdict(self)
        
        # Convert complex types
        data['tools'] = json.dumps(self.tools)
        data['parameters'] = json.dumps(self.parameters)
        data['active'] = int(self.active)  # SQLite compatibility
        
        # Convert datetime
        for field_name in ['created_at', 'updated_at']:
            if data[field_name]:
                data[field_name] = data[field_name].isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentConfig':
        """Create instance from dictionary."""
        # Parse JSON fields
        if isinstance(data.get('tools'), str):
            data['tools'] = json.loads(data['tools'])
        if isinstance(data.get('parameters'), str):
            data['parameters'] = json.loads(data['parameters'])
        
        # Parse boolean (SQLite compatibility)
        if 'active' in data:
            data['active'] = bool(data['active'])
        
        # Parse datetime
        for field_name in ['created_at', 'updated_at']:
            if data.get(field_name) and isinstance(data[field_name], str):
                data[field_name] = datetime.fromisoformat(data[field_name])
        
        return cls(**data)


@dataclass
class ScanReport:
    """
    Model for scan report records.
    
    Represents a generated report from a scan session.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    scan_session_id: str = ""
    format: str = "json"
    content: Optional[Dict[str, Any]] = None
    file_path: Optional[str] = None
    size_bytes: int = 0
    checksum: Optional[str] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Set default timestamp."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        data = asdict(self)
        
        # Convert content to JSON
        if self.content:
            data['content'] = json.dumps(self.content)
        
        # Convert datetime
        if data['created_at']:
            data['created_at'] = data['created_at'].isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScanReport':
        """Create instance from dictionary."""
        # Parse JSON content
        if isinstance(data.get('content'), str):
            data['content'] = json.loads(data['content'])
        
        # Parse datetime
        if data.get('created_at') and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        
        return cls(**data)


@dataclass
class AuditLogEntry:
    """
    Model for audit log entries.
    
    Represents an audit trail entry for security and compliance.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    scan_session_id: Optional[str] = None
    action: str = ""
    actor: Optional[str] = None
    timestamp: Optional[datetime] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Set default timestamp."""
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        data = asdict(self)
        
        # Convert details to JSON
        data['details'] = json.dumps(self.details)
        
        # Convert datetime
        if data['timestamp']:
            data['timestamp'] = data['timestamp'].isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuditLogEntry':
        """Create instance from dictionary."""
        # Parse JSON details
        if isinstance(data.get('details'), str):
            data['details'] = json.loads(data['details'])
        
        # Parse datetime
        if data.get('timestamp') and isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        
        return cls(**data)