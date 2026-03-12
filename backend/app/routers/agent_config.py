from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models.agent_config import AgentConfig
from app.schemas.agent_config import (
    AgentConfigCreate,
    AgentConfigUpdate,
    AgentConfigResponse,
)

router = APIRouter()


@router.get("/agents", response_model=List[AgentConfigResponse])
async def get_agents(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """Get all agent configurations"""
    result = await db.execute(
        select(AgentConfig).offset(skip).limit(limit)
    )
    agents = result.scalars().all()
    return agents


@router.post("/agents", response_model=AgentConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent: AgentConfigCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new agent configuration"""
    db_agent = AgentConfig(**agent.model_dump())
    db.add(db_agent)
    await db.commit()
    await db.refresh(db_agent)
    return db_agent


@router.get("/agents/{agent_id}", response_model=AgentConfigResponse)
async def get_agent(
    agent_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get agent configuration by ID"""
    result = await db.execute(
        select(AgentConfig).where(AgentConfig.id == agent_id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )
    return agent


@router.put("/agents/{agent_id}", response_model=AgentConfigResponse)
async def update_agent(
    agent_id: int,
    agent_update: AgentConfigUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update agent configuration"""
    result = await db.execute(
        select(AgentConfig).where(AgentConfig.id == agent_id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )

    update_data = agent_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(agent, field, value)

    await db.commit()
    await db.refresh(agent)
    return agent


@router.delete("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete agent configuration"""
    result = await db.execute(
        select(AgentConfig).where(AgentConfig.id == agent_id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )

    await db.delete(agent)
    await db.commit()
    return None
