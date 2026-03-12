import requests

url = "http://localhost:8000/api/tasks/2/start"
response = requests.post(url)
print(f"状态码: {response.status_code}")
print(f"返回内容: {response.text}")
