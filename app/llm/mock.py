"""Deterministic mock LLM provider for offline tests, CI, and fallback routing."""

import re

from app.llm.base import BaseLLMProvider, LLMProviderError, ProviderReply
from app.llm.schemas import AssignedTeam, LLMAnalysisOutput
from app.models.ticket import TicketCategory, TicketPriority

_TICKET_BLOCK_RE = re.compile(
    r"<untrusted_ticket>(.*?)</untrusted_ticket>",
    re.DOTALL | re.IGNORECASE,
)
_KB_ID_RE = re.compile(r"\[KB:([A-Za-z0-9_.:-]+)\]")


def _extract_ticket_text(user_prompt: str) -> str:
    """Isolate untrusted ticket content so repair-prompt wrappers do not skew heuristics."""
    match = _TICKET_BLOCK_RE.search(user_prompt)
    return match.group(1).strip() if match else user_prompt


def _classify_ticket_heuristically(text: str, cited_kb_ids: list[str]) -> LLMAnalysisOutput:
    """Classify a ticket deterministically in English or Russian."""
    lower = text.lower()

    if any(
        kw in lower
        for kw in (
            "breach",
            "leak",
            "vulnerability",
            "unauthorized",
            "suspicious",
            "phishing",
            "compromised",
            "утечк",
            "взлом",
            "подозрительн",
            "уязвим",
        )
    ):
        is_critical = any(
            kw in lower
            for kw in ("breach", "leak", "compromised", "unauthorized", "утечк", "взлом")
        )
        priority = TicketPriority.CRITICAL if is_critical else TicketPriority.HIGH
        return LLMAnalysisOutput(
            category=TicketCategory.SECURITY,
            priority=priority,
            assigned_team=AssignedTeam.ACCOUNT_SECURITY,
            summary="Potential security incident or unauthorized access reported by customer.",
            draft_reply=(
                "Thank you for alerting us immediately. Our security team has escalated your "
                "report and is reviewing session logs and access controls right now."
            ),
            confidence=0.93,
            needs_human_review=True,
            reasoning=(
                "Matched security-incident keywords requiring immediate security team triage."
            ),
            cited_kb_ids=cited_kb_ids,
        )

    if any(
        kw in lower
        for kw in (
            "invoice",
            "billing",
            "charge",
            "charged",
            "refund",
            "vat",
            "payment",
            "card",
            "subscription",
            "счет",
            "счёт",
            "оплат",
            "списа",
            "возврат",
            "подписк",
        )
    ):
        is_high = any(
            kw in lower
            for kw in ("double", "twice", "refund", "unauthorized", "двойн", "дважды", "возврат")
        )
        priority = TicketPriority.HIGH if is_high else TicketPriority.MEDIUM
        return LLMAnalysisOutput(
            category=TicketCategory.BILLING,
            priority=priority,
            assigned_team=AssignedTeam.BILLING_OPS,
            summary="Customer reported a billing, invoice, or payment processing inquiry.",
            draft_reply=(
                "Thank you for reaching out about your billing inquiry. Our billing operations "
                "team is reviewing your recent transactions and will follow up with an update."
            ),
            confidence=0.91,
            needs_human_review=priority == TicketPriority.HIGH,
            reasoning="Matched billing/payment indicators routed to billing operations.",
            cited_kb_ids=cited_kb_ids,
        )

    if any(
        kw in lower
        for kw in (
            "login",
            "sso",
            "saml",
            "password",
            "2fa",
            "mfa",
            "locked",
            "account",
            "парол",
            "вход",
            "аккаунт",
            "заблокир",
        )
    ):
        is_high = any(
            kw in lower for kw in ("locked", "cannot login", "sso", "заблокир", "не могу войти")
        )
        priority = TicketPriority.HIGH if is_high else TicketPriority.MEDIUM
        return LLMAnalysisOutput(
            category=TicketCategory.ACCOUNT,
            priority=priority,
            assigned_team=AssignedTeam.ACCOUNT_SECURITY,
            summary="Customer needs assistance with account access, authentication, or SSO.",
            draft_reply=(
                "We have received your account access request. Please verify whether the issue "
                "affects all users in your workspace while our team inspects your SSO settings."
            ),
            confidence=0.89,
            needs_human_review=False,
            reasoning="Matched authentication and account-management keywords.",
            cited_kb_ids=cited_kb_ids,
        )

    if any(
        kw in lower
        for kw in (
            "feature",
            "roadmap",
            "suggestion",
            "would love",
            "dark mode",
            "export csv",
            "фича",
            "добавьте",
            "предложен",
            "хотелось бы",
        )
    ):
        return LLMAnalysisOutput(
            category=TicketCategory.FEATURE_REQUEST,
            priority=TicketPriority.LOW,
            assigned_team=AssignedTeam.PRODUCT_TEAM,
            summary="Customer submitted a product enhancement or feature request.",
            draft_reply=(
                "Thank you for sharing this product suggestion. We have logged your feedback for "
                "our product team to evaluate for an upcoming release."
            ),
            confidence=0.88,
            needs_human_review=False,
            reasoning="Matched product feedback and feature-request phrasing.",
            cited_kb_ids=cited_kb_ids,
        )

    if any(
        kw in lower
        for kw in (
            "error",
            "500",
            "502",
            "504",
            "timeout",
            "api",
            "webhook",
            "bug",
            "crash",
            "latency",
            "outage",
            "down",
            "ошибк",
            "таймаут",
            "не работает",
            "падает",
            "вебхук",
        )
    ):
        if any(kw in lower for kw in ("outage", "down", "production", "500", "лежит")):
            priority = TicketPriority.CRITICAL
        elif any(kw in lower for kw in ("timeout", "fail", "crash", "webhook", "ошибк", "таймаут")):
            priority = TicketPriority.HIGH
        else:
            priority = TicketPriority.MEDIUM

        return LLMAnalysisOutput(
            category=TicketCategory.TECHNICAL,
            priority=priority,
            assigned_team=AssignedTeam.TECH_SUPPORT,
            summary="Customer reported a technical error, API failure, or service degradation.",
            draft_reply=(
                "Thanks for reporting this technical issue. Our engineering support team is "
                "investigating the error logs and will share diagnostic steps shortly."
            ),
            confidence=0.90,
            needs_human_review=priority == TicketPriority.CRITICAL,
            reasoning="Matched technical troubleshooting keywords for API/infrastructure support.",
            cited_kb_ids=cited_kb_ids,
        )

    return LLMAnalysisOutput(
        category=TicketCategory.OTHER,
        priority=TicketPriority.LOW,
        assigned_team=AssignedTeam.GENERAL_SUPPORT,
        summary="General customer inquiry requiring manual classification.",
        draft_reply=(
            "Thank you for contacting SupportFlow. A support specialist will review your "
            "message and get back to you with more details."
        ),
        confidence=0.72,
        needs_human_review=True,
        reasoning="No specific domain pattern matched; marked for human review.",
        cited_kb_ids=cited_kb_ids,
    )


class MockLLMProvider(BaseLLMProvider):
    """Deterministic heuristic provider supporting scripted responses for tests."""

    def __init__(
        self,
        *,
        model: str = "mock-heuristic-v1",
        scripted_outputs: list[str] | None = None,
        should_fail: bool = False,
    ) -> None:
        self.name = "mock"
        self.model = model
        self._scripted_outputs: list[str] = list(scripted_outputs or [])
        self.should_fail = should_fail
        self.call_count = 0
        self.prompts_received: list[str] = []

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
    ) -> ProviderReply:
        """Return scripted output when configured, else run deterministic heuristic triage."""
        del system_prompt, temperature
        self.call_count += 1
        self.prompts_received.append(user_prompt)

        if self.should_fail:
            raise LLMProviderError("Mock provider configured to fail")

        if self._scripted_outputs:
            content = self._scripted_outputs.pop(0)
            return ProviderReply(
                content=content,
                provider=self.name,
                model=self.model,
                latency_ms=1.0,
            )

        ticket_text = _extract_ticket_text(user_prompt)
        cited_kb_ids = list(dict.fromkeys(_KB_ID_RE.findall(user_prompt)))
        output = _classify_ticket_heuristically(ticket_text, cited_kb_ids)
        return ProviderReply(
            content=output.model_dump_json(),
            provider=self.name,
            model=self.model,
            latency_ms=1.0,
        )
