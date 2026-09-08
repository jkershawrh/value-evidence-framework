"""Fail-closed helpers for bounded AI usage and cost evidence."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def bounded_counter_delta(
    start: dict[str, Any] | None,
    end: dict[str, Any] | None,
    fields: Iterable[str],
) -> dict[str, int | float | None]:
    """Subtract cumulative counters while preserving missing data and resets."""

    start = start or {}
    end = end or {}
    result: dict[str, int | float | None] = {}
    for field in fields:
        before = start.get(field)
        after = end.get(field)
        if (
            not isinstance(before, (int, float))
            or isinstance(before, bool)
            or not isinstance(after, (int, float))
            or isinstance(after, bool)
            or after < before
        ):
            result[field] = None
        else:
            result[field] = after - before
    return result


def bounded_usage_delta(start: dict[str, Any], end: dict[str, Any]) -> dict[str, Any]:
    """Build an aggregate usage delta only when both snapshots share one ledger epoch."""

    fields = (
        "requests",
        "completed_requests",
        "failed_requests",
        "unknown_usage_requests",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "inference_milliseconds",
    )
    same_epoch = bool(start.get("started_at")) and start.get("started_at") == end.get("started_at")
    totals = bounded_counter_delta(start.get("totals"), end.get("totals"), fields)
    complete = (
        same_epoch
        and all(value is not None for value in totals.values())
        and totals["failed_requests"] == 0
        and totals["unknown_usage_requests"] == 0
        and totals["requests"] == totals["completed_requests"]
    )
    return {
        "schema_version": "vef.bounded-ai-usage.v1alpha1",
        "window_started_at": start.get("captured_at"),
        "window_ended_at": end.get("captured_at"),
        "ledger_epoch": start.get("started_at") if same_epoch else None,
        "totals": totals,
        "usage_complete": complete,
    }


def token_cost_usd(usage: dict[str, Any], pricing: dict[str, Any]) -> float | None:
    """Price measured tokens only when usage and a named pricing basis are complete."""

    totals = usage.get("totals") or {}
    required_usage = (totals.get("input_tokens"), totals.get("output_tokens"))
    input_rate = pricing.get("input_cost_per_1k_tokens_usd")
    output_rate = pricing.get("output_cost_per_1k_tokens_usd")
    if (
        usage.get("usage_complete") is not True
        or not pricing.get("pricing_class")
        or not pricing.get("source")
        or any(not isinstance(value, (int, float)) or value < 0 for value in required_usage)
        or any(
            not isinstance(value, (int, float)) or value < 0 for value in (input_rate, output_rate)
        )
    ):
        return None
    return round(
        totals["input_tokens"] * input_rate / 1000 + totals["output_tokens"] * output_rate / 1000,
        6,
    )


def estimated_avoided_token_cost_usd(
    *,
    handled_signals: int | None,
    baseline_ai_eligible_fraction: float | None,
    average_input_tokens: float | None,
    average_output_tokens: float | None,
    pricing: dict[str, Any],
) -> float | None:
    """Estimate avoided cost without pretending all handled signals were AI eligible."""

    values = (
        handled_signals,
        baseline_ai_eligible_fraction,
        average_input_tokens,
        average_output_tokens,
    )
    if any(not isinstance(value, (int, float)) or value < 0 for value in values):
        return None
    if baseline_ai_eligible_fraction > 1:
        return None
    synthetic_usage = {
        "usage_complete": True,
        "totals": {
            "input_tokens": handled_signals * baseline_ai_eligible_fraction * average_input_tokens,
            "output_tokens": handled_signals
            * baseline_ai_eligible_fraction
            * average_output_tokens,
        },
    }
    return token_cost_usd(synthetic_usage, pricing)
