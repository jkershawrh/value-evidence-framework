from __future__ import annotations

import argparse
import json
from pathlib import Path

from .inspector import inspect_repository, load_policy, render_inspection_markdown
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
    inspect = sub.add_parser("inspect")
    inspect.add_argument("repo")
    inspect.add_argument("--format", choices=("markdown", "json"), default="markdown")
    inspect.add_argument("--output")
    inspect.add_argument("--config")
    args = parser.parse_args()
    if args.command == "inspect":
        try:
            default_policy = Path(args.repo) / ".vef" / "inspect.yaml"
            policy_path = args.config or (str(default_policy) if default_policy.is_file() else None)
            policy = load_policy(policy_path) if policy_path else None
            report = inspect_repository(args.repo, policy=policy)
        except (OSError, TypeError, ValueError) as exc:
            parser.error(str(exc))
        rendered = (json.dumps(report, indent=2, sort_keys=True) + "\n"
                    if args.format == "json" else render_inspection_markdown(report))
        if args.output:
            Path(args.output).write_text(rendered)
        else:
            print(rendered, end="")
        return 0
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
