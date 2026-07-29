from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import DATABASE_NAME

DATABASE_URL = f"sqlite:///{DATABASE_NAME}"

engine = create_engine(
    DATABASE_URL,
    echo=False
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)