import os
import logging
import httpx
import json
from dotenv import load_dotenv

# 加载环境变量
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
logger = logging.getLogger(__name__)

async def classify_with_llm(text: str) -> list:
    """
    使用 LLM 进行语义场景分类
    """
    if not DASHSCOPE_API_KEY:
        logger.warning("No API Key found for semantic routing.")
        return ["general"]
        
    prompt = f"""
请分析以下文本内容的类型，并返回最匹配的场景标签列表。
可选标签：
- log (系统日志、错误堆栈、Traceback)
- config (配置文件、参数列表、环境变量)
- academic (学术论文、研报、Abstract、Reference)
- book (书籍、小说、章节内容)
- general (普通文本、其他)

文本片段：
{text[:1000]}

请仅返回 JSON 数组格式，例如 ["log"] 或 ["academic", "book"]。
"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                headers={
                    "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "qwen-max",
                    "input": {"messages": [{"role": "user", "content": prompt}]},
                    "parameters": {"result_format": "message"}
                }
            )
        
        if response.status_code == 200:
            content = response.json()["output"]["choices"][0]["message"]["content"]
            # 简单的清洗
            content = content.replace("```json", "").replace("```", "").strip()
            return json.loads(content)
    except Exception as e:
        logger.error(f"Semantic classification failed: {e}")
    
    return ["general"]

def classify_scene_by_rules(text: str) -> list:
    """纯文本规则分类 (Old Logic)"""
    types = []
    lower_text = text.lower()
    
    if any(kw in lower_text for kw in ["abstract", "introduction", "references", "doi", "arxiv"]):
        types.append("academic")
    
    # Only classify as log if it doesn't look like a paper, or if we are very sure
    is_academic = "academic" in types
    if any(kw in lower_text for kw in ["error", "exception", "traceback", "stack trace"]):
        # If it's a paper, these might just be content. Strict check for log lines?
        # Simple fix: if it's academic, don't auto-tag as log merely by keywords.
        if not is_academic:
            types.append("log")

    if any(kw in lower_text for kw in ["chapter", "isbn", "contents"]):
        if "academic" not in types and "log" not in types:
            types.append("book")
            
    return types

async def route_scene(file_path: str, raw_text: str = None):
    """
    路由入口：混合路由策略 (Rules + Semantic)
    """
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    # 1. 预处理文本
    if raw_text is None:
        # (简化读取逻辑，实际项目中应复用 main.py 的读取或在此完善)
        return {"error": "raw_text required"}

    # 2. 规则初筛 (Fast)
    agent_types = classify_scene_by_rules(raw_text)
    
    # 3. 如果规则匹配失败或只匹配到 general，启用语义路由 (Slow but Accurate)
    if not agent_types or agent_types == ["general"]:
        logger.info("规则路由未命中，启用 Semantic LLM Routing...")
        agent_types = await classify_with_llm(raw_text)
    
    return {
        "file_type": ext,
        "raw_text": raw_text,
        "agent_types": agent_types
    }
