import asyncio
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

# Global shared HTTP client for efficiency and connection pooling
HTTP_CLIENT = httpx.AsyncClient(timeout=30.0)


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
            task = result.scalar_one_or_none()
            if not task:
                return

            # Get environment config
            env_result = await db.execute(
                select(SchemaEnv).where(SchemaEnv.id == task.env_id)
            )
            env = env_result.scalar_one_or_none()
            if not env:
                await _update_task_status(task_id, db, TaskStatus.FAILED.value)
                return

            # Get agent config
            agent_result = await db.execute(
                select(AgentConfig).where(AgentConfig.id == task.agent_id)
            )
            agent = agent_result.scalar_one_or_none()
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
            test_cases = cases_result.scalars().all()

            total = len(test_cases)
            passed = 0
            failed = 0
            errors = 0

            # Execute each test case
            for case in test_cases:
                case_result = await execute_single_case(
                    case=case,
                    env=env,
                    agent=agent,
                    task_id=task_id,
                    judge_llm_model=task.judge_llm_model,
                    db=db,
                )

                if case_result == "passed":
                    passed += 1
                elif case_result == "failed":
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
            task.completed_at = datetime.now()
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
        if not is_passed and judge_llm_model:
            diagnosis = await get_llm_diagnosis(
                question=case.question,
                golden_sql=safe_golden_sql,
                agent_sql=safe_agent_sql,
                golden_data=golden_data,
                agent_data=agent_data,
                error_message=diff_details.get("has_diff") and diff_details,
                model=judge_llm_model,
            )
            result.ai_diagnosis = diagnosis

        await db.commit()
        return "passed" if is_passed else "failed"

    except Exception as e:
        result.execution_status = "error"
        result.error_message = str(e)
        await db.commit()
        return "error"


async def fetch_sql_from_agent(
    question: str,
    ddl: str,
    agent: AgentConfig,
) -> str:
    """
    Fetch SQL from the configured agent.

    This is a mock implementation. In production, this would call the actual
    agent API endpoint.
    """
    # Mock response for demo purposes
    # In production, make actual API call to agent endpoint

    mock_responses = {
        "select": "SELECT * FROM ",
        "count": "SELECT COUNT(*) FROM ",
        "sum": "SELECT SUM() FROM ",
        "avg": "SELECT AVG() FROM ",
    }

    # Simple mock: try to extract table from question
    question_lower = question.lower()

    # Check if there's a mock endpoint configured
    if agent.api_endpoint and agent.api_endpoint != "mock":
        try:
            response = await HTTP_CLIENT.post(
                agent.api_endpoint,
                json={
                    "question": question,
                    "schema": ddl,
                },
                headers={
                    "Authorization": f"Bearer {agent.auth_token}",
                },
                timeout=agent.timeout_ms / 1000,
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("sql", "")
            else:
                print(f"Agent API returned status {response.status_code}")
        except Exception as e:
            print(f"Agent API error: {e}")

    # Mock response based on question content
    if "count" in question_lower:
        return "SELECT COUNT(*) FROM users LIMIT 10"
    elif "sum" in question_lower:
        return "SELECT SUM(amount) FROM orders LIMIT 10"
    elif "average" in question_lower or "avg" in question_lower:
        return "SELECT AVG(price) FROM products LIMIT 10"
    else:
        # Default mock
        return "SELECT * FROM users LIMIT 10"


async def _update_task_status(task_id: int, db: AsyncSession, status: str):
    """Helper to update task status"""
    result = await db.execute(
        select(EvaluationTask).where(EvaluationTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if task:
        task.status = status
        await db.commit()
