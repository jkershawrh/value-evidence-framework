from __future__ import annotations

import argparse
import json
from pathlib import Path

from .model import evaluate_portfolio, validate_claim
from .scorecard import render_markdown


def _claims(path: str) -> list[dict]:
    data = json.loads(Path(path).read_text())
    return data["claims"] if isinstance(data, dict) else data


def main() -> int:
    parser = argparse.ArgumentParser(prog="vef")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("file")
    score = sub.add_parser("score")
    score.add_argument("file")
    score.add_argument("--audience", choices=("customer", "red-hat"), default="customer")
    score.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args()
    claims = _claims(args.file)
    if args.command == "validate":
        failures = {claim.get("id", "unknown"): validate_claim(claim) for claim in claims}
        failures = {key: value for key, value in failures.items() if value}
        print(json.dumps({"valid": not failures, "errors": failures}, indent=2))
        return 1 if failures else 0
    portfolio = evaluate_portfolio(claims)
    print(json.dumps(portfolio, indent=2) if args.format == "json"
          else render_markdown(portfolio, args.audience), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

