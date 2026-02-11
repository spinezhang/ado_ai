"""Database session management for ADO AI Web Service."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from ado_ai_web.models.database import Base

# Database URL from environment or default to SQLite
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./ado_ai.db")

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=False,  # Set to True for SQL query logging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database - create all tables."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """
    Dependency function to get database session.

    Usage in FastAPI:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
