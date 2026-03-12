from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List
from datetime import datetime
import asyncio

from app.database import get_db
from app.models.evaluation_task import EvaluationTask, TaskStatus
from app.models.test_case import TestCase
from app.models.evaluation_result import EvaluationResult
from app.schemas.evaluation_task import (
    EvaluationTaskCreate,
    EvaluationTaskUpdate,
    EvaluationTaskResponse,
    TaskProgressResponse,
    TaskStats,
)
from app.schemas.evaluation_result import EvaluationResultResponse
from app.services.evaluator import run_evaluation

router = APIRouter()

# Store for task progress (in production, use Redis or similar)
task_progress_store = {}


@router.get("/tasks", response_model=List[EvaluationTaskResponse])
async def get_tasks(
    status_filter: str = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """Get all evaluation tasks"""
    query = select(EvaluationTask)
    if status_filter:
        query = query.where(EvaluationTask.status == status_filter)
    query = query.offset(skip).limit(limit).order_by(EvaluationTask.id.desc())

    result = await db.execute(query)
    tasks = result.scalars().all()
    return tasks


@router.post("/tasks", response_model=EvaluationTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task: EvaluationTaskCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new evaluation task"""
    db_task = EvaluationTask(**task.model_dump())
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return db_task


@router.get("/tasks/{task_id}", response_model=EvaluationTaskResponse)
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get task by ID"""
    result = await db.execute(
        select(EvaluationTask).where(EvaluationTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    return task


@router.put("/tasks/{task_id}", response_model=EvaluationTaskResponse)
async def update_task(
    task_id: int,
    task_update: EvaluationTaskUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update task"""
    result = await db.execute(
        select(EvaluationTask).where(EvaluationTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    update_data = task_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    await db.commit()
    await db.refresh(task)
    return task


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete task"""
    result = await db.execute(
        select(EvaluationTask).where(EvaluationTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    await db.delete(task)
    await db.commit()
    return None


@router.post("/tasks/{task_id}/start")
async def start_task(
    task_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Start evaluation task execution"""
    result = await db.execute(
        select(EvaluationTask).where(EvaluationTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    if task.status == TaskStatus.RUNNING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task is already running",
        )

    # Update task status to running
    task.status = TaskStatus.RUNNING.value
    await db.commit()

    # Schedule background execution
    background_tasks.add_task(run_evaluation, task_id)

    return {"message": "Task started", "task_id": task_id}


@router.get("/tasks/{task_id}/progress", response_model=TaskProgressResponse)
async def get_task_progress(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get task execution progress"""
    result = await db.execute(
        select(EvaluationTask).where(EvaluationTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    # Get total cases count
    case_ids = task.case_ids or []
    if case_ids:
        total_cases = len(case_ids)
    else:
        case_result = await db.execute(
            select(TestCase).where(TestCase.env_id == task.env_id)
        )
        total_cases = len(case_result.scalars().all())

    # Get completed results
    results_result = await db.execute(
        select(EvaluationResult).where(EvaluationResult.task_id == task_id)
    )
    completed_results = results_result.scalars().all()
    completed_cases = len(completed_results)

    progress_percentage = (completed_cases / total_cases * 100) if total_cases > 0 else 0

    return TaskProgressResponse(
        task_id=task_id,
        status=task.status,
        total_cases=total_cases,
        completed_cases=completed_cases,
        progress_percentage=progress_percentage,
    )


# Results endpoints
@router.get("/results", response_model=List[EvaluationResultResponse])
async def get_results(
    task_id: int = None,
    case_id: int = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """Get evaluation results"""
    query = select(EvaluationResult)
    if task_id:
        query = query.where(EvaluationResult.task_id == task_id)
    if case_id:
        query = query.where(EvaluationResult.case_id == case_id)
    query = query.offset(skip).limit(limit).order_by(EvaluationResult.id.desc())

    result = await db.execute(query)
    results = result.scalars().all()
    return results


@router.get("/results/{result_id}", response_model=EvaluationResultResponse)
async def get_result(
    result_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get result by ID"""
    result = await db.execute(
        select(EvaluationResult).where(EvaluationResult.id == result_id)
    )
    res = result.scalar_one_or_none()
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Result {result_id} not found",
        )
    return res


@router.get("/results/{result_id}/diagnosis")
async def get_diagnosis(
    result_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get AI diagnosis for a result"""
    result = await db.execute(
        select(EvaluationResult).where(EvaluationResult.id == result_id)
    )
    res = result.scalar_one_or_none()
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Result {result_id} not found",
        )

    return {
        "result_id": result_id,
        "diagnosis": res.ai_diagnosis,
    }
