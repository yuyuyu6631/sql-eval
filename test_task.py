import requests
import json

url = "http://localhost:8000/api/tasks"
payload = {
    "agent_id": 1,
    "env_id": 1,
    "task_name": "测试任务",
    "judge_llm_model": ""
}
headers = {
    "Content-Type": "application/json"
}

response = requests.post(url, data=json.dumps(payload), headers=headers)
print(f"状态码: {response.status_code}")
print(f"返回内容: {response.text}")
