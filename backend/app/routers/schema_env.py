from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models.schema_env import SchemaEnv
from app.schemas.schema_env import (
    SchemaEnvCreate,
    SchemaEnvUpdate,
    SchemaEnvResponse,
)

router = APIRouter()


@router.get("/schema-envs", response_model=List[SchemaEnvResponse])
async def get_schema_envs(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """Get all schema environments"""
    result = await db.execute(
        select(SchemaEnv).offset(skip).limit(limit)
    )
    envs = result.scalars().all()
    return envs


@router.post("/schema-envs", response_model=SchemaEnvResponse, status_code=status.HTTP_201_CREATED)
async def create_schema_env(
    env: SchemaEnvCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new schema environment"""
    db_env = SchemaEnv(**env.model_dump())
    db.add(db_env)
    await db.commit()
    await db.refresh(db_env)
    return db_env


@router.get("/schema-envs/{env_id}", response_model=SchemaEnvResponse)
async def get_schema_env(
    env_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get schema environment by ID"""
    result = await db.execute(
        select(SchemaEnv).where(SchemaEnv.id == env_id)
    )
    env = result.scalar_one_or_none()
    if not env:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schema environment {env_id} not found",
        )
    return env


@router.put("/schema-envs/{env_id}", response_model=SchemaEnvResponse)
async def update_schema_env(
    env_id: int,
    env_update: SchemaEnvUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update schema environment"""
    result = await db.execute(
        select(SchemaEnv).where(SchemaEnv.id == env_id)
    )
    env = result.scalar_one_or_none()
    if not env:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schema environment {env_id} not found",
        )

    update_data = env_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(env, field, value)

    await db.commit()
    await db.refresh(env)
    return env


@router.delete("/schema-envs/{env_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schema_env(
    env_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete schema environment"""
    result = await db.execute(
        select(SchemaEnv).where(SchemaEnv.id == env_id)
    )
    env = result.scalar_one_or_none()
    if not env:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schema environment {env_id} not found",
        )

    await db.delete(env)
    await db.commit()
    return None
