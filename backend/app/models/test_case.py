from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class TestCase(Base):
    """Test case model"""
    __tablename__ = "test_case"

    id = Column(Integer, primary_key=True, index=True)
    env_id = Column(Integer, ForeignKey("schema_env.id"), nullable=False)
    question = Column(Text, nullable=False)
    golden_sql = Column(Text, nullable=False)
    tags = Column(JSON, nullable=True, default=list)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    env = relationship("SchemaEnv", backref="test_cases")
