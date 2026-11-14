# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in **SupportFlow AI**, please report it responsibly by opening a private security advisory on GitHub rather than filing a public issue.

Please include:
- A clear description of the vulnerability and affected component
- Steps to reproduce or a minimal proof of concept
- Potential impact and any suggested remediation

## Built-in Security Controls

SupportFlow AI is designed with defense-in-depth for untrusted customer input and outbound integrations:

- **Prompt Injection Guard (`app/llm/security.py`)**: Scans bilingual (`EN`/`RU`) inputs for instruction overrides, role hijacking, delimiter breakouts, prompt leaks, and forced JSON overrides; neutralizes breakout tags and forces `awaiting_review` escalation when detected.
- **Strict Output Validation (`app/llm/schemas.py`)**: Enforces Pydantic v2 schemas (`extra="forbid"`) on all LLM responses before persistence or routing.
- **Signed Webhooks (`app/integrations/webhooks.py`)**: Signs outbound webhook payloads with `HMAC-SHA256` (`X-SupportFlow-Signature`, `X-SupportFlow-Timestamp`).
- **Safe Integration Defaults**: Both `WEBHOOK_DRY_RUN` and `GOOGLE_SHEETS_DRY_RUN` default to `true` in `.env.example`.
