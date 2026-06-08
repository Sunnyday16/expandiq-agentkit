from app.runtime.guardrails import StuckDetector, cost_cap_exceeded


def test_stuck_detector_fires_on_third_identical_tool_call() -> None:
    detector = StuckDetector()

    assert not detector.record("search_docs", {"q": "repeat"})
    assert not detector.record("search_docs", {"q": "repeat"})
    assert detector.record("search_docs", {"q": "repeat"})


def test_stuck_detector_uses_tool_name_and_args() -> None:
    detector = StuckDetector()

    assert not detector.record("search_docs", {"q": "repeat"})
    assert not detector.record("fetch_doc", {"q": "repeat"})
    assert not detector.record("search_docs", {"q": "different"})


def test_cost_cap_uses_crossed_budget_semantics() -> None:
    assert not cost_cap_exceeded(0.50, 0.50)
    assert cost_cap_exceeded(0.51, 0.50)
