"""Tests for value_evidence.dimensions — each dimension type's validation,
calculation, defaults, and edge cases."""

import pytest

from value_evidence.dimensions import (
    DIMENSION_DEFAULTS,
    DIMENSION_REGISTRY,
    InferenceCostAvoided,
    InfrastructureCostAvoided,
    HumanOperationalCostAvoided,
    IncidentResponseValue,
    DownstreamBusinessImpact,
    OrganizationalKnowledgeValue,
    HumanCostOfOwnership,
    is_cost_dimension,
    validate_dimension,
    validate_dimensions,
    calculate_dimension,
    evaluate_dimensions,
)


def _dim(dimension, inputs, **overrides):
    base = {
        "dimension": dimension,
        "inputs": inputs,
        "source": "test",
        "confidence": "medium",
        "evidence_basis": "observed",
    }
    base.update(overrides)
    return base


# --- InferenceCostAvoided ---

class TestInferenceCostAvoided:
    def test_observed_cost_difference(self):
        d = _dim("inference_cost_avoided", {"observed_cost_difference_usd": 46.0})
        assert validate_dimension(d) == []
        assert calculate_dimension(d) == 46.0

    def test_calls_times_cost(self):
        d = _dim("inference_cost_avoided", {"calls_avoided": 470, "cost_per_call_usd": 0.10})
        assert validate_dimension(d) == []
        assert calculate_dimension(d) == 47.0

    def test_missing_both_paths(self):
        d = _dim("inference_cost_avoided", {})
        errors = validate_dimension(d)
        assert any("calls_avoided" in e for e in errors)

    def test_negative_cost(self):
        d = _dim("inference_cost_avoided", {"observed_cost_difference_usd": -5})
        errors = validate_dimension(d)
        assert any("non-negative" in e for e in errors)


# --- InfrastructureCostAvoided ---

class TestInfrastructureCostAvoided:
    def test_on_prem(self):
        d = _dim("infrastructure_cost_avoided", {
            "mode": "on_prem",
            "units_avoided": 1,
            "hardware_cost_per_unit_usd": 30000,
            "power_watts": 1200,
        })
        assert validate_dimension(d) == []
        value = calculate_dimension(d)
        assert value > 0

    def test_on_prem_uses_defaults(self):
        d = _dim("infrastructure_cost_avoided", {
            "mode": "on_prem",
            "units_avoided": 1,
            "hardware_cost_per_unit_usd": 30000,
            "power_watts": 1200,
        })
        value = calculate_dimension(d)
        defaults = DIMENSION_DEFAULTS["infrastructure_cost_avoided"]
        pue = defaults["pue_factor"]["value"]
        kwh = defaults["cost_per_kwh"]["value"]
        years = defaults["amortization_years"]["value"]
        capex = 30000
        annual_power = 1 * 1200 * 8760 * kwh * pue / 1000
        expected = (capex + annual_power * years) / years
        assert abs(value - round(expected, 2)) < 0.01

    def test_cloud_mode(self):
        d = _dim("infrastructure_cost_avoided", {
            "mode": "cloud",
            "tokens_avoided": 100000,
            "cloud_cost_per_1k_input_tokens_usd": 0.15,
        })
        assert validate_dimension(d) == []
        assert calculate_dimension(d) == 15.0

    def test_invalid_mode(self):
        d = _dim("infrastructure_cost_avoided", {"mode": "hybrid"})
        errors = validate_dimension(d)
        assert any("mode" in e for e in errors)


# --- HumanOperationalCostAvoided ---

class TestHumanOperationalCostAvoided:
    def test_with_defaults(self):
        d = _dim("human_operational_cost_avoided", {
            "signals_not_requiring_human_review": 470,
        })
        assert validate_dimension(d) == []
        value = calculate_dimension(d)
        defaults = DIMENSION_DEFAULTS["human_operational_cost_avoided"]
        touch_rate = defaults["human_touch_rate"]["value"]
        triage = defaults["avg_triage_minutes_per_signal"]["value"]
        investigation = defaults["avg_investigation_minutes_per_signal"]["value"]
        rate = defaults["loaded_hourly_rate_usd"]["value"]
        expected = 470 * touch_rate * (triage + investigation) * rate / 60
        assert abs(value - round(expected, 2)) < 0.01

    def test_with_explicit_inputs(self):
        d = _dim("human_operational_cost_avoided", {
            "signals_not_requiring_human_review": 100,
            "human_touch_rate": 0.50,
            "avg_triage_minutes_per_signal": 5.0,
            "avg_investigation_minutes_per_signal": 20.0,
            "loaded_hourly_rate_usd": 100.0,
        })
        assert validate_dimension(d) == []
        expected = 100 * 0.50 * 25 * 100 / 60
        assert calculate_dimension(d) == round(expected, 2)

    def test_touch_rate_one_means_all_signals(self):
        d = _dim("human_operational_cost_avoided", {
            "signals_not_requiring_human_review": 100,
            "human_touch_rate": 1.0,
            "avg_triage_minutes_per_signal": 6.0,
            "avg_investigation_minutes_per_signal": 0.0,
            "loaded_hourly_rate_usd": 60.0,
        })
        assert calculate_dimension(d) == 100 * 6 * 60 / 60  # 600.0

    def test_touch_rate_clamped(self):
        d = _dim("human_operational_cost_avoided", {
            "signals_not_requiring_human_review": 100,
            "human_touch_rate": 1.5,
            "avg_triage_minutes_per_signal": 6.0,
            "avg_investigation_minutes_per_signal": 0.0,
            "loaded_hourly_rate_usd": 60.0,
        })
        assert calculate_dimension(d) == 100 * 6 * 60 / 60  # clamped to 1.0

    def test_missing_signals(self):
        d = _dim("human_operational_cost_avoided", {})
        errors = validate_dimension(d)
        assert any("signals_not_requiring_human_review" in e for e in errors)


# --- IncidentResponseValue ---

class TestIncidentResponseValue:
    def test_basic_calculation(self):
        d = _dim("incident_response_value", {
            "incident_count": 5,
            "baseline_mttr_minutes": 60,
            "improved_mttr_minutes": 20,
            "cost_per_minute_of_incident_usd": 100,
        })
        assert validate_dimension(d) == []
        assert calculate_dimension(d) == 20000.0

    def test_uses_default_baseline(self):
        d = _dim("incident_response_value", {
            "incident_count": 1,
            "improved_mttr_minutes": 30,
            "cost_per_minute_of_incident_usd": 50,
        })
        assert validate_dimension(d) == []
        value = calculate_dimension(d)
        expected = (60 - 30) * 1 * 50
        assert value == expected

    def test_improved_greater_than_baseline_rejected(self):
        d = _dim("incident_response_value", {
            "incident_count": 1,
            "baseline_mttr_minutes": 30,
            "improved_mttr_minutes": 60,
            "cost_per_minute_of_incident_usd": 100,
        })
        errors = validate_dimension(d)
        assert any("improved_mttr" in e for e in errors)


# --- DownstreamBusinessImpact ---

class TestDownstreamBusinessImpact:
    def test_sla_only(self):
        d = _dim("downstream_business_impact", {
            "sla_penalty_per_breach_usd": 10000,
            "breaches_avoided": 3,
        })
        assert validate_dimension(d) == []
        assert calculate_dimension(d) == 30000.0

    def test_all_three_impacts(self):
        d = _dim("downstream_business_impact", {
            "sla_penalty_per_breach_usd": 5000,
            "breaches_avoided": 2,
            "user_productivity_cost_per_hour_usd": 75,
            "hours_preserved": 40,
            "support_ticket_cost_usd": 25,
            "tickets_avoided": 100,
        })
        assert validate_dimension(d) == []
        expected = 5000 * 2 + 75 * 40 + 25 * 100
        assert calculate_dimension(d) == expected

    def test_requires_at_least_one_pair(self):
        d = _dim("downstream_business_impact", {})
        errors = validate_dimension(d)
        assert any("at least one impact pair" in e for e in errors)


# --- OrganizationalKnowledgeValue (OKV) ---

class TestOrganizationalKnowledgeValue:
    def test_decision_acceleration_only(self):
        d = _dim("organizational_knowledge_value", {
            "decisions_informed_per_period": 10,
            "avg_decision_time_saved_minutes": 15,
            "loaded_hourly_rate_usd": 90,
        })
        assert validate_dimension(d) == []
        expected = 10 * 15 * 90 / 60  # 225.0
        assert calculate_dimension(d) == expected

    def test_onboarding_only(self):
        d = _dim("organizational_knowledge_value", {
            "new_hires_per_year": 4,
            "onboarding_weeks_reduction": 3,
            "new_hire_loaded_cost_per_week_usd": 3400,
        })
        assert validate_dimension(d) == []
        expected = round(4 * 3 * 3400 / 365, 2)
        assert calculate_dimension(d) == expected

    def test_knowledge_retention_only(self):
        d = _dim("organizational_knowledge_value", {
            "knowledge_consumers": 20,
            "annual_departure_rate": 0.13,
            "knowledge_loss_per_departure_usd": 50000,
            "knowledge_retention_factor": 0.50,
        })
        assert validate_dimension(d) == []
        departures_per_day = 20 * 0.13 / 365
        expected = round(departures_per_day * 50000 * 0.50, 2)
        assert calculate_dimension(d) == expected

    def test_all_three_paths(self):
        d = _dim("organizational_knowledge_value", {
            "decisions_informed_per_period": 5,
            "avg_decision_time_saved_minutes": 10,
            "loaded_hourly_rate_usd": 85,
            "new_hires_per_year": 2,
            "onboarding_weeks_reduction": 3,
            "new_hire_loaded_cost_per_week_usd": 3400,
            "knowledge_consumers": 15,
            "knowledge_retention_factor": 0.40,
        })
        assert validate_dimension(d) == []
        value = calculate_dimension(d)
        assert value > 0

    def test_requires_at_least_one_path(self):
        d = _dim("organizational_knowledge_value", {})
        errors = validate_dimension(d)
        assert any("at least one" in e for e in errors)

    def test_uses_defaults_for_optional_fields(self):
        d = _dim("organizational_knowledge_value", {
            "decisions_informed_per_period": 10,
        })
        assert validate_dimension(d) == []
        defaults = DIMENSION_DEFAULTS["organizational_knowledge_value"]
        time_saved = defaults["avg_decision_time_saved_minutes"]["value"]
        expected = round(10 * time_saved * 85.0 / 60, 2)
        assert calculate_dimension(d) == expected

    def test_invalid_retention_factor(self):
        d = _dim("organizational_knowledge_value", {
            "knowledge_consumers": 10,
            "knowledge_retention_factor": 1.5,
        })
        errors = validate_dimension(d)
        assert any("knowledge_retention_factor" in e for e in errors)

    def test_is_not_cost_dimension(self):
        assert OrganizationalKnowledgeValue.is_cost is False
        assert is_cost_dimension("organizational_knowledge_value") is False


# --- HumanCostOfOwnership (HCO) ---

class TestHumanCostOfOwnership:
    def test_basic_calculation(self):
        d = _dim("human_cost_of_ownership", {
            "fte_displaced": 1.0,
            "annual_loaded_cost_per_fte_usd": 120000,
        })
        assert validate_dimension(d) == []
        value = calculate_dimension(d)
        assert value > 0
        # Verify it's a daily amortized figure
        defaults = DIMENSION_DEFAULTS["human_cost_of_ownership"]
        reskill = defaults["reskilling_cost_per_fte_usd"]["value"]
        months = defaults["transition_months"]["value"]
        prod_loss = defaults["productivity_loss_during_transition"]["value"]
        attrition = defaults["attrition_risk"]["value"]
        replace_factor = defaults["replacement_cost_factor"]["value"]
        total = (
            1.0 * reskill
            + 1.0 * (120000 / 12) * months * prod_loss
            + 1.0 * attrition * 120000 * replace_factor
        )
        expected_daily = round(total / 365, 2)
        assert value == expected_daily

    def test_fractional_fte(self):
        d = _dim("human_cost_of_ownership", {
            "fte_displaced": 0.1,
            "annual_loaded_cost_per_fte_usd": 100000,
        })
        assert validate_dimension(d) == []
        value = calculate_dimension(d)
        # 10% of one person — should be ~10% of the full FTE cost
        full_d = _dim("human_cost_of_ownership", {
            "fte_displaced": 1.0,
            "annual_loaded_cost_per_fte_usd": 100000,
        })
        full_value = calculate_dimension(full_d)
        assert abs(value - round(full_value * 0.1, 2)) <= 0.01

    def test_explicit_overrides(self):
        d = _dim("human_cost_of_ownership", {
            "fte_displaced": 2.0,
            "annual_loaded_cost_per_fte_usd": 100000,
            "reskilling_cost_per_fte_usd": 10000,
            "transition_months": 3,
            "productivity_loss_during_transition": 0.30,
            "attrition_risk": 0.10,
            "replacement_cost_factor": 0.40,
            "amortization_days": 365,
        })
        assert validate_dimension(d) == []
        total = (
            2 * 10000                          # reskilling
            + 2 * (100000 / 12) * 3 * 0.30    # productivity loss
            + 2 * 0.10 * 100000 * 0.40        # attrition
        )
        expected = round(total / 365, 2)
        assert calculate_dimension(d) == expected

    def test_is_cost_flag(self):
        assert HumanCostOfOwnership.is_cost is True
        assert is_cost_dimension("human_cost_of_ownership") is True
        assert is_cost_dimension("inference_cost_avoided") is False

    def test_missing_required_fields(self):
        d = _dim("human_cost_of_ownership", {})
        errors = validate_dimension(d)
        assert any("fte_displaced" in e for e in errors)
        assert any("annual_loaded_cost_per_fte_usd" in e for e in errors)

    def test_invalid_attrition_risk(self):
        d = _dim("human_cost_of_ownership", {
            "fte_displaced": 1.0,
            "annual_loaded_cost_per_fte_usd": 100000,
            "attrition_risk": 1.5,
        })
        errors = validate_dimension(d)
        assert any("attrition_risk" in e for e in errors)

    def test_evaluate_includes_is_cost(self):
        dims = [
            _dim("inference_cost_avoided", {"observed_cost_difference_usd": 46.0}),
            _dim("human_cost_of_ownership", {
                "fte_displaced": 0.5,
                "annual_loaded_cost_per_fte_usd": 100000,
            }),
        ]
        results = evaluate_dimensions(dims)
        assert len(results) == 2
        assert "is_cost" not in results[0]
        assert results[1]["is_cost"] is True
        assert results[1]["value_usd"] > 0


# --- Common validation ---

class TestCommonValidation:
    def test_unknown_dimension_type(self):
        d = _dim("unknown_type", {})
        errors = validate_dimension(d)
        assert any("unknown dimension type" in e for e in errors)

    def test_missing_inputs(self):
        d = {"dimension": "inference_cost_avoided", "source": "test",
             "confidence": "medium", "evidence_basis": "observed"}
        errors = validate_dimension(d)
        assert any("inputs" in e for e in errors)

    def test_bad_evidence_basis(self):
        d = _dim("inference_cost_avoided", {"calls_avoided": 1, "cost_per_call_usd": 1},
                 evidence_basis="made_up")
        errors = validate_dimension(d)
        assert any("evidence_basis" in e for e in errors)

    def test_bad_confidence(self):
        d = _dim("inference_cost_avoided", {"calls_avoided": 1, "cost_per_call_usd": 1},
                 confidence="very_high")
        errors = validate_dimension(d)
        assert any("confidence" in e for e in errors)

    def test_missing_source(self):
        d = _dim("inference_cost_avoided", {"calls_avoided": 1, "cost_per_call_usd": 1},
                 source="")
        errors = validate_dimension(d)
        assert any("source" in e for e in errors)


# --- Array-level functions ---

class TestArrayFunctions:
    def test_validate_dimensions_propagates_index(self):
        dims = [
            _dim("inference_cost_avoided", {}),
        ]
        errors = validate_dimensions(dims)
        assert any("value_dimensions[0]" in e for e in errors)

    def test_evaluate_dimensions(self):
        dims = [
            _dim("inference_cost_avoided", {"calls_avoided": 100, "cost_per_call_usd": 0.50}),
            _dim("human_operational_cost_avoided", {
                "signals_not_requiring_human_review": 50,
                "human_touch_rate": 0.30,
                "avg_triage_minutes_per_signal": 3,
                "avg_investigation_minutes_per_signal": 15,
                "loaded_hourly_rate_usd": 85,
            }),
        ]
        results = evaluate_dimensions(dims)
        assert len(results) == 2
        assert results[0]["value_usd"] == 50.0
        assert results[0]["dimension"] == "inference_cost_avoided"
        assert results[1]["value_usd"] > 0
        assert results[1]["evidence_basis"] == "observed"

    def test_registry_covers_all_types(self):
        from value_evidence.dimensions import VALID_DIMENSION_TYPES
        assert set(DIMENSION_REGISTRY.keys()) == VALID_DIMENSION_TYPES
