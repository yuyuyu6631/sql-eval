import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.evaluator import run_evaluation

@pytest.mark.asyncio
async def test_run_evaluation_concurrency():
    """
    测试 run_evaluation 是否真的在并发执行而不是串行执行。
    我们模拟 execute_single_case 耗时 0.1 秒，测试 10 个 mock cases。
    如果是串行，总耗时应 > 1.0 秒。
    如果是并发 (并发上限默认 5)，总耗时应在 0.2 ~ 0.3 秒左右，并且远低于 1.0 秒。
    """
    
    # 构建 Mock 对象
    # 为了避免真查数据库，我们要 mock 掉那些 ORM 执行逻辑
    
    mock_task = AsyncMock()
    mock_task.id = 1
    mock_task.env_id = 1
    mock_task.agent_id = 1
    mock_task.case_ids = None
    mock_task.judge_llm_model = None
    
    mock_env = AsyncMock()
    mock_agent = AsyncMock()
    # 设定并发限制为 5
    mock_agent.rate_limit_qps = 5
    
    # Mock出 10 个测试用例
    mock_cases = [AsyncMock(id=i) for i in range(10)]
    
    mock_db = AsyncMock(spec=AsyncSession)
    
    # 模拟 db.execute().scalar_one_or_none() 和 scalars().all() 的返回链
    mock_result_task = AsyncMock()
    mock_result_task.scalar_one_or_none.return_value = mock_task
    
    mock_result_env = AsyncMock()
    mock_result_env.scalar_one_or_none.return_value = mock_env
    
    mock_result_agent = AsyncMock()
    mock_result_agent.scalar_one_or_none.return_value = mock_agent
    
    mock_result_cases = AsyncMock()
    mock_result_cases.scalars.return_value.all.return_value = mock_cases
    
    # 为不同的 select() 返回不同的 mock
    call_counts = {"db_execute": 0}
    async def side_effect_db_execute(*args, **kwargs):
        count = call_counts["db_execute"]
        call_counts["db_execute"] += 1
        if count == 0: return mock_result_task
        if count == 1: return mock_result_env
        if count == 2: return mock_result_agent
        if count == 3: return mock_result_cases
        return AsyncMock()

    mock_db.execute.side_effect = side_effect_db_execute
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()

    # AsyncSessionLocal mock
    class MockSessionContextManager:
        async def __aenter__(self):
            return mock_db
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    async def mock_execute_single_case(*args, **kwargs):
        # 强制休眠 0.1s
        await asyncio.sleep(0.1)
        return "passed"

    with patch("app.services.evaluator.AsyncSessionLocal", return_value=MockSessionContextManager()), \
         patch("app.services.evaluator.execute_single_case", side_effect=mock_execute_single_case):
        
        start_time = asyncio.get_event_loop().time()
        
        await run_evaluation(1)
        
        end_time = asyncio.get_event_loop().time()
        elapsed = end_time - start_time
        
        # 验证结果
        # 断言: 10个任务，串行要 > 1.0s。并发(上限5)大概分为两批，每批 0.1s -> 大约 0.2 ~ 0.3s
        # 只要确信远低于 0.9s 就是并发了。
        assert elapsed < 0.9, f"执行时间 {elapsed}s 太长，说明仍然是串行循环"
        
        # 验证统计逻辑正确更新
        assert mock_task.stats_json["passed"] == 10
        assert mock_task.stats_json["total"] == 10
        assert mock_task.status == "completed"

@pytest.mark.asyncio
async def test_run_evaluation_exception_resilience():
    """测试单个用例崩溃时，并发引擎不会挂掉，其余用例能正常执行完成。"""
    
    mock_task = AsyncMock(id=1, env_id=1, agent_id=1, case_ids=None, judge_llm_model=None)
    mock_agent = AsyncMock(rate_limit_qps=5)
    mock_cases = [AsyncMock(id=i) for i in range(3)]
    mock_db = AsyncMock()
    
    call_counts = {"db_execute": 0}
    async def side_effect_db_execute(*args, **kwargs):
        idx = call_counts["db_execute"]
        call_counts["db_execute"] += 1
        mocks = [
            AsyncMock(scalar_one_or_none=lambda: mock_task),
            AsyncMock(scalar_one_or_none=lambda: AsyncMock()),
            AsyncMock(scalar_one_or_none=lambda: mock_agent),
            AsyncMock(**{"scalars.return_value.all.return_value": mock_cases}),
        ]
        return mocks[idx] if idx < len(mocks) else AsyncMock()

    mock_db.execute.side_effect = side_effect_db_execute

    class MockSessionContextManager:
        async def __aenter__(self): return mock_db
        async def __aexit__(self, exc_type, exc_val, exc_tb): pass

    # 制造一个异常
    async def mock_execute_single_case(case, *args, **kwargs):
        if case.id == 1:
            raise ValueError("模拟异常中断")
        return "passed"

    with patch("app.services.evaluator.AsyncSessionLocal", return_value=MockSessionContextManager()), \
         patch("app.services.evaluator.execute_single_case", side_effect=mock_execute_single_case):
        
        await run_evaluation(1)
        
        # 异常不应向上抛并且影响整体，应该被转化为 errors += 1
        assert mock_task.stats_json["passed"] == 2
        assert mock_task.stats_json["errors"] == 1
        assert mock_task.stats_json["total"] == 3
