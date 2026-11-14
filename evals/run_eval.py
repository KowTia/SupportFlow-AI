"""CLI entrypoint to run SupportFlow AI evaluation harness and write reports."""

import argparse
import asyncio
import sys
from pathlib import Path

from evals.runner import load_eval_dataset, render_markdown_report, run_eval_suite


def parse_args() -> argparse.Namespace:
    """Parse CLI options for the evaluation runner."""
    parser = argparse.ArgumentParser(description="Run SupportFlow AI offline evaluation suite.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=None,
        help="Optional path to custom evaluation JSON dataset.",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("evals/report.md"),
        help="Destination path for rendered Markdown report.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("evals/report.json"),
        help="Destination path for structured JSON metrics report.",
    )
    parser.add_argument(
        "--min-category-accuracy",
        type=float,
        default=0.95,
        help="Minimum acceptable category accuracy threshold [0.0..1.0].",
    )
    return parser.parse_args()


def main() -> int:
    """Run eval suite, persist Markdown and JSON reports, and enforce quality gates."""
    args = parse_args()
    cases = load_eval_dataset(args.dataset)
    report = asyncio.run(run_eval_suite(cases))
    markdown = render_markdown_report(report)

    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(markdown, encoding="utf-8")

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    print(
        f"Evaluated {report.total_cases} cases | "
        f"Pass rate: {report.pass_rate:.1%} | "
        f"Category acc: {report.category_accuracy:.1%} | "
        f"Priority acc: {report.priority_accuracy:.1%} | "
        f"Team acc: {report.team_accuracy:.1%} | "
        f"Injection P/R: {report.injection_precision:.1%}/{report.injection_recall:.1%} | "
        f"RAG hit rate: {report.rag_hit_rate:.1%} | "
        f"Repair recovery: {report.repair_recovery_rate:.1%}"
    )

    if report.category_accuracy < args.min_category_accuracy:
        print(
            f"FAILED: category accuracy {report.category_accuracy:.3f} "
            f"< threshold {args.min_category_accuracy:.3f}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
