from sqlalchemy import Column, Integer, String
from database.connections import Base

class Users(Base):
    """
    Model for users table
    """
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
