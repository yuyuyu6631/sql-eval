import asyncio
import inspect
from typing import Optional, Any, Tuple

import aiosqlite

from app.config import settings

try:
    import asyncpg  # type: ignore
except Exception:
    asyncpg = None


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
            statements = [s.strip() for s in ddl.split(";") if s.strip()]
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
            cursor = await asyncio.wait_for(self.conn.execute(sql), timeout=self.timeout)
            rows = await cursor.fetchall()

            if not rows:
                return True, [], None

            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            results = [dict(zip(columns, row)) for row in rows]
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
        conn = await aiosqlite.connect(":memory:")
        conn.row_factory = aiosqlite.Row

        try:
            if ddl:
                statements = [s.strip() for s in ddl.split(";") if s.strip()]
                for stmt in statements:
                    await conn.execute(stmt)
                await conn.commit()

            cursor = await asyncio.wait_for(conn.execute(sql), timeout=self.timeout)
            rows = await cursor.fetchall()

            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            results = [dict(zip(columns, row)) for row in rows]
            return True, results, None
        except asyncio.TimeoutError:
            return False, None, f"Query timeout after {self.timeout} seconds"
        except Exception as e:
            return False, None, str(e)
        finally:
            await conn.close()


async def _execute_on_real_db(
    db_url: str,
    sql: str,
    timeout: int = None
) -> Tuple[bool, Any, Optional[str]]:
    """
    Connect to read-only sandbox database and execute query.
    """
    timeout = timeout or settings.query_timeout_seconds
    if asyncpg is None:
        return False, None, "asyncpg is not installed; PostgreSQL sandbox is unavailable in current environment."

    try:
        connect_coro = asyncpg.connect(db_url)
        conn = await asyncio.wait_for(connect_coro, timeout=timeout)
        try:
            tx = conn.transaction(readonly=True)
            if inspect.isawaitable(tx):
                tx = await tx
            async with tx:
                rows = await asyncio.wait_for(conn.fetch(sql), timeout=timeout)

            results = [dict(row) for row in rows]
            return True, results, None
        finally:
            await conn.close()
    except asyncio.TimeoutError:
        if inspect.iscoroutine(connect_coro):
            connect_coro.close()
        return False, None, f"查询超时({timeout}s)"
    except Exception as e:
        if asyncpg is not None and isinstance(e, asyncpg.exceptions.UndefinedTableError):
            return False, None, f"表不存在: {str(e)}"
        return False, None, str(e)


async def execute_sql_in_sandbox(
    ddl: str,
    sql: str,
    db_url: Optional[str] = None
) -> Tuple[bool, Any, Optional[str]]:
    """
    Convenience function to execute SQL in a sandbox environment.
    """
    if db_url and (db_url.startswith("postgresql") or db_url.startswith("mysql")):
        return await _execute_on_real_db(db_url, sql)

    executor = SandboxExecutor()
    async with executor:
        return await executor.execute_with_schema(ddl, sql)
