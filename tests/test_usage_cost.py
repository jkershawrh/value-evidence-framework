from value_evidence.usage_cost import (
    bounded_counter_delta,
    bounded_usage_delta,
    estimated_avoided_token_cost_usd,
    token_cost_usd,
)


def snapshot(*, started_at="epoch-a", requests=0, unknown=0, failed=0):
    return {
        "captured_at": "2026-09-01T00:00:00Z",
        "started_at": started_at,
        "totals": {
            "requests": requests,
            "completed_requests": requests - failed,
            "failed_requests": failed,
            "unknown_usage_requests": unknown,
            "input_tokens": requests * 100,
            "output_tokens": requests * 10,
            "total_tokens": requests * 110,
            "inference_milliseconds": requests * 20,
        },
    }


def pricing():
    return {
        "pricing_class": "approved-proxy",
        "source": "approved_rate_card",
        "input_cost_per_1k_tokens_usd": 0.0025,
        "output_cost_per_1k_tokens_usd": 0.01,
    }


def test_missing_and_reset_counters_remain_unknown():
    assert bounded_counter_delta({}, {"calls": 2}, ("calls",))["calls"] is None
    assert bounded_counter_delta({"calls": 4}, {"calls": 2}, ("calls",))["calls"] is None


def test_bounded_usage_requires_same_epoch_and_complete_work():
    good = bounded_usage_delta(snapshot(requests=10), snapshot(requests=12))
    assert good["usage_complete"] is True
    assert good["totals"]["requests"] == 2

    reset = bounded_usage_delta(snapshot(), snapshot(started_at="epoch-b", requests=2))
    assert reset["usage_complete"] is False
    assert reset["ledger_epoch"] is None

    unknown = bounded_usage_delta(snapshot(), snapshot(requests=2, unknown=1))
    assert unknown["usage_complete"] is False


def test_token_cost_requires_complete_usage_and_named_pricing():
    usage = bounded_usage_delta(snapshot(requests=10), snapshot(requests=12))
    assert token_cost_usd(usage, pricing()) == 0.0007
    usage["usage_complete"] = False
    assert token_cost_usd(usage, pricing()) is None
    assert token_cost_usd({**usage, "usage_complete": True}, {}) is None


def test_avoided_cost_requires_explicit_ai_eligible_fraction():
    assert (
        estimated_avoided_token_cost_usd(
            handled_signals=1000,
            baseline_ai_eligible_fraction=None,
            average_input_tokens=100,
            average_output_tokens=10,
            pricing=pricing(),
        )
        is None
    )
    assert (
        estimated_avoided_token_cost_usd(
            handled_signals=1000,
            baseline_ai_eligible_fraction=0.3,
            average_input_tokens=100,
            average_output_tokens=10,
            pricing=pricing(),
        )
        == 0.105
    )
