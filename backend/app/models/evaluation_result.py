from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class EvaluationResult(Base):
    """Evaluation result model"""
    __tablename__ = "evaluation_result"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("evaluation_task.id"), nullable=False)
    case_id = Column(Integer, ForeignKey("test_case.id"), nullable=False)
    agent_sql = Column(Text, nullable=True)
    execution_status = Column(String(50), default="pending")
    golden_data = Column(JSON, nullable=True)
    agent_data = Column(JSON, nullable=True)
    data_diff_passed = Column(Boolean, default=False)
    ai_diagnosis = Column(Text, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    task = relationship("EvaluationTask", back_populates="results")
    case = relationship("TestCase")
