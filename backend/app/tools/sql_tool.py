"""SQL Tool and Read-Only Schema Inspection Engine for Phase 7 (Data Agent)."""
import re
import sqlite3
import time
import logging
from typing import Any, Dict, List, Optional, Tuple
from app.schemas.data_analysis import SQLQueryResponse, TableColumnInfo

logger = logging.getLogger(__name__)

# Dangerous keywords that must be strictly forbidden in read-only SQL queries
FORBIDDEN_SQL_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE",
    "GRANT", "REVOKE", "EXEC", "EXECUTE", "REPLACE", "MERGE", "ATTACH", "DETACH"
}


class SQLTool:
    """Read-only SQL Query Execution & Schema Inspection Tool."""

    def __init__(self, db_path: str = "radis_dev.db") -> None:
        self.db_path = db_path

    def get_connection(self) -> sqlite3.Connection:
        """Returns a read-only SQLite database connection."""
        conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn

    def validate_read_only_sql(self, sql: str) -> Tuple[bool, Optional[str]]:
        """Validates that an SQL query is purely read-only and safe from injection/mutation."""
        clean_sql = sql.strip()
        if not clean_sql:
            return False, "SQL query cannot be empty."

        # Check for multiple statements separated by semicolon
        statements = [s for s in clean_sql.split(";") if s.strip()]
        if len(statements) > 1:
            return False, "Multiple SQL statements are strictly forbidden for security reasons."

        # Tokenize upper-case keywords
        tokens = re.findall(r"\b[A-Z_]+\b", clean_sql.upper())
        for token in tokens:
            if token in FORBIDDEN_SQL_KEYWORDS:
                return False, f"Forbidden non-read-only SQL keyword detected: '{token}'."

        # Check starting verb
        first_word = clean_sql.lstrip(" (").split()[0].upper() if clean_sql.lstrip(" (").split() else ""
        if first_word not in ("SELECT", "WITH", "EXPLAIN", "PRAGMA"):
            return False, f"SQL query must start with SELECT or WITH. Got: '{first_word}'."

        return True, None

    def list_tables(self) -> List[str]:
        """Lists all user tables in the SQLite database."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            tables = [row["name"] for row in cursor.fetchall()]
            conn.close()
            return tables
        except Exception as e:
            logger.error(f"Failed to list SQL tables: {e}")
            return []

    def get_table_schema(self, table_name: str) -> List[TableColumnInfo]:
        """Inspects table schema columns, types, and primary keys."""
        # Sanitize table_name to guard against injection in PRAGMA
        if not re.match(r"^[a-zA-Z0-9_]+$", table_name):
            logger.warning(f"Invalid table name requested for schema inspection: {table_name}")
            return []

        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info('{table_name}')")
            rows = cursor.fetchall()
            conn.close()

            columns = []
            for row in rows:
                columns.append(
                    TableColumnInfo(
                        name=row["name"],
                        data_type=row["type"] or "TEXT",
                        nullable=not bool(row["notnull"]),
                        primary_key=bool(row["pk"]),
                    )
                )
            return columns
        except Exception as e:
            logger.error(f"Failed to inspect schema for table '{table_name}': {e}")
            return []

    def execute_query(self, sql: str, limit: int = 100) -> SQLQueryResponse:
        """Executes a read-only SQL query safely and returns structured output."""
        start_time = time.time()

        # Validate SQL safety
        is_valid, error = self.validate_read_only_sql(sql)
        if not is_valid:
            return SQLQueryResponse(
                sql=sql,
                is_success=False,
                error_message=f"SQL Security Error: {error}",
                execution_time_ms=round((time.time() - start_time) * 1000, 2),
            )

        # Enforce max limit if missing
        final_sql = sql.strip().rstrip(";")
        if "LIMIT" not in final_sql.upper():
            final_sql = f"{final_sql} LIMIT {limit}"

        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(final_sql)
            rows_raw = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            
            rows = [dict(row) for row in rows_raw]
            conn.close()

            exec_time = round((time.time() - start_time) * 1000, 2)
            return SQLQueryResponse(
                sql=final_sql,
                is_success=True,
                columns=columns,
                rows=rows,
                row_count=len(rows),
                execution_time_ms=exec_time,
            )
        except Exception as e:
            exec_time = round((time.time() - start_time) * 1000, 2)
            logger.error(f"SQL execution failed for query '{sql}': {e}")
            return SQLQueryResponse(
                sql=sql,
                is_success=False,
                error_message=f"SQL Execution Error: {str(e)}",
                execution_time_ms=exec_time,
            )
