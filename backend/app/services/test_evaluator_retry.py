import pytest
import asyncio
import httpx
from unittest.mock import AsyncMock, patch

from app.models.agent_config import AgentConfig
from app.services.evaluator import fetch_sql_from_agent

@pytest.mark.asyncio
async def test_fetch_sql_from_agent_retry_resilience():
    """
    测试第三方大模型 API 请求抖动时，我们的函数是否具有退避重试能力。
    我们用 HTTP_CLIENT mock 一个返回：前 2 次连接超时/失败，第 3 次成功返回。
    如果缺乏重试机制，此代码将直接把第一次失败向上抛出并挂掉用例。
    """
    
    # 模拟智能体配置，设置 API endpoint
    agent = AgentConfig(id=1, api_endpoint="https://api.mockagent.com/v1/sql", auth_token="mock_token", timeout_ms=3000)

    # 制造一个 Side Effect：前两次 Exception，最后一次返回 200 成功
    call_counts = {"post": 0}
    async def side_effect_post(*args, **kwargs):
        call_counts["post"] += 1
        if call_counts["post"] == 1:
            raise httpx.TimeoutException("首次连接超时")
        if call_counts["post"] == 2:
            raise httpx.ConnectError("第二次网络抖动断开")
        
        # 第三次成功
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"sql": "SELECT * FROM success"}
        return mock_resp

    with patch("app.services.evaluator.HTTP_CLIENT.post", side_effect=side_effect_post):
        # 执行目标函数
        start_time = asyncio.get_event_loop().time()
        
        sql = await fetch_sql_from_agent("帮我查询一下", "CREATE TABLE dummy", agent)
        
        end_time = asyncio.get_event_loop().time()
        elapsed = end_time - start_time
        
        # 断言: 应该拿到第三次成功的返回，而不是抛错，且至少发生 1秒+2秒的指数退避耗时
        assert sql == "SELECT * FROM success", f"返回值不对，拿到了: {sql}"
        assert elapsed > 0.5, "执行太快了，肯定没有经历过指数退避或 sleep！"
        assert call_counts["post"] == 3, "并没有重试达到 3 次"
