"""Pure calculation kernel. Inputs remain plain dictionaries for portable contracts."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

CONFIDENCE_FACTORS = {"unverified": Decimal("0"), "low": Decimal("0.25"),
                      "medium": Decimal("0.60"), "high": Decimal("0.85")}
METHOD_STRENGTH = {"assertion": 0, "expert_estimate": 1, "modeled_baseline": 2,
                   "historical_baseline": 3, "interrupted_time_series": 4,
                   "difference_in_differences": 5, "matched_control": 6,
                   "randomized_or_phased": 7}

REQUIRED = ("id", "product", "outcome_id", "value_type", "measurement",
            "counterfactual", "attribution", "financial_model", "evidence", "realization_cost")


def validate_claim(claim: dict[str, Any]) -> list[str]:
    errors = [f"missing required field: {key}" for key in REQUIRED if key not in claim]
    if errors:
        return errors
    share = Decimal(str(claim["attribution"].get("product_share", -1)))
    if not Decimal("0") <= share <= Decimal("1"):
        errors.append("attribution.product_share must be between 0 and 1")
    confidence = claim["evidence"].get("confidence")
    if confidence not in CONFIDENCE_FACTORS:
        errors.append(f"unknown evidence confidence: {confidence}")
    method = claim["counterfactual"].get("method")
    if method not in METHOD_STRENGTH:
        errors.append(f"unknown counterfactual method: {method}")
    for field in ("gross_value",):
        if Decimal(str(claim["financial_model"].get(field, -1))) < 0:
            errors.append(f"financial_model.{field} must be non-negative")
    if Decimal(str(claim.get("realization_cost", -1))) < 0:
        errors.append("realization_cost must be non-negative")
    if not claim["evidence"].get("sources"):
        errors.append("evidence.sources must contain at least one source")
    return errors


def _rating(claim: dict[str, Any]) -> tuple[str, list[str]]:
    gaps: list[str] = []
    method = claim["counterfactual"]["method"]
    confidence = claim["evidence"]["confidence"]
    if METHOD_STRENGTH[method] < METHOD_STRENGTH["historical_baseline"]:
        gaps.append("counterfactual is not based on observed comparison data")
    if confidence in {"unverified", "low"}:
        gaps.append("evidence confidence is below medium")
    if not claim["financial_model"].get("customer_validated", False):
        gaps.append("financial assumptions are not customer-validated")
    if not claim["evidence"].get("reproducible", False):
        gaps.append("calculation is not independently reproducible")
    if not claim["attribution"].get("competing_factors"):
        gaps.append("competing explanations are not recorded")
    if not gaps and METHOD_STRENGTH[method] >= METHOD_STRENGTH["matched_control"] and confidence == "high":
        return "green", gaps
    if len(gaps) <= 2 and confidence != "unverified":
        return "amber", gaps
    return "red", gaps


def evaluate_claim(claim: dict[str, Any]) -> dict[str, Any]:
    errors = validate_claim(claim)
    if errors:
        raise ValueError("; ".join(errors))
    gross = Decimal(str(claim["financial_model"]["gross_value"]))
    share = Decimal(str(claim["attribution"]["product_share"]))
    factor = CONFIDENCE_FACTORS[claim["evidence"]["confidence"]]
    attributable = gross * share
    adjusted = attributable * factor
    cost = Decimal(str(claim["realization_cost"]))
    rating, gaps = _rating(claim)
    return {
        "id": claim["id"], "product": claim["product"], "outcome_id": claim["outcome_id"],
        "currency": claim["financial_model"].get("currency", "USD"),
        "gross_value": float(gross), "attributable_value": float(attributable),
        "confidence_adjusted_value": float(adjusted), "realization_cost": float(cost),
        "net_value": float(adjusted - cost),
        "value_leverage": float(adjusted / cost) if cost else None,
        "rating": rating, "gaps": gaps,
    }


def evaluate_portfolio(claims: list[dict[str, Any]]) -> dict[str, Any]:
    results = [evaluate_claim(claim) for claim in claims]
    shares: dict[str, Decimal] = defaultdict(Decimal)
    for claim in claims:
        shares[claim["outcome_id"]] += Decimal(str(claim["attribution"]["product_share"]))
    collisions = {outcome: float(total) for outcome, total in shares.items() if total > 1}
    if collisions:
        details = ", ".join(f"{key}={value:.2f}" for key, value in collisions.items())
        raise ValueError(f"outcome attribution exceeds 100%: {details}")
    return {
        "claims": results,
        "totals": {
            key: sum(item[key] for item in results)
            for key in ("gross_value", "attributable_value", "confidence_adjusted_value",
                        "realization_cost", "net_value")
        },
    }

