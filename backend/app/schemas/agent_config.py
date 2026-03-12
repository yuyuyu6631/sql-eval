from pydantic import BaseModel, ConfigDict, field_validator
from datetime import datetime
from typing import Optional


class AgentConfigBase(BaseModel):
    """Agent configuration base schema"""
    agent_name: str
    api_endpoint: str
    auth_token: Optional[str] = None
    rate_limit_qps: Optional[int] = 10
    timeout_ms: Optional[int] = 30000


class AgentConfigCreate(AgentConfigBase):
    """Agent configuration create schema"""
    pass


class AgentConfigUpdate(BaseModel):
    """Agent configuration update schema"""
    agent_name: Optional[str] = None
    api_endpoint: Optional[str] = None
    auth_token: Optional[str] = None
    rate_limit_qps: Optional[int] = None
    timeout_ms: Optional[int] = None


class AgentConfigResponse(AgentConfigBase):
    """Agent configuration response schema"""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("rate_limit_qps", mode="before")
    @classmethod
    def validate_qps(cls, v):
        return v if v is not None else 10

    @field_validator("timeout_ms", mode="before")
    @classmethod
    def validate_timeout(cls, v):
        return v if v is not None else 30000
