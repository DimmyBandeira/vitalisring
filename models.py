"""Modelo de dados compartilhado entre a API e o dashboard."""

import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, Column, Integer, String, DateTime, Float
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DB_PATH = os.environ.get("DB_PATH", "ring_data.sqlite")
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DB_PATH}")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})


if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def utcnow_naive() -> datetime:
    """UTC sem tzinfo, compatível com o esquema legado já persistido."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Reading(Base):
    __tablename__ = "readings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String, index=True, nullable=False)
    type = Column(String, index=True, nullable=False)  # heart_rate | spo2 | heart_rate_log
    value = Column(Float, nullable=False)
    timestamp = Column(DateTime, index=True, nullable=False)
    received_at = Column(DateTime, default=utcnow_naive)


def init_db():
    # Import tardio evita dependência circular e registra as tabelas aditivas no
    # mesmo metadata antes do create_all. A tabela readings permanece intacta.
    import webapp.models_app  # noqa: F401

    Base.metadata.create_all(bind=engine)
