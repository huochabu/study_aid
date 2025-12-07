from utils.qwen_client import call_qwen

def analyze_config_file(content: str) -> str:
    """
    配置分析专家：专注于参数合理性、安全策略、性能配置。
    返回自然语言分析总结（不再返回 KG）。
    """
    prompt = f"""
你是一个资深 DevOps 工程师，请分析以下配置文件内容，重点关注：
- 关键参数是否合理（如超时值、缓冲区大小、并发数）
- 是否存在安全风险（如明文密码、宽松权限）
- 是否有性能瓶颈配置
- 是否符合最佳实践

请用一段连贯的中文自然语言总结分析结果，不要使用列表或 JSON。

配置内容（截取前3000字）：
{content[:3000]}
"""
    summary = call_qwen(prompt)
    return summary.strip()