"""Modelo de dados compartilhado entre a API e o dashboard."""

import os
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DB_PATH = os.environ.get("DB_PATH", "ring_data.sqlite")
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DB_PATH}")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class Reading(Base):
    __tablename__ = "readings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String, index=True, nullable=False)
    type = Column(String, index=True, nullable=False)  # heart_rate | spo2 | heart_rate_log
    value = Column(Float, nullable=False)
    timestamp = Column(DateTime, index=True, nullable=False)
    received_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)
