import pytest
from story_engine.story import Story

@pytest.fixture
def sample_article():
    return {
        "id": 1,
        "title": "Global Markets Rally Amid Positive Economic Data",
        "summary": "Stocks surged on Monday following better-than-expected jobs reports...",
        "url": "https://example.com/markets-rally",
        "source": "BBC",
        "published": "2026-08-07T10:00:00Z",
        "category": "Economy",
        "virality_score": 80,
        "importance": 8,
        "freshness_score": 90,
    }

@pytest.fixture
def sample_story(sample_article):
    story = Story(
        story_id="test-story-123",
        story_title="Global Markets Rally",
        category="Economy",
        primary_source="BBC",
        primary_article_id=1,
        articles=[sample_article],
        first_published="2026-08-07T10:00:00Z",
        latest_update="2026-08-07T10:00:00Z"
    )
    story.overall_story_score = 85
    return story
