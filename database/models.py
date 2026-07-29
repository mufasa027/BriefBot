from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class NewsArticle(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String, nullable=False)

    source = Column(String)

    url = Column(String, unique=True)

    published = Column(String)

    summary = Column(Text)

    category = Column(String)

    status = Column(String, default="new")