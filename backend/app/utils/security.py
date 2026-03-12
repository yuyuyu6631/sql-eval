import re
from typing import List


# SQL commands that are not allowed in sandbox
FORBIDDEN_KEYWORDS = [
    r'\bDROP\b',
    r'\bDELETE\b',
    r'\bTRUNCATE\b',
    r'\bALTER\b',
    r'\bCREATE\s+(?:TABLE|DATABASE|INDEX|VIEW)\b',
    r'\bGRANT\b',
    r'\bREVOKE\b',
    r'\bINSERT\b',
    r'\bUPDATE\b',
    r';.*--',  # Comments that could hide commands
]

# Compile patterns for performance
FORBIDDEN_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in FORBIDDEN_KEYWORDS]


def is_unsafe_sql(sql: str) -> bool:
    """
    Check if SQL contains dangerous operations.

    Returns True if SQL is unsafe, False otherwise.
    """
    if not sql:
        return True

    for pattern in FORBIDDEN_PATTERNS:
        if pattern.search(sql):
            return True

    return False


def get_unsafe_keywords(sql: str) -> List[str]:
    """
    Get list of unsafe keywords found in SQL.

    Returns a list of forbidden keywords present in the SQL.
    """
    found = []
    for pattern in FORBIDDEN_PATTERNS:
        match = pattern.search(sql)
        if match:
            # Extract the matched keyword/pattern
            matched = match.group(0)
            found.append(matched)
    return found


def enforce_limit(sql: str, max_rows: int = 100) -> str:
    """
    Ensure SQL has a LIMIT clause to prevent large result sets.

    If LIMIT is already present, does nothing.
    Otherwise appends LIMIT max_rows.
    """
    if not sql:
        return sql

    sql_upper = sql.upper()

    # Check if LIMIT already exists
    if 'LIMIT' in sql_upper:
        # Check if there's a number after LIMIT
        limit_match = re.search(r'LIMIT\s+(\d+)', sql, re.IGNORECASE)
        if limit_match:
            existing_limit = int(limit_match.group(1))
            if existing_limit > max_rows:
                # Replace with max_rows
                return re.sub(
                    r'LIMIT\s+\d+',
                    f'LIMIT {max_rows}',
                    sql,
                    flags=re.IGNORECASE
                )
        return sql

    # Append LIMIT
    return f"{sql} LIMIT {max_rows}"
