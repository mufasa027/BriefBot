import uuid
from datetime import datetime


class Story:
    """
    Represents a unified News Story clustering multiple multi-source articles
    covering the same real-world event.
    """

    def __init__(
        self,
        story_id=None,
        story_title="",
        category="World",
        primary_source="",
        primary_article_id=None,
        articles=None,
        supporting_sources=None,
        first_published=None,
        latest_update=None,
        overall_story_score=0,
        entities=None,
        status="new",
        instagram_media_id=None,
        reel_video_path=None,
        publish_attempts=0,
        queued_time=None,
        publishing_time=None,
        published_time=None,
        publish_error=None,
        last_publish_attempt=None,
    ):
        self.story_id = story_id or str(uuid.uuid4())
        self.story_title = story_title
        self.category = category
        self.primary_source = primary_source
        self.primary_article_id = primary_article_id
        self.articles = articles or []
        self.supporting_sources = supporting_sources or []
        self.first_published = first_published or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.latest_update = latest_update or self.first_published
        self.overall_story_score = overall_story_score
        self.entities = entities or {
            "people": [],
            "organizations": [],
            "countries": [],
            "topics": [],
            "keywords": [],
        }
        self.status = status
        
        # Reel Publishing
        self.instagram_media_id = instagram_media_id
        self.reel_video_path = reel_video_path
        self.publish_attempts = publish_attempts
        self.queued_time = queued_time
        self.publishing_time = publishing_time
        self.published_time = published_time
        self.publish_error = publish_error
        self.last_publish_attempt = last_publish_attempt

    @property
    def num_sources(self):
        return len(set([a.get("source") for a in self.articles if a.get("source")]))

    def add_article(self, article):
        """
        Appends an article to this story cluster and updates metadata/timestamps.
        """
        art_id = article.get("id")
        existing_ids = [a.get("id") for a in self.articles if a.get("id")]
        if art_id and art_id in existing_ids:
            return

        self.articles.append(article)

        # Update supporting sources
        sources = list(set([a.get("source") for a in self.articles if a.get("source")]))
        self.supporting_sources = [s for s in sources if s != self.primary_source]

        # Update timestamps
        pub = article.get("published")
        if pub:
            if not self.first_published or pub < self.first_published:
                self.first_published = pub
            if not self.latest_update or pub > self.latest_update:
                self.latest_update = pub

        # Recalculate max overall story score across articles
        max_score = max([a.get("final_score", 0) for a in self.articles] + [self.overall_story_score])
        self.overall_story_score = max_score

    def to_dict(self):
        """
        Serializes Story object to dictionary format.
        """
        return {
            "story_id": self.story_id,
            "story_title": self.story_title,
            "category": self.category,
            "primary_source": self.primary_source,
            "primary_article_id": self.primary_article_id,
            "supporting_sources": self.supporting_sources,
            "num_sources": self.num_sources,
            "first_published": self.first_published,
            "latest_update": self.latest_update,
            "overall_story_score": self.overall_story_score,
            "articles": self.articles,
            "entities": self.entities,
            "status": self.status,
            "rendered_image_path": getattr(self, "rendered_image_path", None),
            "caption": getattr(self, "caption", None),
            "hashtags": getattr(self, "hashtags", None),
            "generated_time": getattr(self, "generated_time", None),
            "instagram_media_id": self.instagram_media_id,
            "reel_video_path": self.reel_video_path,
            "publish_attempts": self.publish_attempts,
            "queued_time": self.queued_time,
            "publishing_time": self.publishing_time,
            "published_time": self.published_time,
            "publish_error": self.publish_error,
            "last_publish_attempt": self.last_publish_attempt,
        }

    @classmethod
    def from_dict(cls, data):
        """
        Instantiates Story object from dictionary data.
        """
        return cls(
            story_id=data.get("story_id"),
            story_title=data.get("story_title", ""),
            category=data.get("category", "World"),
            primary_source=data.get("primary_source", ""),
            primary_article_id=data.get("primary_article_id"),
            articles=data.get("articles", []),
            supporting_sources=data.get("supporting_sources", []),
            first_published=data.get("first_published"),
            latest_update=data.get("latest_update"),
            overall_story_score=data.get("overall_story_score", 0),
            entities=data.get("entities", {}),
            status=data.get("status", "new"),
            instagram_media_id=data.get("instagram_media_id"),
            reel_video_path=data.get("reel_video_path"),
            publish_attempts=data.get("publish_attempts", 0),
            queued_time=data.get("queued_time"),
            publishing_time=data.get("publishing_time"),
            published_time=data.get("published_time"),
            publish_error=data.get("publish_error"),
            last_publish_attempt=data.get("last_publish_attempt"),
        )
