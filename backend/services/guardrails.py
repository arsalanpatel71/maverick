"""Input and output guardrails for LLM agent requests.

Input layer  — hard blocks (injection, length) + redaction of sensitive data.
Output layer — secret scrubbing and length truncation.

To add, remove, or disable a rule: edit the two config dicts below.
Everything else in this file reads from them automatically.
"""
from __future__ import annotations

import re


# ═══════════════════════════════════════════════════════════════════════════════
#  REDACTION CONFIG  —  the only section you need to edit
# ═══════════════════════════════════════════════════════════════════════════════
#
#  Format for both dicts:
#    "rule_name": ("regex_pattern", "REPLACEMENT_LABEL")
#
#  Comment out any entry to disable it.
#  Add new entries following the same pattern.
#
#  NOTE: emails and phone numbers are intentionally NOT redacted — they are
#  normal data in a sales context.  Only document-grade secrets are redacted.
# ───────────────────────────────────────────────────────────────────────────────

# Sensitive info stripped from the user's prompt BEFORE it reaches the LLM.
INPUT_REDACT_RULES: dict[str, tuple[str, str]] = {
    # US Social Security Number  e.g. 123-45-6789 / 123 45 6789 / 123456789
    "ssn": (
        r"\b\d{3}[\s\-]?\d{2}[\s\-]?\d{4}\b",
        "[REDACTED:SSN]",
    ),
    # Payment card numbers (Visa, MC, Amex, etc.)  e.g. 4111 1111 1111 1111
    "credit_card": (
        r"\b(?:\d{4}[\s\-]?){3}\d{4}\b",
        "[REDACTED:CREDIT_CARD]",
    ),
    # US / ICAO machine-readable passport  e.g. A12345678
    "passport": (
        r"\b[A-Z]{1,2}\d{6,9}\b",
        "[REDACTED:PASSPORT]",
    ),
    # Aadhaar (India 12-digit national ID)  e.g. 1234 5678 9012
    "aadhaar": (
        r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b",
        "[REDACTED:AADHAAR]",
    ),
    # National ID / Government ID when labelled explicitly in text
    "national_id_labelled": (
        r"(?:national\s+id|government\s+id|nid|nin)\s*[:#]?\s*[\w\d][\w\d\-\s]{4,19}\b",
        "[REDACTED:NATIONAL_ID]",
    ),
    # Bank account numbers when labelled explicitly in text
    "bank_account_labelled": (
        r"(?:account\s+(?:no|number|#)|acct\.?\s*(?:no|#)?)\s*[:#]?\s*\d[\d\s\-]{6,19}\b",
        "[REDACTED:BANK_ACCOUNT]",
    ),
}

# Secrets scrubbed from the LLM's response BEFORE it is returned to the client.
# Order matters — keep more-specific patterns above broader ones.
OUTPUT_REDACT_RULES: dict[str, tuple[str, str]] = {
    # Anthropic key (must come before generic sk- rule)
    "anthropic_key": (
        r"sk-ant-[A-Za-z0-9\-]{20,}",
        "[REDACTED:ANTHROPIC_KEY]",
    ),
    "openai_key": (
        r"sk-[A-Za-z0-9]{20,}",
        "[REDACTED:OPENAI_KEY]",
    ),
    "google_key": (
        r"AIza[0-9A-Za-z\-_]{30,}",
        "[REDACTED:GOOGLE_KEY]",
    ),
    "perplexity_key": (
        r"pplx-[A-Za-z0-9]{20,}",
        "[REDACTED:PERPLEXITY_KEY]",
    ),
    # Generic credential assignments  e.g. api_key = "abc123xyz"
    "generic_secret": (
        r'(?:password|passwd|secret|token|api[_\-]?key)\s*[=:]\s*["\']?[A-Za-z0-9\-_.]{8,}["\']?',
        "[REDACTED:SECRET]",
    ),
}

# ═══════════════════════════════════════════════════════════════════════════════
#  Internal: compile rules once at import time
# ═══════════════════════════════════════════════════════════════════════════════

_COMPILED_INPUT: list[tuple[str, re.Pattern, str]] = [
    (name, re.compile(pattern, re.IGNORECASE), replacement)
    for name, (pattern, replacement) in INPUT_REDACT_RULES.items()
]

_COMPILED_OUTPUT: list[tuple[re.Pattern, str]] = [
    (re.compile(pattern, re.IGNORECASE), replacement)
    for _, (pattern, replacement) in OUTPUT_REDACT_RULES.items()
]

MAX_INPUT_CHARS = 20_000
MAX_OUTPUT_CHARS = 50_000


# ─── Violation ────────────────────────────────────────────────────────────────


class GuardrailViolation(Exception):
    def __init__(self, detail: str, violation_type: str) -> None:
        self.detail = detail
        self.violation_type = violation_type
        super().__init__(detail)


# ─── Injection patterns (hard block) ─────────────────────────────────────────

_INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|directives?)",
        r"disregard\s+(all\s+)?(previous|prior)\s+instructions?",
        r"forget\s+(everything|all)\s+(you|i)\s+(know|said|told)",
        r"you\s+are\s+now\s+(?:a|an)\s+",
        r"\bjailbreak\b",
        r"\bdan\s+mode\b",
        r"\bdeveloper\s+mode\b",
        r"bypass\s+(?:your\s+)?(?:safety|ethical|content)\s+(?:guidelines?|filters?|restrictions?)",
        r"act\s+as\s+if\s+you\s+(?:have\s+no|don.t\s+have)\s+restrictions?",
        r"<\s*script[\s>]",
    ]
]


# ─── Public API ───────────────────────────────────────────────────────────────


def check_input(prompt: str) -> None:
    """Hard-block check. Raises GuardrailViolation on injection or length."""
    if len(prompt) > MAX_INPUT_CHARS:
        raise GuardrailViolation(
            f"Prompt exceeds the {MAX_INPUT_CHARS:,}-character limit.",
            "input_too_long",
        )
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(prompt):
            raise GuardrailViolation(
                "Prompt contains a potential injection pattern and was rejected.",
                "prompt_injection",
            )


def redact_input(prompt: str) -> tuple[str, list[str]]:
    """Replace sensitive document data in the prompt with labeled placeholders.

    Returns (cleaned_prompt, list_of_redacted_rule_names).
    The LLM receives the cleaned version; the caller can surface what was redacted.
    """
    redacted: list[str] = []
    for name, pattern, replacement in _COMPILED_INPUT:
        cleaned, n = pattern.subn(replacement, prompt)
        if n:
            prompt = cleaned
            redacted.append(name)
    return prompt, redacted


def scrub_output(content: str) -> str:
    """Redact API keys / secrets from model output and enforce max length."""
    for pattern, replacement in _COMPILED_OUTPUT:
        content = pattern.sub(replacement, content)
    return content[:MAX_OUTPUT_CHARS]
