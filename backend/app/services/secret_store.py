from pathlib import Path
from typing import Optional


SECRETS_DIR = Path(__file__).resolve().parents[2] / ".secrets"
JUDGE_API_KEY_FILE = SECRETS_DIR / "judge_api_key"


def get_judge_api_key(env_fallback: Optional[str] = None) -> Optional[str]:
    """
    Read judge API key from local secret file.
    Falls back to env value for backward compatibility.
    """
    if JUDGE_API_KEY_FILE.exists():
        value = JUDGE_API_KEY_FILE.read_text(encoding="utf-8").strip()
        return value or None
    return (env_fallback or "").strip() or None


def set_judge_api_key(value: Optional[str]) -> None:
    """
    Persist judge API key into local secret file (not in .env).
    """
    SECRETS_DIR.mkdir(parents=True, exist_ok=True)
    key = (value or "").strip()
    if not key:
        if JUDGE_API_KEY_FILE.exists():
            JUDGE_API_KEY_FILE.unlink()
        return
    JUDGE_API_KEY_FILE.write_text(key + "\n", encoding="utf-8")
