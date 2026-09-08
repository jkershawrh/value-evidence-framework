import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "soak-to-claim.py"
SPEC = importlib.util.spec_from_file_location("soak_to_claim", SCRIPT)
soak = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(soak)


def snapshot(phase, signals, handled, forwarded, usage_requests):
    return {
        "phase": phase,
        "timestamp": "20260904T000000Z" if phase == "start" else "20260905T000000Z",
        "stats": {
            "stats": {
                "signals_processed": signals,
                "cascade_handled": handled,
                "cascade_forwarded": forwarded,
                "fn_count": 0,
                "llm_dropped": 0,
                "llm_priority_dropped": 0,
                "ledger_writes_dropped": 0,
                "ledger_memory_events_dropped": 0,
            }
        },
        "classifier_stats": {
            "coverage": {
                "sc_authoritative": handled,
                "llm_fallback": forwarded,
                "sc_failure": 0,
                "severity_gated": 0,
                "margin_gated": 0,
            },
            "metrics": {"comparisons": forwarded, "agreements": forwarded, "disagreements": 0},
        },
        "racmaas_usage": {
            "started_at": "epoch-a",
            "totals": {
                "requests": usage_requests,
                "completed_requests": usage_requests,
                "failed_requests": 0,
                "unknown_usage_requests": 0,
                "input_tokens": usage_requests * 100,
                "output_tokens": usage_requests * 10,
                "total_tokens": usage_requests * 110,
                "inference_milliseconds": usage_requests * 20,
            },
        },
    }


def test_unpriced_soak_does_not_invent_roi_or_counterfactual():
    claim = soak.build_claim(snapshot("start", 10, 8, 2, 2), snapshot("end", 20, 16, 4, 4))
    item = claim["claims"][0]
    assert item["measurement"]["observed"] == 8
    assert item["measurement"]["unit"] == "signals_handled"
    assert item["financial_model"]["gross_value"] == "UNKNOWN"
    assert item["financial_model"]["value_dimensions"] == []
    assert item["counterfactual"]["method"] == "unmeasured"
    assert item["evidence"]["value_eligible"] is False
    assert item["evidence"]["false_suppression_rate"] is None


def test_reset_counter_remains_unknown_and_fails_safety_closed():
    start = snapshot("start", 10, 8, 2, 2)
    end = snapshot("end", 5, 4, 1, 4)
    claim = soak.build_claim(start, end)["claims"][0]
    assert claim["measurement"]["observed"] is None
    assert claim["evidence"]["dangerous_misses"] == 0
    assert claim["evidence"]["value_eligible"] is False


def test_explicit_bounded_cost_inputs_enable_calculation_but_not_silent_effort():
    start = snapshot("start", 10, 8, 2, 2)
    end = snapshot("end", 20, 16, 4, 4)
    end["cost_inputs"] = {
        "pricing": {
            "pricing_class": "approved-proxy",
            "source": "approved_rate_card",
            "input_cost_per_1k_tokens_usd": 0.0025,
            "output_cost_per_1k_tokens_usd": 0.01,
        },
        "baseline_ai_eligible_fraction": 0.5,
        "ai_eligible_fraction_basis": "observed",
        "counterfactual_method": "matched_control",
        "matched_workload": True,
        "product_share": 1.0,
        "customer_validated": True,
        "other_realization_cost_usd": 0,
        "engineering_effort": [],
    }
    claim = soak.build_claim(start, end)["claims"][0]
    assert claim["financial_model"]["gross_value"] == 0.0014
    assert claim["financial_model"]["initial_engineering_cost_usd"] is None
    assert claim["evidence"]["value_eligible"] is False
