from __future__ import annotations

from typing import Any


_DIMENSION_LABELS = {
    "inference_cost_avoided": "Inference cost avoided",
    "infrastructure_cost_avoided": "Infrastructure cost avoided",
    "human_operational_cost_avoided": "Human operational cost avoided",
    "incident_response_value": "Incident response value",
    "downstream_business_impact": "Downstream business impact",
    "organizational_knowledge_value": "Organizational knowledge value (OKV)",
    "human_cost_of_ownership": "Human cost of ownership (HCO)",
}


def _render_dimensions(dims: list[dict[str, Any]], audience: str) -> list[str]:
    """Render value dimension breakdown lines."""
    value_dims = [d for d in dims if not d.get("is_cost")]
    cost_dims = [d for d in dims if d.get("is_cost")]

    lines = ["", "Value dimensions:"]
    for dim in value_dims:
        label = _DIMENSION_LABELS.get(dim["dimension"], dim["dimension"])
        basis = dim.get("evidence_basis", "unknown")
        conf = dim.get("confidence", "unknown")
        value = dim.get("value_usd", 0)
        line = f"- {label}: **${value:,.2f}**"
        if audience == "red-hat":
            line += f" (confidence: {conf}, basis: {basis}, source: {dim.get('source', '—')})"
        else:
            line += f" ({basis})"
        lines.append(line)

    if cost_dims:
        lines.append("")
        lines.append("Cost dimensions (subtracted from gross value):")
        for dim in cost_dims:
            label = _DIMENSION_LABELS.get(dim["dimension"], dim["dimension"])
            basis = dim.get("evidence_basis", "unknown")
            conf = dim.get("confidence", "unknown")
            value = dim.get("value_usd", 0)
            line = f"- {label}: **−${value:,.2f}**"
            if audience == "red-hat":
                line += f" (confidence: {conf}, basis: {basis}, source: {dim.get('source', '—')})"
            else:
                line += f" ({basis})"
            lines.append(line)
            ratio = dim.get("displacement_ratio")
            if ratio is not None:
                pct = ratio * 100
                lines.append(
                    f"  - Displacement ratio: **{pct:.1f}%** of function headcount"
                )
            pathway = dim.get("reskilling_pathway")
            if pathway:
                lines.append("  - Reskilling pathway:")
                for entry in pathway:
                    from_role = entry.get("from", "—")
                    to_role = entry.get("to", "—")
                    status = entry.get("status", "planned")
                    lines.append(f"    - {from_role} → {to_role} ({status})")

    return lines


def render_markdown(portfolio: dict[str, Any], audience: str) -> str:
    title = "Customer Value Scorecard" if audience == "customer" else "Red Hat Product Scorecard"
    total = portfolio["totals"]
    lines = [f"# {title}", "", "## Portfolio summary", "",
             f"- Confidence-adjusted value: ${total['confidence_adjusted_value']:,.2f}",
             f"- Cost to realize: ${total['realization_cost']:,.2f}",
             f"- Net confidence-adjusted value: ${total['net_value']:,.2f}", ""]
    if audience == "red-hat":
        leverage = (total["confidence_adjusted_value"] / total["realization_cost"]
                    if total["realization_cost"] else None)
        lines += [f"- Portfolio value leverage: {leverage:.2f}x" if leverage is not None
                  else "- Portfolio value leverage: not measurable (realization cost missing)", ""]
    lines += ["## Claims", ""]
    for claim in portfolio["claims"]:
        lines += [f"### {claim['product']}: {claim['id']} — {claim['rating'].upper()}", "",
                  (f"Attributable value: **${claim['attributable_value']:,.2f}**; "
                   f"confidence-adjusted: **${claim['confidence_adjusted_value']:,.2f}**.")]
        if audience == "red-hat":
            leverage = claim["value_leverage"]
            lines.append(f"Value leverage: **{leverage:.2f}x**." if leverage is not None
                         else "Value leverage cannot be calculated until realization cost is supplied.")
        dims = claim.get("value_dimensions")
        if dims:
            lines += _render_dimensions(dims, audience)
        usage = claim.get("ai_usage", {})
        if usage.get("baseline_eligible_signals") is not None:
            lines += ["",
                      (f"AI-eligible baseline population: "
                       f"**{usage['baseline_eligible_signals']:,}**; "
                       f"baseline AI calls: **{usage['baseline_ai_calls']:,}**; "
                       f"Cascade AI calls: **{usage['cascade_ai_calls']:,}**.")]
        engineering = claim.get("engineering_cost", {})
        if engineering.get("initial") or engineering.get("recurring"):
            lines.append(
                f"Engineering cost — initial: **${engineering['initial']:,.2f}**; "
                f"recurring: **${engineering['recurring']:,.2f}**."
            )
        if claim["gaps"]:
            lines += ["", "Evidence gaps:"] + [f"- {gap}" for gap in claim["gaps"]]
        lines.append("")
    lines += ["---", "This scorecard reports modeled evidence, not a guarantee of causation or savings."]
    return "\n".join(lines) + "\n"
