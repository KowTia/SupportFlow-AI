"""Tests for the 45-case evaluation harness and benchmark report generation."""

from evals.runner import load_eval_dataset, render_markdown_report, run_eval_suite


def test_eval_dataset_has_at_least_40_diverse_bilingual_cases() -> None:
    cases = load_eval_dataset()
    assert len(cases) >= 40

    languages = {case.language for case in cases}
    assert languages == {"en", "ru"}

    categories = {str(case.expected_category) for case in cases}
    assert categories == {"billing", "technical", "account", "security", "feature_request", "other"}

    injection_cases = [case for case in cases if case.expected_injection]
    repair_cases = [case for case in cases if case.simulate_malformed_attempts > 0]
    assert len(injection_cases) >= 8
    assert len(repair_cases) >= 6


async def test_run_eval_suite_meets_quality_and_security_thresholds() -> None:
    report = await run_eval_suite()

    assert report.total_cases == 45
    assert report.category_accuracy >= 0.95
    assert report.priority_accuracy >= 0.95
    assert report.team_accuracy >= 0.95
    assert report.injection_precision == 1.0
    assert report.injection_recall == 1.0
    assert report.rag_hit_rate >= 0.95
    assert report.repair_recovery_rate == 1.0
    assert len(report.category_breakdown) == 6

    markdown = render_markdown_report(report)
    assert "# SupportFlow AI — Evaluation Report" in markdown
    assert "Category Accuracy" in markdown
    assert "Prompt Injection Recall" in markdown
