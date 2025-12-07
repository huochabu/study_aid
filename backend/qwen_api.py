# backend/qwen_api.py
import requests

def call_qwen(prompt: str) -> str:
    url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    headers = {
        "Authorization": "Bearer sk-cd604192cb5d4a81825b81ea69286280",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "qwen-max",
        "input": {
            "messages": [
                {"role": "user", "content": prompt}
            ]
        },
        "parameters": {
            "temperature": 0.7
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    return response.json()["output"]["choices"][0]["message"]["content"]