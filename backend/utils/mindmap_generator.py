from autogen import OpenAIWrapper
import os

def generate_mindmap_json(summary: str) -> dict:
    client = OpenAIWrapper(
        config_list=[{
            "model": "qwen-max",
            "api_key": os.getenv("DASHSCOPE_API_KEY"),
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"
        }]
    )
    
    prompt = f"""
    将以下技术分析结果转换为 mind-elixir 兼容的 JSON 格式。
    要求：
    - 根节点为“系统知识概览”
    - 层级不超过3层
    - 叶子节点加 "isLeaf": true

    内容：{summary}
    
    输出仅 JSON，无其他文字。
    """
    
    response = client.create(messages=[{"role": "user", "content": prompt}])
    return eval(response.choices[0].message.content)  # 实际用 json.loads