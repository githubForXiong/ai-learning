import os
import requests

API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
URL = "https://api.deepseek.com/chat/completions"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

data = {
    "model": "deepseek-chat",
    "messages": [
        {"role": "system", "content": "你是一个友好的AI助手。"},
        {"role": "user", "content": "你好，请介绍一下自己。"},
    ],
    "temperature": 0.7,
    "max_tokens": 500,
}

resp = requests.post(URL, headers=headers, json=data)
print("状态码:", resp.status_code)
print("回答:", resp.json()["choices"][0]["message"]["content"])
print("Token 用量:", resp.json()["usage"])
