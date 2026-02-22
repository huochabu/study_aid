import os
import httpx
import logging
import json
from dotenv import load_dotenv

# 加载环境变量
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
logger = logging.getLogger(__name__)

async def detect_log_anomalies(log_text: str) -> str:
    """
    使用 Qwen 模型识别日志中的异常行
    :param log_text: 原始日志文本
    :return: 异常报告字符串
    """
    if not log_text:
        return "无日志内容"

    # 采用滑动窗口策略处理长日志 (Sliding Window)
    window_size = 50   # 每次分析50行
    stride = 50        # 步长50行 (无重叠，追求速度)
    max_windows = 5    # 最多分析5个窗口 (避免消耗过多Token，可配置)
    
    lines = log_text.split('\n')
    total_lines = len(lines)
    
    # 如果日志太短，直接分析
    if total_lines <= window_size:
        windows = [(0, lines)]
    else:
        # 选取头部、尾部和中间的窗口，而不是全部扫描
        windows = []
        # Head
        windows.append((0, lines[:window_size]))
        # Tail
        start_tail = max(0, total_lines - window_size)
        if start_tail > window_size: 
             windows.append((start_tail, lines[start_tail:]))
        # Random Middle if space permits
        if total_lines > window_size * 2:
            mid = total_lines // 2
            windows.append((mid, lines[mid:mid+window_size]))
            
    combined_report = []
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for start_line, chunk_lines in windows:
            chunk_text = "\n".join(chunk_lines)
            prompt = f"""
你是一名资深系统运维专家。请分析以下日志片段（行号 {start_line+1} - {start_line+len(chunk_lines)}），找出异常。
【日志片段】
{chunk_text}
【输出要求】
仅输出异常行的行号和简要原因。如果没有异常，回答“无”。
"""
            try:
                response = await client.post(
                     "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                    headers={
                        "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "qwen-max",
                        "input": {"messages": [{"role": "user", "content": prompt}]},
                        "parameters": {"temperature": 0.1}
                    }
                )
                if response.status_code == 200:
                    res_content = response.json()["output"]["choices"][0]["message"]["content"]
                    if "无" not in res_content and "未检测到" not in res_content:
                        combined_report.append(f"--- Window (Lines {start_line+1}~) ---\n{res_content}")
            except Exception as e:
                logger.error(f"Window analysis failed: {e}")

    if not combined_report:
        return "未检测到明显异常 (Checked Head/Tail/Mid windows)."
        
    return "\n\n".join(combined_report)
