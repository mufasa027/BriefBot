from story_engine.editorial import calculate_coverage_score

def test_calculate_coverage_score():
    assert calculate_coverage_score(1, ["BBC"]) == 40
    assert calculate_coverage_score(2, ["BBC", "Reuters"]) == 70
    assert calculate_coverage_score(3, ["BBC", "Reuters", "CNN"]) == 88
    assert calculate_coverage_score(5, ["BBC", "Reuters", "CNN", "AP", "DW"]) == 100
