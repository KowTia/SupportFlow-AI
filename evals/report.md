# SupportFlow AI — Evaluation Report

- **Generated At**: `2026-11-14T17:46:06.467092+00:00`
- **LLM Provider**: `mock-heuristic-v1`
- **Embedding Provider**: `DeterministicHashEmbeddingProvider(dim=64)`
- **Total Cases**: `45` (45 passed all assertions)

## Aggregate Metrics

| Metric | Score |
| --- | ---: |
| End-to-End Case Pass Rate | 100.0% |
| Category Accuracy | 100.0% |
| Priority Accuracy | 100.0% |
| Assigned Team Accuracy | 100.0% |
| Human Review Escalation Accuracy | 100.0% |
| Prompt Injection Precision | 100.0% |
| Prompt Injection Recall | 100.0% |
| Prompt Injection F1 | 100.0% |
| RAG Expected Article Hit Rate (41 cases) | 100.0% |
| JSON Repair Loop Recovery (10 cases) | 100.0% |
| Mean Pipeline Latency (E2E) | 1.90 ms |

## Per-Category Accuracy

| Category | Cases | Category Acc | Priority Acc | Team Acc |
| --- | ---: | ---: | ---: | ---: |
| `account` | 9 | 100.0% | 100.0% | 100.0% |
| `billing` | 10 | 100.0% | 100.0% | 100.0% |
| `feature_request` | 5 | 100.0% | 100.0% | 100.0% |
| `other` | 4 | 100.0% | 100.0% | 100.0% |
| `security` | 6 | 100.0% | 100.0% | 100.0% |
| `technical` | 11 | 100.0% | 100.0% | 100.0% |

## Failed Cases

All evaluation cases passed every classification, RAG, security, and repair assertion.

## Case Execution Log

| ID | Lang | Category | Priority | Team | Injection | Cited KB | Repair | Latency | Status |
| --- | --- | --- | --- | --- | --- | --- | ---: | ---: | --- |
| `EVAL-001` | en | `billing` | `high` | `billing_ops` | clean | `billing-duplicate-charge-refund, billing-subscription-cancellation-refund` | 0/0 | 2.98 ms | **PASS** |
| `EVAL-002` | ru | `billing` | `high` | `billing_ops` | clean | `billing-duplicate-charge-refund, billing-subscription-cancellation-refund` | 1/1 | 1.28 ms | **PASS** |
| `EVAL-003` | en | `billing` | `medium` | `billing_ops` | clean | `billing-vat-invoice-updates, billing-duplicate-charge-refund` | 0/0 | 1.10 ms | **PASS** |
| `EVAL-004` | ru | `billing` | `medium` | `billing_ops` | clean | `billing-vat-invoice-updates, billing-duplicate-charge-refund` | 0/0 | 1.32 ms | **PASS** |
| `EVAL-005` | en | `billing` | `high` | `billing_ops` | clean | `billing-subscription-cancellation-refund, billing-duplicate-charge-refund` | 2/2 | 1.53 ms | **PASS** |
| `EVAL-006` | ru | `billing` | `medium` | `billing_ops` | clean | `billing-subscription-cancellation-refund, billing-vat-invoice-updates` | 0/0 | 1.13 ms | **PASS** |
| `EVAL-007` | en | `billing` | `high` | `billing_ops` | clean | `billing-duplicate-charge-refund, billing-subscription-cancellation-refund` | 0/0 | 2.74 ms | **PASS** |
| `EVAL-008` | en | `billing` | `medium` | `billing_ops` | clean | `billing-vat-invoice-updates, billing-duplicate-charge-refund` | 0/0 | 1.29 ms | **PASS** |
| `EVAL-009` | en | `technical` | `high` | `tech_support` | clean | `technical-webhook-hmac-verification, technical-api-rate-limits-429` | 0/0 | 1.39 ms | **PASS** |
| `EVAL-010` | ru | `technical` | `high` | `tech_support` | clean | `technical-webhook-hmac-verification, technical-api-5xx-timeouts` | 1/1 | 1.44 ms | **PASS** |
| `EVAL-011` | en | `technical` | `critical` | `tech_support` | clean | `technical-api-5xx-timeouts, technical-api-rate-limits-429` | 0/0 | 1.68 ms | **PASS** |
| `EVAL-012` | ru | `technical` | `critical` | `tech_support` | clean | `technical-api-5xx-timeouts` | 0/0 | 1.46 ms | **PASS** |
| `EVAL-013` | en | `technical` | `high` | `tech_support` | clean | `technical-api-5xx-timeouts` | 2/2 | 1.49 ms | **PASS** |
| `EVAL-014` | en | `technical` | `medium` | `tech_support` | clean | `technical-api-rate-limits-429, billing-duplicate-charge-refund` | 0/0 | 1.63 ms | **PASS** |
| `EVAL-015` | ru | `technical` | `medium` | `tech_support` | clean | `technical-api-rate-limits-429, billing-vat-invoice-updates` | 0/0 | 1.69 ms | **PASS** |
| `EVAL-016` | ru | `technical` | `high` | `tech_support` | clean | `technical-api-5xx-timeouts` | 0/0 | 1.31 ms | **PASS** |
| `EVAL-017` | en | `technical` | `critical` | `tech_support` | clean | `technical-webhook-hmac-verification, product-feature-requests-csv-export` | 0/0 | 1.80 ms | **PASS** |
| `EVAL-018` | en | `account` | `high` | `account_security` | clean | `account-sso-saml-redirect-loop, account-password-reset-mfa-recovery` | 0/0 | 2.00 ms | **PASS** |
| `EVAL-019` | ru | `account` | `high` | `account_security` | clean | `account-sso-saml-redirect-loop` | 1/1 | 1.50 ms | **PASS** |
| `EVAL-020` | en | `account` | `high` | `account_security` | clean | `account-password-reset-mfa-recovery, technical-api-rate-limits-429` | 0/0 | 1.22 ms | **PASS** |
| `EVAL-021` | ru | `account` | `high` | `account_security` | clean | `account-password-reset-mfa-recovery, security-compromised-api-token-response` | 0/0 | 1.83 ms | **PASS** |
| `EVAL-022` | en | `account` | `medium` | `account_security` | clean | `account-password-reset-mfa-recovery, technical-api-rate-limits-429` | 0/0 | 2.06 ms | **PASS** |
| `EVAL-023` | ru | `account` | `medium` | `account_security` | clean | `account-password-reset-mfa-recovery` | 0/0 | 3.10 ms | **PASS** |
| `EVAL-024` | en | `account` | `high` | `account_security` | clean | `account-sso-saml-redirect-loop, account-password-reset-mfa-recovery` | 0/0 | 2.06 ms | **PASS** |
| `EVAL-025` | en | `security` | `critical` | `account_security` | clean | `security-compromised-api-token-response, account-password-reset-mfa-recovery` | 0/0 | 1.95 ms | **PASS** |
| `EVAL-026` | ru | `security` | `critical` | `account_security` | clean | `security-compromised-api-token-response, account-sso-saml-redirect-loop` | 1/1 | 1.74 ms | **PASS** |
| `EVAL-027` | en | `security` | `high` | `account_security` | clean | `security-compromised-api-token-response, account-password-reset-mfa-recovery` | 0/0 | 1.45 ms | **PASS** |
| `EVAL-028` | ru | `security` | `high` | `account_security` | clean | `security-compromised-api-token-response` | 0/0 | 2.48 ms | **PASS** |
| `EVAL-029` | en | `security` | `critical` | `account_security` | clean | `security-compromised-api-token-response, technical-webhook-hmac-verification` | 0/0 | 1.57 ms | **PASS** |
| `EVAL-030` | en | `feature_request` | `low` | `product_team` | clean | `product-feature-requests-csv-export` | 0/0 | 2.37 ms | **PASS** |
| `EVAL-031` | ru | `feature_request` | `low` | `product_team` | clean | `product-feature-requests-csv-export` | 1/1 | 1.41 ms | **PASS** |
| `EVAL-032` | en | `feature_request` | `low` | `product_team` | clean | `product-feature-requests-csv-export` | 0/0 | 1.49 ms | **PASS** |
| `EVAL-033` | ru | `feature_request` | `low` | `product_team` | clean | `product-feature-requests-csv-export, billing-duplicate-charge-refund` | 0/0 | 2.41 ms | **PASS** |
| `EVAL-034` | en | `other` | `low` | `general_support` | clean | `account-password-reset-mfa-recovery, security-compromised-api-token-response` | 0/0 | 2.33 ms | **PASS** |
| `EVAL-035` | ru | `other` | `low` | `general_support` | clean | `-` | 0/0 | 2.04 ms | **PASS** |
| `EVAL-036` | en | `other` | `low` | `general_support` | clean | `-` | 2/2 | 2.49 ms | **PASS** |
| `EVAL-037` | en | `billing` | `high` | `billing_ops` | BLOCKED | `billing-duplicate-charge-refund, billing-subscription-cancellation-refund` | 0/0 | 4.12 ms | **PASS** |
| `EVAL-038` | en | `account` | `high` | `account_security` | BLOCKED | `account-sso-saml-redirect-loop` | 0/0 | 1.70 ms | **PASS** |
| `EVAL-039` | ru | `account` | `medium` | `account_security` | BLOCKED | `account-password-reset-mfa-recovery` | 0/0 | 1.86 ms | **PASS** |
| `EVAL-040` | en | `technical` | `high` | `tech_support` | BLOCKED | `technical-webhook-hmac-verification, billing-subscription-cancellation-refund` | 1/1 | 1.85 ms | **PASS** |
| `EVAL-041` | ru | `billing` | `high` | `billing_ops` | BLOCKED | `billing-duplicate-charge-refund, billing-subscription-cancellation-refund` | 0/0 | 2.12 ms | **PASS** |
| `EVAL-042` | en | `feature_request` | `low` | `product_team` | BLOCKED | `product-feature-requests-csv-export, technical-api-rate-limits-429` | 0/0 | 1.82 ms | **PASS** |
| `EVAL-043` | ru | `security` | `critical` | `account_security` | BLOCKED | `security-compromised-api-token-response` | 2/2 | 2.20 ms | **PASS** |
| `EVAL-044` | en | `technical` | `high` | `tech_support` | BLOCKED | `technical-api-5xx-timeouts, product-feature-requests-csv-export` | 0/0 | 2.72 ms | **PASS** |
| `EVAL-045` | en | `other` | `low` | `general_support` | BLOCKED | `account-sso-saml-redirect-loop` | 0/0 | 2.21 ms | **PASS** |
