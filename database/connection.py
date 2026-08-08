from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path
from config import DATABASE_NAME

# Convert to an absolute POSIX path (forward slashes) which is required for 
# a robust SQLAlchemy SQLite URI across both Windows and Linux.
db_path = Path(DATABASE_NAME).resolve().as_posix()
DATABASE_URL = f"sqlite:///{db_path}"

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