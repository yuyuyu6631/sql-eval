from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional

from app.database import get_db
from app.models.test_case import TestCase
from app.schemas.test_case import (
    TestCaseCreate,
    TestCaseUpdate,
    TestCaseResponse,
    TestCaseGenerateRequest,
)

router = APIRouter()


@router.get("/test-cases", response_model=List[TestCaseResponse])
async def get_test_cases(
    env_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """Get all test cases with optional filtering"""
    query = select(TestCase)
    if env_id:
        query = query.where(TestCase.env_id == env_id)
    query = query.offset(skip).limit(limit).order_by(TestCase.id.desc())

    result = await db.execute(query)
    cases = result.scalars().all()
    return cases


@router.post("/test-cases", response_model=TestCaseResponse, status_code=status.HTTP_201_CREATED)
async def create_test_case(
    case: TestCaseCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new test case"""
    db_case = TestCase(**case.model_dump())
    db.add(db_case)
    await db.commit()
    await db.refresh(db_case)
    return db_case


@router.post("/test-cases/batch", response_model=List[TestCaseResponse], status_code=status.HTTP_201_CREATED)
async def create_test_cases_batch(
    cases: List[TestCaseCreate],
    db: AsyncSession = Depends(get_db),
):
    """Batch create test cases"""
    db_cases = [TestCase(**case.model_dump()) for case in cases]
    db.add_all(db_cases)
    await db.commit()
    for db_case in db_cases:
        await db.refresh(db_case)
    return db_cases


@router.get("/test-cases/{case_id}", response_model=TestCaseResponse)
async def get_test_case(
    case_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get test case by ID"""
    result = await db.execute(
        select(TestCase).where(TestCase.id == case_id)
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test case {case_id} not found",
        )
    return case


@router.put("/test-cases/{case_id}", response_model=TestCaseResponse)
async def update_test_case(
    case_id: int,
    case_update: TestCaseUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update test case"""
    result = await db.execute(
        select(TestCase).where(TestCase.id == case_id)
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test case {case_id} not found",
        )

    update_data = case_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(case, field, value)

    await db.commit()
    await db.refresh(case)
    return case


@router.delete("/test-cases/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_test_case(
    case_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete test case"""
    result = await db.execute(
        select(TestCase).where(TestCase.id == case_id)
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test case {case_id} not found",
        )

    await db.delete(case)
    await db.commit()
    return None


@router.post("/test-cases/generate", response_model=List[TestCaseResponse], status_code=status.HTTP_201_CREATED)
async def generate_test_cases(
    request: TestCaseGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    AI generate test cases (mock implementation)
    In production, this would call an LLM to generate test cases
    """
    # Mock generated test cases
    mock_cases = [
        {
            "env_id": request.env_id,
            "question": f"Query {i+1}: Sample question for this environment",
            "golden_sql": f"SELECT * FROM table_{i+1} LIMIT 10",
            "tags": ["generated"],
        }
        for i in range(request.count)
    ]

    db_cases = [TestCase(**case) for case in mock_cases]
    db.add_all(db_cases)
    await db.commit()
    for db_case in db_cases:
        await db.refresh(db_case)
    return db_cases
