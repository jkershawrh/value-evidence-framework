from value_evidence.model import evaluate_claim, evaluate_portfolio, validate_claim


def claim(**overrides):
    value = {
        "id": "p.hours-avoided", "product": "product", "outcome_id": "outcome-1",
        "value_type": "cost_avoidance", "measurement": {"observed": 10, "unit": "hours"},
        "counterfactual": {"method": "matched_control", "expected_without_product": 30},
        "attribution": {"product_share": 0.5, "competing_factors": ["training"]},
        "financial_model": {"gross_value": 1000, "currency": "USD", "customer_validated": True},
        "evidence": {"confidence": "high", "sources": ["telemetry"], "reproducible": True},
        "realization_cost": 100,
    }
    value.update(overrides)
    return value


def test_calculation_keeps_value_layers_separate():
    result = evaluate_claim(claim())
    assert result["gross_value"] == 1000
    assert result["attributable_value"] == 500
    assert result["confidence_adjusted_value"] == 425
    assert result["net_value"] == 325
    assert result["value_leverage"] == 4.25
    assert result["rating"] == "green"


def test_missing_evidence_is_rejected():
    broken = claim()
    broken["evidence"]["sources"] = []
    assert "evidence.sources must contain at least one source" in validate_claim(broken)


def test_portfolio_refuses_double_counting():
    first = claim(attribution={"product_share": 0.6, "competing_factors": ["training"]})
    second = claim(id="other", product="other",
                   attribution={"product_share": 0.6, "competing_factors": ["training"]})
    try:
        evaluate_portfolio([first, second])
        assert False, "expected attribution collision"
    except ValueError as exc:
        assert "exceeds 100%" in str(exc)


def test_weak_counterfactual_cannot_be_green():
    weak = claim(counterfactual={"method": "expert_estimate", "expected_without_product": 30})
    result = evaluate_claim(weak)
    assert result["rating"] != "green"
    assert "counterfactual is not based on observed comparison data" in result["gaps"]


def test_route_and_effort_evidence_are_validated_and_projected():
    detailed = claim()
    route = {
        "total_signals": 10, "ai_eligible_signals": 6, "actual_ai_calls": 6,
        "routes": [
            {"route": "existing_rules", "signal_count": 4, "ai_eligible": False,
             "ai_calls": 0},
            {"route": "model", "signal_count": 6, "ai_eligible": True, "ai_calls": 6},
        ],
    }
    detailed["measurement"].update({
        "baseline_route_ledger": route,
        "cascade_route_ledger": route,
        "raw_inference_cost_avoided_usd": 12.5,
    })
    detailed["financial_model"].update({
        "engineering_effort": [{"lifecycle": "initial", "hours": 2,
                                "loaded_rate_usd": 100}],
        "initial_engineering_cost_usd": 200,
        "recurring_engineering_cost_usd": 50,
    })
    assert validate_claim(detailed) == []
    result = evaluate_claim(detailed)
    assert result["ai_usage"]["baseline_eligible_signals"] == 6
    assert result["ai_usage"]["avoided_inference_cost"] == 12.5
    assert result["engineering_cost"] == {"initial": 200, "recurring": 50}


def test_route_ledger_rejects_compression_as_unaccounted_savings():
    detailed = claim()
    detailed["measurement"]["baseline_route_ledger"] = {
        "total_signals": 10, "actual_ai_calls": 6,
        "routes": [{"route": "model", "signal_count": 6, "ai_eligible": True,
                    "ai_calls": 6}],
    }
    errors = validate_claim(detailed)
    assert "measurement.baseline_route_ledger routes must partition total_signals" in errors


# --- value_dimensions integration ---

def test_claim_without_dimensions_still_works():
    """Backward compat: claims with no value_dimensions evaluate as before."""
    result = evaluate_claim(claim())
    assert "value_dimensions" not in result
    assert result["gross_value"] == 1000


def test_claim_with_dimensions_includes_breakdown():
    c = claim()
    c["financial_model"]["value_dimensions"] = [
        {
            "dimension": "inference_cost_avoided",
            "inputs": {"calls_avoided": 470, "cost_per_call_usd": 0.10},
            "source": "replay",
            "confidence": "medium",
            "evidence_basis": "observed",
        },
        {
            "dimension": "human_operational_cost_avoided",
            "inputs": {"signals_not_requiring_human_review": 470},
            "source": "pilot_work_log",
            "confidence": "medium",
            "evidence_basis": "estimated",
        },
    ]
    errors = validate_claim(c)
    assert errors == []
    result = evaluate_claim(c)
    assert "value_dimensions" in result
    assert len(result["value_dimensions"]) == 2
    assert result["value_dimensions"][0]["dimension"] == "inference_cost_avoided"
    assert result["value_dimensions"][0]["value_usd"] == 47.0
    assert result["value_dimensions"][1]["value_usd"] > 0


def test_claim_with_invalid_dimensions_rejected():
    c = claim()
    c["financial_model"]["value_dimensions"] = [
        {
            "dimension": "inference_cost_avoided",
            "inputs": {},
            "source": "test",
            "confidence": "medium",
            "evidence_basis": "observed",
        },
    ]
    errors = validate_claim(c)
    assert any("value_dimensions[0]" in e for e in errors)


def test_portfolio_with_dimensions():
    c = claim()
    c["financial_model"]["value_dimensions"] = [
        {
            "dimension": "inference_cost_avoided",
            "inputs": {"observed_cost_difference_usd": 500.0},
            "source": "replay",
            "confidence": "high",
            "evidence_basis": "observed",
        },
    ]
    portfolio = evaluate_portfolio([c])
    assert portfolio["claims"][0]["value_dimensions"][0]["value_usd"] == 500.0
