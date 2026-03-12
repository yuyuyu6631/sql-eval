from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List


class TestCaseBase(BaseModel):
    """Test case base schema"""
    question: str
    golden_sql: str
    tags: Optional[List[str]] = None


class TestCaseCreate(TestCaseBase):
    """Test case create schema"""
    env_id: int


class TestCaseUpdate(BaseModel):
    """Test case update schema"""
    question: Optional[str] = None
    golden_sql: Optional[str] = None
    tags: Optional[List[str]] = None
    env_id: Optional[int] = None


class TestCaseResponse(TestCaseBase):
    """Test case response schema"""
    id: int
    env_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TestCaseGenerateRequest(BaseModel):
    """Test case generation request"""
    env_id: int
    count: int = 5
    question_hint: Optional[str] = None
