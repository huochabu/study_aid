from dotenv import load_dotenv
load_dotenv()
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))  # 将 backend 目录加入 sys.path
import os
import re
import json
import uuid
import logging
from pathlib import Path
from typing import List
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import httpx


# ======================
# 新增：向量检索依赖
# ======================
try:
    from sentence_transformers import SentenceTransformer
    import faiss
    import numpy as np
except ImportError:
    raise ImportError("请安装 RAG 依赖: pip install sentence-transformers faiss-cpu")

# ======================
# 新增：配置日志
# ======================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ======================
# PaddleOCR 离线配置
# ======================
os.environ["PADDLEOCR_HOME"] = "E:/documap/.paddleocr_cache"
DET_MODEL_DIR = r"E:\documap\models\paddleocr\ch_PP-OCRv4_det_infer"
REC_MODEL_DIR = r"E:\documap\models\paddleocr\ch_PP-OCRv4_rec_infer"
CLS_MODEL_DIR = r"E:\documap\models\paddleocr\ch_ppocr_mobile_v2.0_cls_infer"

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
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# 校验阿里云API Key
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not DASHSCOPE_API_KEY:
    raise ValueError("请在 .env 文件中配置 DASHSCOPE_API_KEY")

# ======================
# 全局文本存储
# ======================
FILE_TEXT_STORE = {}  # {file_id: {"text": str, "chunks": List[str], "keywords": List[str]}}

# ======================
# 向量存储类
# ======================
class VectorStore:
    def __init__(self):
        try:
            local_model_path = "E:/documap/models/bge-small-zh"
            self.model = SentenceTransformer(local_model_path)
            logger.info(f"✅ 向量模型加载成功: {local_model_path}")
        except Exception as e:
            logger.error(f"❌ 向量模型加载失败: {str(e)}", exc_info=True)
            raise RuntimeError("向量模型加载失败，请检查本地路径或网络")
        self.index = None
        self.chunks = []
        self.dim = 512

    def add_texts(self, texts: list):
        if not texts:
            return
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        if self.index is None:
            self.index = faiss.IndexFlatL2(self.dim)
        self.index.add(embeddings)
        self.chunks.extend(texts)

    def search(self, query: str, k=3):
        if self.index is None or len(self.chunks) == 0:
            return []
        query_vec = self.model.encode([query], convert_to_numpy=True)
        _, indices = self.index.search(query_vec, min(k, len(self.chunks)))
        return [self.chunks[i] for i in indices[0]]

VECTOR_STORES = {}

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
def extract_text_from_pdf(pdf_path: str) -> str:
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
    try:
        for model_dir in [DET_MODEL_DIR, REC_MODEL_DIR, CLS_MODEL_DIR]:
            if not os.path.exists(model_dir):
                raise FileNotFoundError(f"模型目录不存在: {model_dir}")
        
        from paddleocr import PaddleOCR
        ocr = PaddleOCR(
            use_angle_cls=True,
            lang="ch",
            use_gpu=False,
            det_model_dir=DET_MODEL_DIR,
            rec_model_dir=REC_MODEL_DIR,
            cls_model_dir=CLS_MODEL_DIR,
            download_model=False,
            show_log=False
        )
        logger.info(f"开始解析图片: {image_path}")
        result = ocr.ocr(image_path, cls=True)
        text = ""
        if result and isinstance(result, list) and len(result) > 0:
            for line in result:
                if line and isinstance(line, list):
                    for word_info in line:
                        if word_info and len(word_info) >= 2:
                            text += word_info[1][0] + "\n"
        text = text.strip()
        logger.info(f"提取的文本: {text if text else '空'}")
        return text
    except ImportError:
        raise HTTPException(status_code=500, detail="缺少OCR依赖：请执行 pip install paddleocr")
    except FileNotFoundError as e:
        logger.error(f"模型文件不存在: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OCR模型文件不存在: {str(e)}")
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
    for chunk in chunks:
        if len(chunk) > 800:
            sentences = re.split(r'[。\.\!\?\n]', chunk)
            temp = ""
            for sent in sentences:
                if len(temp + sent) > 600:
                    if temp:
                        final_chunks.append(temp.strip())
                    temp = sent
                else:
                    temp += sent + ". "
            if temp:
                final_chunks.append(temp.strip())
        else:
            final_chunks.append(chunk)
    return [c.strip() for c in final_chunks if c.strip()]

# ======================
# ✅ RAG 问答（保留）
# ======================
async def rag_answer(question: str, context_chunks: list) -> str:
    if not context_chunks:
        return "未找到相关文档内容。"
    context = "\n".join(context_chunks)[:4000]
    prompt = f"""
你是一个专业的学术论文分析助手，请根据以下【文档内容】准确回答问题。
- 如果文档中有明确的“KEYWORDS”、“Keywords”、“关键词”、“ABSTRACT”、“摘要”等字段，请直接引用其内容。
- 如果问题涉及方法、结果、贡献等，请从引言、方法或结论部分提取。
- 不要编造信息；如果文档确实未提及，请回答“文档中未提及此内容”。

【文档内容】
{context}

【问题】
{question}

【回答】
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
                    "parameters": {"temperature": 0.3}
                }
            )
        response.raise_for_status()
        data = response.json()
        output = data.get("output", {})
        if "choices" in output and isinstance(output["choices"], list):
            answer = output["choices"][0].get("message", {}).get("content", "")
        else:
            answer = str(output)
        return answer.strip()
    except Exception as e:
        logger.error(f"RAG 回答生成失败: {str(e)}")
        return f"生成答案时出错：{str(e)}"

# ======================
# ✅ 导入新模块（Multi-Agent + KG + Mindmap）
# ======================
try:
    from agents.scene_router import route_scene
    from agents.agent_team import analyze_with_agents
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
    
    def analyze_with_agents(text, agent_types):
        return {
            "summary": text[:1000],
            "reasoning_steps": [text[:500]]
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
# API接口
# ======================
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        logger.info(f"开始处理文件: {file.filename}, 类型: {file.content_type}")
        file_id = str(uuid.uuid4())
        ext = file.filename.split('.')[-1].lower()
        file_path = UPLOAD_DIR / f"{file_id}.{ext}"
        
        file_content = await file.read()
        with open(file_path, "wb") as f:
            f.write(file_content)
        logger.info(f"文件已保存到: {file_path}")

        text = ""
        if ext in ["jpg", "jpeg", "png"]:
            text = extract_text_from_image(str(file_path))
        elif ext == "pdf":
            text = extract_text_from_pdf(str(file_path))
        elif ext in ["txt", "log"]:
            try:
                text = file_content.decode("utf-8")
            except UnicodeDecodeError:
                text = file_content.decode("gbk", errors="replace")
        else:
            raise HTTPException(status_code=400, detail="不支持的文件格式（仅支持PDF/TXT/图片）")

        logger.info(f"提取的文本长度: {len(text)}")
        
        keywords = extract_keywords_from_text(text)
        logger.info(f"检测到关键词: {keywords}")
        
        chunks = smart_chunk_text(text)
        FILE_TEXT_STORE[file_id] = {
            "text": text,
            "chunks": chunks,
            "keywords": keywords
        }
        
        vs = VectorStore()
        vs.add_texts(chunks)
        VECTOR_STORES[file_id] = vs
        
        # ======================
        # ✅ 关键修改：使用 Multi-Agent 分析
        # ======================
        logger.info("🧠 启动 Multi-Agent 协作分析...")
        routing = route_scene(file_path, raw_text=text)
        agent_types = routing.get("agent_types", ["general"])
        agent_result = analyze_with_agents(text, agent_types)
        
        if "error" in agent_result:
            raise Exception(agent_result["error"])
        
        summary = agent_result["summary"]
        reasoning_steps = agent_result.get("reasoning_steps", [])
        logger.info("✅ Multi-Agent 分析完成")

        # ======================
        # ✅ 构建知识图谱（添加 await 调用异步函数）
        # ======================
        doc_type = agent_types[0] if agent_types else "general"
        knowledge_graph = await extract_knowledge_graph_from_text(summary, doc_type=doc_type)

        # ======================
        # ✅ 生成思维导图（添加数据校验和格式化）
        # ======================
        mindmap_data = await generate_mindmap_from_kg(knowledge_graph, reasoning_steps)
        
        # 应用格式化
        mindmap_data = format_mindmap_data(mindmap_data)
        logger.info(f"📊 格式化后的思维导图数据: {json.dumps(mindmap_data, ensure_ascii=False)[:200]}...")

        response_data = {
            "file_id": file_id,
            "filename": file.filename,
            "mindmap": mindmap_data,
            "knowledge_graph": knowledge_graph,
            "extracted_text": text,
            "reasoning_steps": reasoning_steps  # 可选：用于调试/展示推理过程
        }
        
        logger.info("文件处理完成，返回响应")
        return Response(
            content=json.dumps(response_data, ensure_ascii=False),
            media_type="application/json"
        )
    
    except HTTPException as e:
        logger.error(f"HTTP异常: {e.status_code} - {e.detail}")
        error_response = {
            "file_id": "",
            "filename": file.filename if 'file' in locals() else "",
            "mindmap": {
                "root": {
                    "id": "root",
                    "topic": f"处理失败: {e.detail}",
                    "children": []
                }
            },
            "knowledge_graph": {"nodes": [], "edges": []},
            "extracted_text": "",
            "reasoning_steps": []
        }
        return Response(
            content=json.dumps(error_response, ensure_ascii=False),
            media_type="application/json",
            status_code=e.status_code
        )
    except Exception as e:
        logger.error(f"服务内部错误: {str(e)}", exc_info=True)
        error_response = {
            "file_id": "",
            "filename": file.filename if 'file' in locals() else "",
            "mindmap": {
                "root": {
                    "id": "root",
                    "topic": f"服务内部错误: {str(e)}",
                    "children": []
                }
            },
            "knowledge_graph": {"nodes": [], "edges": []},
            "extracted_text": "",
            "reasoning_steps": []
        }
        return Response(
            content=json.dumps(error_response, ensure_ascii=False),
            media_type="application/json",
            status_code=500
        )

@app.get("/ask")
async def ask_question(
    question: str = Query(..., description="用户提问"),
    file_id: str = Query(..., description="文件ID，来自 /upload 返回")
):
    if file_id not in FILE_TEXT_STORE:
        raise HTTPException(status_code=404, detail="文件未找到，请先上传")
    
    if not question.strip():
        raise HTTPException(status_code=400, detail="问题不能为空")
    
    lower_q = question.lower()
    if any(trigger in lower_q for trigger in ["关键字", "关键词", "keyword", "keywords"]):
        keywords = FILE_TEXT_STORE[file_id].get("keywords", [])
        if keywords:
            return {"answer": ", ".join(keywords)}
        else:
            return {"answer": "文档中未提及此内容。"}
    
    vs = VECTOR_STORES.get(file_id)
    if vs is None:
        chunks = FILE_TEXT_STORE[file_id]["chunks"]
        relevant_chunks = chunks[:3]
    else:
        relevant_chunks = vs.search(question, k=3)
    
    logger.info(f"检索到 {len(relevant_chunks)} 个相关片段")
    answer = await rag_answer(question, relevant_chunks)
    return {"answer": answer}

@app.get("/")
async def health_check():
    return {"status": "success", "message": "DocMind Pro 后端运行中"}

# ======================
# 启动入口（用于本地调试）
# ======================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)