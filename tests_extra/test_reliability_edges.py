"""Additional boundary regressions; the instructor's tests remain untouched."""

from gameday_lab.cache import SemanticCache
from gameday_lab.sim.contracts import Answer, Request
from gameday_lab.slo.alerting import AlertRule, BurnRateAlerter, error_budget_report


def test_exact_slo_budget_exhaustion_freezes_releases() -> None:
    report = error_budget_report([100_000], [500], slo=0.995)
    assert report["budget_remaining"] == 0.0
    assert report["freeze_releases"] is True


def test_alert_fires_at_exact_burn_threshold() -> None:
    rule = AlertRule("boundary", "ticket", 60, 5, 1.0)
    events = BurnRateAlerter(rules=(rule,)).evaluate([1000] * 60, [5] * 60)
    assert len(events) == 1
    assert events[0].start_min == 0 and events[0].end_min == 60


def test_webhook_blocks_late_delivery_of_an_old_answer() -> None:
    cache = SemanticCache()
    request = Request("Policy?", "u1", False, "v1", (1.0, 0.0))
    old = Answer(1, "v1", ("policy",), 9.0)
    cache.invalidate("policy", 10.0)
    cache.store(request, old, 11.0)
    assert cache.lookup(request, 11.0) is None
    fresh = Answer(2, "v1", ("policy",), 12.0)
    cache.store(request, fresh, 12.0)
    hit = cache.lookup(request, 13.0)
    assert hit is not None and hit.answer == fresh
