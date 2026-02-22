from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from database import Base
import uuid

class GlobalNode(Base):
    """全局知识图谱节点模型"""
    __tablename__ = "global_nodes"
    
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, index=True, nullable=False)  # 概念名称，全局唯一
    category = Column(String, index=True)  # 类别 (例如: "Algorithm", "Person", "Concept")
    digest = Column(Text)  # 摘要/定义
    weight = Column(Float, default=1.0)  # 重要性权重 (可由PageRank计算更新)
    
    # 存储来源文档ID列表 (JSON array)
    document_ids = Column(Text, default="[]") 
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class GlobalEdge(Base):
    """全局知识图谱边模型"""
    __tablename__ = "global_edges"
    
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    source_id = Column(String, ForeignKey("global_nodes.id"), nullable=False)
    target_id = Column(String, ForeignKey("global_nodes.id"), nullable=False)
    relation = Column(String)  # 关系描述 (例如: "is_a", "invented_by")
    weight = Column(Float, default=1.0)  # 连接强度
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
