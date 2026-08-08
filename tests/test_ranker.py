from ai.ranker import calculate_score

def test_calculate_score():
    article = {
        'title': 'Test Article',
        'category': 'technology',
        'importance': 8,
        'confidence': 95,
        'published': '2026-08-07T10:00:00Z'
    }
    score = calculate_score(article)
    assert isinstance(score, int)
    assert 0 <= score <= 100
    
    # Test high values
    high_article = {
        'title': 'Breaking crisis tech surge',
        'category': 'technology',
        'importance': 10,
        'confidence': 100,
        'published': '2026-08-07T10:00:00Z'
    }
    high_score = calculate_score(high_article)
    assert high_score > 80
    
    # Test low values
    low_article = {
        'title': 'Standard news',
        'category': 'sports',
        'importance': 1,
        'confidence': 50,
        'published': '2026-08-01T10:00:00Z'
    }
    low_score = calculate_score(low_article)
    assert low_score < 40
