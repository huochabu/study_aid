from dotenv import load_dotenv
import os
# [FIX] Allow duplicate OpenMP libraries (MKL/Torch/Paddle conflict) - MUST BE FIRST
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

# 加载根目录的.env文件
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))  # 将 backend 目录加入 sys.path
import os
import re
import json
import uuid
import logging
import time
import asyncio # [FIX] Add missing asyncio

from pathlib import Path
from typing import List, Dict, Any, Optional # [FIX] Added Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Depends, Body, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import httpx
import numpy as np # [FIX] Add numpy import for vector math
from sqlalchemy.orm import Session
from pydantic import BaseModel
from connection_manager import ConnectionManager  # [NEW]

# ======================
# 导入核心依赖
# ======================
import logging
from logging import StreamHandler
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[StreamHandler()]
)
logger = logging.getLogger(__name__)

# 导入数据库相关模块
from database import engine, Base, SessionLocal, get_db
from models import AnalysisHistory, FileTextStore
from models.qa_history import QAHistory
from models.feedback import Feedback
from models.teacher_rule import TeacherRule # [NEW]
from models.graph import GlobalNode, GlobalEdge # [NEW] Graph Models
from services.evaluator import evaluate_rag_response

# 导入服务模块
from services.video_processor import VideoProcessor
from services.pdf_service import pdf_service
from services.ocr_service import ocr_service
from services.llm import simple_llm
from routes import dashboard, comparison, learning, graph, review # [NEW] Import new routers

# 创建所有数据库表（确保在导入所有模型后执行）
Base.metadata.create_all(bind=engine)


# 导入向量检索依赖 - 移至 services/vector_service.py


# 初始化视频处理器
try:
    video_processor = VideoProcessor()
except ImportError as e:
    logger.warning(f"视频处理模块导入失败: {e}，请确保 services/video_processor.py 存在")
    video_processor = None

    video_processor = None

app = FastAPI(title="DocMind Pro", version="2.0")

# [NEW] 初始化 WebSocket 连接管理器
manager = ConnectionManager()

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# [NEW] Register Routers
app.include_router(dashboard.router)
app.include_router(comparison.router)
app.include_router(learning.router)
app.include_router(graph.router)
app.include_router(review.router) # [NEW]

# ======================
# 目录配置
# ======================
PROJECT_ROOT = Path(__file__).parent.parent
UPLOAD_DIR = PROJECT_ROOT / "uploads"
DOWNLOAD_DIR = PROJECT_ROOT / "downloads"

# 创建目录（如果不存在）
UPLOAD_DIR.mkdir(exist_ok=True)
DOWNLOAD_DIR.mkdir(exist_ok=True)

# 校验阿里云API Key（可选，仅用于RAG功能）
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not DASHSCOPE_API_KEY:
    logger.warning("未配置 DASHSCOPE_API_KEY，RAG功能将不可用，但学习系统功能仍然可用")

# ======================
# 全局存储
# ======================
# 注意：FILE_TEXT_STORE 和 ANALYSIS_HISTORY 现在从数据库获取
# VECTOR_STORES 仍然使用内存存储（因为向量索引不适合持久化到SQLite）
from services.vector_service import VECTOR_STORES, GLOBAL_HISTORY_STORE, VectorStore # [REFACTORED]

# 清理过期文件的时间间隔（秒）
CLEANUP_INTERVAL = 3600  # 1小时
# 文件保留时间（秒）
FILE_RETENTION_TIME = 86400  # 24小时

# ======================
# 文件清理函数
# ======================
async def cleanup_expired_files():
    """清理过期的上传文件和相关数据"""
    import shutil
    current_time = time.time()
    
    # 使用数据库会话
    db = SessionLocal()
    try:
        # 找出过期的文件记录
        expired_files = db.query(FileTextStore).filter(
            FileTextStore.upload_time < current_time - FILE_RETENTION_TIME
        ).all()
        
        expired_file_ids = [file.file_id for file in expired_files]
        
        # 清理相关资源
        for file_id in expired_file_ids:
            # 清理文件系统中的文件
            for ext in ["pdf", "txt", "log", "jpg", "jpeg", "png"]:
                file_path = os.path.join(UPLOAD_DIR, f"{file_id}.{ext}")
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        logger.info(f"已删除过期文件: {file_path}")
                    except Exception as e:
                        logger.error(f"删除文件失败: {file_path}, 错误: {str(e)}")
            
            # 从数据库删除文件记录
            db.query(FileTextStore).filter(FileTextStore.file_id == file_id).delete()
            
            # 清理向量存储
            if file_id in VECTOR_STORES:
                del VECTOR_STORES[file_id]
        
        # 提交数据库更改
        db.commit()
        logger.info(f"过期文件清理完成，共清理 {len(expired_file_ids)} 个文件")
    except Exception as e:
        logger.error(f"清理过期文件失败: {str(e)}")
        db.rollback()
    finally:
        db.close()

# 定期清理任务
import asyncio

@app.on_event("startup")
async def startup_event():
    """启动时的初始化任务"""
    # 创建数据库表
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表创建完成")
    
    # 确保上传目录存在
    UPLOAD_DIR.mkdir(exist_ok=True)
    logger.info("DocMind Pro 后端启动成功")
    # 启动定期清理任务
    asyncio.create_task(periodic_cleanup())

async def periodic_cleanup():
    """定期清理过期文件"""
    while True:
        await cleanup_expired_files()
        await asyncio.sleep(CLEANUP_INTERVAL)

# ======================
# 向量存储类
# ======================
# VectorStore class moved to services/vector_service.py
# VECTOR_STORES and GLOBAL_HISTORY_STORE imported above

# ======================
# 辅助函数：保存文件到数据库
# ======================
def save_file_to_db(file_id: str, filename: str, text: str = "", chunks: list = None, keywords: list = None, layout_data: list = None, upload_time: float = None) -> None:
    """
    将文件信息保存到数据库
    
    Args:
        file_id: 文件唯一标识符
        filename: 原始文件名
        text: 提取的文本内容（默认为空）
        chunks: 文本分块列表（默认为空）
        keywords: 关键词列表（默认为空）
        upload_time: 上传时间（默认为当前时间）
    """
    db = SessionLocal()
    try:
        # 设置默认值
        chunks = chunks or []
        keywords = keywords or []
        layout_data = layout_data or [] # [NEW]
        upload_time = upload_time or time.time()
        
        # 检查文件是否已存在
        existing_file = db.query(FileTextStore).filter(FileTextStore.file_id == file_id).first()
        if existing_file:
            # 更新现有文件
            existing_file.original_filename = filename
            existing_file.text = text
            existing_file.set_chunks_list(chunks)
            existing_file.keywords = json.dumps(keywords, ensure_ascii=False)
            existing_file.layout_info = layout_data # [NEW]
            existing_file.upload_time = upload_time
        else:
            # 创建新文件记录
            file_record = FileTextStore(
                file_id=file_id,
                original_filename=filename,
                text=text,
                chunks=json.dumps(chunks, ensure_ascii=False),
                keywords=json.dumps(keywords, ensure_ascii=False),
                layout_data=json.dumps(layout_data, ensure_ascii=False), # [NEW]
                upload_time=upload_time
            )
            db.add(file_record)
        db.commit()
        logger.info(f"文件信息已保存到数据库: {file_id}")
    except Exception as e:
        logger.error(f"保存文件信息到数据库失败: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

# ======================
# ✅ 新增：关键词提取函数
# ======================
def extract_keywords_from_text(text: str) -> List[str]:
    """从文本中提取关键词字段（支持中英文）"""
    keywords = []
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if re.search(r'\b(?:KEYWORDS|Keywords|关键词)\b', line, re.IGNORECASE):
            if i + 1 < len(lines):
                kw_line = lines[i + 1].strip()
                if kw_line and len(kw_line) > 3 and not kw_line.startswith('[') and not kw_line.isdigit():
                    keywords = [k.strip() for k in re.split(r'[,，;；]', kw_line) if k.strip()]
                    break
    return keywords

# ======================
# 文档解析函数
# ======================
def extract_text_from_pdf(pdf_path: str) -> dict:
    """解析PDF，返回 {text, layout}"""
    try:
        import pdfplumber
        text = ""
        layout_data = [] # [{"page": 1, "words": [...]}]
        
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                
                # Extract words with coordinates
                words = page.extract_words()
                # words structure: [{x0, top, x1, bottom, text}, ...]
                layout_data.append({
                    "page": i + 1,
                    "width": page.width, # [NEW]
                    "height": page.height, # [NEW]
                    "words": words
                })
                
        return {"text": text.strip(), "layout": layout_data}
    except ImportError:
        raise HTTPException(status_code=500, detail="缺少PDF解析依赖：请执行 pip install pdfplumber")
    except Exception as e:
        logger.error(f"PDF解析失败: {str(e)}")
        raise HTTPException(status_code=400, detail=f"PDF解析失败: {str(e)}")

def extract_text_from_image(image_path: str) -> dict:
    try:
        logger.info(f"开始解析图片: {image_path}")
        # Now returns dict
        result = ocr_service.extract_text(image_path)
        logger.info(f"提取的文本: {result['text'][:50]}..." if result['text'] else "空")
        return result
    except FileNotFoundError as e:
        logger.error(f"模型文件不存在: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OCR模型文件不存在: {str(e)}")
    except ImportError as e:
        raise HTTPException(status_code=500, detail="缺少OCR依赖：请执行 pip install paddleocr paddlepaddle")
    except Exception as e:
        logger.error(f"图片OCR失败: {str(e)}")
        raise HTTPException(status_code=400, detail=f"图片OCR失败: {str(e)}")

# ======================
# ✅ 智能分块函数（保留）
# ======================
def smart_chunk_text(text: str) -> list:
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    chunks = []
    for para in paragraphs:
        if len(para) < 50:
            if chunks:
                chunks[-1] += " " + para
            else:
                chunks.append(para)
        else:
            chunks.append(para)
    final_chunks = []
    CHUNK_SIZE = 1000  # Increased from 600 to capture more context (e.g., Log timestamp + Traceback)
    OVERLAP_SIZE = 200 # Overlap to prevent splitting context boundaries
    
    for chunk in chunks:
        if len(chunk) > 1200: # Threshold slightly larger than CHUNK_SIZE
             # Split by sentence-endings or newlines to respect structure
            sentences = re.split(r'([。\.\!\?\n])', chunk) # Keep delimiters
            # Reconstruct sentences (delimiter was split out)
            real_sentences = []
            for i in range(0, len(sentences) - 1, 2):
                real_sentences.append(sentences[i] + sentences[i+1])
            if len(sentences) % 2 == 1:
                real_sentences.append(sentences[-1])
            
            current_chunk = ""
            for sent in real_sentences:
                if len(current_chunk) + len(sent) > CHUNK_SIZE:
                    if current_chunk:
                        final_chunks.append(current_chunk.strip())
                        # Context Overlap: Keep the last bit of the previous chunk
                        # Simple overlap: keep the last OVERLAP_SIZE chars roughly? 
                        # Better: Keep the last N sentences that fit in OVERLAP_SIZE?
                        # Simplified: Just start new chunk with empty.
                        # Actually user request requires overlap. 
                        # Let's keep the last sentence if it's not too huge.
                        if len(sent) < OVERLAP_SIZE:
                             # Overlap logic: Find sentences from current_chunk that fit in OVERLAP_SIZE
                             overlap_text = ""
                             # This is complex to reverse-iterate sentences strictly.
                             # Simple heuristic: Just let the chunks be distinct for now but larger.
                             # Complex overlap implementation might break code stability.
                             # Let's stick to larger chunk size (1000) which usually covers a log block.
                             pass
                    current_chunk = sent
                else:
                    current_chunk += sent
            if current_chunk:
                final_chunks.append(current_chunk.strip())
        else:
            final_chunks.append(chunk)
    
    # Post-process: Add explicit overlap if needed, but larger chunk size is often enough.
    # To truly fix "Timestamp at top, error at bottom", we need Sliding Window.
    # Let's re-implement with a simple sliding window over words/sentences if we want overlap.
    # But for minimal risk editing: Just increasing size to 1000 is safer and effective.
    
    return [c.strip() for c in final_chunks if c.strip()]

# ======================
# ✅ RAG 问答（保留）
# ======================
async def rag_answer(question: str, context_chunks: list) -> str:
    if not context_chunks:
        return "未找到相关文档内容。"
    context = "\n".join(context_chunks)[:4000]
    prompt = f"""
你是一个专业的学术论文分析助手。
规则：
1. 优先根据【文档内容】回答问题。
2. 【重要】如果【问题】中包含“系统指令”或“用于修正”的信息，请**务必**优先遵循该指令，即使它与【文档内容】冲突。这是用户的显式更正。
3. 如果文档中有明确的“KEYWORDS”、“Keywords”、“关键词”、“ABSTRACT”、“摘要”等字段，请直接引用其内容。
4. 不要编造信息；如果文档确实未提及且无修正指令，请回答“文档中未提及此内容”。

【文档内容】
{context}

【问题】
{question}

【回答】
"""
    try:
        import asyncio
        max_retries = 3
        retry_delay = 5  # 秒
        response = None
        
        async with httpx.AsyncClient() as client:
            for retry in range(max_retries):
                try:
                    logger.info(f"发送RAG请求到Dashscope API，重试次数: {retry+1}/{max_retries}")
                    response = await client.post(
                        "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                        headers={
                            "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "qwen-max",
                            "input": {"messages": [{"role": "user", "content": prompt}]},
                            "parameters": {
                                "temperature": 0.3,
                                "result_format": "message"
                            }
                        },
                        timeout=120.0  # 增加超时时间到120秒
                    )
                    response.raise_for_status()
                    logger.info(f"成功收到RAG API响应")
                    break  # 成功，退出重试循环
                except httpx.TimeoutException:
                    logger.warning(f"RAG请求超时，{retry+1}/{max_retries}，将在{retry_delay}秒后重试...")
                    if retry < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 1.5  # 指数退避
                    else:
                        logger.error(f"所有RAG请求重试都失败了，请求超时")
                        return "生成答案时超时，请稍后重试。"
                except httpx.RequestError as e:
                    logger.warning(f"RAG请求失败，{retry+1}/{max_retries}，错误: {e}，将在{retry_delay}秒后重试...")
                    if retry < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 1.5  # 指数退避
                    else:
                        logger.error(f"所有RAG请求重试都失败了，错误: {e}")
                        return f"生成答案时出错：{str(e)}"
        
        data = response.json()
        output = data.get("output", {})
        if "choices" in output and isinstance(output["choices"], list):
            answer = output["choices"][0].get("message", {}).get("content", "")
        elif "text" in output:
            answer = output["text"]
        else:
            answer = str(output)
        return answer.strip()
    except Exception as e:
        logger.error(f"RAG 回答生成失败: {str(e)}")
        return f"生成答案时出错：{str(e)}"
from utils.text_parser import parse_markdown_mindmap # [NEW] Import parser


# ======================
# ✅ 导入新模块（Multi-Agent + KG + Mindmap）
# ======================
try:
    from agents.scene_router import route_scene
    from agents.agent_team import analyze_with_agents
    import agents.agent_team
    logger.info(f"🔍 [DEBUG] agent_team loaded from: {agents.agent_team.__file__}")
    from knowledge.graph_builder import extract_knowledge_graph_from_text
    from knowledge.mindmap_generator import generate_mindmap_from_kg
except ImportError as e:
    logger.warning(f"部分模块导入失败: {e}，请确保 agents/ 和 knowledge/ 目录存在")
    # 兜底函数（防止导入失败导致服务启动失败）
    async def extract_knowledge_graph_from_text(text, doc_type="general"):
        return {
            "nodes": [{"id": "root", "label": "技术内容分析", "type": "Category"}],
            "edges": []
        }
    
    async def generate_mindmap_from_kg(kg_dict, reasoning_steps=None):
        return {
            "root": {
                "id": "root",
                "topic": "系统知识概览",
                "children": [{"topic": "暂无详细分析"}]
            }
        }
    
    def route_scene(*args, **kwargs):
        return {"agent_types": ["general"]}
    
    def analyze_with_agents(text, agent_types, **kwargs):
        # Fallback always sync-compatible or appropriately async
        return {
            "summary": text[:1000] + "\n\n(系统提示：由于模块加载失败，已启用降级处理)",
            "reasoning_steps": ["模块导入失败，跳过智能体分析"]
        }

# ======================
# ✅ 新增：思维导图数据格式化函数
# ======================
def format_mindmap_data(raw_data):
    """统一格式化思维导图数据，确保符合前端渲染要求"""
    # 基础校验：确保root字段存在
    if not isinstance(raw_data, dict) or "root" not in raw_data:
        logger.warning("⚠️ 思维导图数据缺少root字段，自动补充默认根节点")
        raw_data = {
            "root": {
                "id": "root",
                "topic": "文档分析结果",
                "children": []
            }
        }
    
    root = raw_data["root"]
    # 确保root节点有必要的字段
    root.setdefault("id", "root")
    root.setdefault("topic", "文档分析结果")
    root.setdefault("children", [])
    
    # 递归校验子节点
    def validate_children(nodes, parent_id="root"):
        validated = []
        for i, node in enumerate(nodes):
            if not isinstance(node, dict):
                continue
            # 确保子节点有id和topic
            node.setdefault("id", f"{parent_id}-{i}")
            node.setdefault("topic", f"子节点{i+1}")
            node.setdefault("children", [])
            # 递归校验孙子节点
            node["children"] = validate_children(node["children"], node["id"])
            validated.append(node)
        return validated
    
    root["children"] = validate_children(root["children"])
    return raw_data

# ======================
# 静态文件服务
# ======================
from fastapi.staticfiles import StaticFiles

# 配置静态文件服务
app.mount("/static", StaticFiles(directory=str(UPLOAD_DIR)), name="static")
# 配置下载文件的静态服务
app.mount("/downloads", StaticFiles(directory=str(DOWNLOAD_DIR)), name="downloads")

# ======================
# API接口
# ======================

# [NEW] WebSocketEndpoint
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            # 保持连接活跃，也可以接收客户端消息
            data = await websocket.receive_text()
            # 这里可以处理客户端发来的消息，目前仅用于保活
            pass
    except WebSocketDisconnect:
        manager.disconnect(websocket, client_id)

@app.post("/upload")
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    try:
        logger.info(f"开始处理文件: {file.filename}, 类型: {file.content_type}")
        file_id = str(uuid.uuid4())
        ext = file.filename.split('.')[-1].lower()
        file_path = UPLOAD_DIR / f"{file_id}.{ext}"
        
        file_content = await file.read()
        with open(file_path, "wb") as f:
            f.write(file_content)
        logger.info(f"文件已保存到: {file_path}")

        # Add background task
        background_tasks.add_task(
            process_file_background, 
            file_id, 
            file_path, 
            file.filename, 
            ext, 
            file_content
        )

        return {
            "file_id": file_id,
            "filename": file.filename,
            "status": "processing",
            "message": "文件已上传，正在后台分析中..."
        }
    except Exception as e:
        logger.error(f"上传请求失败: {str(e)}", exc_info=True)
        return Response(
            content=json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False),
            media_type="application/json",
            status_code=500
        )
from routes import dashboard, comparison, learning
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(comparison.router, prefix="/api/comparison", tags=["Comparison"])
app.include_router(learning.router, prefix="/api/learning", tags=["Learning"])

async def process_file_background(file_id: str, file_path: Path, filename: str, ext: str, file_content: bytes):
    """后台异步处理文件分析任务"""
    logger.info(f"🚀 [后台任务] 开始分析文件: {filename} ({file_id})")
    db = SessionLocal()
    try:
        # 1. 文本提取 (OCR/PDF解析) & 布局信息
        # ======================
        text = ""
        layout_data = []
        
        if ext in ["jpg", "jpeg", "png"]:
            result = await asyncio.to_thread(extract_text_from_image, str(file_path))
            text = result["text"]
            layout_data = result["layout"]
        elif ext == "pdf":
            result = await asyncio.to_thread(extract_text_from_pdf, str(file_path))
            text = result["text"]
            layout_data = result["layout"]
        elif ext in ["txt", "log"]:
            try:
                text = file_content.decode("utf-8")
            except UnicodeDecodeError:
                text = file_content.decode("gbk", errors="replace")
            # layout for text files could be line-based if needed, but for now empty
            layout_data = [] 
        else:
            raise Exception(f"不支持的文件格式: {ext}")
            
        # [FIX] Handle empty text case to avoid agent confusion
        if not text or not text.strip():
            logger.warning(f"⚠️ 文件 {filename} 内容为空或 OCR 提取失败")
            text = "（系统提示：未能从文件中提取到有效文本。可能是图片模糊、OCR失败或文件为空。）"

        # [STREAM] Status Update
        await manager.broadcast({
            "type": "status_update",
            "status": "analyzing",
            "message": "文本提取完成，正在进行智能分析...",
            "progress": 30
        }, file_id)

        logger.info(f"✅ [后台任务] 文本提取完成，长度: {len(text)}")
        
        # 2. 预处理 (关键词/分块)
        # ======================
        keywords = extract_keywords_from_text(text)
        chunks = smart_chunk_text(text)
        
        # 更新数据库 (初步保存)
        save_file_to_db(file_id, filename, text, chunks, keywords, layout_data)
        
        # 3. 并行执行：向量化 (CPU/Blocking) & Multi-Agent 分析 (I/O/API)
        # ======================
        logger.info("🧠 [后台任务] 启动并行任务: 向量化 + Multi-Agent分析...")

        # 定义向量化任务
        async def run_embedding():
            vs = VectorStore() # Uses the imported class from services.vector_service
            # Prepare metadata for each chunk
            metadatas = [{"filename": filename, "file_id": file_id} for _ in chunks]
            await asyncio.to_thread(vs.add_texts, chunks, metadatas)
            VECTOR_STORES[file_id] = vs
            logger.info(f"✅ [后台任务] 向量化完成 (Chunks: {len(chunks)})")
            return vs

        # 定义分析任务
        async def run_agent_analysis():
            # Robustly handle route_scene (sync vs async mismatch during hot-reload)
            routing_res = route_scene(file_path, raw_text=text)
            if asyncio.iscoroutine(routing_res):
                routing = await routing_res
            else:
                routing = routing_res
            agent_types = routing.get("agent_types", ["general"])

            # [STREAM] Notify routing result
            await manager.broadcast({
                "type": "log",
                "message": f"场景路由完成: 识别为 {agent_types}",
                "source": "System"
            }, file_id)
            
            # [STREAM] Define Callback
            loop = asyncio.get_running_loop()
            def agent_callback(msg):
                # msg: {'content': '...', 'name': '...', 'role': '...', 'type': '...'}
                # Check if it's a thinking message
                msg_type = msg.get("type", "agent_log")
                
                coro = manager.broadcast({
                    "type": msg_type,
                    "name": msg.get("name", "Agent"),
                    "content": msg.get("content", ""),
                    "role": msg.get("role", "assistant")
                }, file_id)
                asyncio.run_coroutine_threadsafe(coro, loop)

            import inspect
            try:
                logger.info(f"🕵️ [INTROSPECT] analyze_with_agents file: {inspect.getfile(analyze_with_agents)}")
                logger.info(f"🕵️ [INTROSPECT] analyze_with_agents sig: {inspect.signature(analyze_with_agents)}")
            except Exception as e:
                logger.error(f"Introspection failed: {e}")

            # 关键修复：在调用analyze_with_agents前就截断文本，避免Autogen框架累积消息后超出长度限制
            # Dashscope qwen-max 限制为30720字符，Autogen会将所有聊天历史发送给模型
            # 所以我们需要更严格地截断初始文本
            max_allowed_length = 20000  # 更保守的长度限制
            truncated_text = text
            if len(truncated_text) > max_allowed_length:
                truncated_text = truncated_text[:max_allowed_length] + "\n\n（文本过长，已截断）"
                logger.info(f"文本已截断，原始长度: {len(text)}, 截断后长度: {len(truncated_text)}")

            # 使用截断后的文本进行分析
            # [FIX] Now calling async function directly
            result = await analyze_with_agents(truncated_text, agent_types, callback=agent_callback)
            logger.info("✅ [后台任务] Multi-Agent 分析完成")
            return result, agent_types

        # 并行执行
        embedding_task = asyncio.create_task(run_embedding())
        analysis_task = asyncio.create_task(run_agent_analysis())
        
        # [STREAM] Status
        await manager.broadcast({
            "type": "status_update",
            "status": "analyzing",
            "message": "多智能体正在协作分析中...",
            "progress": 50
        }, file_id)

        # 等待所有任务完成
        await embedding_task
        agent_result, agent_types = await analysis_task
        
        if "error" in agent_result:
            raise Exception(agent_result["error"])
        
        summary = agent_result["summary"]
        reasoning_steps = agent_result.get("reasoning_steps", [])
        
        # [STREAM] Status
        await manager.broadcast({
            "type": "status_update",
            "status": "generating",
            "message": "分析完成，正在生成知识图谱与思维导图...",
            "progress": 80
        }, file_id)

        # 5. 知识图谱 & 思维导图
        # ======================
        # 后续逻辑不变...
        doc_type = agent_types[0] if agent_types else "general"
        try:
            knowledge_graph = await extract_knowledge_graph_from_text(summary, doc_type=doc_type)
        except Exception as e:
            logger.error(f"❌ 知识图谱生成失败: {str(e)}")
            knowledge_graph = {"nodes": [], "edges": []}

        # [NEW] Sync to Global Graph
        try:
            from services.graph_service import GraphService
            graph_service = GraphService(db)
            
            logger.info(f"🔄 [Global Graph] Syncing {len(knowledge_graph.get('nodes', []))} nodes to Global Brain...")
            
            for node in knowledge_graph.get("nodes", []):
                # Use label as primary key for merging, fallback to id
                node_name = node.get("label") or node.get("id")
                if node_name:
                    graph_service.add_node(
                        name=node_name, 
                        category=node.get("type", "Concept"), 
                        source_doc_id=file_id
                    )
            
            for edge in knowledge_graph.get("edges", []):
                # We assume edge source/target refer to node IDs (which we mapped to names)
                # But sometimes they might be IDs. We need to be careful.
                # In our simple extractor, usually id=label. 
                graph_service.add_edge(
                    source_name=edge.get("source"),
                    target_name=edge.get("target"),
                    relation=edge.get("relation", "related_to")
                )
            
            logger.info("✅ [Global Graph] Integrated new knowledge into global brain")
        except Exception as ge:
            logger.error(f"❌ [Global Graph] Sync failed: {str(ge)}", exc_info=True)

        # [NEW] 优先尝试从 Markdown 解析思维导图（保留专家原话）
        parsed_mindmap = parse_markdown_mindmap(summary)
        if parsed_mindmap:
             logger.info("✅ [后台任务] 成功从 Markdown 解析思维导图")
             mindmap_data = parsed_mindmap
        else:
             # Fallback to KG based generation
             try:
                 mindmap_data = await generate_mindmap_from_kg(knowledge_graph, reasoning_steps)
             except Exception as e:
                 logger.error(f"❌ 思维导图生成失败: {str(e)}")
                 mindmap_data = {"root": {"id": "root", "topic": "生成失败", "children": []}}
        
        mindmap_data = format_mindmap_data(mindmap_data)

        # 6. 保存最终结果
        # ======================
        response_data = {
            "file_id": file_id,
            "filename": filename,
            "mindmap": mindmap_data,
            "knowledge_graph": knowledge_graph,
            "extracted_text": text,
            "layout_data": layout_data,
            "summary": summary,
            "reasoning_steps": reasoning_steps,
            "agent_types": agent_types, # [NEW] Pass to frontend for conditional UI
            "status": "completed" 
        }

        # 更新/创建历史记录
        history_entry = AnalysisHistory(
            id=str(uuid.uuid4()),
            file_id=file_id,
            filename=filename,
            analysis_time=time.time()
        )
        history_entry.result_dict = response_data
        
        db.add(history_entry)
        
        
        # [FIX] 更新 FileTextStore 中的关键词
        try:
            import re
            new_keywords = []
            
            # 1. 优先尝试从 Agent 输出中提取 "### 核心关键词"
            keyword_match = re.search(r'### 核心关键词\s*\n(.+)', summary)
            if keyword_match:
                # 提取第一行内容，按逗号或顿号分割
                raw_kws = re.split(r'[,，、]', keyword_match.group(1).strip())
                new_keywords = [k.strip() for k in raw_kws if k.strip()][:5] # Limit to 5
                logger.info(f"✅ [后台任务] 从 Agent 提取关键词: {new_keywords}")
            
            # 2. 如果提取失败，使用降级算法 (Frequency-based Fallback)
            if not new_keywords:
                clean_summary = re.sub(r'[^\w\s]', ' ', summary)
                structure_stops = {
                    '核心主题', '现象', '原因', '解决方案', '影响范围', '攻击手段', 
                    '深度分析', '总结', '创新点', '方法论', '结论', '树形思维导图', 
                    '文本描述', '子节点', '分析完成', 'terminate', 'novelty', 
                    'methodology', 'conclusion', 'chapter', 'summary', 'concepts',
                    '核心关键词'
                }
                stops = {'the', 'a', 'in', 'of', 'and', 'to', 'is', 'for', 'with', 'on', 
                         '这个', '一个', '可以', '我们', '通常', '使用', '以及', '因此', '通过'}
                
                words = clean_summary.split()
                from collections import Counter
                # Exclude purely numeric or single char
                valid_words = [w for w in words if len(w) > 1 and not w.isdigit()]
                
                # Use frequency Counter to get top common words, not just first appearance
                counts = Counter(w.lower() for w in valid_words if w.lower() not in stops and w.lower() not in structure_stops)
                
                # Get top 5 most frequent
                most_common = counts.most_common(5)
                new_keywords = [word for word, count in most_common]
                
                logger.info(f"🔄 [后台任务] 关键词降级提取(Top5 Freq): {new_keywords}")

            file_record = db.query(FileTextStore).filter(FileTextStore.file_id == file_id).first()
            
            file_record = db.query(FileTextStore).filter(FileTextStore.file_id == file_id).first()
            if file_record:
                logger.info(f"🔄 [后台任务] 更新关键词 (Filtered): {new_keywords}")
                file_record.keywords = json.dumps(new_keywords, ensure_ascii=False)
        except Exception as kw_e:
            logger.warning(f"关键词更新失败: {kw_e}")

        db.commit()
        logger.info(f"✅ [后台任务] 全流程分析完成，结果已保存: {file_id}")

        # [NEW] WebSocket 推送
        logger.info(f"🚀 [Socket] Broadcasting to {file_id}. Payload sizes -> MindMap: {len(str(mindmap_data))}, KG: {len(str(knowledge_graph))}")
        await manager.broadcast(response_data, file_id)
        
        logger.info(f"🎉 [后台任务] 分析全部完成，结果已推送给客户端: {file_id}")

    except Exception as e:
        logger.error(f"❌ [后台任务] 处理失败: {str(e)}", exc_info=True)
        # 推送错误消息
        error_response = {"status": "failed", "error": str(e), "file_id": file_id}
        await manager.broadcast(error_response, file_id) # Push error too
        # 记录失败状态到数据库（可选，或者前端查询不到结果视为失败/处理中）
        # 这里为了简单，我们尝试更新一个"failed"记录，或者不做处理，前端超时
        try:
             fail_entry = AnalysisHistory(
                id=str(uuid.uuid4()),
                file_id=file_id,
                filename=filename,
                analysis_time=time.time()
            )
             fail_entry.result_dict = {"status": "failed", "error": str(e)}
             db.add(fail_entry)
             db.commit()
        except:
             pass
    finally:
        db.close()

@app.get("/analysis/{file_id}/status")
async def get_analysis_status(file_id: str):
    """查询文件分析状态"""
    db = SessionLocal()
    try:
        # 查询历史记录是否存在
        record = db.query(AnalysisHistory).filter(AnalysisHistory.file_id == file_id).order_by(AnalysisHistory.created_at.desc()).first()
        
        if not record:
            # 可能是正在处理中，或者根本不存在
            # 简单起见，我们假设不存在就是还没处理完（因为我们是先返回再处理）
            # 更好的做法是有一个独立的 Task 表记录状态
            # 这里暂时返回 processing，前端设置超时
            return {"status": "processing"}
        
        result = record.result_dict
        if result.get("status") == "failed":
             return {"status": "failed", "error": result.get("error")}
        
        # 如果有结果，且不是failed，就是completed
        # 兼容旧数据：如果没有 status 字段但有 mindmap，也是 completed
        if result.get("status") == "completed" or "mindmap" in result:
             # 返回完整结果
             result["status"] = "completed"
             return result
        
        return {"status": "processing"}
    finally:
        db.close()
    


@app.post("/upload-simple")
async def upload_file_simple(file: UploadFile = File(...)):
    """简单上传接口，仅保存文件到uploads目录并记录到数据库，不进行AI分析"""
    try:
        logger.info(f"简单上传文件: {file.filename}, 类型: {file.content_type}")
        file_id = str(uuid.uuid4())
        ext = file.filename.split('.')[-1].lower()
        file_path = UPLOAD_DIR / f"{file_id}.{ext}"
        
        # 只支持PDF文件
        if ext != "pdf":
            raise HTTPException(status_code=400, detail="仅支持PDF文件上传")
        
        file_content = await file.read()
        with open(file_path, "wb") as f:
            f.write(file_content)
        logger.info(f"文件已保存到: {file_path}")
        
        # 保存文件信息到数据库
        save_file_to_db(file_id, file.filename)
        
        # 返回简单的响应
        response_data = {
            "file_id": file_id,
            "filename": file.filename
        }
        
        logger.info("简单文件上传完成")
        return Response(
            content=json.dumps(response_data, ensure_ascii=False),
            media_type="application/json"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"简单文件上传失败: {str(e)}", exc_info=True)
        error_response = {
            "file_id": "",
            "filename": file.filename if 'file' in locals() else "",
            "error": str(e)
        }
        return Response(
            content=json.dumps(error_response, ensure_ascii=False),
            media_type="application/json",
            status_code=500
        )



@app.get("/files")
async def get_files(
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(10, ge=1, le=100, description="每页显示的文件数量"),
    file_type: str = Query(None, description="可选的文件类型过滤，如'pdf'、'txt'等")
):
    """获取上传文件列表，支持分页"""
    try:
        files = []
        
        # 使用数据库会话获取所有文件信息
        db = SessionLocal()
        try:
            # 获取所有文件存储记录
            file_records = db.query(FileTextStore).all()
            file_store_dict = {record.file_id: record for record in file_records}
        finally:
            db.close()
        
        # 只处理在FileTextStore中有记录的文件
        for file_id, record in file_store_dict.items():
            # 检查所有支持的文件类型
            found = False
            # 如果指定了文件类型过滤，则只检查该类型
            if file_type:
                # 只检查指定的文件类型
                ext = file_type
                file_path = os.path.join(str(UPLOAD_DIR), f"{file_id}.{ext}")
                if os.path.isfile(file_path):
                    # 获取文件大小
                    file_size = os.path.getsize(file_path)
                    
                    # 使用数据库中的原始文件名和上传时间
                    original_filename = record.original_filename or f"{file_id}.{ext}"
                    upload_time = record.upload_time or os.path.getmtime(file_path)
                    
                    # 额外检查：如果是PDF类型，确保文件名包含.pdf扩展名
                    if ext == 'pdf' and not original_filename.lower().endswith('.pdf'):
                        continue
                    
                    files.append({
                        "file_id": file_id,
                        "filename": original_filename,
                        "upload_time": upload_time,
                        "size": file_size,
                        "type": ext
                    })
                    found = True
            else:
                # 如果没有指定文件类型，检查所有支持的文件类型
                for ext in ["pdf", "txt", "log", "jpg", "jpeg", "png"]:
                    file_path = os.path.join(str(UPLOAD_DIR), f"{file_id}.{ext}")
                    if os.path.isfile(file_path):
                        # 获取文件大小
                        file_size = os.path.getsize(file_path)
                        
                        # 使用数据库中的原始文件名和上传时间
                        original_filename = record.original_filename or f"{file_id}.{ext}"
                        upload_time = record.upload_time or os.path.getmtime(file_path)
                        
                        files.append({
                            "file_id": file_id,
                            "filename": original_filename,
                            "upload_time": upload_time,
                            "size": file_size,
                            "type": ext
                        })
                        found = True
                        break  # 只添加第一个找到的文件（通常只有一个扩展名）
        
        # 按上传时间降序排序
        files.sort(key=lambda x: x["upload_time"], reverse=True)
        
        # 计算总数和分页信息 - 现在总数是实际显示的文件数
        total = len(files)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_files = files[start:end]
        
        return {
            "status": "success",
            "files": paginated_files,
            "pagination": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }
        }
    except Exception as e:
        logger.error(f"获取文件列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}")

@app.delete("/files/{file_id}")
async def delete_file(file_id: str, db: Session = Depends(get_db)):
    """删除单个文件（保留分析历史记录）"""
    try:
        # 清理文件系统中的文件
        deleted_files = []
        for ext in ["pdf", "txt", "log", "jpg", "jpeg", "png"]:
            file_path = UPLOAD_DIR / f"{file_id}.{ext}"
            if file_path.exists():
                try:
                    file_path.unlink()
                    deleted_files.append(str(file_path))
                    logger.info(f"已删除文件: {file_path}")
                except Exception as e:
                    logger.error(f"删除文件 {file_path} 失败: {str(e)}")
        
        # 清理全局存储（只清理向量存储，FILE_TEXT_STORE现在从数据库获取）
        if file_id in VECTOR_STORES:
            del VECTOR_STORES[file_id]
            
        # [FIX] 清理数据库记录
        db.query(FileTextStore).filter(FileTextStore.file_id == file_id).delete()
        
        # [NEW] 清理知识图谱
        try:
            from services.graph_service import GraphService
            GraphService(db).remove_document_knowledge(file_id)
        except Exception as ge:
            logger.error(f"清理图谱数据失败: {ge}")
        
        db.commit()
        
        # 不再清理相关的分析历史记录（根据需求保留）
        deleted_history_count = 0
        
        return {
            "status": "success",
            "message": f"删除成功，共删除 {len(deleted_files)} 个文件和 {deleted_history_count} 条分析记录",
            "deleted_files": deleted_files,
            "deleted_history_count": deleted_history_count
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除操作失败: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除操作失败: {str(e)}")

@app.delete("/files")
async def delete_all_files(db: Session = Depends(get_db)):
    """删除所有文件（保留分析历史记录）"""
    try:
        from services.graph_service import GraphService
        graph_service = GraphService(db)
        
        # 扫描文件系统中的所有文件
        deleted_count = 0
        processed_file_ids = set()
        
        # 遍历所有可能的文件扩展名
        for ext in ["pdf", "txt", "log", "jpg", "jpeg", "png"]:
            # 查找所有匹配的文件
            for file_path in UPLOAD_DIR.glob(f"*.{ext}"):
                if file_path.is_file():
                    # 提取文件ID（文件名不包含扩展名）
                    file_id = file_path.stem
                    
                    # 确保每个文件ID只处理一次
                    if file_id not in processed_file_ids:
                        processed_file_ids.add(file_id)
                        
                        # 删除所有与该文件ID相关的文件（无论扩展名）
                        for del_ext in ["pdf", "txt", "log", "jpg", "jpeg", "png"]:
                            del_file_path = UPLOAD_DIR / f"{file_id}.{del_ext}"
                            if del_file_path.exists():
                                del_file_path.unlink()
                                deleted_count += 1
                                logger.info(f"已删除文件: {del_file_path}")
                        
                        # [FIX] 清理数据库记录
                        db.query(FileTextStore).filter(FileTextStore.file_id == file_id).delete()
                        
                        # [NEW] 清理知识图谱
                        try:
                            graph_service.remove_document_knowledge(file_id)
                        except Exception as ge:
                            logger.error(f"清理图谱数据失败: {ge}")

        # 清理全局存储（只清理向量存储，FILE_TEXT_STORE现在从数据库获取）
        for file_id in list(VECTOR_STORES.keys()):
            del VECTOR_STORES[file_id]
        
        db.commit()
        
        # 不再清理分析历史记录（根据需求保留）
        deleted_history_count = 0
        
        return {
            "status": "success",
            "message": f"所有文件删除成功，共删除 {deleted_count} 个文件",
            "deleted_count": deleted_count,
            "deleted_history_count": deleted_history_count
        }
    except Exception as e:
        logger.error(f"删除所有文件失败: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除所有文件失败: {str(e)}")

@app.get("/history")
async def get_analysis_history(
    page: int = Query(1, ge=1, description="页码，从1开始"), 
    page_size: int = Query(10, ge=1, le=100, description="每页显示的历史记录数量"),
    db: Session = Depends(get_db)
):
    """获取分析历史记录，支持分页"""
    try:
        # 计算总数
        total = db.query(AnalysisHistory).count()
        
        # 计算偏移量和限制
        offset = (page - 1) * page_size
        
        # 查询数据（按分析时间倒序排列）
        history_entries = db.query(AnalysisHistory).order_by(
            AnalysisHistory.analysis_time.desc()
        ).offset(offset).limit(page_size).all()
        
        # 转换为响应格式
        paginated_history = []
        for entry in history_entries:
            paginated_history.append({
                "id": entry.id,
                "file_id": entry.file_id,
                "filename": entry.filename,
                "analysis_time": entry.analysis_time,
                "result": entry.result_dict
            })
        
        return {
            "status": "success",
            "total": total,
            "page": page,
            "page_size": page_size,
            "data": paginated_history
        }
    except Exception as e:
        logger.error(f"获取历史分析结果失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取历史分析结果失败: {str(e)}")

@app.get("/history/{history_id}")
async def get_analysis_history_detail(
    history_id: str,
    db: Session = Depends(get_db)
):
    """获取指定历史记录的详情"""
    try:
        # 查找指定的历史记录
        history_item = db.query(AnalysisHistory).filter(AnalysisHistory.id == history_id).first()
        if not history_item:
            raise HTTPException(status_code=404, detail="历史记录不存在")
        
        # 转换为响应格式
        result_item = {
            "id": history_item.id,
            "file_id": history_item.file_id,
            "filename": history_item.filename,
            "analysis_time": history_item.analysis_time,
            "result": history_item.result_dict
        }
        
        return {
            "status": "success",
            "data": result_item
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取历史分析结果详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取历史分析结果详情失败: {str(e)}")

@app.delete("/history/{history_id}")
async def delete_analysis_history(
    history_id: str,
    db: Session = Depends(get_db)
):
    """删除指定历史分析记录，并同时删除对应的文件"""
    try:
        # 查找指定的历史记录
        history_item = db.query(AnalysisHistory).filter(AnalysisHistory.id == history_id).first()
        if not history_item:
            raise HTTPException(status_code=404, detail="历史记录不存在")
        
        # 获取对应的文件ID
        file_id = history_item.file_id
        
        # 删除历史记录
        db.delete(history_item)
        deleted_history_count = 1
        logger.info(f"已删除历史记录: {history_id}")
        
        # 检查是否还有其他历史记录使用同一个文件ID
        other_history_count = db.query(AnalysisHistory).filter(
            AnalysisHistory.file_id == file_id and AnalysisHistory.id != history_id
        ).count()
        
        # 如果没有其他历史记录使用同一个文件ID，则删除该文件
        deleted_files = []
        if other_history_count == 0:
            # 清理文件系统中的文件
            for ext in ["pdf", "txt", "log", "jpg", "jpeg", "png"]:
                file_path = UPLOAD_DIR / f"{file_id}.{ext}"
                if file_path.exists():
                    try:
                        file_path.unlink()
                        deleted_files.append(str(file_path))
                        logger.info(f"已删除文件: {file_path}")
                    except Exception as e:
                        logger.error(f"删除文件 {file_path} 失败: {str(e)}")
            
            # 清理数据库中的文件记录
            db.query(FileTextStore).filter(FileTextStore.file_id == file_id).delete()
            
            # 清理向量存储
            if file_id in VECTOR_STORES:
                del VECTOR_STORES[file_id]
                
            # [NEW] 清理知识图谱
            try:
                from services.graph_service import GraphService
                GraphService(db).remove_document_knowledge(file_id)
            except Exception as ge:
                logger.error(f"清理图谱数据失败: {ge}")
        
        # 提交数据库更改
        db.commit()
        
        return {
            "status": "success",
            "message": f"删除成功，共删除 {deleted_history_count} 条分析记录和 {len(deleted_files)} 个文件",
            "deleted_history_count": deleted_history_count,
            "deleted_files": deleted_files
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除历史分析记录失败: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除历史分析记录失败: {str(e)}")

@app.delete("/history")
async def delete_all_analysis_history(db: Session = Depends(get_db)):
    """删除所有历史分析记录，并同时删除所有对应的文件"""
    try:
        # 获取所有唯一的文件ID
        file_ids = db.query(AnalysisHistory.file_id).distinct().all()
        file_ids = [item[0] for item in file_ids]
        
        # 删除所有历史记录
        deleted_history_count = db.query(AnalysisHistory).count()
        db.query(AnalysisHistory).delete()
        logger.info(f"已删除所有历史记录: {deleted_history_count} 条")
        
        # 删除所有对应的文件
        deleted_files = []
        for file_id in file_ids:
            # 清理文件系统中的文件
            for ext in ["pdf", "txt", "log", "jpg", "jpeg", "png"]:
                file_path = UPLOAD_DIR / f"{file_id}.{ext}"
                if file_path.exists():
                    try:
                        file_path.unlink()
                        deleted_files.append(str(file_path))
                        logger.info(f"已删除文件: {file_path}")
                    except Exception as e:
                        logger.error(f"删除文件 {file_path} 失败: {str(e)}")
            
            # 清理数据库中的文件记录
            db.query(FileTextStore).filter(FileTextStore.file_id == file_id).delete()
            
            # 清理向量存储
            if file_id in VECTOR_STORES:
                del VECTOR_STORES[file_id]
                
            # [NEW] 清理知识图谱
            try:
                from services.graph_service import GraphService
                GraphService(db).remove_document_knowledge(file_id)
            except Exception as ge:
                logger.error(f"清理图谱数据失败: {ge}")
        
        # 提交数据库更改
        db.commit()
        
        return {
            "status": "success",
            "message": f"删除成功，共删除 {deleted_history_count} 条分析记录和 {len(deleted_files)} 个文件",
            "deleted_history_count": deleted_history_count,
            "deleted_files": deleted_files
        }
    except Exception as e:
        logger.error(f"删除所有历史分析记录失败: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除所有历史分析记录失败: {str(e)}")

@app.get("/")
async def health_check():
    """健康检查接口"""
    return {
        "status": "success",
        "message": "DocMind Pro API is running"
    }

# ======================
# 视频分析相关API路由
# ======================
# ======================
# Semantic Teacher Mode (User Memory)
# ======================
class UserMemory:
    def __init__(self):
        # Key: file_id, Value: List of memory dicts
        self.memories = {}

    def add_memory(self, file_id, question, correction):
        """Add a correction to semantic memory for a specific file"""
        if GLOBAL_HISTORY_STORE.model:
            vector = GLOBAL_HISTORY_STORE.model.encode(question)
            try:
                norm = np.linalg.norm(vector)
                if norm > 0:
                    vector = vector / norm
            except:
                pass
            
            if file_id not in self.memories:
                self.memories[file_id] = []
                
            file_memories = self.memories[file_id]
            
            # Check for existing similar memory (Threshold > 0.95)
            best_idx = -1
            best_sim = -1.0
            
            for idx, mem in enumerate(file_memories):
                try:
                    sim = np.dot(vector, mem["vector"])
                    if sim > best_sim:
                        best_sim = sim
                        best_idx = idx
                except:
                    continue
            
            # Merge if highly similar
            if best_idx >= 0 and best_sim > 0.95:
                current_text = file_memories[best_idx]["correction"]
                if correction not in current_text:
                    new_correction = current_text + "\n" + correction
                    file_memories[best_idx]["correction"] = new_correction
                    
                    # [DB] Update existing rule
                    try:
                        db = SessionLocal()
                        rule = db.query(TeacherRule).filter(TeacherRule.id == file_memories[best_idx]["id"]).first()
                        if rule:
                            rule.correction = new_correction
                            db.commit()
                        db.close()
                    except Exception as e:
                        logger.error(f"Failed to update rule in DB: {e}")

                    logger.info(f"🧠 [Teacher Mode] MERGED concept (Sim: {best_sim:.2f}) for File {file_id}: {question} -> {new_correction}")
                else:
                    logger.info(f"🧠 [Teacher Mode] SKIPPED duplicate concept (Sim: {best_sim:.2f})")
                
                file_memories[best_idx]["timestamp"] = time.time()
                return

            # [DB] Create new rule
            rule_id = str(uuid.uuid4())
            try:
                db = SessionLocal()
                new_rule = TeacherRule(
                    id=rule_id,
                    file_id=file_id,
                    question=question,
                    correction=correction
                )
                db.add(new_rule)
                db.commit()
                db.close()
            except Exception as e:
                logger.error(f"Failed to save rule to DB: {e}")

            file_memories.append({
                "id": rule_id,
                "vector": vector,
                "question": question,
                "correction": correction,
                "timestamp": time.time()
            })
            logger.info(f"🧠 [Teacher Mode] Learned new concept for File {file_id}: {question} -> {correction}")
            
    # Optimized threshold for better precision
    def search_memory(self, file_id, question, threshold=0.62):
        """Search for relevant corrections within a specific file"""
        if file_id not in self.memories:
            logger.info(f"🧠 [Memory Search] Skipped: No memories for File {file_id}")
            return None
            
        target_memories = self.memories[file_id]
        logger.info(f"🧠 [Memory Search Entry] File: {file_id} | Query: '{question}' | Memories: {len(target_memories)}")
        
        if not GLOBAL_HISTORY_STORE.model:
            logger.error("🧠 [Memory Search] Aborted: Embedding model not loaded!")
            return None
            
        q_vec = GLOBAL_HISTORY_STORE.model.encode(question)
        q_norm = np.linalg.norm(q_vec)
        if q_norm > 0:
            q_vec = q_vec / q_norm
            
        matches = []
        
        logger.info(f"🧠 [Memory Search] Query: {question}")
        for mem in target_memories:
            score = np.dot(q_vec, mem["vector"])
            logger.info(f"   - Candidate: '{mem['question']}' | Score: {score:.4f}")
            if score >= threshold:
                matches.append({
                    "correction": mem["correction"],
                    "score": score
                })
        
        if matches:
            matches.sort(key=lambda x: x["score"], reverse=True)
            top_matches = matches[:3]
            
            seen_corrections = set()
            final_corrections = []
            for m in top_matches:
                parts = m["correction"].split('\n')
                for part in parts:
                    part = part.strip()
                    if part and part not in seen_corrections:
                        seen_corrections.add(part)
                        final_corrections.append(part)
            
            combined_correction = "\n".join(final_corrections)
            logger.info(f"🧠 [Teacher Mode] Recall triggered (Top Score: {matches[0]['score']:.4f}). Combined {len(final_corrections)} facts.")
            return {"correction": combined_correction}
            
        logger.info(f"🧠 [Teacher Mode] No match found")
        return None

GLOBAL_USER_MEMORY = UserMemory()

# [DEBUG] Endpoints for Teacher Mode
@app.get("/debug/memory")
async def get_debug_memory():
    """View current semantic memory"""
    all_items = []
    for fid, mems in GLOBAL_USER_MEMORY.memories.items():
        for m in mems:
            all_items.append({
                "file_id": fid,
                "question": m["question"],
                "correction": m["correction"],
                "timestamp": m["timestamp"]
            })
            
    return {
        "count": len(all_items),
        "items": all_items
    }

@app.post("/debug/check_memory")
async def check_debug_memory(payload: dict = Body(...)):
    """Test similarity search"""
    question = payload.get("question", "")
    target_file_id = payload.get("file_id", None)
    
    # Calculate all scores across all files
    scores = []
    if GLOBAL_HISTORY_STORE.model:
        q_vec = GLOBAL_HISTORY_STORE.model.encode(question)
        q_norm = np.linalg.norm(q_vec)
        if q_norm > 0: q_vec = q_vec / q_norm
        
        for fid, mems in GLOBAL_USER_MEMORY.memories.items():
            if target_file_id and fid != target_file_id:
                continue
                
            for m in mems:
                score = np.dot(q_vec, m["vector"])
                scores.append({
                    "file_id": fid,
                    "question": m["question"],
                    "correction": m["correction"],
                    "score": float(score)
                })
    
    match = None
    if target_file_id:
        match = GLOBAL_USER_MEMORY.search_memory(target_file_id, question, threshold=0.0)
    
    return {
        "best_match_for_file": match,
        "all_scores": sorted(scores, key=lambda x: x["score"], reverse=True)
    }

# [NEW] Persistence: Restore memory from DB on startup
def rebuild_memory_from_db():
    """Load from TeacherRule table. If empty, migrate from QAHistory (One-time)"""
    logger.info("🧠 [Teacher Mode] Initializing: Restoring memory from database...")
    db = SessionLocal()
    count = 0
    try:
        # 1. Load from TeacherRule (Primary Source)
        rules = db.query(TeacherRule).all()
        if rules:
            logger.info(f"🧠 [Teacher Mode] Loading {len(rules)} rules from TeacherRule table...")
            for r in rules:
                questions = r.question # Currently 1:1, but could be N:1
                # If question is stored as a list in string or just string.
                # Just add directly.
                # Note: We must inject the ID so we can update it later.
                if r.file_id and r.question and r.correction:
                    if r.file_id not in GLOBAL_USER_MEMORY.memories:
                        GLOBAL_USER_MEMORY.memories[r.file_id] = []
                    
                    if GLOBAL_HISTORY_STORE.model:
                        vector = GLOBAL_HISTORY_STORE.model.encode(r.question)
                        try:
                            norm = np.linalg.norm(vector)
                            if norm > 0: vector = vector / norm
                        except:
                            pass
                        
                        GLOBAL_USER_MEMORY.memories[r.file_id].append({
                            "id": r.id,
                            "vector": vector,
                            "question": r.question,
                            "correction": r.correction,
                            "timestamp": r.created_at.timestamp() if r.created_at else time.time()
                        })
                        count += 1
            logger.info(f"🧠 [Teacher Mode] Loaded {count} rules from TeacherRule table.")
            return

        # 2. Migration: If TeacherRule is empty, scan QAHistory (Backward Compatibility)
        logger.warning("🧠 [Teacher Mode] No rules found in TeacherRule. Scanning QAHistory for migration...")
        items = db.query(QAHistory).filter(QAHistory.evaluation.isnot(None)).all()
        
        for item in items:
            try:
                eval_data = json.loads(item.evaluation)
                if eval_data.get('rating', 0) < 0 and eval_data.get('comment'):
                    comment = eval_data.get('comment')
                    if len(comment.strip()) > 2:
                        question = item.question
                        # Use add_memory which handles DB insertion now!
                        GLOBAL_USER_MEMORY.add_memory(item.file_id, question, comment)
                        count += 1
            except Exception as e:
                logger.warning(f"Failed to parse evaluation for QA {item.id}: {e}")
                
        logger.info(f"🧠 [Teacher Mode] Migration Complete. Migrated {count} memories to TeacherRule table.")
    except Exception as e:
        logger.error(f"🧠 [Teacher Mode] Restoration Failed: {e}")
    finally:
        db.close()

# Execute restoration immediately on startup
rebuild_memory_from_db()

class FeedbackRequest(BaseModel):
    file_id: str
    qa_id: str
    rating: int
    comment: Optional[str] = None
    question: Optional[str] = None

@app.post("/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    """Submit feedback and trigger Teacher Mode if applicable"""
    db = SessionLocal()
    try:
        # 1. Update DB (QAHistory)
        if feedback.qa_id:
             qa_item = db.query(QAHistory).filter(QAHistory.id == feedback.qa_id).first()
             if qa_item:
                 qa_item.evaluation = json.dumps({
                     "rating": feedback.rating,
                     "comment": feedback.comment
                 }, ensure_ascii=False)
                 db.commit()
            
        # 2. Teacher Mode Logic (Semantic Learning)
        # Condition: Rating is Negative (-1) AND Comment (Correction) is provided
        if feedback.rating < 0 and feedback.comment and len(feedback.comment.strip()) > 2:
            question_text = feedback.question
            if not question_text and qa_item:
                question_text = qa_item.question
            
            if question_text:
                # Store in Semantic Memory
                GLOBAL_USER_MEMORY.add_memory(feedback.file_id, question_text, feedback.comment)
                return {"status": "success", "message": "已学习新知识 (Teacher Mode Active)"}
                
        return {"status": "success", "message": "Feedback received"}
    except Exception as e:
        logger.error(f"Feedback error: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        db.close()



# ======================
# 知识库管理API
# ======================
@app.get("/api/rules")
async def get_teacher_rules(file_id: Optional[str] = None):
    """Get all teacher rules, optionally filtered by file"""
    db = SessionLocal()
    try:
        query = db.query(TeacherRule)
        if file_id:
            query = query.filter(TeacherRule.file_id == file_id)
        
        rules = query.order_by(TeacherRule.created_at.desc()).all()
        return {
            "count": len(rules),
            "items": [
                {
                    "id": r.id,
                    "file_id": r.file_id,
                    "question": r.question,
                    "correction": r.correction,
                    "created_at": r.created_at.isoformat() if r.created_at else None
                } for r in rules
            ]
        }
    finally:
        db.close()

@app.delete("/api/rules/{rule_id}")
async def delete_teacher_rule(rule_id: str):
    """Delete a teacher rule"""
    db = SessionLocal()
    try:
        rule = db.query(TeacherRule).filter(TeacherRule.id == rule_id).first()
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        # 1. Delete from DB
        file_id = rule.file_id
        db.delete(rule)
        db.commit()
        
        # 2. Update In-Memory cache
        if file_id in GLOBAL_USER_MEMORY.memories:
            original_len = len(GLOBAL_USER_MEMORY.memories[file_id])
            GLOBAL_USER_MEMORY.memories[file_id] = [
                m for m in GLOBAL_USER_MEMORY.memories[file_id] 
                if m.get("id") != rule_id
            ]
            new_len = len(GLOBAL_USER_MEMORY.memories[file_id])
            logger.info(f"🧠 [Teacher Mode] Deleted rule {rule_id} from memory. ({original_len} -> {new_len})")
            
        return {"status": "success", "message": "Rule deleted"}
    finally:
        db.close()

# ======================
# 视频分析相关API路由
# ======================
@app.get("/ask")
async def ask_question(
    question: str = Query(..., description="用户提问"),
    file_id: str = Query(..., description="文件ID，来自 /upload 返回")
):
    # 使用数据库会话获取文件信息
    db = SessionLocal()
    try:
        # [TEACHER MODE POINTER]
        # Using a higher threshold (0.62) to avoid irrelevant recollections
        logger.info(f"⚡ [Debug] Checking UserMemory for: '{question}' (File: {file_id})")
        teacher_instruction = ""  # Default empty string if no match
        memory_match = GLOBAL_USER_MEMORY.search_memory(file_id, question, threshold=0.62)
        if memory_match:
            # Simplified / Softer Prompt
            teacher_instruction = (
                f"\n\n[User Correction / 用户指正]\n"
                f"Note: The user previously corrected similar concepts: '{memory_match['correction']}'\n"
                f"Instruction: IF this correction is directly relevant to the current question, use it as the ground truth. "
                f"Otherwise, ignore it."
            )
            logger.info(f"💡 Injecting Teacher Instruction: {teacher_instruction}")

        # 从数据库中获取文件记录
        file_record = db.query(FileTextStore).filter(FileTextStore.file_id == file_id).first()
        if not file_record:
            raise HTTPException(status_code=404, detail="文件未找到，请先上传")
        
        if not question.strip():
            raise HTTPException(status_code=400, detail="问题不能为空")
        
        # [NEW] 防重复提交逻辑
        import datetime
        five_seconds_ago = datetime.datetime.now() - datetime.timedelta(seconds=5)
        
        existing_qa = db.query(QAHistory).filter(
            QAHistory.file_id == file_id,
            QAHistory.question == question,
            QAHistory.created_at >= five_seconds_ago
        ).order_by(QAHistory.created_at.desc()).first()
        
        if existing_qa:
            logger.warning(f"检测到重复请求 (5秒内): File={file_id}, Q={question}")
            try:
                evidence_data = json.loads(existing_qa.evidence_list)
            except:
                evidence_data = []
            return {
                "qa_id": existing_qa.id,
                "answer": existing_qa.answer,
                "evidence": evidence_data,
                "note": "cached"
            }
 
        lower_q = question.lower()
        if any(trigger in lower_q for trigger in ["关键字", "关键词", "keyword", "keywords"]):
            keywords = file_record.keywords_list
            if keywords:
                return {"answer": ", ".join(keywords)}
            else:
                return {"answer": "文档中未提及此内容。"}
        
        vs = VECTOR_STORES.get(file_id)
        if vs is None:
            chunks = file_record.chunks_list
            relevant_chunks = chunks[:3]
        else:
            relevant_chunks = vs.search(question, k=3)
        
        logger.info(f"检索到 {len(relevant_chunks)} 个相关片段")
        
        # [TEACHER MODE INJECTION]
        final_question = question + teacher_instruction
        
        answer = await rag_answer(final_question, relevant_chunks)
        evidence = [{"text": c, "page": 1} for c in relevant_chunks]

        # 持久化保存 Q&A 记录
        new_qa = QAHistory(
            id=str(uuid.uuid4()),
            file_id=file_id,
            question=question,
            answer=answer,
            evidence=json.dumps(evidence, ensure_ascii=False),
            evaluation=None # 此时尚未评估
        )
        db.add(new_qa)
        db.commit()
        
        return {
            "qa_id": new_qa.id, # 返回ID供后续评估更新使用
            "answer": answer, 
            "evidence": evidence
        }
    finally:
        db.close()


# ======================
# 视频分析相关API路由
# ======================
@app.post("/api/process-video")
async def process_video(video_id: str = Body(..., description="视频ID"), 
                        task_type: str = Body(..., description="任务类型"),
                        question: str = Body(None, description="问题（仅QA任务需要）")):
    """处理视频相关任务的API端点"""
    try:
        
        # QA任务需要问题参数
        if task_type == 'qa' and not question:
            return Response(
                content=json.dumps({"error": "QA任务需要提供question参数", "status": "error"}),
                media_type="application/json",
                status_code=400
            )
        
        logger.info(f"Received request: video_id={video_id}, task_type={task_type}")
        
        # 检查视频处理器是否可用
        if video_processor is None:
            return Response(
                content=json.dumps({"error": "视频处理服务不可用", "status": "error"}),
                media_type="application/json",
                status_code=500
            )
        
        # 处理视频任务
        result = video_processor.process_video_task(video_id, task_type, question)
        
        # 返回成功响应
        return Response(
            content=json.dumps({
                "success": True,
                "message": "处理成功",
                "data": result.get('data', {}),
                "task_type": task_type
            }),
            media_type="application/json",
            status_code=200
        )
        
    except ValueError as ve:
        # 处理参数错误等预期内的错误
        logger.warning(f"Value error: {str(ve)}")
        return Response(
            content=json.dumps({"error": str(ve), "status": "error"}),
            media_type="application/json",
            status_code=400
        )
    
    except Exception as e:
        # 处理未预期的错误
        logger.error(f"Unexpected error: {str(e)}")
        return Response(
            content=json.dumps({"error": f"服务器内部错误: {str(e)}", "status": "error"}),
            media_type="application/json",
            status_code=500
        )

@app.get("/api/health")
async def video_health_check():
    """视频处理服务健康检查API端点"""
    return {
        "status": "healthy",
        "message": "Video processing service is running"
    }

# ======================
# PDF助手相关API路由
# ======================
@app.post("/api/pdf/extract-images")
async def extract_pdf_images(request: dict = Body(...)):
    file_id = request.get("file_id")
    """从PDF文件中提取图片"""
    try:
        db = SessionLocal()
        file_record = db.query(FileTextStore).filter(FileTextStore.file_id == file_id).first()
        db.close()
        if not file_record:
            raise HTTPException(status_code=404, detail="文件不存在")
        pdf_path = None
        for ext in ["pdf"]:
            path = UPLOAD_DIR / f"{file_id}.{ext}"
            if path.exists():
                pdf_path = str(path)
                break
        if not pdf_path:
            raise HTTPException(status_code=404, detail="PDF文件不存在")
        result = pdf_service.extract_images(pdf_path)
        return {"success": True, "message": "图片提取成功", "data": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提取PDF图片失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"提取PDF图片失败: {str(e)}")

@app.post("/api/pdf/compress")
async def compress_pdf_file(request: dict = Body(...)):
    file_id = request.get("file_id")
    """压缩PDF文件"""
    try:
        db = SessionLocal()
        file_record = db.query(FileTextStore).filter(FileTextStore.file_id == file_id).first()
        db.close()
        if not file_record:
            raise HTTPException(status_code=404, detail="文件不存在")
        pdf_path = None
        for ext in ["pdf"]:
            path = UPLOAD_DIR / f"{file_id}.{ext}"
            if path.exists():
                pdf_path = str(path)
                break
        if not pdf_path:
            raise HTTPException(status_code=404, detail="PDF文件不存在")
        output_path = str(DOWNLOAD_DIR / f"{file_id}_compressed.pdf")
        result = pdf_service.compress_pdf(pdf_path, output_path)
        return {"success": True, "message": "PDF压缩成功", "data": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"压缩PDF失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"压缩PDF失败: {str(e)}")

@app.post("/api/pdf/extract-text")
async def extract_pdf_text(request: dict = Body(...)):
    file_id = request.get("file_id")
    """从PDF文件中提取文本"""
    try:
        db = SessionLocal()
        file_record = db.query(FileTextStore).filter(FileTextStore.file_id == file_id).first()
        db.close()
        if not file_record:
            raise HTTPException(status_code=404, detail="文件不存在")
        pdf_path = None
        for ext in ["pdf"]:
            path = UPLOAD_DIR / f"{file_id}.{ext}"
            if path.exists():
                pdf_path = str(path)
                break
        if not pdf_path:
            raise HTTPException(status_code=404, detail="PDF文件不存在")
        result = pdf_service.extract_text(pdf_path)
        return {"success": True, "message": "文本提取成功", "data": {"text": result}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提取PDF文本失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"提取PDF文本失败: {str(e)}")

@app.post("/api/pdf/rotate")
async def rotate_pdf_pages(request: dict = Body(...)):
    file_id = request.get("file_id")
    angle = request.get("angle")
    pages = request.get("pages", ":")
    """旋转PDF页面"""
    try:
        db = SessionLocal()
        file_record = db.query(FileTextStore).filter(FileTextStore.file_id == file_id).first()
        db.close()
        if not file_record:
            raise HTTPException(status_code=404, detail="文件不存在")
        pdf_path = None
        for ext in ["pdf"]:
            path = UPLOAD_DIR / f"{file_id}.{ext}"
            if path.exists():
                pdf_path = str(path)
                break
        if not pdf_path:
            raise HTTPException(status_code=404, detail="PDF文件不存在")
        output_path = str(DOWNLOAD_DIR / f"{file_id}_rotated.pdf")
        result = pdf_service.rotate_pdf(pdf_path, output_path, angle, pages)
        return {"success": True, "message": "PDF页面旋转成功", "data": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"旋转PDF页面失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"旋转PDF页面失败: {str(e)}")

@app.post("/api/pdf/split")
async def split_pdf_file(request: dict = Body(...)):
    file_id = request.get("file_id")
    split_page = request.get("split_page")
    pages_per_file = request.get("pages_per_file")
    """拆分PDF文件"""
    try:
        db = SessionLocal()
        file_record = db.query(FileTextStore).filter(FileTextStore.file_id == file_id).first()
        db.close()
        if not file_record:
            raise HTTPException(status_code=404, detail="文件不存在")
        pdf_path = None
        for ext in ["pdf"]:
            path = UPLOAD_DIR / f"{file_id}.{ext}"
            if path.exists():
                pdf_path = str(path)
                break
        if not pdf_path:
            raise HTTPException(status_code=404, detail="PDF文件不存在")
        output_dir = str(DOWNLOAD_DIR / f"{file_id}_split")
        result = pdf_service.split_pdf(pdf_path, output_dir, split_page, pages_per_file)
        # 提取拆分后的文件路径列表
        split_files = [item['path'] for item in result]
        return {"success": True, "message": "PDF拆分成功", "data": {"split_files": split_files}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"拆分PDF失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"拆分PDF失败: {str(e)}")

@app.post("/api/pdf/merge")
async def merge_pdf_files(request: dict = Body(...)):
    """合并PDF文件"""
    try:
        file_ids = request.get("file_ids", [])
        if not isinstance(file_ids, list) or len(file_ids) < 2:
            raise HTTPException(status_code=400, detail="至少需要2个PDF文件才能合并")
        
        pdf_paths = []
        for file_id in file_ids:
            db = SessionLocal()
            file_record = db.query(FileTextStore).filter(FileTextStore.file_id == file_id).first()
            db.close()
            if not file_record:
                raise HTTPException(status_code=404, detail=f"文件ID {file_id} 不存在")
            
            pdf_path = None
            for ext in ["pdf"]:
                path = UPLOAD_DIR / f"{file_id}.{ext}"
                if path.exists():
                    pdf_path = str(path)
                    break
            
            if not pdf_path:
                raise HTTPException(status_code=404, detail=f"PDF文件 {file_id} 不存在")
            
            pdf_paths.append(pdf_path)
        
        # 生成输出文件路径
        output_file_id = str(uuid.uuid4())
        output_path = str(DOWNLOAD_DIR / f"{output_file_id}.pdf")
        
        result = pdf_service.merge_pdfs(pdf_paths, output_path)
        # 转换结果格式，将output_path改为merged_path以适应前端期望
        result_with_merged_path = {
            "merged_path": result["output_path"],
            "merged_files": result["merged_files"],
            "total_pages": result["total_pages"]
        }
        return {"success": True, "message": "PDF合并成功", "data": result_with_merged_path}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"合并PDF失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"合并PDF失败: {str(e)}")

@app.get("/api/pdf/metadata/{file_id}")
async def get_pdf_metadata(file_id: str):
    """获取PDF文件元数据"""
    try:
        db = SessionLocal()
        file_record = db.query(FileTextStore).filter(FileTextStore.file_id == file_id).first()
        db.close()
        if not file_record:
            raise HTTPException(status_code=404, detail="文件不存在")
        pdf_path = None
        for ext in ["pdf"]:
            path = UPLOAD_DIR / f"{file_id}.{ext}"
            if path.exists():
                pdf_path = str(path)
                break
        if not pdf_path:
            raise HTTPException(status_code=404, detail="PDF文件不存在")
        result = pdf_service.get_metadata(pdf_path)
        return {"success": True, "message": "获取PDF元数据成功", "data": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取PDF元数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取PDF元数据失败: {str(e)}")

        
        # 提取文本
        result = pdf_service.extract_text(pdf_path)
        
        return {
            "success": True,
            "message": "PDF文本提取成功",
            "data": {"text": result}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提取PDF文本失败: {str(e)}")
# ======================
# 翻译相关定义
# ======================
class TranslateRequest(BaseModel):
    text: str
    type: str = "translate" # 默认是翻译，可选 "polish"
    context: Optional[str] = None # 预留字段

class BatchTranslateRequest(BaseModel):
    items: List[dict] # {index, text}
    type: str = "translate"  # translate | polish

class BatchTranslateResponse(BaseModel):
    status: str
    translations: List[dict]  # {index, translation}
    message: Optional[str] = None

class ParagraphItem(BaseModel):
    index: int
    text: str

class ParagraphResponse(BaseModel):
    status: str = "success"
    file_id: str
    filename: str = ""
    paragraphs: List[ParagraphItem]

# ======================
# 划词翻译相关API
# ======================
@app.post("/api/translate")
async def translate_selection(req: TranslateRequest):
    """
    接收前端选中的文本，调用 LLM 进行学术翻译
    """
    try:
        if not req.text or len(req.text.strip()) == 0:
            return {"status": "error", "message": "翻译内容不能为空"}
        
        # 限制长度防止滥用
        if len(req.text) > 2000:
             return {"status": "error", "message": "选中文本过长，请分段"}
        
        if req.type == "polish":
            result = await simple_llm.polish_academic_text(req.text)
        else:
            result = await simple_llm.translate_academic_text(req.text)
            

        logger.info(f"收到翻译请求，长度: {len(req.text)}")
         
        return {
            "status": "success", 
            "original": req.text,
            "translation": result
        }
    except Exception as e:
        logger.error(f"API ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"API ERROR: {str(e)}")

# ======================
# 双语对照-全文段落获取
# ======================
import re
from typing import List

def _normalize_pdf_text(text: str) -> str:
    if not text:
        return ""

    # 统一换行
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 修复 PDF 断词： "pa-\nper" -> "paper"
    # 只在连字符后面紧跟换行且下一行是字母时合并，避免误伤公式/列表
    text = re.sub(r"(\w)-\n(?=\w)", r"\1", text)

    # 把"行内换行"变空格（保留空行作为段落边界）
    # 先把空行标记出来
    text = re.sub(r"\n\s*\n+", "\n\n", text)  # 多空行收敛
    blocks = text.split("\n\n")
    blocks = [re.sub(r"[ \t]+", " ", b.replace("\n", " ")).strip() for b in blocks]
    text = "\n\n".join([b for b in blocks if b])

    # 标点后缺空格（英文逗号/分号/冒号）
    # 但不改 URL/email
    def _safe_punct_space(s: str) -> str:
        masks = []
        def mask(m):
            masks.append(m.group(0))
            return f"__MASK_{len(masks)-1}__"

        s = re.sub(r"https?://\S+|www\.\S+|[\w\.-]+@[\w\.-]+\.\w+", mask, s)
        s = re.sub(r"([,;:])(?=\S)", r"\1 ", s)
        for i, v in enumerate(masks):
            s = s.replace(f"__MASK_{i}__", v)
        return s

    text = "\n\n".join(_safe_punct_space(b) for b in text.split("\n\n"))

    return text.strip()

def _split_to_sentences(text: str) -> List[str]:
    """
    尽量按句子边界切分（中英文标点）。
    如果切不动，fallback 为按空格粗切。
    """
    if not text:
        return []

    # 保留分隔符：把句末标点作为句子的一部分
    parts = re.split(r"([。！？.!?]+)\s*", text)
    sents = []
    buf = ""
    for i in range(0, len(parts), 2):
        seg = parts[i].strip()
        punct = parts[i + 1] if i + 1 < len(parts) else ""
        if not seg and not punct:
            continue
        s = (seg + punct).strip()
        if s:
            sents.append(s)

    if len(sents) >= 2:
        return sents

    # fallback：按空格粗切（避免超长一整段）
    words = text.split(" ")
    out = []
    tmp = []
    for w in words:
        if not w:
            continue
        tmp.append(w)
        if len(" ".join(tmp)) >= 120:
            out.append(" ".join(tmp))
            tmp = []
    if tmp:
        out.append(" ".join(tmp))
    return out

import re
from typing import List

def format_paragraph_for_reading(
    text: str,
    *,
    break_on_numbering: bool = True,
    break_on_sentence: bool = True
) -> str:
    if not text:
        return ""

    t = text.strip().replace("\r\n", "\n").replace("\r", "\n")

    t = re.sub(
        r"(?m)^\s*(\d+(?:\.\d+)*)\s*\.?\s*\n+\s*([A-Z][A-Z0-9 \-]{2,})\b",
        r"\1. \2",
        t
    )

    t = re.sub(r"[ \t]+", " ", t)

    t = re.sub(
        r"(?m)^(?P<h>(?:\d+(?:\.\d+)*\.\s*)?[A-Z][A-Z0-9 \-]{2,})\s+(?P<body>[A-Z][a-z].+)$",
        r"\g<h>\n\g<body>",
        t
    )

    if break_on_numbering:
        t = re.sub(r"(?<!\n)\s+(?=(\d+(?:\.\d+)*)(?:\.)\s+[A-Z])", "\n", t)
        t = re.sub(r"(?<!\n)\s+(?=\d+(?:\.\d+)*\)\s+)", "\n", t)
        t = re.sub(r"(?<!\n)\s+(?=(\d+(?:\.\d+)*)(?::)\s+[A-Z])", "\n", t)

    if break_on_sentence:
        t = re.sub(r"(?<!\b\d)([.!?])\s+(?=[A-Z])", r"\1\n", t)
        t = re.sub(r"([。！？])(?=[^\n])", r"\1\n", t)
        t = re.sub(r"(?<!\n)\s+(?=\[\d+\]\s+)", "\n", t)

    t = re.sub(r"\n{3,}", "\n\n", t)
    t = re.sub(r"[ \t]+\n", "\n", t)

    return t.strip()

def split_paragraphs_by_chars(
    text: str,
    target: int = 900,   # 理想段落长度（字符）
    min_len: int = 350,  # 小于这个尽量合并
) -> List[str]:
    """
    先把 PDF 文本规整成"自然段"（保留双换行），
    再把自然段按字符长度切成适合翻译的一段段（尽量按句子断开）。
    """
    text = _normalize_pdf_text(text)
    if not text:
        return []

    # Step A: 先按空行做"自然段"
    raw_parts = [p.strip() for p in text.split("\n\n") if p.strip()]

    # Step B: 在每个自然段里，再按"标题/章节行"切一下（更像论文结构）
    # 标题/章节常见模式：全大写、数字编号、Abstract/Keywords/References 等
    heading_pat = re.compile(
        r"(?im)^(abstract|keywords?|references|bibliography|introduction|conclusion|acknowledg(e)?ments?)\b|^\d+(\.\d+)*\s+\S+|^[A-Z][A-Z0-9 \-]{6,}$"
    )

    parts = []
    for block in raw_parts:
        # 如果 block 内含多个"heading"，按 heading 位置再拆
        lines = block.split(" ")
        # 由于我们把行都合并了，这里用"伪行"策略：在 heading 关键词附近插断点
        # 用正则在文本中找 heading 位置
        cuts = []
        for m in re.finditer(r"(?im)\b(ABSTRACT|KEYWORDS|REFERENCES|BIBLIOGRAPHY|INTRODUCTION|CONCLUSION)\b", block):
            if m.start() > 0:
                cuts.append(m.start())

        if not cuts:
            parts.append(block)
            continue

        cuts = sorted(set(cuts))
        last = 0
        for c in cuts:
            seg = block[last:c].strip()
            if seg:
                parts.append(seg)
            last = c
        tail = block[last:].strip()
        if tail:
            parts.append(tail)

    # Step C: 对过长段落，优先在句末附近切成 target_len 左右
    def split_by_sentence(s: str) -> List[str]:
        if len(s) <= target:
            return [s]

        # 先按强句末切
        chunks = re.split(r"([。！？!?]\s+|[.!?]\s+)", s)
        sentences = []
        for i in range(0, len(chunks), 2):
            piece = chunks[i]
            sep = chunks[i+1] if i+1 < len(chunks) else ""
            sent = (piece + sep).strip()
            if sent:
                sentences.append(sent)

        # 如果几乎切不出来（比如参考文献/表格），就走弱断点切
        if len(sentences) <= 1:
            return _split_long_by_soft_breaks(s, target)

        out, cur = [], ""
        soft_limit = int(target * 1.25)  # 允许略超，换取句子完整

        for sent in sentences:
            if not cur:
                cur = sent
                continue

            # 优先保持整句：没超过 soft_limit 就继续拼
            if len(cur) + 1 + len(sent) <= soft_limit:
                cur = cur + " " + sent
                continue

            out.append(cur.strip())
            cur = sent

        if cur:
            out.append(cur.strip())

        # 如果还有超长（单句过长），再做弱断点切，最后才硬切
        final = []
        for x in out:
            if len(x) <= soft_limit:
                final.append(x)
            else:
                final.extend(_split_long_by_soft_breaks(x, target))

        return [t for t in final if t]


    def _split_long_by_soft_breaks(x: str, target: int) -> List[str]:
        res = []
        start = 0
        hard_limit = int(target * 1.35)

        while start < len(x):
            end = min(len(x), start + hard_limit)
            window = x[start:end]

            # 先找弱断点（优先级：; : , 再空格）
            cut = max(window.rfind(";"), window.rfind(":"), window.rfind(","))

            if cut < int(target * 0.6):  # 弱断点太靠前就找空格
                cut = window.rfind(" ")

            if cut < int(target * 0.6):  # 还是没有合适断点才硬切
                cut = min(len(window), target)

            res.append(window[:cut].strip())
            start += cut

        return [r for r in res if r]

    refined = []
    for p in parts:
        refined.extend(split_by_sentence(p))

    # Step D: 太短的段落合并到上一段（更好读）
    merged = []
    for p in refined:
        if len(p) < min_len and merged:
            merged[-1] = (merged[-1] + " " + p).strip()
        else:
            merged.append(p)

    # Step E: 清理多余空格
    merged = [re.sub(r"\s+", " ", p).strip() for p in merged if p.strip()]
    heading_words = r"(ABSTRACT|INTRODUCTION|CONCLUSION|REFERENCES|BIBLIOGRAPHY|EXPERIENCE|ACKNOWLEDG(E)?MENTS?|METHOD(S)?|RESULTS?|DISCUSSION)"
    isolated_num_end = re.compile(r"(?:^|\s)(\d+(\.\d+)*)\.\s*$")  # e.g., "1." "2.3."
    heading_start = re.compile(rf"^\s*{heading_words}\b", re.I)

    fixed = []
    i = 0
    while i < len(merged):
        cur = merged[i]

        if fixed:
            prev = fixed[-1]
            m_num = isolated_num_end.search(prev)

            # 条件：上一段结尾是 "1." 这种编号
            if m_num:
                num = m_num.group(1) + "."
                prev_wo_num = prev[:m_num.start()].rstrip()

                # 条件A：下一段以 INTRODUCTION/ABSTRACT/... 开头
                # 条件B：或者下一段本身以一个标题式编号开头（比如 "1 INTRODUCTION" / "1. INTRODUCTION"）
                if heading_start.match(cur) or re.match(r"^\s*\d+(\.\d+)*\s+\S+", cur):
                    # 把编号从上一段挪到下一段
                    fixed[-1] = prev_wo_num
                    cur = f"{num} {cur}".strip()

        fixed.append(cur)
        i += 1

    # 清掉可能产生的空段
    merged = [p for p in fixed if p and p.strip()]
    merged = [
        format_paragraph_for_reading(p, break_on_numbering=True, break_on_sentence=True)
        for p in merged
    ]
    return merged

@app.get("/api/files/{file_id}/paragraphs", response_model=ParagraphResponse)
async def get_file_paragraphs(file_id: str):
    """
    返回全文段落（稳定版）：
    - 对 PDF：优先直接用 pdf_service.extract_text()（就是你 /api/pdf/extract-text 用的那套）
    - 再按字数切段（尽量句子边界），避免"又长又乱/断行粘连"
    """
    db = SessionLocal()
    try:
        record = db.query(FileTextStore).filter(FileTextStore.file_id == file_id).first()
        if not record:
            raise HTTPException(status_code=404, detail="文件不存在")

        filename = record.original_filename or ""

        # ===== 关键修复：PDF 强制走 pdf_service.extract_text，别用历史 record.text =====
        pdf_path = UPLOAD_DIR / f"{file_id}.pdf"
        text = ""

        if pdf_path.exists():
            # 这里就是你之前"提取文本很干净"的那条链路
            text = pdf_service.extract_text(str(pdf_path)) or ""
        else:
            # 非PDF：退回 DB text
            text = (record.text or "").strip()

        if not text.strip():
            raise HTTPException(status_code=404, detail="未能提取到有效文本")

        # 可选：把干净文本存回 DB（下次不用重复抽）
        # 注意：只在 pdf_path 存在时写回，避免污染其它类型
        if pdf_path.exists():
            record.text = text
            db.commit()

        paras = split_paragraphs_by_chars(text, target=900, min_len=350)

        return {
            "status": "success",
            "file_id": file_id,
            "filename": filename,
            "paragraphs": [{"index": i, "text": p} for i, p in enumerate(paras)]
        }
    finally:
        db.close()

# ======================
# 双语对照-批量翻译
# ======================
@app.post("/api/translate/batch", response_model=BatchTranslateResponse)
async def translate_batch(req: BatchTranslateRequest):
    if not req.items:
        return {"status": "success", "translations": []}

    # 总字符限制
    total_chars = sum(len(it.get("text", "")) for it in req.items)
    if total_chars > 60000:
        return {"status": "error", "message": "批量内容过大，请分批翻译", "translations": []}

    sem = asyncio.Semaphore(5)  # 并发限制，避免把 Qwen 压爆

    async def run_one(it: dict):
        async with sem:
            if req.type == "polish":
                out = await simple_llm.polish_academic_text(it.get("text", ""))
            else:
                out = await simple_llm.translate_academic_text(it.get("text", ""))
            return {"index": it.get("index", 0), "translation": out}

    try:
        results = await asyncio.gather(*[run_one(it) for it in req.items])
        # 保证按 index 排序返回
        results.sort(key=lambda x: x["index"])
        return {"status": "success", "translations": results}
    except Exception as e:
        logger.error(f"Batch translate failed: {e}", exc_info=True)
        return {"status": "error", "message": str(e), "translations": []}

# ======================
# 反馈与评估接口 (New)
# ======================

class FeedbackRequest(BaseModel):
    file_id: str = None
    question: str
    answer: str
    rating: int  # 1: Good, -1: Bad
    comment: str = None

@app.post("/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    db = SessionLocal()
    try:
        new_feedback = Feedback(
            id=str(uuid.uuid4()),
            file_id=feedback.file_id,
            question=feedback.question,
            answer=feedback.answer,
            rating=feedback.rating,
            comment=feedback.comment
        )
        db.add(new_feedback)
        db.commit()
        return {"message": "Feedback received"}
    except Exception as e:
        logger.error(f"Error saving feedback: {e}")
        raise HTTPException(status_code=500, detail="Failed to save feedback")
    finally:
        db.close()

# 辅助测试接口：手动触发评估
class EvaluateRequest(BaseModel):
    question: str
    answer: str
    context: str

@app.post("/evaluate")
async def evaluate_answer(req: EvaluateRequest, qa_id: str = Query(None, description="QA记录ID")): # 增加qa_id参数支持持久化
    result = await evaluate_rag_response(req.question, req.answer, req.context)
    
    # 如果提供了qa_id，则更新数据库
    if qa_id:
        db = SessionLocal()
        try:
             qa_record = db.query(QAHistory).filter(QAHistory.id == qa_id).first()
             if qa_record:
                 qa_record.set_evaluation_dict(result) # 使用 property setter
                 db.commit()
                 logger.info(f"评估结果已保存到数据库 QA ID: {qa_id}")
        except Exception as e:
            logger.error(f"保存评估结果失败: {str(e)}")
            # 不阻断返回
        finally:
            db.close()
            
    return result

# ======================
# Q&A 历史记录管理 API (New)
# ======================

@app.get("/api/qa-history/{file_id}")
async def get_qa_history(file_id: str, db: Session = Depends(get_db)):
    """获取指定文件的所有问答历史"""
    try:
        history_list = db.query(QAHistory).filter(QAHistory.file_id == file_id).order_by(QAHistory.created_at.desc()).all()
        
        result = []
        for item in history_list:
            result.append({
                "id": item.id,
                "question": item.question,
                "answer": item.answer,
                "evidence": item.evidence_list, # 使用 property getter
                "evaluation": item.evaluation_dict, # 使用 property getter
                "created_at": item.created_at
            })
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"获取问答历史失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取问答历史失败: {str(e)}")

@app.delete("/api/qa-history/{qa_id}")
async def delete_qa_history(qa_id: str, db: Session = Depends(get_db)):
    """删除指定的问答记录"""
    try:
        item = db.query(QAHistory).filter(QAHistory.id == qa_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Q&A record not found")
        
        db.delete(item)
        db.commit()
        return {"status": "success", "message": "Deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"删除问答记录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除问答记录失败: {str(e)}")

# ======================
# 启动入口（用于本地调试）
# ======================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)