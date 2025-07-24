"""Database connector abstraction for multiple database types"""

import logging
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
import sqlite3
import os

logger = logging.getLogger(__name__)


class DBConnector(ABC):
    """Abstract base class for database connectors"""
    
    @abstractmethod
    def execute_query(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute SQL query and return results"""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """Test database connection"""
        pass


class SQLiteConnector(DBConnector):
    """SQLite database connector"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        
    def execute_query(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute SQL query on SQLite database"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            rows = cursor.fetchall()
            
            # Convert to list of dicts
            results = []
            for row in rows:
                results.append(dict(row))
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"SQLite query error: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test SQLite connection"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("SELECT 1")
            conn.close()
            return True
        except Exception as e:
            logger.error(f"SQLite connection test failed: {e}")
            return False


class SQLServerConnector(DBConnector):
    """SQL Server (MSSQL) database connector"""
    
    def __init__(
        self, 
        server: str,
        database: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        driver: str = "{ODBC Driver 17 for SQL Server}",
        trusted_connection: bool = False
    ):
        self.server = server
        self.database = database
        self.username = username
        self.password = password
        self.driver = driver
        self.trusted_connection = trusted_connection
        
        # Import pyodbc only when SQL Server is used
        try:
            import pyodbc
            self.pyodbc = pyodbc
        except ImportError:
            raise ImportError(
                "pyodbc is required for SQL Server connection. "
                "Install with: pip install pyodbc"
            )
    
    def _get_connection_string(self) -> str:
        """Build SQL Server connection string"""
        if self.trusted_connection:
            return (
                f"DRIVER={self.driver};"
                f"SERVER={self.server};"
                f"DATABASE={self.database};"
                f"Trusted_Connection=yes;"
            )
        else:
            return (
                f"DRIVER={self.driver};"
                f"SERVER={self.server};"
                f"DATABASE={self.database};"
                f"UID={self.username};"
                f"PWD={self.password};"
            )
    
    def execute_query(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute SQL query on SQL Server"""
        try:
            conn = self.pyodbc.connect(self._get_connection_string())
            cursor = conn.cursor()
            
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            
            # Get column names
            columns = [column[0] for column in cursor.description]
            
            # Fetch all rows
            rows = cursor.fetchall()
            
            # Convert to list of dicts
            results = []
            for row in rows:
                results.append(dict(zip(columns, row)))
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"SQL Server query error: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test SQL Server connection"""
        try:
            conn = self.pyodbc.connect(self._get_connection_string())
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.close()
            return True
        except Exception as e:
            logger.error(f"SQL Server connection test failed: {e}")
            return False


class PostgreSQLConnector(DBConnector):
    """PostgreSQL database connector"""
    
    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str
    ):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        
        # Import psycopg2 only when PostgreSQL is used
        try:
            import psycopg2
            import psycopg2.extras
            self.psycopg2 = psycopg2
            self.extras = psycopg2.extras
        except ImportError:
            raise ImportError(
                "psycopg2 is required for PostgreSQL connection. "
                "Install with: pip install psycopg2-binary"
            )
    
    def execute_query(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute SQL query on PostgreSQL"""
        try:
            conn = self.psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            
            # Use RealDictCursor to get results as dictionaries
            cursor = conn.cursor(cursor_factory=self.extras.RealDictCursor)
            
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            rows = cursor.fetchall()
            
            # Convert to list of dicts
            results = [dict(row) for row in rows]
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"PostgreSQL query error: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test PostgreSQL connection"""
        try:
            conn = self.psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.close()
            return True
        except Exception as e:
            logger.error(f"PostgreSQL connection test failed: {e}")
            return False


def create_db_connector(db_config: Dict[str, Any]) -> DBConnector:
    """Factory function to create appropriate database connector"""
    db_type = db_config.get("type", "sqlite").lower()
    
    if db_type == "sqlite":
        return SQLiteConnector(
            db_path=db_config.get("path", "./data/iacsgraph.db")
        )
    
    elif db_type == "sqlserver" or db_type == "mssql":
        return SQLServerConnector(
            server=db_config["server"],
            database=db_config["database"],
            username=db_config.get("username"),
            password=db_config.get("password"),
            driver=db_config.get("driver", "{ODBC Driver 17 for SQL Server}"),
            trusted_connection=db_config.get("trusted_connection", False)
        )
    
    elif db_type == "postgresql" or db_type == "postgres":
        return PostgreSQLConnector(
            host=db_config["host"],
            port=db_config.get("port", 5432),
            database=db_config["database"],
            user=db_config["user"],
            password=db_config["password"]
        )
    
    else:
        raise ValueError(f"Unsupported database type: {db_type}")