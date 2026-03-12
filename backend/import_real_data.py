import pandas as pd
import sqlite3
import os
import json

# 配置路径
EXCEL_DIR = r"D:\数璇项目开发\file\file"
DB_PATH = r"D:\数璇项目开发\file\backend\text2sql.db"

def import_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. 导入环境 (Mock 一个真实环境)
    cursor.execute("INSERT OR IGNORE INTO schema_env (id, env_name, ddl_content) VALUES (10, '真实数据环境', 'CREATE TABLE sales (id INT, car_model STRING, price FLOAT);')")
    
    # 清理旧数据
    cursor.execute("DELETE FROM test_case WHERE env_id = 10")
    
    # 2. 导入智能体
    config_path = os.path.join(EXCEL_DIR, "智能体配置.xlsx")
    config_df = pd.read_excel(config_path)
    
    for idx, row in config_df.iterrows():
        agent_id = str(row['ROBOT_ID'])
        agent_name = row['agent_name']
        # 统一注入到数据库
        cursor.execute("""
            INSERT OR REPLACE INTO agent_config (id, agent_name, api_endpoint, auth_token, timeout_ms, rate_limit_qps)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (idx + 10, agent_name, "http://1.92.195.88/brain/faq/session/ask", "TOKEN_PLACEHOLDER", 60000, 10))

    # 3. 导入测试用例
    # 例如导入“汽车销售智能体”
    car_cases_path = os.path.join(EXCEL_DIR, "汽车销售智能体.xlsx")
    car_df = pd.read_excel(car_cases_path)
    
    for idx, row in car_df.iterrows():
        question = row['问题']
        golden_sql = row['结果']
        # 修正列名：没有 complexity，可能有 tags
        cursor.execute("""
            INSERT INTO test_case (env_id, question, golden_sql, tags)
            VALUES (10, ?, ?, ?)
        """, (question, golden_sql, json.dumps([])))

    conn.commit()
    print(f"成功导入 {len(config_df)} 个智能体和 {len(car_df)} 个测试用例。")
    conn.close()

if __name__ == "__main__":
    import_data()
