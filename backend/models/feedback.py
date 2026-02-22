from sqlalchemy import Column, String, Integer, Float, Text, BigInteger
from database import Base
import time

class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(String, primary_key=True, index=True)
    file_id = Column(String, nullable=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    rating = Column(Integer, default=0) # 1: Like, -1: Dislike
    comment = Column(Text, nullable=True)
    created_at = Column(Float, default=time.time)
