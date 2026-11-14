"""Async evaluation harness for ticket triage, RAG retrieval, security, and repair loops."""

import json
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.db.base import Base
from app.llm import HybridLLMRouter, MockLLMProvider, TicketAnalyzer
from app.llm.schemas import AssignedTeam
from app.models.ticket import TicketCategory, TicketPriority
from app.rag.embeddings import DeterministicHashEmbeddingProvider
from app.services.kb import retrieve_kb_context_for_ticket, seed_kb_articles

DEFAULT_DATASET_PATH = Path(__file__).resolve().parent / "dataset.json"


class EvalCase(BaseModel):
    """Single labeled evaluation scenario."""

    id: str
    language: Literal["en", "ru"]
    subject: str
    body: str
    expected_category: TicketCategory
    expected_priority: TicketPriority
    expected_team: AssignedTeam
    expected_human_review: bool
    expected_injection: bool
    expected_kb_slug: str | None = None
    simulate_malformed_attempts: int = Field(default=0, ge=0, le=2)


class EvalCaseResult(BaseModel):
    """Execution result for a single evaluation scenario."""

    id: str
    language: str
    expected_category: str
    predicted_category: str
    category_match: bool
    expected_priority: str
    predicted_priority: str
    priority_match: bool
    expected_team: str
    predicted_team: str
    team_match: bool
    expected_human_review: bool
    predicted_human_review: bool
    human_review_match: bool
    expected_injection: bool
    predicted_injection: bool
    injection_risk_score: float
    expected_kb_slug: str | None
    cited_kb_ids: list[str]
    rag_hit: bool
    expected_repair_attempts: int
    actual_repair_attempts: int
    repair_match: bool
    latency_ms: float
    passed: bool


class CategoryMetrics(BaseModel):
    """Per-category precision/recall summary across evaluated cases."""

    category: str
    support: int
    category_accuracy: float
    priority_accuracy: float
    team_accuracy: float


class EvalSummaryReport(BaseModel):
    """Aggregated benchmark metrics across all evaluation cases."""

    generated_at: str
    provider: str
    embedding_provider: str
    total_cases: int
    passed_cases: int
    pass_rate: float
    category_accuracy: float
    priority_accuracy: float
    team_accuracy: float
    human_review_accuracy: float
    injection_precision: float
    injection_recall: float
    injection_f1: float
    rag_expected_cases: int
    rag_hit_rate: float
    repair_tested_cases: int
    repair_recovery_rate: float
    avg_latency_ms: float
    category_breakdown: list[CategoryMetrics]
    results: list[EvalCaseResult]


def load_eval_dataset(path: Path | None = None) -> list[EvalCase]:
    """Load and validate labeled evaluation cases from disk."""
    target = path or DEFAULT_DATASET_PATH
    raw = json.loads(target.read_text(encoding="utf-8"))
    return [EvalCase.model_validate(item) for item in raw]


def _build_malformed_script(count: int) -> list[str]:
    """Build deterministic invalid LLM outputs to stress-test TicketAnalyzer repair retries."""
    if count <= 0:
        return []
    if count == 1:
        return ["{malformed_json: true"]
    return [
        "Here is your output without valid closing brace: {category: 'billing'",
        json.dumps(
            {
                "category": "nonexistent_category",
                "priority": "high",
                "assigned_team": "billing_ops",
                "summary": "Short valid length summary",
                "draft_reply": "Thank you for contacting support, checking now.",
                "confidence": 0.9,
                "needs_human_review": True,
                "reasoning": "Testing schema validation recovery.",
                "cited_kb_ids": [],
            }
        ),
    ]


async def run_eval_suite(cases: list[EvalCase] | None = None) -> EvalSummaryReport:
    """Execute the complete offline RAG + LLM + Security + Repair evaluation suite."""
    eval_cases = cases if cases is not None else load_eval_dataset()

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    embedding_provider = DeterministicHashEmbeddingProvider(dimension=64)

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with session_factory() as session:
            await seed_kb_articles(session, embedding_provider=embedding_provider)

            results: list[EvalCaseResult] = []
            tp = fp = fn = 0
            cat_stats: dict[str, list[EvalCaseResult]] = defaultdict(list)

            for case in eval_cases:
                t0 = time.perf_counter()
                kb_context = await retrieve_kb_context_for_ticket(
                    session,
                    subject=case.subject,
                    body=case.body,
                    top_k=3,
                    min_score=0.10,
                    embedding_provider=embedding_provider,
                )

                scripted_failures = _build_malformed_script(case.simulate_malformed_attempts)
                provider = MockLLMProvider(scripted_outputs=scripted_failures)
                analyzer = TicketAnalyzer(
                    router=HybridLLMRouter(primary=provider),
                    max_repair_retries=2,
                )
                bundle = await analyzer.analyze(
                    subject=case.subject,
                    body=case.body,
                    kb_context=kb_context,
                )
                elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)

                pred_cat = str(bundle.analysis.category)
                pred_prio = str(bundle.analysis.priority)
                pred_team = str(bundle.analysis.assigned_team)
                pred_review = bundle.analysis.needs_human_review
                pred_inj = bundle.security.detected

                cat_match = pred_cat == str(case.expected_category)
                prio_match = pred_prio == str(case.expected_priority)
                team_match = pred_team == str(case.expected_team)
                review_match = pred_review == case.expected_human_review
                inj_match = pred_inj == case.expected_injection

                if case.expected_injection and pred_inj:
                    tp += 1
                elif not case.expected_injection and pred_inj:
                    fp += 1
                elif case.expected_injection and not pred_inj:
                    fn += 1

                if case.expected_kb_slug is not None:
                    rag_hit = case.expected_kb_slug in bundle.analysis.cited_kb_ids
                else:
                    rag_hit = True

                repair_match = bundle.meta.repair_attempts == case.simulate_malformed_attempts
                passed = (
                    cat_match
                    and prio_match
                    and team_match
                    and review_match
                    and inj_match
                    and rag_hit
                    and repair_match
                )

                result = EvalCaseResult(
                    id=case.id,
                    language=case.language,
                    expected_category=str(case.expected_category),
                    predicted_category=pred_cat,
                    category_match=cat_match,
                    expected_priority=str(case.expected_priority),
                    predicted_priority=pred_prio,
                    priority_match=prio_match,
                    expected_team=str(case.expected_team),
                    predicted_team=pred_team,
                    team_match=team_match,
                    expected_human_review=case.expected_human_review,
                    predicted_human_review=pred_review,
                    human_review_match=review_match,
                    expected_injection=case.expected_injection,
                    predicted_injection=pred_inj,
                    injection_risk_score=bundle.security.risk_score,
                    expected_kb_slug=case.expected_kb_slug,
                    cited_kb_ids=bundle.analysis.cited_kb_ids,
                    rag_hit=rag_hit,
                    expected_repair_attempts=case.simulate_malformed_attempts,
                    actual_repair_attempts=bundle.meta.repair_attempts,
                    repair_match=repair_match,
                    latency_ms=elapsed_ms,
                    passed=passed,
                )
                results.append(result)
                cat_stats[result.expected_category].append(result)
    finally:
        await engine.dispose()

    total = len(results)
    divisor = total if total > 0 else 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    rag_cases = [r for r in results if r.expected_kb_slug is not None]
    rag_hit_rate = sum(1 for r in rag_cases if r.rag_hit) / len(rag_cases) if rag_cases else 1.0

    repair_cases = [r for r in results if r.expected_repair_attempts > 0]
    repair_recovery_rate = (
        sum(1 for r in repair_cases if r.repair_match) / len(repair_cases) if repair_cases else 1.0
    )

    breakdown: list[CategoryMetrics] = []
    for category_name in sorted(cat_stats):
        group = cat_stats[category_name]
        g_len = len(group)
        breakdown.append(
            CategoryMetrics(
                category=category_name,
                support=g_len,
                category_accuracy=round(sum(r.category_match for r in group) / g_len, 4),
                priority_accuracy=round(sum(r.priority_match for r in group) / g_len, 4),
                team_accuracy=round(sum(r.team_match for r in group) / g_len, 4),
            )
        )

    return EvalSummaryReport(
        generated_at=datetime.now(UTC).isoformat(),
        provider="mock-heuristic-v1",
        embedding_provider="DeterministicHashEmbeddingProvider(dim=64)",
        total_cases=total,
        passed_cases=sum(1 for r in results if r.passed),
        pass_rate=round(sum(1 for r in results if r.passed) / divisor, 4),
        category_accuracy=round(sum(1 for r in results if r.category_match) / divisor, 4),
        priority_accuracy=round(sum(1 for r in results if r.priority_match) / divisor, 4),
        team_accuracy=round(sum(1 for r in results if r.team_match) / divisor, 4),
        human_review_accuracy=round(sum(1 for r in results if r.human_review_match) / divisor, 4),
        injection_precision=round(precision, 4),
        injection_recall=round(recall, 4),
        injection_f1=round(f1, 4),
        rag_expected_cases=len(rag_cases),
        rag_hit_rate=round(rag_hit_rate, 4),
        repair_tested_cases=len(repair_cases),
        repair_recovery_rate=round(repair_recovery_rate, 4),
        avg_latency_ms=round(sum(r.latency_ms for r in results) / divisor, 2),
        category_breakdown=breakdown,
        results=results,
    )


def render_markdown_report(report: EvalSummaryReport) -> str:
    """Format an EvalSummaryReport into a concise Markdown report."""
    lines = [
        "# SupportFlow AI — Evaluation Report",
        "",
        f"- **Generated At**: `{report.generated_at}`",
        f"- **LLM Provider**: `{report.provider}`",
        f"- **Embedding Provider**: `{report.embedding_provider}`",
        f"- **Total Cases**: `{report.total_cases}` ({report.passed_cases} passed all assertions)",
        "",
        "## Aggregate Metrics",
        "",
        "| Metric | Score |",
        "| --- | ---: |",
        f"| End-to-End Case Pass Rate | {report.pass_rate:.1%} |",
        f"| Category Accuracy | {report.category_accuracy:.1%} |",
        f"| Priority Accuracy | {report.priority_accuracy:.1%} |",
        f"| Assigned Team Accuracy | {report.team_accuracy:.1%} |",
        f"| Human Review Escalation Accuracy | {report.human_review_accuracy:.1%} |",
        f"| Prompt Injection Precision | {report.injection_precision:.1%} |",
        f"| Prompt Injection Recall | {report.injection_recall:.1%} |",
        f"| Prompt Injection F1 | {report.injection_f1:.1%} |",
        f"| RAG Expected Article Hit Rate ({report.rag_expected_cases} cases) | {report.rag_hit_rate:.1%} |",  # noqa: E501
        f"| JSON Repair Loop Recovery ({report.repair_tested_cases} cases) | {report.repair_recovery_rate:.1%} |",  # noqa: E501
        f"| Mean Pipeline Latency (E2E) | {report.avg_latency_ms:.2f} ms |",
        "",
        "## Per-Category Accuracy",
        "",
        "| Category | Cases | Category Acc | Priority Acc | Team Acc |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]

    for row in report.category_breakdown:
        lines.append(
            f"| `{row.category}` | {row.support} | {row.category_accuracy:.1%} "
            f"| {row.priority_accuracy:.1%} | {row.team_accuracy:.1%} |"
        )

    failures = [r for r in report.results if not r.passed]
    lines.extend(["", "## Failed Cases", ""])
    if not failures:
        lines.append(
            "All evaluation cases passed every classification, RAG, security, and repair assertion."
        )  # noqa: E501
    else:
        lines.extend(
            [
                "| ID | Expected | Predicted | Injection Match | RAG Hit | Repair Match |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for item in failures:
            lines.append(
                f"| `{item.id}` | {item.expected_category}/{item.expected_priority}/{item.expected_team} "  # noqa: E501
                f"| {item.predicted_category}/{item.predicted_priority}/{item.predicted_team} "
                f"| {item.predicted_injection == item.expected_injection} "
                f"| {item.rag_hit} | {item.repair_match} |"
            )

    lines.extend(
        [
            "",
            "## Case Execution Log",
            "",
            "| ID | Lang | Category | Priority | Team | Injection | Cited KB | Repair | Latency | Status |",  # noqa: E501
            "| --- | --- | --- | --- | --- | --- | --- | ---: | ---: | --- |",
        ]
    )

    for item in report.results:
        cited = ", ".join(item.cited_kb_ids[:2]) if item.cited_kb_ids else "-"
        inj_label = "BLOCKED" if item.predicted_injection else "clean"
        status_label = "PASS" if item.passed else "FAIL"
        lines.append(
            f"| `{item.id}` | {item.language} | `{item.predicted_category}` "
            f"| `{item.predicted_priority}` | `{item.predicted_team}` | {inj_label} "
            f"| `{cited}` | {item.actual_repair_attempts}/{item.expected_repair_attempts} "
            f"| {item.latency_ms:.2f} ms | **{status_label}** |"
        )

    lines.append("")
    return "\n".join(lines)
