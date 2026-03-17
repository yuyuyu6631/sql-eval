import logging
import traceback
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import init_db
from app.routers import (
    schema_env,
    test_case,
    agent_config,
    evaluation_task,
    dashboard,
    system_config,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("server.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("text2sql-api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup: initialize database
    await init_db()
    yield
    # Shutdown: cleanup if needed


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(schema_env.router, prefix="/api", tags=["Environment"])
app.include_router(test_case.router, prefix="/api", tags=["Test Cases"])
app.include_router(agent_config.router, prefix="/api", tags=["Agents"])
app.include_router(evaluation_task.router, prefix="/api", tags=["Evaluation"])
app.include_router(dashboard.router, prefix="/api", tags=["Dashboard"])
app.include_router(system_config.router, prefix="/api", tags=["System"])


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to capture all unhandled errors"""
    error_msg = f"Unhandled exception: {str(exc)}"
    stack_trace = traceback.format_exc()
    logger.error(f"500 Internal Server Error: {request.url}\n{error_msg}\n{stack_trace}")
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal Server Error",
            "message": str(exc) if settings.debug else "An unexpected error occurred",
            "type": exc.__class__.__name__
        },
    )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
