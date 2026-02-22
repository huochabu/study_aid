from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from database import get_db
from models import AnalysisHistory, FileTextStore
from services.llm import simple_llm
from pydantic import BaseModel
from typing import List
import json
import asyncio

router = APIRouter(
    prefix="/api/comparison",
    tags=["comparison"]
)

class CompareRequest(BaseModel):
    file_ids: List[str]

@router.post("/compare")
async def compare_documents(
    request: CompareRequest, 
    db: Session = Depends(get_db)
):
    """
    智能对比分析选中的文档
    """
    file_ids = request.file_ids
    if len(file_ids) < 2:
        raise HTTPException(status_code=400, detail="请至少选择两个文档进行对比")
    if len(file_ids) > 5:
        raise HTTPException(status_code=400, detail="最多支持同时对比 5 个文档")

    # 获取文档内容（优先从历史记录获取摘要，如果没有则从TextStore获取全文摘要）
    docs_context = ""
    
    for i, fid in enumerate(file_ids):
        # 尝试获取分析历史
        history = db.query(AnalysisHistory).filter(AnalysisHistory.file_id == fid).first()
        file_record = db.query(FileTextStore).filter(FileTextStore.file_id == fid).first()
        
        filename = file_record.original_filename if file_record else f"Doc {i+1}"
        content = ""
        
        if history:
            res = history.result_dict
            summary = res.get("summary", "")
            entities = res.get("knowledge_graph", {}).get("nodes", [])
            # 提取实体名称
            entity_names = [n['label'] for n in entities if 'label' in n]
            content = f"摘要: {summary}\n关键实体: {', '.join(entity_names[:10])}"
        elif file_record:
            # 如果没有分析历史，截取部分全文
            content = file_record.text[:2000] if file_record.text else "无内容"
        else:
            content = "未找到文档内容"
            
        docs_context += f"【文档 {i+1}: {filename}】\n{content}\n\n-------------------\n\n"

    # 构建 Prompt
    prompt = f"""
你是一个专业的文档对比与分析专家。请根据以下提供的多个文档内容，生成一份详细的对比分析报告。

【对比要求】
1. 以 Markdown 表格形式展示（列名为文档名，行名为对比维度）。
2. 对比维度应包括但不限于：核心主题/观点、主要背景、关键技术/方法、局限性或待解决问题。
3. 表格之后，请给出一个“综合总结”，分析这些文档之间的联系（如：是否有演进关系、互补关系或对立观点）。

【文档内容】
{docs_context}

【输出格式】
直接输出 Markdown 内容，包含 ## 对比表格 和 ## 综合分析 两个章节。
"""

    try:
        # 调用 LLM
        response = await simple_llm.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return {"markdown": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"对比分析生成失败: {str(e)}")
