from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from services.graph_service import GraphService
from pydantic import BaseModel
from typing import List, Optional
from services.llm import simple_llm
import re
import json

router = APIRouter(prefix="/api/graph", tags=["Knowledge Graph"])

class PathQuery(BaseModel):
    start_node: str
    end_node: str

class QAQuery(BaseModel):
    question: str

@router.get("/data")
def get_graph_data(db: Session = Depends(get_db)):
    """获取全量图谱数据用于3D展示"""
    service = GraphService(db)
    return service.get_full_graph_data()

@router.post("/build")
def rebuild_graph_stats(db: Session = Depends(get_db)):
    """重新计算PageRank等图指标"""
    service = GraphService(db)
    service.update_pagerank()
    return {"status": "success", "message": "Graph stats updated"}

@router.post("/path")
def find_knowledge_path(query: PathQuery, db: Session = Depends(get_db)):
    """寻找两个概念之间的逻辑路径"""
    service = GraphService(db)
    path = service.find_shortest_path(query.start_node, query.end_node)
    
    if path is None:
        raise HTTPException(status_code=404, detail="One or both nodes not found")
        
    return {"path": path}

@router.post("/qa")
async def graph_rag_qa(query: QAQuery, db: Session = Depends(get_db)):
    """基于图谱的深度问答 (GraphRAG) + 全局文本检索 (Global Vector)"""
    service = GraphService(db)
    
    # 0. Global Vector Search (Retrieval across ALL loaded files)
    from services.vector_service import VECTOR_STORES
    vector_context_chunks = []
    
    # Simple iteration: Search top 2 chunks from EACH file
    # Optimize: In production, use a single global index or parallel search.
    for file_id, vs in VECTOR_STORES.items():
        results = vs.search(query.question, k=2)
        if results:
            # Result from vs.search is now a dict: {'text':..., 'metadata':..., 'score':...}
            for res in results:
                # Format: [Source: filename] content...
                meta = res.get("metadata", {})
                filename = meta.get("filename", "Unknown File")
                text = res.get("text", "")
                vector_context_chunks.append(f"[Source: {filename}]\n{text}")
    
    # Limit total context size to avoid LLM context overflow (approx 20 chunks)
    vector_context_chunks = vector_context_chunks[:20]
    vector_context_str = "\n---\n".join(vector_context_chunks) if vector_context_chunks else "No relevant document text found."

    # 1. Entity Extraction (LLM)
    # We ask LLM to identify potential entities in the question that might exist in our graph.
    extraction_prompt = [
        {"role": "system", "content": "You are a helper to extract technical entities from a user question. Return only a JSON list of strings. Example: [\"Transformer\", \"CNN\"]. Do NOT output anything else."},
        {"role": "user", "content": f"Extract key technical terms from: '{query.question}'. Respond JSON only."}
    ]
    
    entities = []
    try:
        raw_entities = await simple_llm.chat_completion(extraction_prompt)
        # Handle code blocks
        raw_entities = raw_entities.replace('```json', '').replace('```', '').strip()
        
        # Try to parse JSON
        match = re.search(r'\[.*\]', raw_entities, re.DOTALL)
        if match:
            entities = json.loads(match.group(0))
        else:
            # Fallback split if JSON fails but might be comma separated
            clean_text = re.sub(r'[\[\]"]', '', raw_entities)
            entities = [e.strip() for e in clean_text.split(',')]
            
    except Exception as e:
        print(f"Entity extraction failed: {e}")
        entities = query.question.split() # Fallback to naive tokens
        
    # 2. Get Subgraph Context
    context, context_data = service.get_subgraph_context(entities)
    
    if not context:
        context = "No direct knowledge graph connections found."
        
    # 3. Generate Answer (LLM) - HYBRID RAG
    qa_prompt = [
        {"role": "system", "content": "You are a Knowledge Graph specialized assistant. \nRULES:\n1. Answer the question using BOTH the 'Graph Context' (structural relationships) and 'Document Text' (detailed content) provided below.\n2. If the info is missing, state it clearly.\n3. Keep the answer concise and professional.\n4. If you use information from the Document Text, try to mention it (e.g., 'According to the documents...')."},
        {"role": "user", "content": f"Graph Context:\n{context}\n\nDocument Text:\n{vector_context_str}\n\nQuestion: {query.question}"}
    ]
    
    answer = await simple_llm.chat_completion(qa_prompt)
    
    return {
        "answer": answer,
        "context": context, # Legacy text context
        "vector_context": vector_context_str, # [NEW]
        "extracted_entities": entities,
        "context_data": context_data # Structured data for 3D highlighting
    }

@router.get("/seed")
def seed_test_data(db: Session = Depends(get_db)):
    """生成测试数据 (仅供演示)"""
    service = GraphService(db)
    
    # 模拟深度学习知识图谱
    service.add_edge("Deep Learning", "Neural Network", "is_based_on")
    service.add_edge("Convolutional Neural Network", "Deep Learning", "is_a")
    service.add_edge("Transformer", "Deep Learning", "is_a")
    service.add_edge("Attention Mechanism", "Transformer", "is_part_of")
    service.add_edge("RNN", "Deep Learning", "is_a")
    service.add_edge("LSTM", "RNN", "improves")
    service.add_edge("Gradient Descent", "Neural Network", "optimizes")
    service.add_edge("Backpropagation", "Gradient Descent", "algorithm_for")
    service.add_edge("BERT", "Transformer", "based_on")
    service.add_edge("GPT", "Transformer", "based_on")
    service.add_edge("NLP", "BERT", "application")
    service.add_edge("Computer Vision", "Convolutional Neural Network", "application")
    
    service.update_pagerank()
    
    return {"status": "seeded", "message": "Added test nodes and edges"}
