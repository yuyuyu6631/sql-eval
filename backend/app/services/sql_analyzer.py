from typing import Any, List, Dict, Tuple


def compare_result_sets(
    golden_data: List[Dict[str, Any]],
    agent_data: List[Dict[str, Any]],
    ordered: bool = False
) -> Tuple[bool, Dict[str, Any]]:
    """
    Compare two result sets for equality.

    Args:
        golden_data: Expected result set
        agent_data: Actual result set from agent
        ordered: Whether order matters (default: False for unordered comparison)

    Returns:
        Tuple of (is_equal, diff_details)
    """
    if golden_data is None:
        golden_data = []
    if agent_data is None:
        agent_data = []

    diff_details = {
        "golden_count": len(golden_data),
        "agent_count": len(agent_data),
        "row_diff": len(golden_data) - len(agent_data),
        "has_diff": False,
        "missing_rows": [],
        "extra_rows": [],
        "different_values": [],
    }

    # Check row count
    if len(golden_data) != len(agent_data):
        diff_details["has_diff"] = True

    if not golden_data and not agent_data:
        return True, diff_details

    if not golden_data:
        diff_details["has_diff"] = True
        diff_details["extra_rows"] = agent_data[:10]  # Show first 10
        return False, diff_details

    if not agent_data:
        diff_details["has_diff"] = True
        diff_details["missing_rows"] = golden_data[:10]  # Show first 10
        return False, diff_details

    if ordered:
        # Ordered comparison
        max_len = max(len(golden_data), len(agent_data))
        for i in range(max_len):
            if i >= len(golden_data):
                diff_details["extra_rows"].append(agent_data[i])
                diff_details["has_diff"] = True
            elif i >= len(agent_data):
                diff_details["missing_rows"].append(golden_data[i])
                diff_details["has_diff"] = True
            elif golden_data[i] != agent_data[i]:
                diff_details["different_values"].append({
                    "row": i,
                    "expected": golden_data[i],
                    "actual": agent_data[i],
                })
                diff_details["has_diff"] = True
    else:
        # Unordered comparison - check if all golden rows exist in agent data
        golden_set = set()
        for row in golden_data:
            # Create a hashable representation
            key = tuple(sorted(row.items()))
            golden_set.add(key)

        agent_set = set()
        for row in agent_data:
            key = tuple(sorted(row.items()))
            agent_set.add(key)

        # Find missing (in golden but not in agent)
        missing = golden_set - agent_set
        # Find extra (in agent but not in golden)
        extra = agent_set - golden_set

        if missing:
            diff_details["missing_rows"] = [dict(m) for m in list(missing)[:10]]
            diff_details["has_diff"] = True

        if extra:
            diff_details["extra_rows"] = [dict(e) for e in list(extra)[:10]]
            diff_details["has_diff"] = True

    is_equal = not diff_details["has_diff"]
    return is_equal, diff_details


def analyze_sql_complexity(sql: str) -> Dict[str, Any]:
    """
    Analyze SQL query complexity.

    Returns a dictionary with complexity metrics.
    """
    sql_upper = sql.upper()

    complexity = {
        "has_join": "JOIN" in sql_upper,
        "has_subquery": "SELECT" in sql_upper and sql_upper.count("SELECT") > 1,
        "has_aggregation": any(kw in sql_upper for kw in ["COUNT", "SUM", "AVG", "MAX", "MIN", "GROUP BY"]),
        "has_order_by": "ORDER BY" in sql_upper,
        "has_limit": "LIMIT" in sql_upper,
        "has_distinct": "DISTINCT" in sql_upper,
        "has_case": "CASE" in sql_upper,
        "estimated_complexity": "simple",
    }

    # Estimate complexity level
    score = sum([
        complexity["has_join"] * 2,
        complexity["has_subquery"] * 3,
        complexity["has_aggregation"] * 1,
    ])

    if score >= 5:
        complexity["estimated_complexity"] = "high"
    elif score >= 2:
        complexity["estimated_complexity"] = "medium"
    else:
        complexity["estimated_complexity"] = "simple"

    return complexity
