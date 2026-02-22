from dotenv import load_dotenv
import os

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))

# 加载根目录的.env文件
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))
import re
import json
import uuid
import logging
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import httpx

# ======================
# 新增：导入 RAG 模块（关键！）
# ======================
from rag.document_store import indexing_pipeline, document_store
from rag.generator import generate_answer_with_evidence
from haystack.dataclasses import Document

# ======================
# 新增：配置日志
# ======================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# 使用统一的OCR服务
from backend.services.ocr_service import ocr_service

app = FastAPI(title="DocMind Pro", version="2.0")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 上传目录
UPLOAD_DIR = PROJECT_ROOT / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# 校验阿里云API Key
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not DASHSCOPE_API_KEY:
    raise ValueError("请在 .env 文件中配置 DASHSCOPE_API_KEY")

# ======================
# 新增：用于存储原始文本（供调试或后续扩展）
# ======================
FILE_TEXT_STORE = {}  # file_id -> full_text

# ======================
# 文档解析函数（保持不变）
# ======================
def extract_text_from_pdf(pdf_path: str) -> str:
    """提取PDF文本"""
    try:
        import pdfplumber
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
        return text.strip()
    except ImportError:
        raise HTTPException(status_code=500, detail="缺少PDF解析依赖：请执行 pip install pdfplumber")
    except Exception as e:
        logger.error(f"PDF解析失败: {str(e)}")
        raise HTTPException(status_code=400, detail=f"PDF解析失败: {str(e)}")

def extract_text_from_image(image_path: str) -> str:
    """提取图片文本（OCR）"""
    try:
        logger.info(f"开始解析图片: {image_path}")
        text = ocr_service.extract_text(image_path)
        logger.info(f"提取的文本: {text if text else '空'}")
        return text
    except Exception as e:
        logger.error(f"图片OCR失败: {str(e)}")
        raise HTTPException(status_code=400, detail=f"图片OCR失败: {str(e)}")

# ======================
# 调用Qwen大模型分析文档（保持不变）
# ======================
async def analyze_with_qwen(text: str) -> dict:
    if not text.strip():
        return {
            "summary": "文档内容为空",
            "errors": [],
            "entities": [],
            "suggestions": []
        }
    
    prompt = f"""
你是专业的文档分析助手，请严格按照JSON格式输出以下内容：
1. summary: 一句话总结文档核心内容（不超过50字）
2. errors: 文档中存在的问题/异常（数组，无则为空）
3. entities: 文档中的关键实体（数组，如技术栈、名称、参数等）
4. suggestions: 针对问题的优化建议（数组，无则为空）

文档内容：
{text[:3000]}

输出要求：仅返回JSON，不要其他文字！
"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                headers={
                    "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "qwen-max",
                    "input": {"messages": [{"role": "user", "content": prompt}]},
                    "parameters": {"result_format": "message", "temperature": 0.1}
                }
            )
        response.raise_for_status()
        content = response.json()["output"]["choices"][0]["message"]["content"]
        content = re.sub(r"```json\s*|\s*```", "", content).strip()
        return json.loads(content)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="大模型调用超时，请重试")
    except json.JSONDecodeError:
        return {
            "summary": "文档内容分析完成",
            "errors": [],
            "entities": [text[:100] + "..." if len(text) > 100 else text],
            "suggestions": ["建议人工复核文档内容"]
        }
    except Exception as e:
        logger.error(f"AI分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI分析失败: {str(e)}")

# ======================
# 构建可视化数据（保持不变）
# ======================
def build_knowledge_graph(agent_result: dict) -> dict:
    nodes = []
    edges = []
    root_id = "root"
    nodes.append({"id": root_id, "label": agent_result["summary"], "group": "summary"})
    for i, err in enumerate(agent_result.get("errors", [])):
        node_id = f"error_{i}"
        nodes.append({"id": node_id, "label": err, "group": "error"})
        edges.append({"from": root_id, "to": node_id})
    for i, ent in enumerate(agent_result.get("entities", [])):
        node_id = f"entity_{i}"
        nodes.append({"id": node_id, "label": ent, "group": "entity"})
        edges.append({"from": root_id, "to": node_id})
    return {"nodes": nodes, "edges": edges}

def build_mindmap_data(agent_result: dict) -> dict:
    def generate_unique_id(node, parent_id, index):
        node["id"] = f"{parent_id}-{index}"
        if "children" in node and isinstance(node["children"], list):
            for idx, child in enumerate(node["children"]):
                generate_unique_id(child, node["id"], idx)
        return node

    summary = str(agent_result.get("summary", "文档分析完成")).strip()
    mindmap = {
        "root": {
            "id": "root",
            "topic": summary,
            "children": []
        }
    }

    errors = [str(e).strip() for e in agent_result.get("errors", []) if e]
    if errors:
        mindmap["root"]["children"].append(generate_unique_id({
            "topic": "发现问题",
            "children": [{"topic": e} for e in errors]
        }, "root", 0))

    entities = [str(e).strip() for e in agent_result.get("entities", []) if e]
    if entities:
        mindmap["root"]["children"].append(generate_unique_id({
            "topic": "关键实体",
            "children": [{"topic": e} for e in entities]
        }, "root", 1))

    suggestions = [str(s).strip() for s in agent_result.get("suggestions", []) if s]
    if suggestions:
        mindmap["root"]["children"].append(generate_unique_id({
            "topic": "优化建议",
            "children": [{"topic": s} for s in suggestions]
        }, "root", 2))

    return mindmap

# ======================
# API接口
# ======================
# 注意：这个文件中的/upload接口已经移到main.py中，这里不再重复定义

# ======================
# 新增：RAG 问答接口
# ======================
@app.post("/ask")
async def ask_question(
    question: str = Query(..., description="用户提问"),
    file_id: str = Query(..., description="文件ID，来自 /upload 返回")
):
    if file_id not in FILE_TEXT_STORE:
        raise HTTPException(status_code=404, detail="文件未找到，请先上传")
    
    if not question.strip():
        raise HTTPException(status_code=400, detail="问题不能为空")
    
    # 使用 Haystack 搜索 pipeline
    result = search_pipeline.run({
        "embedder": {"text": question},
        "retriever": {"top_k": 3}
    })
    
    retrieved_docs = []
    for doc in result["retriever"]["documents"]:
        retrieved_docs.append({
            "content": doc.content,
            "meta": doc.meta
        })
    
    logger.info(f"检索到 {len(retrieved_docs)} 个相关文档")
    
    # 调用你的 generator（带引用编号）
    response = generate_answer_with_evidence(question, retrieved_docs)
    
    return response

# 健康检查接口保持不变，但不应该作为独立服务运行
@app.get("/")
async def health_check():
346|     return {"status": "success", "message": "DocMind Pro RAG 服务运行中"}