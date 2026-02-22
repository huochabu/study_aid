from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from sqlalchemy.sql import func
from database import Base
import json

class AnalysisHistory(Base):
    """分析历史记录模型"""
    __tablename__ = "analysis_history"
    
    id = Column(String, primary_key=True, index=True)  # 历史记录ID
    file_id = Column(String, index=True)  # 文件ID
    filename = Column(String)  # 文件名
    analysis_time = Column(Float)  # 分析时间（时间戳）
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 记录创建时间
    result = Column(Text)  # 分析结果（JSON字符串）
    
    def get_result_dict(self):
        """将result字段从JSON字符串转换为字典"""
        if self.result:
            return json.loads(self.result)
        return {}
    
    def set_result_dict(self, result_dict):
        """将字典转换为JSON字符串设置到result字段"""
        self.result = json.dumps(result_dict, ensure_ascii=False)
    
    # 创建属性，方便使用
    result_dict = property(get_result_dict, set_result_dict)

class FileTextStore(Base):
    """文件文本存储模型"""
    __tablename__ = "file_text_store"
    
    file_id = Column(String, primary_key=True, index=True)
    original_filename = Column(String)  # 原始文件名
    text = Column(Text)  # 提取的文本
    chunks = Column(Text)  # 文本块（JSON字符串）
    keywords = Column(Text)  # 关键词（JSON字符串）
    layout_data = Column(Text) # [NEW] 布局信息 (JSON字符串: PDF坐标/OCR Box)
    upload_time = Column(Float)  # 上传时间（时间戳）
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 记录创建时间
    
    def get_chunks_list(self):
        """将chunks字段从JSON字符串转换为列表"""
        if self.chunks:
            return json.loads(self.chunks)
        return []
    
    def set_chunks_list(self, chunks_list):
        """将列表转换为JSON字符串设置到chunks字段"""
        self.chunks = json.dumps(chunks_list, ensure_ascii=False)

    def get_layout_data_json(self):
        """获取布局数据"""
        if self.layout_data:
            return json.loads(self.layout_data)
        return None

    def set_layout_data_json(self, data):
        """设置布局数据"""
        self.layout_data = json.dumps(data, ensure_ascii=False)
    
    def get_keywords_list(self):
        """将keywords字段从JSON字符串转换为列表"""
        if self.keywords:
            return json.loads(self.keywords)
        return []
    
    def set_keywords_list(self, keywords_list):
        """将列表转换为JSON字符串设置到keywords字段"""
        self.keywords = json.dumps(keywords_list, ensure_ascii=False)
    
    # 创建属性，方便使用
    chunks_list = property(get_chunks_list, set_chunks_list)
    keywords_list = property(get_keywords_list, set_keywords_list)
    layout_info = property(get_layout_data_json, set_layout_data_json) # [NEW]

# 导入视频处理相关的模型
from .document import BilibiliLoader
from .llm import SimpleLLM
from .qa_history import QAHistory # [NEW]

class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class LearningPlan(Base):
    """学习计划模型"""
    __tablename__ = "learning_plans"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True)
    title = Column(String)
    description = Column(Text)
    start_date = Column(Float)
    end_date = Column(Float)
    status = Column(String)  # active, completed, paused
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class LearningModule(Base):
    """学习模块模型"""
    __tablename__ = "learning_modules"
    
    id = Column(String, primary_key=True, index=True)
    plan_id = Column(String, index=True)
    title = Column(String)
    description = Column(Text)
    order_index = Column(Integer)
    estimated_time = Column(Integer)  # 预计学习时间（分钟）

class LearningProgress(Base):
    """学习进度模型"""
    __tablename__ = "learning_progress"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True)
    module_id = Column(String, index=True)
    plan_id = Column(String, index=True)
    progress = Column(Integer)  # 进度百分比
    completed_at = Column(Float)
    last_updated = Column(Float)

class Note(Base):
    """笔记模型"""
    __tablename__ = "notes"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True)
    module_id = Column(String, index=True)
    content = Column(Text)
    title = Column(String)
    tags = Column(Text)  # JSON字符串
    created_at = Column(Float)
    updated_at = Column(Float)

class Quiz(Base):
    """测验模型"""
    __tablename__ = "quizzes"
    
    id = Column(String, primary_key=True, index=True)
    module_id = Column(String, index=True)
    title = Column(String)
    description = Column(Text)
    time_limit = Column(Integer)  # 时间限制（分钟）

class Question(Base):
    """问题模型"""
    __tablename__ = "questions"
    
    id = Column(String, primary_key=True, index=True)
    quiz_id = Column(String, index=True)
    content = Column(Text)
    question_type = Column(String)  # multiple_choice, true_false, short_answer
    options = Column(Text)  # JSON字符串，存储选项
    correct_answer = Column(Text)
    points = Column(Integer)

class QuizAttempt(Base):
    """测验尝试模型"""
    __tablename__ = "quiz_attempts"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True)
    quiz_id = Column(String, index=True)
    score = Column(Integer)
    total_points = Column(Integer)
    completed_at = Column(Float)
    answers = Column(Text)  # JSON字符串，存储用户答案

class LearningAnalytics(Base):
    """学习分析模型"""
    __tablename__ = "learning_analytics"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True)
    module_id = Column(String, index=True)
    activity_type = Column(String)  # study, quiz, note
    duration = Column(Integer)  # 持续时间（秒）
    timestamp = Column(Float)
    extra_metadata = Column(Text)  # JSON字符串，存储额外信息

class Collaboration(Base):
    """协作学习模型"""
    __tablename__ = "collaborations"
    
    id = Column(String, primary_key=True, index=True)
    plan_id = Column(String, index=True)
    user_id = Column(String, index=True)
    role = Column(String)  # owner, contributor
    joined_at = Column(Float)

class LearningPreference(Base):
    """学习偏好模型"""
    __tablename__ = "learning_preferences"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True)
    learning_style = Column(String)  # visual, auditory, kinesthetic, read_write
    preferred_difficulty = Column(String)  # easy, medium, hard
    study_time_preference = Column(String)  # morning, afternoon, evening
    goals = Column(Text)  # JSON字符串，存储学习目标
    created_at = Column(Float)
    updated_at = Column(Float)

class LearningBehavior(Base):
    """学习行为模型"""
    __tablename__ = "learning_behaviors"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True)
    module_id = Column(String, index=True)
    behavior_type = Column(String)  # view, study, quiz, pause, resume
    duration = Column(Integer)  # 持续时间（秒）
    timestamp = Column(Float)
    extra_metadata = Column(Text)  # JSON字符串，存储额外信息

class LearningPrediction(Base):
    """学习预测模型"""
    __tablename__ = "learning_predictions"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True)
    module_id = Column(String, index=True)
    predicted_completion_time = Column(Float)  # 预测完成时间
    difficulty_prediction = Column(String)  # 预测难度
    success_probability = Column(Float)  # 成功概率
    created_at = Column(Float)
