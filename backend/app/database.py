from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
    pool_pre_ping=True,  # Check connection health before use
    pool_recycle=3600,   # Recycle connections every hour
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for models
Base = declarative_base()


async def get_db():
    """Dependency for getting database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # [Hotfix] 自动检查并补全 evaluation_task 缺失的 completed_count 字段
        # 解决因 TDD 迭代过程中的数据库 Schema 不匹配导致的 500 错误
        def _migrate(connection):
            # 获取表信息并检查列是否存在
            # connection 这里是 SQLAlchemy 的 Connection 对象
            result = connection.exec_driver_sql("PRAGMA table_info(evaluation_task)")
            columns = [row[1] for row in result.fetchall()]
            if "completed_count" not in columns:
                connection.exec_driver_sql("ALTER TABLE evaluation_task ADD COLUMN completed_count INTEGER DEFAULT 0 NOT NULL")
        
        await conn.run_sync(_migrate)
