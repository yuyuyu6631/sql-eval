import asyncio
import aiosqlite
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import re

from app.config import settings


class SandboxExecutor:
    """
    SQL Sandbox Executor with timeout protection
    """

    def __init__(self, db_path: str = ":memory:", timeout: int = None):
        self.db_path = db_path
        self.timeout = timeout or settings.query_timeout_seconds
        self.conn: Optional[aiosqlite.Connection] = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.conn = await aiosqlite.connect(self.db_path)
        self.conn.row_factory = aiosqlite.Row
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.conn:
            await self.conn.close()

    async def execute_ddl(self, ddl: str) -> bool:
        """Execute DDL statements to set up schema"""
        if not ddl:
            return True

        try:
            # Split by semicolon and execute each statement
            statements = [s.strip() for s in ddl.split(';') if s.strip()]
            for stmt in statements:
                await self.conn.execute(stmt)
            await self.conn.commit()
            return True
        except Exception as e:
            print(f"DDL execution error: {e}")
            return False

    async def execute_query(self, sql: str) -> Tuple[bool, Any, Optional[str]]:
        """
        Execute a SELECT query with timeout protection.

        Returns: (success, data, error_message)
        """
        try:
            # Execute with timeout
            cursor = await asyncio.wait_for(
                self.conn.execute(sql),
                timeout=self.timeout
            )

            # Fetch results
            rows = await cursor.fetchall()

            # Convert to list of dicts
            if not rows:
                return True, [], None

            # Get column names from cursor description
            columns = [desc[0] for desc in cursor.description] if cursor.description else []

            # Convert rows to list of dicts
            results = []
            for row in rows:
                results.append(dict(zip(columns, row)))

            return True, results, None

        except asyncio.TimeoutError:
            return False, None, f"Query timeout after {self.timeout} seconds"
        except Exception as e:
            return False, None, str(e)

    async def execute_with_schema(self, ddl: str, sql: str) -> Tuple[bool, Any, Optional[str]]:
        """
        Execute SQL with a given schema.

        Creates an in-memory database, executes DDL, then runs the query.
        """
        # Create in-memory database
        conn = await aiosqlite.connect(":memory:")
        conn.row_factory = aiosqlite.Row

        try:
            # Execute DDL
            if ddl:
                statements = [s.strip() for s in ddl.split(';') if s.strip()]
                for stmt in statements:
                    if stmt:
                        await conn.execute(stmt)
                await conn.commit()

            # Execute query with timeout
            cursor = await asyncio.wait_for(
                conn.execute(sql),
                timeout=self.timeout
            )

            rows = await cursor.fetchall()

            # Get columns
            columns = [desc[0] for desc in cursor.description] if cursor.description else []

            results = []
            for row in rows:
                results.append(dict(zip(columns, row)))

            return True, results, None

        except asyncio.TimeoutError:
            return False, None, f"Query timeout after {self.timeout} seconds"
        except Exception as e:
            return False, None, str(e)
        finally:
            await conn.close()


async def execute_sql_in_sandbox(
    ddl: str,
    sql: str,
    db_url: Optional[str] = None
) -> Tuple[bool, Any, Optional[str]]:
    """
    Convenience function to execute SQL in a sandbox environment.

    Args:
        ddl: Schema definition (CREATE TABLE statements)
        sql: Query to execute
        db_url: Optional database URL (uses in-memory if not provided)

    Returns:
        Tuple of (success, data, error_message)
    """
    if db_url:
        # Use provided database
        executor = SandboxExecutor(db_path=db_url)
        async with executor:
            return await executor.execute_with_schema(ddl, sql)
    else:
        # Use in-memory database
        executor = SandboxExecutor()
        async with executor:
            return await executor.execute_with_schema(ddl, sql)
