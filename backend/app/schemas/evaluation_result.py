from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, Any


class EvaluationResultBase(BaseModel):
    """Evaluation result base schema"""
    task_id: int
    case_id: int


class EvaluationResultResponse(BaseModel):
    """Evaluation result response schema"""
    id: int
    task_id: int
    case_id: int
    agent_sql: Optional[str] = None
    execution_status: str
    golden_data: Optional[Any] = None
    agent_data: Optional[Any] = None
    data_diff_passed: bool = False
    ai_diagnosis: Optional[str] = None
    execution_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DiagnosisResponse(BaseModel):
    """AI diagnosis response"""
    result_id: int
    diagnosis: str
    suggested_fix: Optional[str] = None
