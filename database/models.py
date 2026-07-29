from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class NewsArticle(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)

    source = Column(String, nullable=False)

    title = Column(String, nullable=False)

    summary = Column(Text)

    url = Column(String, unique=True, nullable=False)

    published = Column(String)

    category = Column(String, default="World")

    keywords = Column(Text)

    importance = Column(Integer, default=5)

    confidence = Column(Integer, default=50)

    sentiment = Column(String, default="Neutral")

    region = Column(String, default="Global")

    people = Column(Text)

    organizations = Column(Text)

    countries = Column(Text)

    topics = Column(Text)

    image_url = Column(Text)

    status = Column(String, default="new")