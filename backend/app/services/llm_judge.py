import httpx
from typing import Optional, Dict, Any
from app.config import settings


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
    if not settings.judge_llm_endpoint:
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
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.judge_llm_endpoint,
                json={
                    "model": model or "gpt-4",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500,
                },
                headers={
                    "Authorization": f"Bearer {settings.judge_llm_api_key}",
                },
                timeout=30.0,
            )
            if response.status_code == 200:
                result = response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", "No diagnosis available")
            else:
                return f"LLM API error: {response.status_code}"
    except Exception as e:
        return f"LLM diagnosis failed: {str(e)}"
