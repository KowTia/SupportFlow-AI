"""Prompt injection detection and untrusted input sanitization."""

import re

from app.llm.schemas import PromptInjectionReport

_INJECTION_RULES: list[tuple[str, re.Pattern[str], float]] = [
    (
        "instruction_override",
        re.compile(
            r"(ignore\s+(?:all\s+|any\s+)?(?:previous|prior|above)\s+(?:instructions|prompts|rules)"
            r"|игнорируй(?:те)?\s+(?:все\s+)?(?:предыдущие|прошлые|системные)\s+"
            r"(?:инструкции|правила|промпты)"
            r"|забудь\s+(?:все\s+)?(?:инструкции|правила))",
            re.IGNORECASE,
        ),
        0.6,
    ),
    (
        "role_hijack",
        re.compile(
            r"(you\s+are\s+now|act\s+as\s+system|new\s+system\s+prompt"
            r"|ты\s+теперь|действуй\s+как\s+администратор)",
            re.IGNORECASE,
        ),
        0.5,
    ),
    (
        "delimiter_breakout",
        re.compile(
            r"(</?untrusted_ticket>|</?system>|<\|im_start\|>|<\|im_end\|>|\[SYSTEM\])",
            re.IGNORECASE,
        ),
        0.7,
    ),
    (
        "prompt_leak",
        re.compile(
            r"((?:reveal|print|show|output)\s+(?:your\s+|the\s+)?(?:system|initial|hidden)\s+"
            r"(?:prompt|instructions)"
            r"|(?:покажи|выведи)\s+(?:свой\s+)?(?:системный\s+промпт|скрытые\s+инструкции))",
            re.IGNORECASE,
        ),
        0.6,
    ),
    (
        "forced_json_override",
        re.compile(
            r"(return\s+only\s+json|set\s+priority\s+to|set\s+category\s+to"
            r"|auto_approve|выдай\s+json)",
            re.IGNORECASE,
        ),
        0.5,
    ),
]

_ESCAPE_TAGS_RE = re.compile(
    r"(</?untrusted_ticket>|</?system>|<\|im_start\|>|<\|im_end\|>|\[SYSTEM\])",
    re.IGNORECASE,
)


def sanitize_untrusted_text(text: str) -> str:
    """Neutralize XML/chat-template delimiter tags inside untrusted ticket content."""
    return _ESCAPE_TAGS_RE.sub("[ESCAPED_TAG]", text)


def inspect_prompt_injection(subject: str, body: str) -> PromptInjectionReport:
    """Scan ticket subject/body for prompt injection patterns and return sanitized text."""
    combined = f"{subject}\n{body}"
    matched_patterns: list[str] = []
    score = 0.0

    for rule_name, pattern, weight in _INJECTION_RULES:
        if pattern.search(combined):
            matched_patterns.append(rule_name)
            score += weight

    risk_score = min(1.0, round(score, 2))
    return PromptInjectionReport(
        detected=len(matched_patterns) > 0,
        risk_score=risk_score,
        matched_patterns=matched_patterns,
        sanitized_subject=sanitize_untrusted_text(subject),
        sanitized_body=sanitize_untrusted_text(body),
    )
