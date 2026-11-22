"""
SQLAlchemy engine, session factory, and dependency for FastAPI.

Key decision: we use plain `def` endpoints (not async) because
mysql-connector-python is a blocking driver. SQLAlchemy's pool handles
connection reuse across requests. `pool_pre_ping=True` detects stale
connections after MySQL restarts.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

db_url = settings.DATABASE_URL
if "@db:" in db_url:
    try:
        import socket
        socket.gethostbyname("db")
    except socket.gaierror:
        db_url = "sqlite:///./fitness_temple.db"

engine_kwargs = {"pool_pre_ping": True}
if "sqlite" not in db_url:
    engine_kwargs.update({
        "pool_size": 10,       # fits 300-member gym traffic easily
        "max_overflow": 5,     # burst up to 15 connections
        "pool_recycle": 1800,  # recycle connections every 30 min (MySQL default wait_timeout is 28800)
    })
else:
    engine_kwargs.update({"connect_args": {"check_same_thread": False}})

engine = create_engine(db_url, **engine_kwargs)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base()


def get_db():
    """FastAPI dependency that provides a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
