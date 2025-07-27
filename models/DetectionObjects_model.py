from sqlalchemy import Column, Integer, String, Float, ForeignKey
from database.connections import Base  # import shared Base

class DetectionObject(Base):
    """
    Model for detection_objects table
    """
    __tablename__ = 'detection_objects'

    id = Column(Integer, primary_key=True, autoincrement=True)
    prediction_uid = Column(String, ForeignKey("prediction_sessions.uid"))
    label = Column(String)
    score = Column(Float)
    box = Column(String)
