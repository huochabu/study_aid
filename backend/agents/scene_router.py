# agents/scene_router.py
import os

def classify_scene_by_content(text: str) -> list:
    """纯文本分类，不依赖文件路径"""
    types = []
    lower_text = text.lower()
    if any(kw in lower_text for kw in ["error", "exception", "fail", "timeout", "stack trace"]):
        types.append("log")
    if any(kw in lower_text for kw in ["config", "parameter", "setting", "max_", "buffer", "port"]):
        types.append("config")
    if not types:
        types.append("general")
    return types

def route_scene(file_path: str, raw_text: str = None):
    """
    路由入口：根据文件类型和内容决定分析策略
    :param file_path: 文件路径
    :param raw_text: 可选，已解析的文本（避免重复读取）
    """
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    # 如果未提供 raw_text，则读取
    if raw_text is None:
        if ext == ".log":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                raw_text = f.read()
        elif ext == ".pdf":
            from ..parsers.pdf_parser import parse_pdf
            chunks = parse_pdf(file_path)
            raw_text = "\n".join(chunks[:10])  # 取前10段
        elif ext == ".txt":
            with open(file_path, "r", encoding="utf-8") as f:
                raw_text = f.read()
        else:
            return {"error": "不支持的文件格式"}

    # 场景分类
    agent_types = classify_scene_by_content(raw_text)

    return {
        "file_type": ext,
        "raw_text": raw_text,
        "agent_types": agent_types
    }