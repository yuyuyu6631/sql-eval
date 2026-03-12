import asyncio
import sys
import os

# Add the current directory to sys.path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), 'backend')))

from backend.app.database import init_db
from backend.app.models.schema_env import SchemaEnv
from backend.app.models.test_case import TestCase
from backend.app.models.agent_config import AgentConfig
from backend.app.models.evaluation_task import EvaluationTask
from backend.app.models.evaluation_result import EvaluationResult

async def main():
    print("Initializing database...")
    await init_db()
    print("Database initialized successfully.")

if __name__ == "__main__":
    asyncio.run(main())
