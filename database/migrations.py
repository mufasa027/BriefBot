from database.connection import engine
from database.models import Base


def create_database():
    Base.metadata.create_all(bind=engine)