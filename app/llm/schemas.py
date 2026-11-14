"""Strict Pydantic v2 schemas for LLM triage analysis and security metadata."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.models.ticket import TicketCategory, TicketPriority


class AssignedTeam(StrEnum):
    """Normalized routing destinations for triaged tickets."""

    BILLING_OPS = "billing_ops"
    TECH_SUPPORT = "tech_support"
    ACCOUNT_SECURITY = "account_security"
    PRODUCT_TEAM = "product_team"
    GENERAL_SUPPORT = "general_support"


class LLMAnalysisOutput(BaseModel):
    """Strict structured output expected from the LLM triage step."""

    model_config = ConfigDict(extra="forbid")

    category: TicketCategory
    priority: TicketPriority
    assigned_team: AssignedTeam
    summary: str = Field(min_length=10, max_length=500)
    draft_reply: str = Field(min_length=20, max_length=4000)
    confidence: float = Field(ge=0.0, le=1.0)
    needs_human_review: bool
    reasoning: str = Field(min_length=10, max_length=1000)
    cited_kb_ids: list[str] = Field(default_factory=list)


class PromptInjectionReport(BaseModel):
    """Heuristic prompt-injection scan result and sanitized ticket content."""

    detected: bool
    risk_score: float = Field(ge=0.0, le=1.0)
    matched_patterns: list[str] = Field(default_factory=list)
    sanitized_subject: str
    sanitized_body: str


class LLMGenerationMeta(BaseModel):
    """Operational telemetry for an LLM analysis invocation."""

    provider: str
    model: str
    repair_attempts: int = Field(default=0, ge=0)
    fallback_used: bool = False
    latency_ms: float = Field(default=0.0, ge=0.0)


class TicketAnalysisBundle(BaseModel):
    """Complete result returned by TicketAnalyzer."""

    analysis: LLMAnalysisOutput
    security: PromptInjectionReport
    meta: LLMGenerationMeta
