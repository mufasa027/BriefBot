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
        self.overall_story_score = overall_story_score if overall_story_score is not None else 0
        self.entities = entities or {
            "people": [],
            "organizations": [],
            "countries": [],
            "topics": [],
            "keywords": [],
        }
        self.status = status

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
            status=data.get("status", "new")
        )
