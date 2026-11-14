"""Curated knowledge base seed articles for SupportFlow AI."""

from typing import Any

from app.models.ticket import TicketCategory

SEED_KB_ARTICLES: list[dict[str, Any]] = [
    {
        "slug": "billing-duplicate-charge-refund",
        "title": "Handling Duplicate Card Charges and Pending Authorizations",
        "category": TicketCategory.BILLING,
        "tags": ["billing", "duplicate", "charge", "card", "refund", "оплата", "двойное списание"],
        "content": (
            "Duplicate card charges usually occur when a payment retry overlaps with an "
            "authorization hold. Verify whether one transaction is still in 'pending' state "
            "(auto-expires in 3-5 business days). If two settled charges exist for the same "
            "invoice ID, issue a full refund for the duplicate charge via Billing Ops within "
            "24 hours and confirm the refund reference ID to the customer."
        ),
    },
    {
        "slug": "billing-vat-invoice-updates",
        "title": "Adding VAT IDs, Tax Details, and Downloading PDF Invoices",
        "category": TicketCategory.BILLING,
        "tags": ["invoice", "vat", "tax", "pdf", "billing", "счет", "ндс"],
        "content": (
            "Workspace admins can update company legal name, billing address, and VAT/Tax ID "
            "under Settings -> Billing -> Tax Details. Newly generated monthly PDF invoices "
            "reflect updated tax information automatically. Past paid invoices requiring "
            "retroactive VAT edits must be re-issued manually by Billing Operations."
        ),
    },
    {
        "slug": "billing-subscription-cancellation-refund",
        "title": "Subscription Cancellation, Proration, and Refund Policy",
        "category": TicketCategory.BILLING,
        "tags": ["subscription", "cancel", "refund", "proration", "подписка", "возврат"],
        "content": (
            "Annual plans canceled within 14 days of purchase or renewal qualify for a full "
            "refund. Monthly subscriptions remain active until the end of the current billing "
            "cycle without partial proration unless an accidental duplicate renewal occurred. "
            "Downgrading seats applies credit toward the next invoice."
        ),
    },
    {
        "slug": "technical-webhook-hmac-verification",
        "title": "Verifying Outbound Webhook HMAC-SHA256 Signatures",
        "category": TicketCategory.TECHNICAL,
        "tags": ["webhook", "hmac", "sha256", "signature", "retry", "вебхук", "подпись"],
        "content": (
            "Every webhook request includes X-SupportFlow-Signature formatted as "
            "'sha256=<hex_digest>' computed over the exact raw UTF-8 request body using your "
            "workspace webhook secret. Signature mismatches happen when frameworks parse and "
            "re-serialize JSON before computing the HMAC, or when whitespace changes. Use "
            "constant-time comparison (hmac.compare_digest) against the raw HTTP payload."
        ),
    },
    {
        "slug": "technical-api-5xx-timeouts",
        "title": "Troubleshooting API 500/502 Errors and Gateway Timeouts",
        "category": TicketCategory.TECHNICAL,
        "tags": ["api", "500", "502", "504", "timeout", "latency", "ошибка", "таймаут"],
        "content": (
            "Intermittent HTTP 500, 502, or 504 gateway timeouts typically point to oversized "
            "batch payloads, upstream connection pool exhaustion, or missing Idempotency-Key "
            "headers during retries. Recommend splitting batch requests below 100 items, "
            "setting client timeouts >= 15s, and always sending an Idempotency-Key header on "
            "POST requests so retries remain safe."
        ),
    },
    {
        "slug": "technical-api-rate-limits-429",
        "title": "API Rate Limit Quotas, Headers, and 429 Exponential Backoff",
        "category": TicketCategory.TECHNICAL,
        "tags": ["rate limit", "429", "quota", "headers", "backoff", "лимит"],
        "content": (
            "API responses include X-RateLimit-Limit, X-RateLimit-Remaining, and "
            "X-RateLimit-Reset headers. Standard workspaces receive 120 requests/minute and "
            "Pro workspaces receive 600 requests/minute. When receiving HTTP 429, respect the "
            "Retry-After header and apply jittered exponential backoff before retrying."
        ),
    },
    {
        "slug": "account-sso-saml-redirect-loop",
        "title": "Resolving SAML SSO Login Redirect Loops (Okta / Azure AD)",
        "category": TicketCategory.ACCOUNT,
        "tags": ["sso", "saml", "okta", "login", "redirect", "вход", "авторизация"],
        "content": (
            "SAML redirect loops after identity provider login usually result from mismatched "
            "ACS URLs, expired X.509 signing certificates, or clock skew exceeding 120 seconds. "
            "Verify that the NameID format is set to EmailAddress, confirm the ACS URL matches "
            "https://app.supportflow.dev/sso/saml/acs, and test with an incognito browser to "
            "rule out stale session cookies."
        ),
    },
    {
        "slug": "account-password-reset-mfa-recovery",
        "title": "Password Reset Delivery Issues and MFA Device Recovery",
        "category": TicketCategory.ACCOUNT,
        "tags": ["password", "mfa", "2fa", "locked", "email", "пароль", "аккаунт"],
        "content": (
            "If password reset emails fail to arrive on corporate domains, ask the IT team to "
            "allowlist mailer@supportflow.dev and check quarantine filters. For locked accounts "
            "or lost MFA authenticator devices, a workspace owner can reset 2FA from Admin -> "
            "Members, or Account Security can verify identity via backup recovery codes."
        ),
    },
    {
        "slug": "security-compromised-api-token-response",
        "title": "Immediate Response for Leaked API Keys or Unauthorized Access",
        "category": TicketCategory.SECURITY,
        "tags": ["security", "leak", "token", "breach", "unauthorized", "утечка", "взлом"],
        "content": (
            "If an API token or webhook secret is exposed in logs, git commits, or suspected "
            "unauthorized sessions, immediately revoke the token in Settings -> API Keys, "
            "invalidate active workspace sessions, and rotate webhook signing secrets. Escalate "
            "all potential breach or unauthorized access reports to Account Security with "
            "affected timestamps and IP addresses from the Audit Log."
        ),
    },
    {
        "slug": "product-feature-requests-csv-export",
        "title": "Feature Requests, Public Roadmap, and Scheduled CSV Exports",
        "category": TicketCategory.FEATURE_REQUEST,
        "tags": ["feature", "roadmap", "csv", "export", "suggestion", "фича", "экспорт"],
        "content": (
            "Enhancement requests and roadmap ideas should be logged with customer workspace "
            "tier and workflow use-case for the Product Team. Note that manual ticket CSV "
            "exports are available via the Reports tab, while automated scheduled exports and "
            "custom dashboard widgets are tracked on the Q4 product roadmap."
        ),
    },
]
