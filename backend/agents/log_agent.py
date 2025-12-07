from utils.qwen_client import call_qwen

def analyze_log_file(content: str) -> str:
    """
    日志分析专家：专注于识别错误、异常、时间序列问题。
    返回自然语言分析总结（不再返回 KG）。
    """
    prompt = f"""
你是一个资深系统运维工程师，请分析以下日志内容，重点关注：
- 错误类型（如超时、连接失败、权限拒绝等）
- 异常发生的时间点或频率
- 可能的根本原因
- 是否存在重复性问题

请用一段连贯的中文自然语言总结分析结果，不要使用列表或 JSON。

日志内容（截取前3000字）：
{content[:3000]}
"""
    summary = call_qwen(prompt)
    return summary.strip()