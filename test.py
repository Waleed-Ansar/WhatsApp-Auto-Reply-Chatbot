import requests
from app.core.config import config


url = "https://api.deepseek.com/user/balance"
headers = {
    "Authorization": f"Bearer sk-d7c28e9e9ed94ebab3f982158b602709",
    "Accept": "application/json"
}

response = requests.get(url, headers=headers)

if response.status_code == 200:
    print(response.json())
else:
    print(f"Error: {response.status_code} - {response.text}")
