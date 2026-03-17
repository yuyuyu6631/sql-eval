import httpx
from typing import Optional, Any
from app.config import settings
from app.services.secret_store import get_judge_api_key


async def get_llm_diagnosis(
    question: str,
    golden_sql: str,
    agent_sql: str,
    golden_data: Any,
    agent_data: Any,
    error_message: Optional[str] = None,
    model: Optional[str] = None,
) -> str:
    """
    Get AI diagnosis for a failed test case.

    This is a mock implementation. In production, this would call an LLM API
    to analyze the difference between expected and actual results.

    Args:
        question: The natural language question
        golden_sql: The expected/golden SQL
        agent_sql: The agent-generated SQL
        golden_data: Expected result data
        agent_data: Actual result data
        error_message: Optional error message
        model: LLM model to use

    Returns:
        AI diagnosis string
    """
    endpoint = settings.judge_llm_endpoint
    api_key = get_judge_api_key(settings.judge_llm_api_key)

    if not endpoint or not api_key:
        # Return mock diagnosis if no LLM endpoint configured
        diagnosis = f"""## AI Diagnosis Report

### Question
{question}

### Golden SQL
```sql
{golden_sql}
```

### Agent SQL
```sql
{agent_sql}
```

### Analysis
"""

        if error_message:
            diagnosis += f"""
**Error**: {error_message}

**Possible Causes**:
1. Syntax error in the generated SQL
2. Incorrect table or column references
3. Missing or incorrect JOIN conditions
4. Wrong aggregation or grouping
"""
        else:
            diagnosis += f"""
**Expected Results**: {len(golden_data) if golden_data else 0} rows
**Actual Results**: {len(agent_data) if agent_data else 0} rows

**Possible Causes**:
1. Missing or incorrect WHERE conditions
2. Wrong JOIN type or table aliases
3. Incorrect column selection
4. Missing GROUP BY or HAVING clauses
"""

        diagnosis += "\n**Recommendation**: Review the SQL syntax and ensure it matches the question requirements."
        return diagnosis

    # In production, call actual LLM API
    prompt = f"""You are a SQL expert. Analyze the following test case and provide diagnosis:

Question: {question}

Expected SQL:
```sql
{golden_sql}
```

Agent Generated SQL:
```sql
{agent_sql}
```

Expected Result Count: {len(golden_data) if golden_data else 0}
Actual Result Count: {len(agent_data) if agent_data else 0}
{f"Error: {error_message}" if error_message else ""}

Provide a diagnosis explaining why the agent's SQL failed to produce the expected results.
"""

    try:
        result = await _call_chat_completion(
            endpoint=endpoint,
            api_key=api_key,
            model=model or settings.judge_llm_default_model or "MiniMax-M2.5",
            messages=[{"role": "user", "content": prompt}],
        )
        content = _extract_message_content(result)
        return content or "No diagnosis available"
    except Exception as e:
        return f"LLM diagnosis failed: {str(e)}"


async def test_judge_llm_connection(
    endpoint: str,
    api_key: str,
    model: str,
) -> dict[str, Any]:
    """Lightweight connectivity test for OpenAI-compatible judge endpoints."""
    payload = await _call_chat_completion(
        endpoint=endpoint,
        api_key=api_key,
        model=model,
        messages=[{"role": "user", "content": "Hello, how are you?"}],
        max_tokens=128,
        timeout_s=60.0,
    )
    return {
        "ok": True,
        "model": payload.get("model", model),
        "preview": (_extract_message_content(payload) or "")[:200],
    }


async def _call_chat_completion(
    endpoint: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int = 500,
    timeout_s: float = 30.0,
) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        response = await client.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
            },
        )
        response.raise_for_status()
        return response.json()


def _extract_message_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    return message.get("content") or ""
