import os
import pytest
import numpy as np
from PIL import Image
from designer.image import get_cropped_face_positions, detect_faces, fit_image
from designer.renderer import render
from services.storage_service import validate_story_assets

def test_truth_value_fix_detect_faces(monkeypatch):
    """Test that if detect_faces returns a numpy array with multiple faces, it doesn't crash get_cropped_face_positions."""
    # Mock detect_faces to return a mock NumPy array with >1 element
    mock_faces = np.array([[10, 10, 50, 50], [100, 100, 50, 50]])
    monkeypatch.setattr("designer.image.detect_faces", lambda x: mock_faces)
    
    # Create a dummy image for PIL to open
    test_img_path = "test_faces.png"
    Image.new("RGB", (500, 500), color="white").save(test_img_path)
    
    try:
        # This used to raise "ValueError: The truth value of an array with more than one element is ambiguous"
        result = get_cropped_face_positions(test_img_path, 1080, 1920)
        assert len(result) == 2
    finally:
        if os.path.exists(test_img_path):
            os.remove(test_img_path)


def test_renderer_pipeline_success(monkeypatch, tmp_path):
    """Test that the renderer produces a valid render.png and transactional validation passes."""
    # Create a mock source image
    source_img_path = str(tmp_path / "source.png")
    Image.new("RGB", (1000, 1000), color="blue").save(source_img_path)
    
    output_img_path = str(tmp_path / "render.png")
    
    article = {
        "title": "Test Headline for Render",
        "summary": "This is a test summary for the renderer to process.",
        "category": "TECH",
        "published": "2026-01-01"
    }
    
    # Mock fonts so the test doesn't crash if fonts are missing in CI
    from PIL import ImageFont
    dummy_font = ImageFont.load_default()
    monkeypatch.setattr("PIL.ImageFont.truetype", lambda *args, **kwargs: dummy_font)
    
    # Mock the logo and fallback
    original_exists = os.path.exists
    def mock_exists(path):
        if path in [source_img_path, output_img_path]:
            return True
        return original_exists(path)
    monkeypatch.setattr("os.path.exists", mock_exists)
    
    # Run the renderer
    try:
        from designer import renderer
        monkeypatch.setattr("designer.typography.ImageFont.truetype", lambda *args, **kwargs: dummy_font)
        monkeypatch.setattr("designer.layout.ImageFont.truetype", lambda *args, **kwargs: dummy_font)
        monkeypatch.setattr("designer.renderer.ImageFont.truetype", lambda *args, **kwargs: dummy_font)

        result_path = renderer.render(article, source_img_path, output_path=output_img_path)
        
        # Verify render.png exists
        assert result_path == output_img_path
        assert os.path.exists(result_path)
        
        # Verify render.png is not empty
        assert os.path.getsize(result_path) > 100
        
        # Verify it can be opened by PIL and has correct dimensions
        with Image.open(result_path) as img:
            assert img.size == (1080, 1920)
            
        # Verify transactional validation (simulated)
        # We simulate the assets existing
        test_uuid = "test-123"
        monkeypatch.setattr("services.storage_service.get_render_path_for_uuid", lambda x: result_path)
        monkeypatch.setattr("os.path.exists", lambda x: True) # Everything exists
        monkeypatch.setattr("os.path.getsize", lambda x: 1000) # Everything is non-empty
        
        from services.storage_service import validate_story_assets
        is_valid, errors = validate_story_assets(test_uuid, result_path)
        assert is_valid is True
        assert len(errors) == 0
        
    finally:
        pass


def test_truth_value_fix_fit_image(monkeypatch, tmp_path):
    """Test fit_image with multiple faces (numpy array)."""
    mock_faces = np.array([[10, 10, 50, 50], [100, 100, 50, 50]])
    monkeypatch.setattr("designer.image.detect_faces", lambda x: mock_faces)
    
    test_img_path = str(tmp_path / "test_fit.png")
    Image.new("RGB", (500, 500), color="red").save(test_img_path)
    
    box = {"width": 1080, "height": 1920}
    
    # Should not crash
    cropped = fit_image(test_img_path, box)
    assert cropped.size == (1080, 1920)

