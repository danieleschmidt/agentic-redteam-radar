"""
Repository pattern implementations for Agentic RedTeam Radar.

Provides data access layer with CRUD operations and business logic
for scan sessions, vulnerabilities, and configurations.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from .connection import DatabaseManager, get_db_connection
from .models import (
    ScanSession, Vulnerability, AttackPattern, AgentConfig,
    ScanReport, AuditLogEntry, ScanStatus
)
from ..utils.logger import get_logger


class BaseRepository:
    """Base repository with common database operations."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize repository.
        
        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager or get_db_connection()
        self.logger = get_logger(__name__)


class ScanSessionRepository(BaseRepository):
    """Repository for scan session operations."""
    
    def create(self, session: ScanSession) -> ScanSession:
        """
        Create a new scan session.
        
        Args:
            session: Scan session to create
            
        Returns:
            Created scan session with ID
        """
        data = session.to_dict()
        
        query = """
        INSERT INTO scan_sessions 
        (id, name, description, agent_config, status, created_at, updated_at, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            data['id'], data['name'], data['description'], data['agent_config'],
            data['status'], data['created_at'], data['updated_at'], data['metadata']
        )
        
        self.db.execute_update(query, params)
        self.logger.info(f"Created scan session: {session.id}")
        
        return session
    
    def get_by_id(self, session_id: str) -> Optional[ScanSession]:
        """
        Get scan session by ID.
        
        Args:
            session_id: Session ID to retrieve
            
        Returns:
            Scan session if found, None otherwise
        """
        query = "SELECT * FROM scan_sessions WHERE id = ?"
        results = self.db.execute_query(query, (session_id,))
        
        if results:
            return ScanSession.from_dict(dict(results[0]))
        return None
    
    def update(self, session: ScanSession) -> ScanSession:
        """
        Update scan session.
        
        Args:
            session: Session to update
            
        Returns:
            Updated session
        """
        session.updated_at = datetime.utcnow()
        data = session.to_dict()
        
        query = """
        UPDATE scan_sessions 
        SET name = ?, description = ?, agent_config = ?, status = ?,
            updated_at = ?, started_at = ?, completed_at = ?, 
            error_message = ?, metadata = ?
        WHERE id = ?
        """
        
        params = (
            data['name'], data['description'], data['agent_config'], data['status'],
            data['updated_at'], data['started_at'], data['completed_at'],
            data['error_message'], data['metadata'], data['id']
        )
        
        self.db.execute_update(query, params)
        self.logger.info(f"Updated scan session: {session.id}")
        
        return session
    
    def list_recent(self, limit: int = 50) -> List[ScanSession]:
        """
        List recent scan sessions.
        
        Args:
            limit: Maximum number of sessions to return
            
        Returns:
            List of recent scan sessions
        """
        query = """
        SELECT * FROM scan_sessions 
        ORDER BY created_at DESC 
        LIMIT ?
        """
        
        results = self.db.execute_query(query, (limit,))
        return [ScanSession.from_dict(dict(row)) for row in results]
    
    def list_by_status(self, status: ScanStatus) -> List[ScanSession]:
        """
        List scan sessions by status.
        
        Args:
            status: Status to filter by
            
        Returns:
            List of scan sessions with specified status
        """
        query = "SELECT * FROM scan_sessions WHERE status = ? ORDER BY created_at DESC"
        results = self.db.execute_query(query, (status.value,))
        return [ScanSession.from_dict(dict(row)) for row in results]
    
    def delete(self, session_id: str) -> bool:
        """
        Delete scan session and related data.
        
        Args:
            session_id: Session ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        # Delete will cascade to related tables due to foreign key constraints
        query = "DELETE FROM scan_sessions WHERE id = ?"
        rows_affected = self.db.execute_update(query, (session_id,))
        
        if rows_affected > 0:
            self.logger.info(f"Deleted scan session: {session_id}")
            return True
        return False


class VulnerabilityRepository(BaseRepository):
    """Repository for vulnerability operations."""
    
    def create(self, vulnerability: Vulnerability) -> Vulnerability:
        """
        Create a new vulnerability.
        
        Args:
            vulnerability: Vulnerability to create
            
        Returns:
            Created vulnerability
        """
        data = vulnerability.to_dict()
        
        query = """
        INSERT INTO vulnerabilities 
        (id, scan_session_id, pattern_name, vulnerability_type, severity, 
         title, description, evidence, remediation, confidence_score, 
         false_positive, created_at, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            data['id'], data['scan_session_id'], data['pattern_name'],
            data['vulnerability_type'], data['severity'], data['title'],
            data['description'], data['evidence'], data['remediation'],
            data['confidence_score'], data['false_positive'], 
            data['created_at'], data['metadata']
        )
        
        self.db.execute_update(query, params)
        self.logger.info(f"Created vulnerability: {vulnerability.id}")
        
        return vulnerability
    
    def create_many(self, vulnerabilities: List[Vulnerability]) -> List[Vulnerability]:
        """
        Create multiple vulnerabilities efficiently.
        
        Args:
            vulnerabilities: List of vulnerabilities to create
            
        Returns:
            List of created vulnerabilities
        """
        if not vulnerabilities:
            return []
        
        query = """
        INSERT INTO vulnerabilities 
        (id, scan_session_id, pattern_name, vulnerability_type, severity, 
         title, description, evidence, remediation, confidence_score, 
         false_positive, created_at, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params_list = []
        for vuln in vulnerabilities:
            data = vuln.to_dict()
            params_list.append((
                data['id'], data['scan_session_id'], data['pattern_name'],
                data['vulnerability_type'], data['severity'], data['title'],
                data['description'], data['evidence'], data['remediation'],
                data['confidence_score'], data['false_positive'], 
                data['created_at'], data['metadata']
            ))
        
        self.db.execute_many(query, params_list)
        self.logger.info(f"Created {len(vulnerabilities)} vulnerabilities")
        
        return vulnerabilities
    
    def get_by_session(self, session_id: str) -> List[Vulnerability]:
        """
        Get vulnerabilities for a scan session.
        
        Args:
            session_id: Scan session ID
            
        Returns:
            List of vulnerabilities for the session
        """
        query = """
        SELECT * FROM vulnerabilities 
        WHERE scan_session_id = ? 
        ORDER BY severity DESC, created_at ASC
        """
        
        results = self.db.execute_query(query, (session_id,))
        return [Vulnerability.from_dict(dict(row)) for row in results]
    
    def get_by_severity(self, severity: str, limit: int = 100) -> List[Vulnerability]:
        """
        Get vulnerabilities by severity level.
        
        Args:
            severity: Severity level to filter by
            limit: Maximum number of results
            
        Returns:
            List of vulnerabilities with specified severity
        """
        query = """
        SELECT * FROM vulnerabilities 
        WHERE severity = ? AND false_positive = 0
        ORDER BY created_at DESC 
        LIMIT ?
        """
        
        results = self.db.execute_query(query, (severity, limit))
        return [Vulnerability.from_dict(dict(row)) for row in results]
    
    def mark_false_positive(self, vulnerability_id: str, reason: str = "") -> bool:
        """
        Mark vulnerability as false positive.
        
        Args:
            vulnerability_id: Vulnerability ID
            reason: Reason for marking as false positive
            
        Returns:
            True if updated, False if not found
        """
        query = """
        UPDATE vulnerabilities 
        SET false_positive = 1, metadata = json_set(metadata, '$.false_positive_reason', ?)
        WHERE id = ?
        """
        
        rows_affected = self.db.execute_update(query, (reason, vulnerability_id))
        
        if rows_affected > 0:
            self.logger.info(f"Marked vulnerability {vulnerability_id} as false positive")
            return True
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get vulnerability statistics.
        
        Returns:
            Dictionary with vulnerability statistics
        """
        # Count by severity
        severity_query = """
        SELECT severity, COUNT(*) as count 
        FROM vulnerabilities 
        WHERE false_positive = 0 
        GROUP BY severity
        """
        
        severity_results = self.db.execute_query(severity_query)
        severity_stats = {row['severity']: row['count'] for row in severity_results}
        
        # Count by type
        type_query = """
        SELECT vulnerability_type, COUNT(*) as count 
        FROM vulnerabilities 
        WHERE false_positive = 0 
        GROUP BY vulnerability_type
        """
        
        type_results = self.db.execute_query(type_query)
        type_stats = {row['vulnerability_type']: row['count'] for row in type_results}
        
        # Total counts
        total_query = """
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN false_positive = 1 THEN 1 END) as false_positives,
            AVG(confidence_score) as avg_confidence
        FROM vulnerabilities
        """
        
        total_results = self.db.execute_query(total_query)
        total_stats = dict(total_results[0]) if total_results else {}
        
        return {
            'by_severity': severity_stats,
            'by_type': type_stats,
            'totals': total_stats
        }


class AttackPatternRepository(BaseRepository):
    """Repository for attack pattern operations."""
    
    def create(self, pattern: AttackPattern) -> AttackPattern:
        """
        Create a new attack pattern.
        
        Args:
            pattern: Attack pattern to create
            
        Returns:
            Created attack pattern
        """
        data = pattern.to_dict()
        
        query = """
        INSERT INTO attack_patterns 
        (id, name, category, description, technique, tags, severity, 
         active, created_at, updated_at, version)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            data['id'], data['name'], data['category'], data['description'],
            data['technique'], data['tags'], data['severity'], data['active'],
            data['created_at'], data['updated_at'], data['version']
        )
        
        self.db.execute_update(query, params)
        self.logger.info(f"Created attack pattern: {pattern.name}")
        
        return pattern
    
    def get_by_name(self, name: str) -> Optional[AttackPattern]:
        """
        Get attack pattern by name.
        
        Args:
            name: Pattern name
            
        Returns:
            Attack pattern if found, None otherwise
        """
        query = "SELECT * FROM attack_patterns WHERE name = ?"
        results = self.db.execute_query(query, (name,))
        
        if results:
            return AttackPattern.from_dict(dict(results[0]))
        return None
    
    def list_active(self) -> List[AttackPattern]:
        """
        List all active attack patterns.
        
        Returns:
            List of active attack patterns
        """
        query = """
        SELECT * FROM attack_patterns 
        WHERE active = 1 
        ORDER BY category, name
        """
        
        results = self.db.execute_query(query)
        return [AttackPattern.from_dict(dict(row)) for row in results]
    
    def list_by_category(self, category: str) -> List[AttackPattern]:
        """
        List attack patterns by category.
        
        Args:
            category: Category to filter by
            
        Returns:
            List of patterns in the specified category
        """
        query = """
        SELECT * FROM attack_patterns 
        WHERE category = ? AND active = 1 
        ORDER BY name
        """
        
        results = self.db.execute_query(query, (category,))
        return [AttackPattern.from_dict(dict(row)) for row in results]
    
    def update(self, pattern: AttackPattern) -> AttackPattern:
        """
        Update attack pattern.
        
        Args:
            pattern: Pattern to update
            
        Returns:
            Updated pattern
        """
        pattern.update_version()
        data = pattern.to_dict()
        
        query = """
        UPDATE attack_patterns 
        SET category = ?, description = ?, technique = ?, tags = ?, 
            severity = ?, active = ?, updated_at = ?, version = ?
        WHERE id = ?
        """
        
        params = (
            data['category'], data['description'], data['technique'], data['tags'],
            data['severity'], data['active'], data['updated_at'], data['version'],
            data['id']
        )
        
        self.db.execute_update(query, params)
        self.logger.info(f"Updated attack pattern: {pattern.name}")
        
        return pattern


class AgentConfigRepository(BaseRepository):
    """Repository for agent configuration operations."""
    
    def create(self, config: AgentConfig) -> AgentConfig:
        """
        Create a new agent configuration.
        
        Args:
            config: Agent configuration to create
            
        Returns:
            Created agent configuration
        """
        data = config.to_dict()
        
        query = """
        INSERT INTO agent_configs 
        (id, name, model, system_prompt, tools, parameters, 
         active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            data['id'], data['name'], data['model'], data['system_prompt'],
            data['tools'], data['parameters'], data['active'],
            data['created_at'], data['updated_at']
        )
        
        self.db.execute_update(query, params)
        self.logger.info(f"Created agent config: {config.name}")
        
        return config
    
    def get_by_name(self, name: str) -> Optional[AgentConfig]:
        """
        Get agent configuration by name.
        
        Args:
            name: Configuration name
            
        Returns:
            Agent configuration if found, None otherwise
        """
        query = "SELECT * FROM agent_configs WHERE name = ? AND active = 1"
        results = self.db.execute_query(query, (name,))
        
        if results:
            return AgentConfig.from_dict(dict(results[0]))
        return None
    
    def list_active(self) -> List[AgentConfig]:
        """
        List all active agent configurations.
        
        Returns:
            List of active agent configurations
        """
        query = """
        SELECT * FROM agent_configs 
        WHERE active = 1 
        ORDER BY name
        """
        
        results = self.db.execute_query(query)
        return [AgentConfig.from_dict(dict(row)) for row in results]


class AuditLogRepository(BaseRepository):
    """Repository for audit log operations."""
    
    def log_action(self, action: str, scan_session_id: Optional[str] = None,
                   actor: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """
        Log an audit action.
        
        Args:
            action: Action being performed
            scan_session_id: Optional scan session ID
            actor: Optional actor performing the action
            details: Optional additional details
        """
        entry = AuditLogEntry(
            scan_session_id=scan_session_id,
            action=action,
            actor=actor,
            details=details or {}
        )
        
        data = entry.to_dict()
        
        query = """
        INSERT INTO audit_log 
        (id, scan_session_id, action, actor, timestamp, details)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        
        params = (
            data['id'], data['scan_session_id'], data['action'],
            data['actor'], data['timestamp'], data['details']
        )
        
        self.db.execute_update(query, params)
    
    def get_session_log(self, session_id: str) -> List[AuditLogEntry]:
        """
        Get audit log for a specific session.
        
        Args:
            session_id: Scan session ID
            
        Returns:
            List of audit log entries for the session
        """
        query = """
        SELECT * FROM audit_log 
        WHERE scan_session_id = ? 
        ORDER BY timestamp ASC
        """
        
        results = self.db.execute_query(query, (session_id,))
        return [AuditLogEntry.from_dict(dict(row)) for row in results]