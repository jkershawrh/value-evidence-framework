from __future__ import annotations

from typing import Any


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
                  f"Attributable value: **${claim['attributable_value']:,.2f}**; "
                  f"confidence-adjusted: **${claim['confidence_adjusted_value']:,.2f}**."]
        if audience == "red-hat":
            leverage = claim["value_leverage"]
            lines.append(f"Value leverage: **{leverage:.2f}x**." if leverage is not None
                         else "Value leverage cannot be calculated until realization cost is supplied.")
        if claim["gaps"]:
            lines += ["", "Evidence gaps:"] + [f"- {gap}" for gap in claim["gaps"]]
        lines.append("")
    lines += ["---", "This scorecard reports modeled evidence, not a guarantee of causation or savings."]
    return "\n".join(lines) + "\n"

