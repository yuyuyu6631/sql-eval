import pytest
import asyncio
from unittest.mock import AsyncMock, patch
import asyncpg
from app.services.sandbox import execute_sql_in_sandbox

@pytest.mark.asyncio
async def test_sandbox_routes_to_real_db():
    """
    测试当 db_url 是 postgresql:// 开头时，会不会正确调用 asyncpg 连接并使用只读事务。
    如果没有路由，依然走了 SandboxExecutor (sqlite)，那么内部就会当作本地 sqlite 而没跑 real db 的逻辑。
    """
    db_url = "postgresql://user:pass@localhost:5432/testdb"
    sql = "SELECT * FROM real_table LIMIT 5"
    
    mock_conn = AsyncMock()
    mock_rows = [{"id": 1, "name": "test"}]
    mock_conn.fetch.return_value = mock_rows
    
    mock_transaction = AsyncMock()
    # Mock asyncpg transaction context manager
    mock_conn.transaction.return_value.__aenter__.return_value = mock_transaction
    
    # 捕获它有没有调 asyncpg.connect
    with patch("asyncpg.connect", new_callable=AsyncMock) as mock_connect:
        mock_connect.return_value = mock_conn
        
        success, data, error = await execute_sql_in_sandbox(ddl="CREATE TABLE real_table(id int);", sql=sql, db_url=db_url)
        
        # 1. 期望路由生效，并调用 asyncpg.connect
        assert mock_connect.call_count == 1
        assert mock_connect.call_args[0][0] == db_url
        
        # 2. 期望使用了只读事务
        assert mock_conn.transaction.call_count == 1
        assert mock_conn.transaction.call_args[1].get("readonly") is True
        
        # 3. 数据返回被正确转换
        assert success is True
        assert data == mock_rows
        assert error is None

@pytest.mark.asyncio
async def test_sandbox_real_db_timeout():
    """
    测试当连接真实数据库执行超市时，能否返回合理的错误。
    """
    db_url = "mysql://user:pass@localhost:3306/testdb"
    
    with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError("timeout")):
        success, data, error = await execute_sql_in_sandbox(ddl="", sql="SELECT SLEEP(10)", db_url=db_url)
        
        assert success is False
        assert data is None
        assert "查询超时" in error

@pytest.mark.asyncio
async def test_sandbox_real_db_table_not_found():
    """测试表不存在异常的捕获"""
    db_url = "postgresql://dummy"
    
    async def mock_wait_for(coro, timeout):
        if hasattr(coro, "__name__") and coro.__name__ == "connect":
            mock_conn = AsyncMock()
            mock_conn.transaction.return_value.__aenter__.return_value = AsyncMock()
            mock_conn.fetch.side_effect = asyncpg.exceptions.UndefinedTableError("table not found")
            return mock_conn
        return await coro

    with patch("asyncio.wait_for", side_effect=mock_wait_for):
        success, data, error = await execute_sql_in_sandbox(ddl="", sql="SELECT * FROM unknown", db_url=db_url)
        
        assert success is False
        assert "表不存在" in error
