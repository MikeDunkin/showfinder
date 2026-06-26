from sqlalchemy import Column, Integer, String, Float, Text
from app.db import Base


class CarShow(Base):
    __tablename__ = "car_shows"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    date = Column(String(50))
    venue = Column(String(255))
    city = Column(String(100))
    state = Column(String(2))
    zip_code = Column(String(10))
    lat = Column(Float)
    lng = Column(Float)
    url = Column(String(500))
    description = Column(Text)
