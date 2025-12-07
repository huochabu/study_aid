import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

QWEN_API_KEY = os.getenv("QWEN_API_KEY")
QWEN_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

def call_qwen(prompt: str, timeout: int = 60) -> str:
    """
    调用 Qwen-Max 模型生成文本。
    
    Args:
        prompt (str): 输入提示
        timeout (int): 请求超时时间（秒）
    
    Returns:
        str: 模型生成的文本，失败时返回空字符串
    """
    if not QWEN_API_KEY:
        print("❌ QWEN_API_KEY 未设置，请检查 .env 文件")
        return ""

    headers = {
        "Authorization": f"Bearer {QWEN_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "qwen-max",
        "input": {"messages": [{"role": "user", "content": prompt}]},
        "parameters": {"temperature": 0.3}
        # 注意：DashScope 默认返回 "text" 格式，无需指定 result_format
    }

    try:
        resp = requests.post(QWEN_URL, json=data, headers=headers, timeout=timeout)

        if resp.status_code == 200:
            result = resp.json()
            output = result.get("output", {})
            
            # ✅ 关键修改：优先使用 "text" 字段（DashScope 默认格式）
            if "text" in output:
                return output["text"].strip()
            elif "choices" in output and len(output["choices"]) > 0:
                # 兼容 message 格式（如未来启用 result_format="message"）
                return output["choices"][0]["message"]["content"].strip()
            else:
                print("❌ Qwen API response has neither 'text' nor 'choices'")
                print(f"Full response: {json.dumps(result, ensure_ascii=False, indent=2)}")
                return ""
                
        else:
            error_detail = resp.text
            print(f"❌ Qwen API error: {resp.status_code}")
            print(f"Error body: {error_detail}")
            try:
                err_json = resp.json()
                print(f"Parsed error: {json.dumps(err_json, ensure_ascii=False, indent=2)}")
            except:
                pass
            return ""

    except requests.exceptions.Timeout:
        print("❌ Qwen API request timeout")
        return ""
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error when calling Qwen API: {e}")
        return ""
    except Exception as e:
        print(f"❌ Unexpected error in call_qwen: {e}")
        return ""