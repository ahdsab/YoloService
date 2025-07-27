from sqlalchemy import Column, String, DateTime, Integer, Float, ForeignKey
from datetime import datetime
from database.connections import Base

class PredictionSession(Base):
    """
    Model for prediction_sessions table
    """
    __tablename__ = 'prediction_sessions'
    
    uid = Column(String, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    original_image = Column(String)
    predicted_image = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"))