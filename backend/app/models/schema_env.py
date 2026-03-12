from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.database import Base


class SchemaEnv(Base):
    """Environment configuration model"""
    __tablename__ = "schema_env"

    id = Column(Integer, primary_key=True, index=True)
    env_name = Column(String(255), nullable=False, unique=True)
    ddl_content = Column(Text, nullable=False, default="")
    sandbox_db_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
