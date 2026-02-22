from sqlalchemy import Column, String, Float, DateTime, Text
from database import Base
import uuid
from datetime import datetime

class TeacherRule(Base):
    __tablename__ = "teacher_rules"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    file_id = Column(String, index=True)
    question = Column(String) # The trigger question/concept
    correction = Column(Text) # The fact/instruction
    created_at = Column(DateTime, default=datetime.now)
