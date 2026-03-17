import asyncio
import inspect
import time
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx

from app.models.evaluation_task import EvaluationTask, TaskStatus
from app.models.test_case import TestCase
from app.models.schema_env import SchemaEnv
from app.models.agent_config import AgentConfig
from app.models.evaluation_result import EvaluationResult
from app.utils.security import is_unsafe_sql, enforce_limit
from app.services.sandbox import execute_sql_in_sandbox
from app.services.sql_analyzer import compare_result_sets
from app.services.llm_judge import get_llm_diagnosis
from app.database import AsyncSessionLocal
from app.config import settings
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

# Global shared HTTP client for efficiency and connection pooling
HTTP_CLIENT = httpx.AsyncClient(timeout=30.0)

async def _resolve_maybe_await(value):
    """Resolve both sync and async return values (useful for test doubles)."""
    if inspect.isawaitable(value):
        return await value
    return value


async def _invoke_maybe_await(fn):
    """Invoke a callable and resolve if it returns an awaitable."""
    return await _resolve_maybe_await(fn())


async def run_evaluation(task_id: int):
    """
    Main evaluation execution engine.

    This runs in background and processes all test cases for a task.
    """
    async with AsyncSessionLocal() as db:
        try:
            # Get task
            result = await db.execute(
                select(EvaluationTask).where(EvaluationTask.id == task_id)
            )
            task = await _invoke_maybe_await(result.scalar_one_or_none)
            if not task:
                return

            # Get environment config
            env_result = await db.execute(
                select(SchemaEnv).where(SchemaEnv.id == task.env_id)
            )
            env = await _invoke_maybe_await(env_result.scalar_one_or_none)
            if not env:
                await _update_task_status(task_id, db, TaskStatus.FAILED.value)
                return

            # Get agent config
            agent_result = await db.execute(
                select(AgentConfig).where(AgentConfig.id == task.agent_id)
            )
            agent = await _invoke_maybe_await(agent_result.scalar_one_or_none)
            if not agent:
                await _update_task_status(task_id, db, TaskStatus.FAILED.value)
                return

            # Get test cases
            if task.case_ids:
                cases_result = await db.execute(
                    select(TestCase).where(TestCase.id.in_(task.case_ids))
                )
            else:
                cases_result = await db.execute(
                    select(TestCase).where(TestCase.env_id == task.env_id)
                )
            scalars_result = await _resolve_maybe_await(cases_result.scalars())
            test_cases = await _invoke_maybe_await(scalars_result.all)
            if test_cases is None:
                test_cases = []

            total = len(test_cases)
            passed = 0
            failed = 0
            errors = 0

            # Execute each test case
            # 从智能体配置读取并发上限，防止打挂被测服务
            concurrency_limit = agent.rate_limit_qps if agent.rate_limit_qps else 5
            sem = asyncio.Semaphore(concurrency_limit)
            
            async def _run_case_with_limit(c: TestCase) -> str:
                """带信号量限制的单用例执行包装器"""
                async with sem:
                    return await execute_single_case(
                        case=c,
                        env=env,
                        agent=agent,
                        task_id=task_id,
                        judge_llm_model=task.judge_llm_model,
                        db=db,
                    )

            # 并发批量执行所有用例，利用 return_exceptions=True 阻断局部单点失败雪崩
            case_outcomes = await asyncio.gather(
                *[_run_case_with_limit(c) for c in test_cases],
                return_exceptions=True
            )

            for outcome in case_outcomes:
                if isinstance(outcome, Exception):
                    errors += 1
                elif outcome == "passed":
                    passed += 1
                elif outcome == "failed":
                    failed += 1
                else:
                    errors += 1

            # Update task with stats
            stats = {
                "total": total,
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "pass_rate": round(passed / total * 100, 2) if total > 0 else 0,
            }
            task.stats_json = stats
            task.status = TaskStatus.COMPLETED.value
            from datetime import datetime as dt
            task.completed_at = dt.now()
            await db.commit()

        except Exception as e:
            print(f"Evaluation error: {e}")
            await db.rollback()  # Ensure rollback on error
            await _update_task_status(task_id, db, TaskStatus.FAILED.value)


async def execute_single_case(
    case: TestCase,
    env: SchemaEnv,
    agent: AgentConfig,
    task_id: int,
    judge_llm_model: str,
    db: AsyncSession,
) -> str:
    """
    Execute a single test case evaluation.

    Returns: "passed", "failed", or "error"
    """
    start_time = time.time()
    result = EvaluationResult(
        task_id=task_id,
        case_id=case.id,
        execution_status="running",
    )
    db.add(result)
    result.created_at = datetime.now()
    await db.commit()
    await db.refresh(result)

    try:
        # Step 1: Get SQL from agent (mock for now)
        agent_sql = await fetch_sql_from_agent(
            question=case.question,
            ddl=env.ddl_content,
            agent=agent,
        )

        result.agent_sql = agent_sql

        # Step 2: Security check
        if is_unsafe_sql(agent_sql):
            result.execution_status = "security_blocked"
            result.error_message = "SQL contains forbidden operations"
            await db.commit()
            return "error"

        # Step 3: Enforce LIMIT
        safe_golden_sql = enforce_limit(case.golden_sql, settings.max_result_rows)
        safe_agent_sql = enforce_limit(agent_sql, settings.max_result_rows)

        # Step 4: Execute golden SQL in sandbox
        golden_success, golden_data, golden_error = await execute_sql_in_sandbox(
            ddl=env.ddl_content,
            sql=safe_golden_sql,
        )

        if not golden_success:
            result.golden_data = []
            result.agent_data = []
            result.execution_status = "golden_error"
            result.error_message = f"Golden SQL error: {golden_error}"
            result.data_diff_passed = False
            await db.commit()
            return "error"

        result.golden_data = golden_data

        # Step 5: Execute agent SQL in sandbox
        agent_success, agent_data, agent_error = await execute_sql_in_sandbox(
            ddl=env.ddl_content,
            sql=safe_agent_sql,
        )

        if not agent_success:
            result.agent_data = []
            result.execution_status = "execution_error"
            result.error_message = agent_error
            await db.commit()
            return "error"

        result.agent_data = agent_data
        result.execution_time_ms = int((time.time() - start_time) * 1000)

        # Step 6: Compare results
        is_passed, diff_details = compare_result_sets(golden_data, agent_data)
        result.data_diff_passed = is_passed
        result.execution_status = "completed"

        # Step 7: Get LLM diagnosis if failed
        judge_model = judge_llm_model or settings.judge_llm_default_model
        if not is_passed and judge_model:
            diagnosis = await get_llm_diagnosis(
                question=case.question,
                golden_sql=safe_golden_sql,
                agent_sql=safe_agent_sql,
                golden_data=golden_data,
                agent_data=agent_data,
                error_message=diff_details.get("has_diff") and diff_details,
                model=judge_model,
            )
            result.ai_diagnosis = diagnosis

        await db.commit()
        return "passed" if is_passed else "failed"

    except Exception as e:
        result.execution_status = "error"
        result.error_message = str(e)
        await db.commit()
        return "error"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    reraise=True,
)
async def _call_agent_api(endpoint: str, token: str, question: str, ddl: str, timeout_s: float) -> str:
    """调用智能体 API（含退避重试机制，防止网络抖动）"""
    response = await HTTP_CLIENT.post(
        endpoint,
        json={"question": question, "schema": ddl},
        headers={"Authorization": f"Bearer {token}"},
        timeout=timeout_s,
    )
    await _resolve_maybe_await(response.raise_for_status())
    data = await _resolve_maybe_await(response.json())
    if not isinstance(data, dict):
        raise ValueError("Agent API response must be a JSON object")
    return data.get("sql", "")


async def fetch_sql_from_agent(
    question: str,
    ddl: str,
    agent: AgentConfig,
) -> str:
    """获取智能体生成的 SQL，真实 API 失败时降级到 Mock"""
    if agent.api_endpoint and agent.api_endpoint != "mock":
        try:
            return await _call_agent_api(
                endpoint=agent.api_endpoint,
                token=agent.auth_token or "",
                question=question,
                ddl=ddl,
                timeout_s=(agent.timeout_ms or 30000) / 1000,
            )
        except Exception as e:
            # 记录警告，自动降级为 Mock 测试数据
            print(f"[WARN] 智能体 API 重试后仍然失败，降级 Mock兜底: {e}")

    # Mock 降级逻辑（保留原有实现）
    question_lower = question.lower()
    if "count" in question_lower:
        return "SELECT COUNT(*) FROM users LIMIT 10"
    elif "sum" in question_lower:
        return "SELECT SUM(amount) FROM orders LIMIT 10"
    elif "average" in question_lower or "avg" in question_lower:
        return "SELECT AVG(price) FROM products LIMIT 10"
    return "SELECT * FROM users LIMIT 10"


async def _update_task_status(task_id: int, db: AsyncSession, status: str):
    """Helper to update task status"""
    result = await db.execute(
        select(EvaluationTask).where(EvaluationTask.id == task_id)
    )
    task = await _invoke_maybe_await(result.scalar_one_or_none)
    if task:
        task.status = status
        await db.commit()
