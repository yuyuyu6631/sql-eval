from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Dict, Any, List

from app.database import get_db
from app.models.evaluation_task import EvaluationTask, TaskStatus
from app.models.evaluation_result import EvaluationResult
from app.models.test_case import TestCase

router = APIRouter()


@router.get("/dashboard/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Get global dashboard statistics"""

    # Total tasks
    total_tasks_result = await db.execute(
        select(func.count(EvaluationTask.id))
    )
    total_tasks = total_tasks_result.scalar() or 0

    # Tasks by status
    status_result = await db.execute(
        select(EvaluationTask.status, func.count(EvaluationTask.id))
        .group_by(EvaluationTask.status)
    )
    status_counts = {row[0]: row[1] for row in status_result.all()}

    # Total test cases
    total_cases_result = await db.execute(
        select(func.count(TestCase.id))
    )
    total_cases = total_cases_result.scalar() or 0

    # Total results
    total_results_result = await db.execute(
        select(func.count(EvaluationResult.id))
    )
    total_results = total_results_result.scalar() or 0

    # Pass rate
    passed_result = await db.execute(
        select(func.count(EvaluationResult.id))
        .where(EvaluationResult.data_diff_passed == True)
    )
    passed_count = passed_result.scalar() or 0
    pass_rate = (passed_count / total_results * 100) if total_results > 0 else 0

    return {
        "total_tasks": total_tasks,
        "total_cases": total_cases,
        "total_results": total_results,
        "status_counts": status_counts,
        "pass_rate": round(pass_rate, 2),
    }


@router.get("/dashboard/error-distribution")
async def get_error_distribution(db: AsyncSession = Depends(get_db)):
    """Get error distribution by type"""

    # Group by execution status
    result = await db.execute(
        select(
            EvaluationResult.execution_status,
            func.count(EvaluationResult.id)
        ).group_by(EvaluationResult.execution_status)
    )

    distribution = {}
    for status, count in result.all():
        distribution[status or "unknown"] = count

    return {
        "distribution": distribution,
    }


@router.get("/dashboard/complexity-analysis")
async def get_complexity_analysis(db: AsyncSession = Depends(get_db)):
    """Get complexity analysis based on SQL patterns"""

    # Get results with execution time
    result = await db.execute(
        select(EvaluationResult).where(
            EvaluationResult.execution_time_ms.isnot(None)
        )
    )
    results = result.scalars().all()

    if not results:
        return {
            "avg_execution_time_ms": 0,
            "slowest_query_ms": 0,
            "fastest_query_ms": 0,
        }

    times = [r.execution_time_ms for r in results if r.execution_time_ms]
    avg_time = sum(times) / len(times) if times else 0

    return {
        "avg_execution_time_ms": round(avg_time, 2),
        "slowest_query_ms": max(times) if times else 0,
        "fastest_query_ms": min(times) if times else 0,
        "total_queries": len(times),
    }


@router.get("/dashboard/leaderboard")
async def get_leaderboard(db: AsyncSession = Depends(get_db)):
    """Get agent leaderboard by pass rate"""

    result = await db.execute(
        select(
            EvaluationTask.agent_id,
            func.count(EvaluationResult.id).label("total"),
            func.sum(
                func.cast(EvaluationResult.data_diff_passed, int)
            ).label("passed")
        )
        .join(EvaluationResult, EvaluationResult.task_id == EvaluationTask.id)
        .group_by(EvaluationTask.agent_id)
    )

    leaderboard = []
    for agent_id, total, passed in result.all():
        pass_rate = (passed / total * 100) if total > 0 else 0
        leaderboard.append({
            "agent_id": agent_id,
            "total_tests": total,
            "passed": passed,
            "pass_rate": round(pass_rate, 2),
        })

    # Sort by pass rate descending
    leaderboard.sort(key=lambda x: x["pass_rate"], reverse=True)

    return {"leaderboard": leaderboard}
