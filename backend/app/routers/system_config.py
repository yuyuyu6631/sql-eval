from typing import Optional
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.services.llm_judge import test_judge_llm_connection
from app.services.secret_store import get_judge_api_key, set_judge_api_key

router = APIRouter()
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


class JudgeConfigResponse(BaseModel):
    endpoint: Optional[str] = None
    default_model: Optional[str] = None
    api_key_configured: bool = False


class JudgeConfigUpdateRequest(BaseModel):
    endpoint: Optional[str] = None
    api_key: Optional[str] = None
    default_model: Optional[str] = None


class JudgeConfigTestRequest(BaseModel):
    endpoint: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None


@router.get("/system/judge-config", response_model=JudgeConfigResponse)
async def get_judge_config():
    api_key = _get_or_migrate_api_key()
    return JudgeConfigResponse(
        endpoint=settings.judge_llm_endpoint,
        default_model=settings.judge_llm_default_model,
        api_key_configured=bool(api_key),
    )


@router.put("/system/judge-config", response_model=JudgeConfigResponse)
async def update_judge_config(payload: JudgeConfigUpdateRequest):
    if payload.endpoint is not None:
        settings.judge_llm_endpoint = payload.endpoint.strip() or None
    if payload.api_key is not None:
        settings.judge_llm_api_key = None
        set_judge_api_key(payload.api_key)
    if payload.default_model is not None:
        settings.judge_llm_default_model = payload.default_model.strip() or None

    _persist_judge_config_to_env(
        endpoint=settings.judge_llm_endpoint,
        default_model=settings.judge_llm_default_model,
    )

    api_key = get_judge_api_key(settings.judge_llm_api_key)
    return JudgeConfigResponse(
        endpoint=settings.judge_llm_endpoint,
        default_model=settings.judge_llm_default_model,
        api_key_configured=bool(api_key),
    )


@router.post("/system/judge-config/test")
async def test_judge_config(payload: JudgeConfigTestRequest):
    endpoint = (payload.endpoint or settings.judge_llm_endpoint or "").strip()
    api_key = (payload.api_key or _get_or_migrate_api_key() or "").strip()
    model = (payload.model or settings.judge_llm_default_model or "MiniMax-M2.5").strip()

    if not endpoint or not api_key:
        raise HTTPException(status_code=400, detail="Endpoint and API key are required")

    try:
        return await test_judge_llm_connection(endpoint=endpoint, api_key=api_key, model=model)
    except httpx.HTTPStatusError as exc:
        detail = f"Judge API returned {exc.response.status_code}"
        try:
            body = exc.response.json()
        except Exception:
            body = exc.response.text
        raise HTTPException(status_code=400, detail={"message": detail, "body": body}) from exc
    except Exception as exc:
        message = str(exc) or exc.__class__.__name__
        raise HTTPException(status_code=400, detail=message) from exc


def _persist_judge_config_to_env(
    endpoint: Optional[str],
    default_model: Optional[str],
) -> None:
    updates = {
        "JUDGE_LLM_ENDPOINT": endpoint or "",
        "JUDGE_LLM_DEFAULT_MODEL": default_model or "",
    }

    lines: list[str] = []
    existing: dict[str, str] = {}
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
        for line in lines:
            if "=" in line and not line.strip().startswith("#"):
                key, _ = line.split("=", 1)
                existing[key.strip()] = line

    # Remove sensitive key from .env if it exists from previous versions.
    lines = [
        line for line in lines
        if not line.startswith("JUDGE_LLM_API_KEY=") and not line.strip().startswith("JUDGE_LLM_API_KEY=")
    ]

    for key, value in updates.items():
        rendered = f"{key}={value}"
        if key in existing:
            idx = next(
                i for i, line in enumerate(lines)
                if line.startswith(f"{key}=") or line.strip().startswith(f"{key}=")
            )
            lines[idx] = rendered
        else:
            lines.append(rendered)

    ENV_PATH.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def _get_or_migrate_api_key() -> Optional[str]:
    """
    Keep backward compatibility: if key exists in env, migrate it to secret store once.
    """
    secret_key = get_judge_api_key(None)
    if secret_key:
        return secret_key

    env_key = (settings.judge_llm_api_key or "").strip()
    if not env_key:
        return None

    set_judge_api_key(env_key)
    settings.judge_llm_api_key = None
    _persist_judge_config_to_env(
        endpoint=settings.judge_llm_endpoint,
        default_model=settings.judge_llm_default_model,
    )
    return env_key
