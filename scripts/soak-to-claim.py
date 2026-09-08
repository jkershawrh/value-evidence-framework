#!/usr/bin/env python3
"""Generate a VEF claim from soak start/end snapshots.

Usage:
    python scripts/soak-to-claim.py \\
        --start soak-data/snapshot-start-*.json \\
        --end   soak-data/snapshot-end-*.json \\
        [--output examples/cascade-soak-72h.json]

Reads the two JSON snapshots produced by soak-collect.sh and builds a
VEF claim with observed data wherever possible, falling back to the
pilot estimates for dimensions that need manual input.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from value_evidence.usage_cost import bounded_usage_delta, estimated_avoided_token_cost_usd


def load(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def delta(start: dict, end: dict, *keys: str) -> float | None:
    """Compute end[k] - start[k] for a nested key path, or None if missing."""
    s, e = start, end
    for k in keys:
        s = s.get(k) if isinstance(s, dict) else None
        e = e.get(k) if isinstance(e, dict) else None
    if (
        isinstance(s, (int, float))
        and not isinstance(s, bool)
        and isinstance(e, (int, float))
        and not isinstance(e, bool)
        and e >= s
    ):
        return e - s
    return None


def mapping_delta(start: dict, end: dict, key: str) -> float | None:
    return delta({"value": start.get(key)}, {"value": end.get(key)}, "value")


def safe_get(data: dict, *keys: str, default=None):
    val = data
    for k in keys:
        if isinstance(val, dict):
            val = val.get(k)
        else:
            return default
    return val if val is not None else default


def extract_sc_metrics(cls_end: dict, cls_start: dict) -> dict:
    """Extract SC hybrid coverage and quality metrics from classifier stats."""
    cov_end = cls_end.get("coverage") or {}
    cov_start = cls_start.get("coverage") or {}
    metrics_end = cls_end.get("metrics") or {}

    sc_authoritative = mapping_delta(cov_start, cov_end, "sc_authoritative")
    llm_fallback = mapping_delta(cov_start, cov_end, "llm_fallback")
    severity_gated = mapping_delta(cov_start, cov_end, "severity_gated")
    margin_gated = mapping_delta(cov_start, cov_end, "margin_gated")
    sc_failure = mapping_delta(cov_start, cov_end, "sc_failure")
    total_classified = (
        sc_authoritative + llm_fallback + sc_failure
        if all(value is not None for value in (sc_authoritative, llm_fallback, sc_failure))
        else None
    )

    metrics_start = cls_start.get("metrics") or {}
    comparisons = mapping_delta(metrics_start, metrics_end, "comparisons")
    agreements = mapping_delta(metrics_start, metrics_end, "agreements")
    disagreements = mapping_delta(metrics_start, metrics_end, "disagreements")

    adjudicated = (
        agreements + disagreements if agreements is not None and disagreements is not None else None
    )
    agreement_rate = agreements / adjudicated if adjudicated and adjudicated > 0 else None

    latency = metrics_end.get("latency_ms") or {}
    sc_latency_p50 = safe_get(latency, "semantic", "p50")
    llm_latency_p50 = safe_get(latency, "generative", "p50")

    return {
        "sc_authoritative": sc_authoritative,
        "llm_fallback": llm_fallback,
        "severity_gated": severity_gated,
        "margin_gated": margin_gated,
        "sc_failure": sc_failure,
        "total_classified": total_classified,
        "sc_coverage_rate": (
            round(sc_authoritative / total_classified, 4)
            if total_classified and sc_authoritative is not None
            else None
        ),
        "comparisons": comparisons,
        "agreements": agreements,
        "disagreements": disagreements,
        "agreement_rate": round(agreement_rate, 4) if agreement_rate is not None else None,
        "sc_latency_p50_ms": sc_latency_p50,
        "llm_latency_p50_ms": llm_latency_p50,
        "hybrid_margin": cls_end.get("hybrid_margin"),
        "hybrid_suppress_margin": cls_end.get("hybrid_suppress_margin"),
        "serializer_revision": cls_end.get("serializer_revision"),
        "mode": cls_end.get("mode"),
    }


def count_false_suppressions(comparisons_data: dict | list | None) -> dict:
    """Count dangerous false suppressions from classifier comparison data."""
    if not comparisons_data:
        return {
            "false_suppressions": None,
            "total_comparisons": None,
            "false_suppression_rate": None,
        }

    records = (
        comparisons_data
        if isinstance(comparisons_data, list)
        else (comparisons_data.get("comparisons", []) if isinstance(comparisons_data, dict) else [])
    )

    total = len(records)
    false_suppressions = 0
    for r in records:
        sc_label = r.get("sc_label") or r.get("semantic_label") or ""
        llm_label = r.get("llm_label") or r.get("generative_label") or ""
        suppress_labels = {"routine_noise", "known_pattern"}
        escalate_labels = {"needs_attention", "real_incident"}
        if sc_label in suppress_labels and llm_label in escalate_labels:
            false_suppressions += 1

    return {
        "false_suppressions": false_suppressions,
        "total_comparisons": total,
        "false_suppression_rate": (round(false_suppressions / total, 4) if total > 0 else None),
    }


def build_claim(start: dict, end: dict) -> dict:
    ts_start = start.get("timestamp") or start.get("captured_at") or "unknown"
    ts_end = end.get("timestamp") or end.get("captured_at") or "unknown"

    try:
        if ts_start.endswith("Z") and "-" not in ts_start:
            dt_start = datetime.strptime(ts_start, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
            dt_end = datetime.strptime(ts_end, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
        else:
            dt_start = datetime.fromisoformat(ts_start)
            dt_end = datetime.fromisoformat(ts_end)
        hours = (dt_end - dt_start).total_seconds() / 3600
    except (ValueError, TypeError):
        hours = None

    raw_start_stats = start.get("stats") or {}
    raw_end_stats = end.get("stats") or {}
    start_stats = raw_start_stats.get("stats", raw_start_stats)
    end_stats = raw_end_stats.get("stats", raw_end_stats)
    signals_processed = mapping_delta(start_stats, end_stats, "signals_processed")
    cascade_handled = mapping_delta(start_stats, end_stats, "cascade_handled")
    cascade_forwarded = mapping_delta(start_stats, end_stats, "cascade_forwarded")

    compression_ratio = (
        cascade_handled / signals_processed
        if signals_processed and cascade_handled is not None
        else None
    )

    # Memory deltas
    mem_start = start.get("memory_stats") or {}
    mem_end = end.get("memory_stats") or {}
    memories_formed = mapping_delta(mem_start, mem_end, "formed_total")
    memories_end_size = mem_end.get("size")
    evictions = mapping_delta(mem_start, mem_end, "evictions_total")

    # Agent counts
    end_agents = end.get("agents") or {}
    agent_list = end_agents.get("agents", []) if isinstance(end_agents, dict) else []
    active_agents = sum(1 for a in agent_list if a.get("status") == "active")
    total_agents = len(agent_list)

    # Classifier stats — includes SC hybrid coverage SLI
    cls_end = end.get("classifier_stats") or {}
    cls_start = start.get("classifier_stats") or {}

    # SC hybrid metrics
    sc_metrics = extract_sc_metrics(cls_end, cls_start)

    # False suppression tracking from comparison records
    end_comparisons = end.get("classifier_comparisons")
    false_supp = count_false_suppressions(end_comparisons)

    cost_inputs = end.get("cost_inputs") or {}
    pricing = cost_inputs.get("pricing") or {}
    usage_start = {**(start.get("racmaas_usage") or {}), "captured_at": ts_start}
    usage_end = {**(end.get("racmaas_usage") or {}), "captured_at": ts_end}
    usage = bounded_usage_delta(usage_start, usage_end)
    completed = usage["totals"].get("completed_requests")
    average_input = (
        usage["totals"]["input_tokens"] / completed
        if completed and usage["totals"].get("input_tokens") is not None
        else None
    )
    average_output = (
        usage["totals"]["output_tokens"] / completed
        if completed and usage["totals"].get("output_tokens") is not None
        else None
    )
    ai_fraction = cost_inputs.get("baseline_ai_eligible_fraction")
    avoided_cost = estimated_avoided_token_cost_usd(
        handled_signals=int(cascade_handled) if cascade_handled is not None else None,
        baseline_ai_eligible_fraction=ai_fraction,
        average_input_tokens=average_input,
        average_output_tokens=average_output,
        pricing=pricing,
    )
    dimensions = list(cost_inputs.get("value_dimensions") or [])
    if avoided_cost is not None:
        dimensions.insert(
            0,
            {
                "dimension": "inference_cost_avoided",
                "inputs": {"observed_cost_difference_usd": avoided_cost},
                "source": pricing["source"],
                "confidence": (
                    "medium"
                    if cost_inputs.get("ai_eligible_fraction_basis") == "observed"
                    else "low"
                ),
                "evidence_basis": (
                    "observed"
                    if cost_inputs.get("ai_eligible_fraction_basis") == "observed"
                    else "estimated"
                ),
            },
        )

    engineering_effort = cost_inputs.get("engineering_effort") or []
    required_activities = {
        "ruleset_design",
        "ruleset_review",
        "ruleset_testing",
        "ruleset_deployment",
        "ruleset_monitoring",
        "ruleset_maintenance",
    }
    valid_effort = required_activities <= {
        row.get("activity") for row in engineering_effort
    } and all(
        isinstance(row.get("hours"), (int, float))
        and isinstance(row.get("loaded_rate_usd"), (int, float))
        and row.get("lifecycle") in {"initial", "recurring"}
        and bool(row.get("role"))
        and bool(row.get("source"))
        for row in engineering_effort
    )
    initial_cost = (
        round(
            sum(
                row["hours"] * row["loaded_rate_usd"]
                for row in engineering_effort
                if row.get("lifecycle") == "initial"
            ),
            2,
        )
        if valid_effort
        else None
    )
    recurring_cost = (
        round(
            sum(
                row["hours"] * row["loaded_rate_usd"]
                for row in engineering_effort
                if row.get("lifecycle") == "recurring"
            ),
            2,
        )
        if valid_effort
        else None
    )
    other_cost = cost_inputs.get("other_realization_cost_usd")
    realization_cost = (
        round(initial_cost + recurring_cost + other_cost, 2)
        if initial_cost is not None
        and recurring_cost is not None
        and isinstance(other_cost, (int, float))
        else None
    )
    dangerous_misses = mapping_delta(start_stats, end_stats, "fn_count")
    drop_fields = (
        "llm_dropped",
        "llm_priority_dropped",
        "ledger_writes_dropped",
        "ledger_memory_events_dropped",
    )
    drops = {field: mapping_delta(start_stats, end_stats, field) for field in drop_fields}
    ai_work_complete = usage["usage_complete"] and all(value == 0 for value in drops.values())
    counterfactual_method = cost_inputs.get("counterfactual_method", "unmeasured")
    customer_validated = cost_inputs.get("customer_validated") is True
    value_eligible = (
        avoided_cost is not None
        and dangerous_misses == 0
        and ai_work_complete
        and counterfactual_method != "unmeasured"
        and customer_validated
        and realization_cost is not None
    )

    period = (
        f"soak-{hours:.0f}h-{ts_start}-to-{ts_end}"
        if hours is not None
        else f"soak-{ts_start}-to-{ts_end}"
    )

    claim = {
        "_description": (
            "Auto-generated VEF draft from bounded aggregate observations. "
            "Repository structure and signal handling are not proof of realized value."
        ),
        "_soak_metadata": {
            "start_snapshot": ts_start,
            "end_snapshot": ts_end,
            "duration_hours": round(hours, 1) if hours is not None else None,
            "signals_processed": int(signals_processed) if signals_processed is not None else None,
            "cascade_handled": int(cascade_handled) if cascade_handled is not None else None,
            "cascade_forwarded": int(cascade_forwarded) if cascade_forwarded is not None else None,
            "compression_ratio": round(compression_ratio, 4)
            if compression_ratio is not None
            else None,
            "memories_formed": memories_formed,
            "memories_retained": memories_end_size,
            "evictions": evictions,
            "active_agents": active_agents,
            "total_agents": total_agents,
            "sc_hybrid": {
                "mode": sc_metrics["mode"],
                "sc_authoritative": sc_metrics["sc_authoritative"],
                "llm_fallback": sc_metrics["llm_fallback"],
                "severity_gated": sc_metrics["severity_gated"],
                "margin_gated": sc_metrics["margin_gated"],
                "sc_failure": sc_metrics["sc_failure"],
                "sc_coverage_rate": sc_metrics["sc_coverage_rate"],
                "agreement_rate": sc_metrics["agreement_rate"],
                "comparisons": sc_metrics["comparisons"],
                "disagreements": sc_metrics["disagreements"],
                "false_suppressions": false_supp["false_suppressions"],
                "false_suppression_rate": false_supp["false_suppression_rate"],
                "hybrid_margin": sc_metrics["hybrid_margin"],
                "hybrid_suppress_margin": sc_metrics["hybrid_suppress_margin"],
                "serializer_revision": sc_metrics["serializer_revision"],
                "sc_latency_p50_ms": sc_metrics["sc_latency_p50_ms"],
                "llm_latency_p50_ms": sc_metrics["llm_latency_p50_ms"],
            },
            "bounded_ai_usage": usage,
            "drop_deltas": drops,
        },
        "claims": [
            {
                "id": "cascade.full-business-impact",
                "product": "cascade-compression",
                "outcome_id": f"rhpds-via-infra01-soak:{period}",
                "value_type": "cost_avoidance"
                if avoided_cost is not None
                else "operational_efficiency",
                "measurement": {
                    "observed": int(cascade_handled) if cascade_handled is not None else None,
                    "unit": "signals_handled",
                    "period": period,
                    "pilot_signal_population": int(signals_processed)
                    if signals_processed is not None
                    else None,
                    "baseline_ai_eligible_fraction": ai_fraction,
                },
                "counterfactual": {
                    "method": counterfactual_method,
                    "expected_without_product": cost_inputs.get("expected_without_product"),
                    "matched_workload": cost_inputs.get("matched_workload") is True,
                },
                "attribution": {
                    "product_share": cost_inputs.get("product_share"),
                    "competing_factors": [
                        "workload_mix",
                        "model_routing",
                        "pricing_basis",
                        "baseline_ai_eligibility",
                    ],
                },
                "financial_model": {
                    "gross_value": avoided_cost if avoided_cost is not None else "UNKNOWN",
                    "currency": "USD",
                    "customer_validated": customer_validated,
                    "value_dimensions": dimensions,
                    "engineering_effort": engineering_effort,
                    "initial_engineering_cost_usd": initial_cost,
                    "recurring_engineering_cost_usd": recurring_cost,
                },
                "evidence": {
                    "confidence": "medium" if value_eligible else "unverified",
                    "sources": [
                        "bounded_aggregate_snapshots",
                        "aggregate_ai_usage_ledger",
                        "sc_hybrid_coverage_sli",
                    ],
                    "reproducible": True,
                    "dangerous_misses": dangerous_misses,
                    "dangerous_misses_measured": dangerous_misses is not None,
                    "ai_work_complete": ai_work_complete,
                    "shadow_validation_coverage": cost_inputs.get("shadow_validation_coverage"),
                    "sc_agreement_rate": sc_metrics["agreement_rate"],
                    "false_suppression_rate": false_supp["false_suppression_rate"],
                    "value_eligible": value_eligible,
                },
                "realization_cost": realization_cost,
            }
        ],
    }

    return claim


def main():
    parser = argparse.ArgumentParser(description="Generate VEF claim from soak snapshots")
    parser.add_argument("--start", required=True, help="Path to start snapshot JSON")
    parser.add_argument("--end", required=True, help="Path to end snapshot JSON")
    parser.add_argument("--output", default=None, help="Output claim path (default: stdout)")
    args = parser.parse_args()

    start = load(args.start)
    end = load(args.end)

    if start.get("phase") != "start":
        print(
            f"WARNING: start file phase is '{start.get('phase')}', expected 'start'",
            file=sys.stderr,
        )
    if end.get("phase") != "end":
        print(f"WARNING: end file phase is '{end.get('phase')}', expected 'end'", file=sys.stderr)

    claim = build_claim(start, end)

    print(file=sys.stderr)
    meta = claim["_soak_metadata"]
    sc = meta.get("sc_hybrid") or {}
    print(
        f"Soak: {meta['duration_hours'] if meta['duration_hours'] is not None else 'unknown'}h",
        file=sys.stderr,
    )
    print(
        "Signals: "
        f"{meta['signals_processed'] if meta['signals_processed'] is not None else 'unknown'} "
        f"processed; compression="
        f"{meta['compression_ratio'] if meta['compression_ratio'] is not None else 'unknown'}",
        file=sys.stderr,
    )
    print(
        "Memories: "
        f"formed={meta['memories_formed'] if meta['memories_formed'] is not None else 'unknown'}, "
        f"retained={meta['memories_retained'] if meta['memories_retained'] is not None else 'unknown'}, "
        f"evicted={meta['evictions'] if meta['evictions'] is not None else 'unknown'}",
        file=sys.stderr,
    )
    print(f"Agents: {meta['active_agents']} active / {meta['total_agents']} total", file=sys.stderr)
    if sc.get("mode"):
        print(file=sys.stderr)
        print(f"SC Hybrid: mode={sc['mode']}", file=sys.stderr)
        sc_auth = sc.get("sc_authoritative", 0)
        llm_fb = sc.get("llm_fallback", 0)
        cov = sc.get("sc_coverage_rate")
        agr = sc.get("agreement_rate")
        fs = sc.get("false_suppressions", 0)
        fsr = sc.get("false_suppression_rate")
        print(
            f"  SC authoritative: {sc_auth if sc_auth is not None else 'unknown'}  "
            f"LLM fallback: {llm_fb if llm_fb is not None else 'unknown'}  "
            + (f"Coverage: {cov:.1%}" if cov is not None else "Coverage: unknown"),
            file=sys.stderr,
        )
        print(f"  Agreement: {agr:.1%}" if agr else "  Agreement: n/a", file=sys.stderr)
        print(
            f"  False suppressions: {fs if fs is not None else 'unknown'}"
            + (f" ({fsr:.1%})" if fsr is not None else ""),
            file=sys.stderr,
        )
        print(
            f"  Severity gated: {sc.get('severity_gated', 0)}  "
            f"Margin gated: {sc.get('margin_gated', 0)}",
            file=sys.stderr,
        )
    print(file=sys.stderr)
    gross = claim["claims"][0]["financial_model"]["gross_value"]
    print(f"Financial value: {gross}", file=sys.stderr)
    if gross == "UNKNOWN":
        print(
            "Add bounded usage, named pricing, counterfactual, and effort inputs.", file=sys.stderr
        )

    output = json.dumps(claim, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(output)
        print(f"Claim written to: {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
