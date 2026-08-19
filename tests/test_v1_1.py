import pytest
from story_engine.story import Story
from story_engine.editorial_v1_1 import evaluate_story_v1_1

def test_story_serialization_v1_1():
    s = Story(
        story_id="test_123",
        story_title="Test",
        impact_score=95,
        confidence_level="HIGH"
    )
    d = s.to_dict()
    assert d["impact_score"] == 95
    assert d["confidence_level"] == "HIGH"
    
    s2 = Story.from_dict(d)
    assert s2.story_id == "test_123"
    assert s2.impact_score == 95
    assert s2.confidence_level == "HIGH"

def test_evaluate_story_v1_1_deterministic_freshness():
    # evaluate_story_v1_1 uses LLM, we can mock it or just test the freshness portion
    # Wait, mocking the AI client is better
    from unittest.mock import patch, MagicMock
    
    s = Story(story_id="test_123", latest_update="2026-08-19 10:00:00")
    
    with patch("story_engine.editorial_v1_1.get_ai_client") as mock_client:
        mock_ai = MagicMock()
        mock_client.return_value = mock_ai
        
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"impact": 80, "virality": 70, "credibility": 90, "audience_relevance": 60, "editorial_reason": "Test", "editorial_recommendation": "REVIEW"}'
        mock_ai.chat.completions.create.return_value = mock_response
        
        evaluate_story_v1_1(s)
        
        assert s.impact_score == 80
        assert s.virality_score == 70
        assert s.credibility_score == 90
        assert s.audience_relevance_score == 60
        assert s.editorial_reason == "Test"
        assert s.editorial_recommendation == "REVIEW"
        
        # Freshness is deterministic
        assert s.freshness_score is not None
        assert isinstance(s.freshness_score, int)
        
        # Weighted score check
        # impact * 0.30 + freshness * 0.20 + credibility * 0.20 + virality * 0.15 + audience_relevance * 0.15
        expected = int((80 * 0.30) + (s.freshness_score * 0.20) + (90 * 0.20) + (70 * 0.15) + (60 * 0.15))
        assert s.editorial_score == expected
