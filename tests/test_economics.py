"""Tests for value_evidence.economics — BusinessEconomics composition,
backward compatibility, and financial model building."""

from value_evidence.economics import (
    build_financial_model,
    validate_business_economics,
)


def test_flat_input_backward_compat():
    economics = {
        "model_call_cost_usd": 0.10,
        "other_realization_cost_usd": 5.00,
        "customer_validated": True,
        "engineering_effort": [
            {"activity": "rule_authoring", "role": "platform_engineer",
             "hours": 0.20, "loaded_rate_usd": 100.0, "lifecycle": "initial",
             "source": "pilot_work_log"},
        ],
    }
    assert validate_business_economics(economics) == []
    model, cost = build_financial_model(economics, calls_avoided=470)
    assert model["gross_value"] == 47.0
    assert model["model_call_cost_usd"] == 0.10
    assert model["cost_basis"] == "average_call_cost"
    assert len(model["value_dimensions"]) == 1
    assert model["value_dimensions"][0]["dimension"] == "inference_cost_avoided"
    assert cost == 25.0  # 5 + 20


def test_flat_input_with_observed_cost():
    economics = {"model_call_cost_usd": 0.10}
    model, _ = build_financial_model(economics, observed_cost_difference_usd=46.0)
    assert model["gross_value"] == 46.0
    assert model["cost_basis"] == "observed_route_cost"


def test_dimensions_input():
    economics = {
        "value_dimensions": [
            {
                "dimension": "inference_cost_avoided",
                "inputs": {"calls_avoided": 470, "cost_per_call_usd": 0.10},
                "source": "replay",
                "confidence": "medium",
                "evidence_basis": "observed",
            },
            {
                "dimension": "human_operational_cost_avoided",
                "inputs": {
                    "signals_not_requiring_human_review": 470,
                    "avg_triage_minutes_per_signal": 3,
                    "avg_investigation_minutes_per_signal": 15,
                    "loaded_hourly_rate_usd": 85,
                },
                "source": "pilot_work_log",
                "confidence": "medium",
                "evidence_basis": "estimated",
            },
        ],
        "other_realization_cost_usd": 10.0,
        "engineering_effort": [],
    }
    assert validate_business_economics(economics) == []
    model, cost = build_financial_model(economics)
    assert len(model["value_dimensions"]) == 2
    assert model["gross_value"] == sum(d["value_usd"] for d in model["value_dimensions"])
    assert model["gross_value"] > 47.0  # inference + human cost
    assert cost == 10.0


def test_requires_either_dimensions_or_flat():
    errors = validate_business_economics({"other_realization_cost_usd": 5.0})
    assert any("requires either" in e for e in errors)


def test_validates_engineering_effort():
    economics = {
        "model_call_cost_usd": 0.10,
        "engineering_effort": [
            {"activity": "", "role": "eng", "hours": 1, "loaded_rate_usd": 100,
             "lifecycle": "initial", "source": "log"},
        ],
    }
    errors = validate_business_economics(economics)
    assert any("activity" in e for e in errors)


def test_negative_realization_cost():
    economics = {
        "model_call_cost_usd": 0.10,
        "other_realization_cost_usd": -5.0,
    }
    errors = validate_business_economics(economics)
    assert any("non-negative" in e for e in errors)


def test_engineering_effort_cost_calculation():
    economics = {
        "model_call_cost_usd": 0.10,
        "other_realization_cost_usd": 5.0,
        "engineering_effort": [
            {"activity": "rule_authoring", "role": "eng", "hours": 0.2,
             "loaded_rate_usd": 100, "lifecycle": "initial", "source": "log"},
            {"activity": "drift_review", "role": "eng", "hours": 0.1,
             "loaded_rate_usd": 100, "lifecycle": "recurring", "source": "log"},
        ],
    }
    model, cost = build_financial_model(economics, calls_avoided=100)
    assert model["initial_engineering_cost_usd"] == 20.0
    assert model["recurring_engineering_cost_usd"] == 10.0
    assert cost == 35.0  # 5 + 20 + 10
