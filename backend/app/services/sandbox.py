import asyncio
import aiosqlite
import asyncpg
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


async def _execute_on_real_db(
    db_url: str,
    sql: str,
    timeout: int = None
) -> Tuple[bool, Any, Optional[str]]:
    """
    连接真实只读沙箱数据库执行查询。
    
    注意：沙箱 DB 账号必须仅有 SELECT 权限。
    """
    timeout = timeout or settings.query_timeout_seconds
    try:
        conn = await asyncio.wait_for(
            asyncpg.connect(db_url),
            timeout=timeout
        )
        try:
            # 强制只读事务，双重保险
            async with conn.transaction(readonly=True):
                rows = await asyncio.wait_for(
                    conn.fetch(sql),
                    timeout=timeout
                )
            # asyncpg Record 对象转换为普通字典列表
            results = [dict(row) for row in rows]
            return True, results, None
        finally:
            await conn.close()
    except asyncio.TimeoutError:
        return False, None, f"查询超时（{timeout}s）"
    except asyncpg.exceptions.UndefinedTableError as e:
        return False, None, f"表不存在: {str(e)}"
    except Exception as e:
        return False, None, str(e)


async def execute_sql_in_sandbox(
    ddl: str,
    sql: str,
    db_url: Optional[str] = None
) -> Tuple[bool, Any, Optional[str]]:
    """
    Convenience function to execute SQL in a sandbox environment.
    """
    # 优先使用真实数据库
    if db_url and (db_url.startswith("postgresql") or db_url.startswith("mysql")):
        return await _execute_on_real_db(db_url, sql)
    
    # 降级到 SQLite 内存库（保留原有逻辑）
    executor = SandboxExecutor()
    async with executor:
        return await executor.execute_with_schema(ddl, sql)
