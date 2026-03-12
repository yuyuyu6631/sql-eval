import sqlite3
import json
import requests
import os

DB_PATH = r"D:\数璇项目开发\file\backend\text2sql.db"

def check_db():
    print(f"--- Checking Database: {DB_PATH} ---")
    if not os.path.exists(DB_PATH):
        print("ERROR: Database file NOT FOUND!")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    tables = ['agent_config', 'test_case', 'schema_env']
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"Table {table}: {count} records")
        except Exception as e:
            print(f"Error querying {table}: {e}")
    conn.close()

def check_api():
    print("\n--- Checking Local API ---")
    urls = [
        "http://127.0.0.1:8000/api/dashboard/stats",
        "http://127.0.0.1:8000/api/agents",
        "http://127.0.0.1:8000/api/tasks"
    ]
    for url in urls:
        try:
            resp = requests.get(url, timeout=5)
            print(f"URL: {url}")
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"Data Sample: {str(data)[:200]}...")
            else:
                print(f"Error Body: {resp.text}")
        except Exception as e:
            print(f"Request failed for {url}: {e}")

if __name__ == "__main__":
    check_db()
    check_api()
