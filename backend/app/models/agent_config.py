from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.database import Base


class AgentConfig(Base):
    """Agent configuration model"""
    __tablename__ = "agent_config"

    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String(255), nullable=False, unique=True)
    api_endpoint = Column(String(500), nullable=False)
    auth_token = Column(String(500), nullable=True)
    rate_limit_qps = Column(Integer, default=10)
    timeout_ms = Column(Integer, default=30000)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
