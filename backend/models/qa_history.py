from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.sql import func
from database import Base
import json
import uuid

class QAHistory(Base):
    """Q&A 历史记录模型"""
    __tablename__ = "qa_history"
    
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    file_id = Column(String, index=True)  # 关联的文件ID
    question = Column(Text)  # 问题
    answer = Column(Text)  # 回答
    evidence = Column(Text)  # 引用证据（JSON字符串）
    evaluation = Column(Text)  # 评估结果（JSON字符串）
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 记录创建时间
    
    def get_evidence_list(self):
        if self.evidence:
            return json.loads(self.evidence)
        return []

    def set_evidence_list(self, evidence_list):
        self.evidence = json.dumps(evidence_list, ensure_ascii=False)

    def get_evaluation_dict(self):
        if self.evaluation:
            return json.loads(self.evaluation)
        return None

    def set_evaluation_dict(self, evaluation_dict):
        self.evaluation = json.dumps(evaluation_dict, ensure_ascii=False)

    evidence_list = property(get_evidence_list, set_evidence_list)
    evaluation_dict = property(get_evaluation_dict, set_evaluation_dict)
