from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class SchemaEnvBase(BaseModel):
    """Schema environment base schema"""
    env_name: str
    ddl_content: str = ""
    sandbox_db_url: Optional[str] = None


class SchemaEnvCreate(SchemaEnvBase):
    """Schema environment create schema"""
    pass


class SchemaEnvUpdate(BaseModel):
    """Schema environment update schema"""
    env_name: Optional[str] = None
    ddl_content: Optional[str] = None
    sandbox_db_url: Optional[str] = None


class SchemaEnvResponse(SchemaEnvBase):
    """Schema environment response schema"""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
