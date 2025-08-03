"""
Database connection management for Agentic RedTeam Radar.

Handles SQLite and PostgreSQL connections with connection pooling
and automatic migration support.
"""

import os
import sqlite3
import logging
from typing import Optional, Union, Dict, Any
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse

try:
    import psycopg2
    from psycopg2.pool import ThreadedConnectionPool
    from psycopg2.extras import RealDictCursor
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False

from ..utils.logger import get_logger


class DatabaseManager:
    """
    Manages database connections and provides high-level database operations.
    
    Supports both SQLite (for development/testing) and PostgreSQL (for production).
    """
    
    def __init__(self, database_url: str):
        """
        Initialize database manager.
        
        Args:
            database_url: Database connection URL
        """
        self.database_url = database_url
        self.logger = get_logger(__name__)
        self._connection_pool = None
        self._sqlite_path = None
        
        # Parse database URL
        parsed = urlparse(database_url)
        self.db_type = parsed.scheme
        
        if self.db_type == 'sqlite':
            self._setup_sqlite(parsed)
        elif self.db_type == 'postgresql':
            self._setup_postgresql()
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")
    
    def _setup_sqlite(self, parsed_url):
        """Setup SQLite database."""
        # Extract path from URL
        if parsed_url.path == '/:memory:':
            self._sqlite_path = ':memory:'
        else:
            self._sqlite_path = parsed_url.path
            if self._sqlite_path.startswith('/'):
                self._sqlite_path = self._sqlite_path[1:]
            
            # Ensure directory exists
            db_dir = Path(self._sqlite_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Using SQLite database: {self._sqlite_path}")
        
        # Initialize database schema
        self._init_sqlite_schema()
    
    def _setup_postgresql(self):
        """Setup PostgreSQL database with connection pooling."""
        if not POSTGRESQL_AVAILABLE:
            raise RuntimeError("psycopg2 not available for PostgreSQL connections")
        
        try:
            # Create connection pool
            self._connection_pool = ThreadedConnectionPool(
                minconn=1,
                maxconn=20,
                dsn=self.database_url,
                cursor_factory=RealDictCursor
            )
            
            self.logger.info("PostgreSQL connection pool created")
            
            # Test connection
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT version()")
                    version = cursor.fetchone()[0]
                    self.logger.info(f"Connected to PostgreSQL: {version}")
        
        except Exception as e:
            self.logger.error(f"Failed to setup PostgreSQL: {e}")
            raise
    
    def _init_sqlite_schema(self):
        """Initialize SQLite schema with simplified tables."""
        schema_sql = """
        -- Enable foreign keys
        PRAGMA foreign_keys = ON;
        
        -- Create scan_sessions table
        CREATE TABLE IF NOT EXISTS scan_sessions (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            agent_config TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            error_message TEXT,
            metadata TEXT DEFAULT '{}'
        );
        
        -- Create vulnerabilities table
        CREATE TABLE IF NOT EXISTS vulnerabilities (
            id TEXT PRIMARY KEY,
            scan_session_id TEXT NOT NULL REFERENCES scan_sessions(id) ON DELETE CASCADE,
            pattern_name TEXT NOT NULL,
            vulnerability_type TEXT NOT NULL,
            severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            evidence TEXT,
            remediation TEXT,
            confidence_score REAL CHECK (confidence_score >= 0 AND confidence_score <= 1),
            false_positive INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT DEFAULT '{}'
        );
        
        -- Create attack_patterns table
        CREATE TABLE IF NOT EXISTS attack_patterns (
            id TEXT PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            technique TEXT NOT NULL,
            tags TEXT,
            severity TEXT NOT NULL,
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            version INTEGER DEFAULT 1
        );
        
        -- Create agent_configs table
        CREATE TABLE IF NOT EXISTS agent_configs (
            id TEXT PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            model TEXT NOT NULL,
            system_prompt TEXT,
            tools TEXT DEFAULT '[]',
            parameters TEXT DEFAULT '{}',
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Create scan_reports table
        CREATE TABLE IF NOT EXISTS scan_reports (
            id TEXT PRIMARY KEY,
            scan_session_id TEXT NOT NULL REFERENCES scan_sessions(id) ON DELETE CASCADE,
            format TEXT NOT NULL,
            content TEXT,
            file_path TEXT,
            size_bytes INTEGER,
            checksum TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Create audit table
        CREATE TABLE IF NOT EXISTS audit_log (
            id TEXT PRIMARY KEY,
            scan_session_id TEXT,
            action TEXT NOT NULL,
            actor TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            details TEXT DEFAULT '{}'
        );
        
        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_scan_sessions_status ON scan_sessions(status);
        CREATE INDEX IF NOT EXISTS idx_scan_sessions_created_at ON scan_sessions(created_at);
        CREATE INDEX IF NOT EXISTS idx_vulnerabilities_scan_session ON vulnerabilities(scan_session_id);
        CREATE INDEX IF NOT EXISTS idx_vulnerabilities_severity ON vulnerabilities(severity);
        CREATE INDEX IF NOT EXISTS idx_vulnerabilities_type ON vulnerabilities(vulnerability_type);
        CREATE INDEX IF NOT EXISTS idx_attack_patterns_category ON attack_patterns(category);
        CREATE INDEX IF NOT EXISTS idx_attack_patterns_active ON attack_patterns(active);
        CREATE INDEX IF NOT EXISTS idx_agent_configs_active ON agent_configs(active);
        CREATE INDEX IF NOT EXISTS idx_audit_log_session ON audit_log(scan_session_id);
        CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp);
        """
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executescript(schema_sql)
            conn.commit()
            self.logger.info("SQLite schema initialized")
    
    @contextmanager
    def get_connection(self):
        """
        Get database connection context manager.
        
        Yields:
            Database connection object
        """
        if self.db_type == 'sqlite':
            conn = sqlite3.connect(self._sqlite_path)
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            try:
                yield conn
            finally:
                conn.close()
        
        elif self.db_type == 'postgresql':
            conn = self._connection_pool.getconn()
            try:
                yield conn
            except Exception:
                conn.rollback()
                raise
            finally:
                self._connection_pool.putconn(conn)
        
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> list:
        """
        Execute a SELECT query and return results.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of result rows
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            return cursor.fetchall()
    
    def execute_update(self, query: str, params: Optional[tuple] = None) -> int:
        """
        Execute an INSERT/UPDATE/DELETE query.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Number of affected rows
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            conn.commit()
            return cursor.rowcount
    
    def execute_many(self, query: str, params_list: list) -> int:
        """
        Execute a query with multiple parameter sets.
        
        Args:
            query: SQL query string
            params_list: List of parameter tuples
            
        Returns:
            Number of affected rows
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()
            return cursor.rowcount
    
    def close(self):
        """Close database connections and cleanup."""
        if self.db_type == 'postgresql' and self._connection_pool:
            self._connection_pool.closeall()
            self.logger.info("PostgreSQL connection pool closed")


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_connection() -> DatabaseManager:
    """
    Get global database manager instance.
    
    Returns:
        DatabaseManager instance
    """
    global _db_manager
    
    if _db_manager is None:
        database_url = os.getenv('DATABASE_URL', 'sqlite:///./data/radar.db')
        _db_manager = DatabaseManager(database_url)
    
    return _db_manager


def init_database(database_url: Optional[str] = None) -> DatabaseManager:
    """
    Initialize database with custom URL.
    
    Args:
        database_url: Database connection URL
        
    Returns:
        DatabaseManager instance
    """
    global _db_manager
    
    if database_url is None:
        database_url = os.getenv('DATABASE_URL', 'sqlite:///./data/radar.db')
    
    _db_manager = DatabaseManager(database_url)
    return _db_manager


def close_database():
    """Close database connections."""
    global _db_manager
    
    if _db_manager:
        _db_manager.close()
        _db_manager = None