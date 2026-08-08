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

    # Multi-Metric AI Scores
    importance = Column(Integer, default=5)
    virality_score = Column(Integer, default=50)
    growth_score = Column(Integer, default=50)
    freshness_score = Column(Integer, default=50)
    final_score = Column(Integer, default=0)

    confidence = Column(Integer, default=50)
    sentiment = Column(String, default="Neutral")
    region = Column(String, default="Global")

    people = Column(Text)
    organizations = Column(Text)
    countries = Column(Text)
    topics = Column(Text)

    image_url = Column(Text)
    rendered_image_path = Column(Text)
    caption = Column(Text)
    hashtags = Column(Text)

    status = Column(String, default="new")  # new, generated, approved, rejected, posted
    generated_time = Column(String)
    approved_time = Column(String)
    rejected_time = Column(String)
    posted = Column(Integer, default=0)
    posted_time = Column(String)
    instagram_post_id = Column(String)


class StoryModel(Base):
    __tablename__ = "stories"

    id = Column(Integer, primary_key=True, index=True)
    story_id = Column(String, unique=True, nullable=False, index=True)
    story_title = Column(String, nullable=False)
    category = Column(String, default="World")
    primary_source = Column(String, nullable=False)
    primary_article_id = Column(Integer)
    supporting_sources = Column(Text)  # Comma-separated or JSON
    num_sources = Column(Integer, default=1)
    first_published = Column(String)
    latest_update = Column(String)
    overall_story_score = Column(Integer, default=0)
    articles_json = Column(Text)  # JSON serialized list of articles
    entities_json = Column(Text)   # JSON serialized entities
    rendered_image_path = Column(Text)
    caption = Column(Text)
    hashtags = Column(Text)
    status = Column(String, default="new")
    generated_time = Column(String)
    approved_time = Column(String)
    rejected_time = Column(String)
    posted = Column(Integer, default=0)
    posted_time = Column(String)
    instagram_post_id = Column(String)
