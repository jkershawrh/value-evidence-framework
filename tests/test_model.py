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
