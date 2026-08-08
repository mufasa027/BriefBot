from unittest.mock import patch
from services.publishing_service import publish_approved_story_as_reel

@patch('services.publishing_service._update_db_publishing_state')
@patch('services.publishing_service.generate_static_reel')
@patch('services.publishing_service.sync_approved_post_to_github')
@patch('services.publishing_service.publish_reel_to_instagram')
@patch('services.publishing_service.transition_article_status')
@patch('os.path.exists')
def test_publish_attempts_increment(mock_exists, mock_transition, mock_publish, mock_sync, mock_generate, mock_update_db):
    """Test that publish_attempts safely increments whether it is None, 0, or an integer."""
    mock_exists.return_value = True
    mock_generate.return_value = ("fake_path.mp4", None)
    mock_sync.return_value = ("http://fake/mp4", None)
    mock_publish.return_value = ("fake_ig_id", None)
    
    # 1. Test when publish_attempts is None
    article_none = {
        "status": "approved",
        "rendered_image_path": "fake.png",
        "caption": "test",
        "hashtags": "#test",
        "publish_attempts": None
    }
    publish_approved_story_as_reel(article_none)
    # _update_db_publishing_state is called as: (art_id, attempts, now_str)
    # The 2nd argument (index 1) should be 1
    mock_update_db.assert_called_with(None, 1, mock_update_db.call_args[0][2])
    
    # 2. Test when publish_attempts is 0
    article_zero = {
        "status": "approved",
        "rendered_image_path": "fake.png",
        "caption": "test",
        "hashtags": "#test",
        "publish_attempts": 0
    }
    publish_approved_story_as_reel(article_zero)
    mock_update_db.assert_called_with(None, 1, mock_update_db.call_args[0][2])
    
    # 3. Test when publish_attempts is 5
    article_five = {
        "status": "approved",
        "rendered_image_path": "fake.png",
        "caption": "test",
        "hashtags": "#test",
        "publish_attempts": 5
    }
    publish_approved_story_as_reel(article_five)
    mock_update_db.assert_called_with(None, 6, mock_update_db.call_args[0][2])
    
    # 4. Test when publish_attempts is entirely missing
    article_missing = {
        "status": "approved",
        "rendered_image_path": "fake.png",
        "caption": "test",
        "hashtags": "#test"
    }
    publish_approved_story_as_reel(article_missing)
    mock_update_db.assert_called_with(None, 1, mock_update_db.call_args[0][2])
