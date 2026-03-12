from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List


class EvaluationTaskBase(BaseModel):
    """Evaluation task base schema"""
    task_name: str
    agent_id: int
    env_id: int
    case_ids: Optional[List[int]] = []
    judge_llm_model: Optional[str] = None


class EvaluationTaskCreate(EvaluationTaskBase):
    """Evaluation task create schema"""
    pass


class EvaluationTaskUpdate(BaseModel):
    """Evaluation task update schema"""
    task_name: Optional[str] = None
    agent_id: Optional[int] = None
    env_id: Optional[int] = None
    case_ids: Optional[List[int]] = None
    judge_llm_model: Optional[str] = None
    status: Optional[str] = None


class TaskStats(BaseModel):
    """Task statistics"""
    total: int = 0
    passed: int = 0
    failed: int = 0
    error: int = 0
    pass_rate: float = 0.0


class EvaluationTaskResponse(EvaluationTaskBase):
    """Evaluation task response schema"""
    id: int
    status: str
    stats_json: Optional[dict] = {}
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TaskProgressResponse(BaseModel):
    """Task progress response"""
    task_id: int
    status: str
    total_cases: int
    completed_cases: int
    progress_percentage: float
    current_result: Optional[dict] = None
