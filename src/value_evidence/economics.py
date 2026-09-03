"""Compose value dimensions into a BusinessEconomics input for VEF claims.

BusinessEconomics is the structured replacement for the flat
``model_call_cost_usd`` / ``realization_cost_usd`` pattern. It holds typed
value dimensions, engineering effort, and other realization costs. When only
legacy flat inputs are provided it auto-creates a single
``inference_cost_avoided`` dimension for backward compatibility.
"""

from __future__ import annotations

from typing import Any

from .dimensions import (
    VALID_CONFIDENCES,
    VALID_EVIDENCE_BASES,
    evaluate_dimensions,
    is_cost_dimension,
    validate_dimensions,
)


def _require_non_negative(data: dict, key: str, errors: list[str]) -> None:
    val = data.get(key)
    if val is not None and (not isinstance(val, (int, float)) or val < 0):
        errors.append(f"{key} must be a non-negative number")


def validate_business_economics(economics: dict[str, Any]) -> list[str]:
    """Validate a BusinessEconomics dict.

    Accepts either:
      - ``value_dimensions`` (list of dimension dicts) for the full model, or
      - ``model_call_cost_usd`` for backward-compatible flat input.
    """
    errors: list[str] = []
    has_dimensions = "value_dimensions" in economics
    has_flat = "model_call_cost_usd" in economics

    if not has_dimensions and not has_flat:
        errors.append(
            "economics requires either 'value_dimensions' or "
            "'model_call_cost_usd'"
        )
        return errors

    if has_dimensions:
        errors.extend(validate_dimensions(economics["value_dimensions"]))

    if has_flat:
        _require_non_negative(economics, "model_call_cost_usd", errors)

    _require_non_negative(economics, "other_realization_cost_usd", errors)

    efforts = economics.get("engineering_effort", [])
    if not isinstance(efforts, list):
        errors.append("engineering_effort must be a list")
    else:
        for i, effort in enumerate(efforts):
            prefix = f"engineering_effort[{i}]"
            if effort.get("lifecycle") not in {"initial", "recurring"}:
                errors.append(f"{prefix}.lifecycle must be initial or recurring")
            for field in ("hours", "loaded_rate_usd"):
                val = effort.get(field)
                if val is None or not isinstance(val, (int, float)) or val < 0:
                    errors.append(f"{prefix}.{field} must be a non-negative number")
            for field in ("activity", "role", "source"):
                if not effort.get(field):
                    errors.append(f"{prefix}.{field} is required")

    return errors


def build_financial_model(
    economics: dict[str, Any],
    *,
    calls_avoided: int = 0,
    observed_cost_difference_usd: float | None = None,
) -> dict[str, Any]:
    """Build the ``financial_model`` portion of a VEF claim from economics input.

    When ``value_dimensions`` are provided, gross_value is the sum of all
    dimension values. When only flat inputs are present, the legacy
    inference-only path is used.

    Parameters
    ----------
    economics:
        A validated BusinessEconomics dict.
    calls_avoided:
        Number of model calls avoided (used only when auto-creating the
        inference dimension from flat inputs).
    observed_cost_difference_usd:
        Explicit observed cost difference (takes precedence over
        calls_avoided * cost_per_call).
    """
    dimensions = economics.get("value_dimensions")
    customer_validated = economics.get("customer_validated", False)

    if dimensions:
        evaluated = evaluate_dimensions(dimensions)
        value_total = sum(
            d["value_usd"] for d in evaluated if not d.get("is_cost")
        )
        cost_total = sum(
            d["value_usd"] for d in evaluated if d.get("is_cost")
        )
        gross_value = round(max(0.0, value_total - cost_total), 2)
    else:
        cost_per_call = float(economics.get("model_call_cost_usd", 0))
        if observed_cost_difference_usd is not None:
            infer_value = round(observed_cost_difference_usd, 2)
            cost_basis = "observed_route_cost"
        else:
            infer_value = round(calls_avoided * cost_per_call, 2)
            cost_basis = "average_call_cost"
        evaluated = [{
            "dimension": "inference_cost_avoided",
            "value_usd": infer_value,
            "inputs": (
                {"observed_cost_difference_usd": observed_cost_difference_usd}
                if observed_cost_difference_usd is not None
                else {"calls_avoided": calls_avoided, "cost_per_call_usd": cost_per_call}
            ),
            "source": economics.get("source", "claim_input"),
            "confidence": economics.get("confidence", "medium"),
            "evidence_basis": economics.get("evidence_basis", "estimated"),
        }]
        gross_value = infer_value

    efforts = economics.get("engineering_effort", [])
    effort_rows = [
        {**effort, "cost_usd": round(
            float(effort.get("hours", 0)) * float(effort.get("loaded_rate_usd", 0)), 2,
        )}
        for effort in efforts
    ]
    initial_cost = sum(
        r["cost_usd"] for r in effort_rows if r.get("lifecycle") == "initial"
    )
    recurring_cost = sum(
        r["cost_usd"] for r in effort_rows if r.get("lifecycle") == "recurring"
    )
    other_cost = float(economics.get("other_realization_cost_usd", 0))
    realization_cost = round(other_cost + initial_cost + recurring_cost, 2)

    model: dict[str, Any] = {
        "gross_value": gross_value,
        "currency": economics.get("currency", "USD"),
        "customer_validated": customer_validated,
        "value_dimensions": evaluated,
        "engineering_effort": effort_rows,
        "initial_engineering_cost_usd": round(initial_cost, 2),
        "recurring_engineering_cost_usd": round(recurring_cost, 2),
    }

    if not dimensions:
        model["model_call_cost_usd"] = float(economics.get("model_call_cost_usd", 0))
        if "cost_basis" in locals():
            model["cost_basis"] = cost_basis

    return model, realization_cost
