from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class TaskStatus(str, enum.Enum):
    """Task status enum"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class EvaluationTask(Base):
    """Evaluation task model"""
    __tablename__ = "evaluation_task"

    id = Column(Integer, primary_key=True, index=True)
    task_name = Column(String(255), nullable=False)
    agent_id = Column(Integer, ForeignKey("agent_config.id"), nullable=False)
    env_id = Column(Integer, ForeignKey("schema_env.id"), nullable=False)
    case_ids = Column(JSON, nullable=True, default=list)
    judge_llm_model = Column(String(100), nullable=True)
    status = Column(String(50), default=TaskStatus.PENDING.value)
    stats_json = Column(JSON, nullable=True, default=dict)
    completed_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    agent = relationship("AgentConfig", backref="evaluation_tasks")
    env = relationship("SchemaEnv", backref="evaluation_tasks")
    results = relationship("EvaluationResult", back_populates="task", cascade="all, delete-orphan")
