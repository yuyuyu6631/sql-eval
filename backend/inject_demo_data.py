import sqlite3
import json
import time

def inject_mock_data():
    conn = sqlite3.connect('d:/数璇项目开发/file/backend/text2sql.db')
    cursor = conn.cursor()

    # 1. Clear old demo data if exists
    cursor.execute("DELETE FROM evaluation_result")
    cursor.execute("DELETE FROM evaluation_task")
    cursor.execute("DELETE FROM test_case")
    cursor.execute("DELETE FROM schema_env")
    cursor.execute("DELETE FROM agent_config")

    # 2. Add Env
    cursor.execute("""
        INSERT INTO schema_env (id, env_name, ddl_content, sandbox_db_url)
        VALUES (1, '医院经营沙箱', 'CREATE TABLE sales (id INT, amount DECIMAL);', 'sqlite:///:memory:')
    """)

    # 3. Add Agent
    cursor.execute("""
        INSERT INTO agent_config (id, agent_name, api_endpoint, rate_limit_qps, timeout_ms)
        VALUES (1, '智算 SQL 助手', 'mock', 10, 5000)
    """)

    # 4. Add Test Cases
    cases = [
        (1, 1, '查询昨日销售总额', 'SELECT SUM(amount) FROM sales;', '["聚合"]'),
        (2, 1, '列出前10条订单', 'SELECT * FROM sales LIMIT 10;', '["过滤"]'),
        (3, 1, '按日期统计订单数', 'SELECT date, COUNT(*) FROM sales GROUP BY date;', '["分组"]')
    ]
    cursor.executemany("INSERT INTO test_case (id, env_id, question, golden_sql, tags) VALUES (?,?,?,?,?)",
                       [(c[0], c[1], c[2], c[3], c[4]) for c in cases])

    # 5. Add Task
    cursor.execute("""
        INSERT INTO evaluation_task (id, task_name, agent_id, env_id, status, stats_json, created_at)
        VALUES (1, '验收演示任务-001', 1, 1, 'completed', ?, datetime('now'))
    """, (json.dumps({"total": 3, "passed": 1, "failed": 2, "errors": 0, "pass_rate": 33.33}),))

    # 6. Add Results
    # Result 1: Success
    cursor.execute("""
        INSERT INTO evaluation_result (task_id, case_id, agent_sql, execution_status, golden_data, agent_data, data_diff_passed, ai_diagnosis, execution_time_ms)
        VALUES (1, 1, 'SELECT SUM(amount) FROM sales;', 'completed', ?, ?, 1, NULL, 120)
    """, (json.dumps([{"SUM(amount)": 5000}]), json.dumps([{"SUM(amount)": 5000}])))

    # Result 2: Failed (Data mismatch)
    cursor.execute("""
        INSERT INTO evaluation_result (task_id, case_id, agent_sql, execution_status, golden_data, agent_data, data_diff_passed, ai_diagnosis, execution_time_ms)
        VALUES (1, 2, 'SELECT * FROM sales;', 'completed', ?, ?, 0, '模型 SQL 遗漏了 LIMIT 10 限制条件，导致返回数据量不符。', 150)
    """, (json.dumps([{"id":1, "amount":100}, {"id":2, "amount":200}]), json.dumps([{"id":1, "amount":100}, {"id":2, "amount":200}, {"id":3, "amount":300}])))

    # Result 3: Failed (Syntax Error)
    cursor.execute("""
        INSERT INTO evaluation_result (task_id, case_id, agent_sql, execution_status, golden_data, agent_data, data_diff_passed, ai_diagnosis, execution_time_ms)
        VALUES (1, 3, 'SELECT date COUNT(*) FROM sales GROUP BY date;', 'syntax_error', ?, ?, 0, '模型 SQL 遗漏了 date 和函数之间的逗号。', 50)
    """, (json.dumps([{"date":"2024-01-01", "count":5}]), json.dumps([])))

    conn.commit()
    conn.close()
    print("Demo data injected successfully!")

if __name__ == "__main__":
    inject_mock_data()
