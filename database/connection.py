from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import DATABASE_NAME

DATABASE_URL = f"sqlite:///{DATABASE_NAME}"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


def get_session():
    return SessionLocal()


def get_connection():
    return engine.raw_connection()