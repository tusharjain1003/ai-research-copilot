import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

logger = logging.getLogger(__name__)

engine = create_engine(settings.database_url, echo=settings.debug)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Safe to call repeatedly."""
    import app.models  # noqa: F401 – ensure models are registered
    logger.info("Creating database tables ...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ready.")
