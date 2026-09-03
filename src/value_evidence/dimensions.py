"""Product-agnostic value dimensions for the VEF claim chain.

Each dimension captures an independent, typed value contribution with its own
evidence basis. Products populate dimension inputs when exporting claims;
the framework validates, calculates, and renders them without product-specific
knowledge.

Dimension types:
  - inference_cost_avoided
  - infrastructure_cost_avoided
  - human_operational_cost_avoided
  - incident_response_value
  - downstream_business_impact
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


VALID_EVIDENCE_BASES = {"observed", "estimated", "industry_benchmark"}
VALID_CONFIDENCES = {"unverified", "low", "medium", "high"}
VALID_DIMENSION_TYPES = frozenset({
    "inference_cost_avoided",
    "infrastructure_cost_avoided",
    "human_operational_cost_avoided",
    "incident_response_value",
    "downstream_business_impact",
    "human_cost_of_ownership",
    "organizational_knowledge_value",
})

DIMENSION_DEFAULTS: dict[str, dict[str, Any]] = {
    "infrastructure_cost_avoided": {
        "cost_per_kwh": {"value": 0.10, "source": "US EIA commercial average 2025"},
        "pue_factor": {"value": 1.2, "source": "Uptime Institute global average 2024"},
        "amortization_years": {"value": 3, "source": "typical server refresh cycle"},
    },
    "human_operational_cost_avoided": {
        "avg_triage_minutes_per_signal": {
            "value": 3.0,
            "source": "PagerDuty State of Digital Operations 2024",
        },
        "avg_investigation_minutes_per_signal": {
            "value": 15.0,
            "source": "Gartner IT operations benchmark",
        },
        "loaded_hourly_rate_usd": {
            "value": 85.0,
            "source": "blended SRE/platform-eng rate, Gartner 2024",
        },
        "human_touch_rate": {
            "value": 0.30,
            "source": "fraction of alerts that reach a human after existing "
                      "automation (PagerDuty grouping, silence rules, runbooks); "
                      "PagerDuty 2024 reports ~70% of alerts are noise/auto-resolved",
        },
    },
    "incident_response_value": {
        "baseline_mttr_minutes": {
            "value": 60.0,
            "source": "DORA State of DevOps median MTTR",
        },
    },
    "organizational_knowledge_value": {
        "avg_decision_time_saved_minutes": {
            "value": 15.0,
            "source": "McKinsey knowledge worker productivity — avg time to find "
                      "relevant institutional context for a decision",
        },
        "onboarding_weeks_baseline": {
            "value": 12.0,
            "source": "SHRM 2024 — median time to full productivity for "
                      "technical roles",
        },
        "knowledge_loss_per_departure_usd": {
            "value": 50000.0,
            "source": "Deloitte human capital — estimated cost of institutional "
                      "knowledge loss per departing technical employee",
        },
        "annual_departure_rate": {
            "value": 0.13,
            "source": "Bureau of Labor Statistics 2024 — professional/technical "
                      "voluntary turnover rate",
        },
    },
    "human_cost_of_ownership": {
        "reskilling_cost_per_fte_usd": {
            "value": 24800.0,
            "source": "SHRM 2024 average training expenditure per displaced employee",
        },
        "transition_months": {
            "value": 6.0,
            "source": "McKinsey workforce transition report — median reskilling horizon",
        },
        "productivity_loss_during_transition": {
            "value": 0.20,
            "source": "Gallup workplace disruption research — 20% productivity dip "
                      "during role transition",
        },
        "attrition_risk": {
            "value": 0.15,
            "source": "SHRM 2024 — 15% voluntary attrition during major role changes",
        },
        "replacement_cost_factor": {
            "value": 0.50,
            "source": "SHRM 2024 — average cost-to-replace at 50% of annual salary "
                      "for technical roles",
        },
        "amortization_days": {
            "value": 365,
            "source": "annualized default — matches typical budget cycle",
        },
    },
}


class ValueDimension(ABC):
    """Base class for a single value dimension in a VEF claim."""

    dimension: str
    is_cost: bool = False

    @staticmethod
    def validate_common(data: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        dim_type = data.get("dimension")
        if dim_type not in VALID_DIMENSION_TYPES:
            errors.append(f"unknown dimension type: {dim_type}")
        if "inputs" not in data or not isinstance(data.get("inputs"), dict):
            errors.append("dimension requires an 'inputs' dict")
        basis = data.get("evidence_basis")
        if basis not in VALID_EVIDENCE_BASES:
            errors.append(f"evidence_basis must be one of {sorted(VALID_EVIDENCE_BASES)}")
        conf = data.get("confidence")
        if conf not in VALID_CONFIDENCES:
            errors.append(f"confidence must be one of {sorted(VALID_CONFIDENCES)}")
        source = data.get("source")
        if not source or not isinstance(source, str):
            errors.append("dimension requires a non-empty 'source' string")
        return errors

    @staticmethod
    @abstractmethod
    def validate_inputs(inputs: dict[str, Any]) -> list[str]:
        ...

    @staticmethod
    @abstractmethod
    def calculate(inputs: dict[str, Any]) -> float:
        ...


def _require_positive(inputs: dict, key: str, errors: list[str]) -> None:
    val = inputs.get(key)
    if val is None:
        errors.append(f"inputs.{key} is required")
    elif not isinstance(val, (int, float)) or val < 0:
        errors.append(f"inputs.{key} must be a non-negative number")


class InferenceCostAvoided(ValueDimension):
    """Model inference calls that did not happen."""

    dimension = "inference_cost_avoided"

    @staticmethod
    def validate_inputs(inputs: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        if "observed_cost_difference_usd" in inputs:
            _require_positive(inputs, "observed_cost_difference_usd", errors)
        else:
            _require_positive(inputs, "calls_avoided", errors)
            _require_positive(inputs, "cost_per_call_usd", errors)
        return errors

    @staticmethod
    def calculate(inputs: dict[str, Any]) -> float:
        if "observed_cost_difference_usd" in inputs:
            return round(float(inputs["observed_cost_difference_usd"]), 2)
        return round(
            float(inputs.get("calls_avoided", 0))
            * float(inputs.get("cost_per_call_usd", 0)),
            2,
        )


class InfrastructureCostAvoided(ValueDimension):
    """Hardware, power, or cloud API costs for inference that was not needed."""

    dimension = "infrastructure_cost_avoided"

    @staticmethod
    def validate_inputs(inputs: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        mode = inputs.get("mode", "on_prem")
        if mode == "cloud":
            _require_positive(inputs, "tokens_avoided", errors)
            _require_positive(inputs, "cloud_cost_per_1k_input_tokens_usd", errors)
        elif mode == "on_prem":
            _require_positive(inputs, "units_avoided", errors)
            _require_positive(inputs, "hardware_cost_per_unit_usd", errors)
            _require_positive(inputs, "power_watts", errors)
        else:
            errors.append("inputs.mode must be 'on_prem' or 'cloud'")
        return errors

    @staticmethod
    def calculate(inputs: dict[str, Any]) -> float:
        defaults = DIMENSION_DEFAULTS["infrastructure_cost_avoided"]
        mode = inputs.get("mode", "on_prem")

        if mode == "cloud":
            tokens = float(inputs.get("tokens_avoided", 0))
            rate = float(inputs.get("cloud_cost_per_1k_input_tokens_usd", 0))
            return round(tokens * rate / 1000, 2)

        units = float(inputs.get("units_avoided", 0))
        hw_cost = float(inputs.get("hardware_cost_per_unit_usd", 0))
        power_w = float(inputs.get("power_watts", 0))
        pue = float(inputs.get("pue_factor", defaults["pue_factor"]["value"]))
        kwh_cost = float(inputs.get("cost_per_kwh", defaults["cost_per_kwh"]["value"]))
        years = float(inputs.get(
            "amortization_years", defaults["amortization_years"]["value"],
        ))

        capex = units * hw_cost
        annual_power = units * power_w * 8760 * kwh_cost * pue / 1000
        total = capex + annual_power * years
        amortized = total / years if years else 0.0
        return round(amortized, 2)


class HumanOperationalCostAvoided(ValueDimension):
    """Engineer time not spent triaging and investigating signals."""

    dimension = "human_operational_cost_avoided"

    @staticmethod
    def validate_inputs(inputs: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        _require_positive(inputs, "signals_not_requiring_human_review", errors)
        return errors

    @staticmethod
    def calculate(inputs: dict[str, Any]) -> float:
        defaults = DIMENSION_DEFAULTS["human_operational_cost_avoided"]
        signals = float(inputs.get("signals_not_requiring_human_review", 0))
        touch_rate = float(inputs.get(
            "human_touch_rate",
            defaults["human_touch_rate"]["value"],
        ))
        triage_min = float(inputs.get(
            "avg_triage_minutes_per_signal",
            defaults["avg_triage_minutes_per_signal"]["value"],
        ))
        investigation_min = float(inputs.get(
            "avg_investigation_minutes_per_signal",
            defaults["avg_investigation_minutes_per_signal"]["value"],
        ))
        rate = float(inputs.get(
            "loaded_hourly_rate_usd",
            defaults["loaded_hourly_rate_usd"]["value"],
        ))
        effective_signals = signals * min(max(touch_rate, 0.0), 1.0)
        total_minutes = effective_signals * (triage_min + investigation_min)
        return round(total_minutes * rate / 60, 2)


class IncidentResponseValue(ValueDimension):
    """Value of faster incident detection and response."""

    dimension = "incident_response_value"

    @staticmethod
    def validate_inputs(inputs: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        _require_positive(inputs, "incident_count", errors)
        _require_positive(inputs, "improved_mttr_minutes", errors)
        _require_positive(inputs, "cost_per_minute_of_incident_usd", errors)
        baseline = inputs.get("baseline_mttr_minutes")
        improved = inputs.get("improved_mttr_minutes")
        if (isinstance(baseline, (int, float)) and isinstance(improved, (int, float))
                and improved > baseline):
            errors.append("improved_mttr_minutes must be <= baseline_mttr_minutes")
        return errors

    @staticmethod
    def calculate(inputs: dict[str, Any]) -> float:
        defaults = DIMENSION_DEFAULTS["incident_response_value"]
        baseline = float(inputs.get(
            "baseline_mttr_minutes",
            defaults["baseline_mttr_minutes"]["value"],
        ))
        improved = float(inputs.get("improved_mttr_minutes", 0))
        count = float(inputs.get("incident_count", 0))
        cost_per_min = float(inputs.get("cost_per_minute_of_incident_usd", 0))
        saved_min = max(0.0, baseline - improved)
        return round(saved_min * count * cost_per_min, 2)


class DownstreamBusinessImpact(ValueDimension):
    """SLA penalties avoided, user productivity preserved, support tickets prevented."""

    dimension = "downstream_business_impact"

    @staticmethod
    def validate_inputs(inputs: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        has_any = False
        for pair in (
            ("sla_penalty_per_breach_usd", "breaches_avoided"),
            ("user_productivity_cost_per_hour_usd", "hours_preserved"),
            ("support_ticket_cost_usd", "tickets_avoided"),
        ):
            if any(k in inputs for k in pair):
                has_any = True
                for k in pair:
                    if k in inputs:
                        _require_positive(inputs, k, errors)
        if not has_any:
            errors.append(
                "downstream_business_impact requires at least one impact pair "
                "(sla, productivity, or support)"
            )
        return errors

    @staticmethod
    def calculate(inputs: dict[str, Any]) -> float:
        total = 0.0
        total += (
            float(inputs.get("sla_penalty_per_breach_usd", 0))
            * float(inputs.get("breaches_avoided", 0))
        )
        total += (
            float(inputs.get("user_productivity_cost_per_hour_usd", 0))
            * float(inputs.get("hours_preserved", 0))
        )
        total += (
            float(inputs.get("support_ticket_cost_usd", 0))
            * float(inputs.get("tickets_avoided", 0))
        )
        return round(total, 2)


class OrganizationalKnowledgeValue(ValueDimension):
    """OKV — value of institutional knowledge that would otherwise live only
    in people's heads.

    Three value paths:
      1. Decision acceleration — time saved when anyone in the org can recall
         institutional context instead of re-investigating or asking the one
         person who knows.
      2. Onboarding acceleration — new hires reach productivity faster because
         the knowledge system has answers that used to take months to absorb.
      3. Knowledge retention — when people leave, the knowledge doesn't leave
         with them. Reduces the real cost of attrition.

    Inputs can supply any combination of the three paths. The dimension
    calculates each independently and sums them.
    """

    dimension = "organizational_knowledge_value"

    @staticmethod
    def validate_inputs(inputs: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        has_any = False
        for key in (
            "decisions_informed_per_period",
            "new_hires_per_year",
            "knowledge_consumers",
        ):
            if key in inputs:
                has_any = True
                _require_positive(inputs, key, errors)
        if not has_any:
            errors.append(
                "organizational_knowledge_value requires at least one of: "
                "decisions_informed_per_period, new_hires_per_year, "
                "knowledge_consumers"
            )
        for optional in (
            "avg_decision_time_saved_minutes",
            "loaded_hourly_rate_usd",
            "onboarding_weeks_reduction",
            "new_hire_loaded_cost_per_week_usd",
            "knowledge_consumers",
            "annual_departure_rate",
            "knowledge_loss_per_departure_usd",
            "knowledge_retention_factor",
        ):
            if optional in inputs:
                _require_positive(inputs, optional, errors)
        kr = inputs.get("knowledge_retention_factor")
        if kr is not None and (not isinstance(kr, (int, float)) or not 0 <= kr <= 1):
            errors.append(
                "inputs.knowledge_retention_factor must be between 0 and 1"
            )
        return errors

    @staticmethod
    def calculate(inputs: dict[str, Any]) -> float:
        defaults = DIMENSION_DEFAULTS["organizational_knowledge_value"]
        total = 0.0

        decisions = float(inputs.get("decisions_informed_per_period", 0))
        if decisions:
            time_saved = float(inputs.get(
                "avg_decision_time_saved_minutes",
                defaults["avg_decision_time_saved_minutes"]["value"],
            ))
            rate = float(inputs.get("loaded_hourly_rate_usd", 85.0))
            total += decisions * time_saved * rate / 60

        new_hires = float(inputs.get("new_hires_per_year", 0))
        if new_hires:
            baseline_weeks = float(inputs.get(
                "onboarding_weeks_baseline",
                defaults["onboarding_weeks_baseline"]["value"],
            ))
            reduction = float(inputs.get("onboarding_weeks_reduction", baseline_weeks * 0.25))
            weekly_cost = float(inputs.get("new_hire_loaded_cost_per_week_usd", 85.0 * 40))
            total += new_hires * reduction * weekly_cost / 365

        consumers = float(inputs.get("knowledge_consumers", 0))
        if consumers:
            departure_rate = float(inputs.get(
                "annual_departure_rate",
                defaults["annual_departure_rate"]["value"],
            ))
            loss_per_departure = float(inputs.get(
                "knowledge_loss_per_departure_usd",
                defaults["knowledge_loss_per_departure_usd"]["value"],
            ))
            retention = float(inputs.get("knowledge_retention_factor", 0.50))
            departures_per_day = consumers * departure_rate / 365
            total += departures_per_day * loss_per_departure * retention

        return round(total, 2)


class HumanCostOfOwnership(ValueDimension):
    """HCO — the human price of automation.

    Captures the reskilling investment, productivity loss during role
    transition, and expected attrition-driven replacement cost. The result
    is amortized to a per-day figure so it can be compared directly with
    the value dimensions in the same claim period.

    This is a *cost* dimension — it subtracts from gross value.
    """

    dimension = "human_cost_of_ownership"
    is_cost = True

    @staticmethod
    def validate_inputs(inputs: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        _require_positive(inputs, "fte_displaced", errors)
        _require_positive(inputs, "annual_loaded_cost_per_fte_usd", errors)
        headcount = inputs.get("current_headcount_in_function")
        if headcount is not None:
            if not isinstance(headcount, (int, float)) or headcount < 1:
                errors.append("inputs.current_headcount_in_function must be >= 1")
            fte = inputs.get("fte_displaced")
            if (isinstance(fte, (int, float)) and isinstance(headcount, (int, float))
                    and fte > headcount):
                errors.append(
                    "inputs.fte_displaced cannot exceed current_headcount_in_function"
                )
        tr = inputs.get("attrition_risk")
        if tr is not None and (not isinstance(tr, (int, float)) or not 0 <= tr <= 1):
            errors.append("inputs.attrition_risk must be between 0 and 1")
        pl = inputs.get("productivity_loss_during_transition")
        if pl is not None and (not isinstance(pl, (int, float)) or not 0 <= pl <= 1):
            errors.append(
                "inputs.productivity_loss_during_transition must be between 0 and 1"
            )
        pathway = inputs.get("reskilling_pathway")
        if pathway is not None and not isinstance(pathway, list):
            errors.append("inputs.reskilling_pathway must be a list of pathway entries")
        return errors

    @staticmethod
    def calculate(inputs: dict[str, Any]) -> float:
        defaults = DIMENSION_DEFAULTS["human_cost_of_ownership"]
        fte = float(inputs.get("fte_displaced", 0))
        annual_cost = float(inputs.get("annual_loaded_cost_per_fte_usd", 0))
        reskill = float(inputs.get(
            "reskilling_cost_per_fte_usd",
            defaults["reskilling_cost_per_fte_usd"]["value"],
        ))
        months = float(inputs.get(
            "transition_months",
            defaults["transition_months"]["value"],
        ))
        prod_loss = float(inputs.get(
            "productivity_loss_during_transition",
            defaults["productivity_loss_during_transition"]["value"],
        ))
        attrition = float(inputs.get(
            "attrition_risk",
            defaults["attrition_risk"]["value"],
        ))
        replace_factor = float(inputs.get(
            "replacement_cost_factor",
            defaults["replacement_cost_factor"]["value"],
        ))
        amort_days = float(inputs.get(
            "amortization_days",
            defaults["amortization_days"]["value"],
        ))

        reskilling_total = fte * reskill
        productivity_loss_total = (
            fte * (annual_cost / 12) * months * prod_loss
        )
        attrition_total = fte * attrition * annual_cost * replace_factor

        total_transition = reskilling_total + productivity_loss_total + attrition_total
        daily = total_transition / amort_days if amort_days else 0.0
        return round(daily, 2)

    @staticmethod
    def displacement_ratio(inputs: dict[str, Any]) -> float | None:
        """Fraction of the function's workforce affected by displacement."""
        headcount = inputs.get("current_headcount_in_function")
        fte = inputs.get("fte_displaced")
        if headcount and fte and isinstance(headcount, (int, float)):
            return round(float(fte) / float(headcount), 4)
        return None


DIMENSION_REGISTRY: dict[str, type[ValueDimension]] = {
    "inference_cost_avoided": InferenceCostAvoided,
    "infrastructure_cost_avoided": InfrastructureCostAvoided,
    "human_operational_cost_avoided": HumanOperationalCostAvoided,
    "incident_response_value": IncidentResponseValue,
    "downstream_business_impact": DownstreamBusinessImpact,
    "organizational_knowledge_value": OrganizationalKnowledgeValue,
    "human_cost_of_ownership": HumanCostOfOwnership,
}


def validate_dimension(data: dict[str, Any]) -> list[str]:
    """Validate a single value dimension dict."""
    errors = ValueDimension.validate_common(data)
    dim_type = data.get("dimension")
    cls = DIMENSION_REGISTRY.get(dim_type)  # type: ignore[arg-type]
    if cls and isinstance(data.get("inputs"), dict):
        errors.extend(cls.validate_inputs(data["inputs"]))
    return errors


def calculate_dimension(data: dict[str, Any]) -> float:
    """Calculate the USD value for a validated dimension dict."""
    cls = DIMENSION_REGISTRY[data["dimension"]]
    return cls.calculate(data["inputs"])


def validate_dimensions(dimensions: list[dict[str, Any]]) -> list[str]:
    """Validate an entire value_dimensions array."""
    errors: list[str] = []
    if not isinstance(dimensions, list):
        return ["value_dimensions must be a list"]
    for i, dim in enumerate(dimensions):
        for err in validate_dimension(dim):
            errors.append(f"value_dimensions[{i}]: {err}")
    return errors


def is_cost_dimension(dim_type: str) -> bool:
    """Return True if the dimension type is a cost (subtracts from value)."""
    cls = DIMENSION_REGISTRY.get(dim_type)
    return cls.is_cost if cls else False


def evaluate_dimensions(dimensions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Calculate value for each dimension and return enriched dicts."""
    results: list[dict[str, Any]] = []
    for dim in dimensions:
        value = calculate_dimension(dim)
        entry: dict[str, Any] = {
            "dimension": dim["dimension"],
            "value_usd": value,
            "inputs": dim["inputs"],
            "source": dim["source"],
            "confidence": dim["confidence"],
            "evidence_basis": dim["evidence_basis"],
        }
        if is_cost_dimension(dim["dimension"]):
            entry["is_cost"] = True
        if dim["dimension"] == "human_cost_of_ownership":
            ratio = HumanCostOfOwnership.displacement_ratio(dim.get("inputs", {}))
            if ratio is not None:
                entry["displacement_ratio"] = ratio
            pathway = dim.get("inputs", {}).get("reskilling_pathway")
            if pathway:
                entry["reskilling_pathway"] = pathway
        results.append(entry)
    return results
