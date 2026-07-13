#!/usr/bin/env python3
"""
Sync the model catalog (credits/rates.py) with the latest pricing data.

Source: litellm's community-maintained pricing JSON, updated on every
model release across all major providers.

Usage:
    python scripts/update_models.py            # add new models + rewrite rates.py
    python scripts/update_models.py --dry-run  # preview only, no file changes
"""
import json
import re
import sys
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError

# ── config ────────────────────────────────────────────────────────────────────

LITELLM_URL = (
    "https://raw.githubusercontent.com/BerriAI/litellm/main/"
    "model_prices_and_context_window.json"
)

RATES_FILE = Path(__file__).parent.parent / "credits" / "rates.py"

# litellm_provider → our provider key
# Google models use vertex_ai-language-models or gemini as their provider
PROVIDER_MAP = {
    "anthropic":                  "anthropic",
    "openai":                     "openai",
    "vertex_ai-language-models":  "google",
    "gemini":                     "google",
    "perplexity":                 "perplexity",
}

# Perplexity sonar models are stored as "perplexity/<model_id>" in litellm.
# We strip the prefix and look up with our_provider = "perplexity".
PERPLEXITY_PREFIX = "perplexity/"

# Only add models matching these regexes (per provider).
# Keeps old/deprecated/specialised models out of the catalog.
CURRENT_PATTERNS: dict[str, list[str]] = {
    "anthropic": [
        r"^claude-(haiku|sonnet|opus|fable)-\d",        # claude-sonnet-4-6, claude-opus-4-8
        r"^claude-[4-9]-?(opus|sonnet|haiku|fable)",    # claude-4-opus (v4+ alt naming)
        r"^claude-3-5-(sonnet|haiku)",                   # claude-3.5 family
        r"^claude-3-7-sonnet",                           # claude-3.7
    ],
    "openai": [
        r"^gpt-4o(-mini|-nano)?$",
        r"^gpt-4\.1(-mini|-nano|-pro)?$",
        r"^gpt-5(\.\d+)?(-mini|-nano|-pro|-turbo)?$",
        r"^o[1-9](-mini|-pro|-high)?$",
        r"^o[1-9]\.\d",
    ],
    # Match clean Gemini names only — no dated previews, no version suffixes (-001)
    # Examples that match: gemini-2.5-flash, gemini-3-flash-preview, gemini-3.1-flash-lite
    # Examples excluded: gemini-2.5-flash-preview-09-2025, gemini-2.0-flash-001
    "google": [
        r"^gemini-\d+[\.\d]*-(flash|pro|ultra)(-lite)?(-preview)?$",
    ],
    "perplexity": [
        r"^sonar(-pro|-reasoning(-pro)?|-deep-research)?$",
    ],
}

# Model IDs to never add regardless of patterns
BLOCKLIST = {
    "o1", "o1-mini", "o1-preview",
    "gpt-4", "gpt-4-turbo",
    "gemini-flash-latest", "gemini-flash-lite-latest", "gemini-pro-latest",
    "gemini-exp-1206",
}

# Skip any model whose ID matches these substrings
SKIP_SUBSTRINGS = [
    "audio", "tts", "realtime", "image", "embedding",
    "search-api", "transcribe", "codex", "chat-latest",
    "customtools", "robotics", "computer-use",
    "ft:", "diarize",
]

# ── helpers ───────────────────────────────────────────────────────────────────

def should_skip(model_id: str) -> bool:
    m = model_id.lower()
    return any(s in m for s in SKIP_SUBSTRINGS)


def strip_version_suffix(model_id: str) -> str:
    """Remove trailing date/version suffixes: -20250514, -001, -preview-09-2025."""
    s = re.sub(r"-\d{8}$", "", model_id)          # -20250514
    s = re.sub(r"-\d{3}$", "", s)                  # -001
    s = re.sub(r"-preview-\d{2}-\d{4}$", "", s)   # -preview-06-17
    s = re.sub(r"-preview-\d{4,}$", "", s)         # -preview-2025 / -preview-09-2025
    return s


def is_current(model_id: str, provider: str) -> bool:
    patterns = CURRENT_PATTERNS.get(provider, [])
    return any(re.search(p, model_id, re.IGNORECASE) for p in patterns)


def infer_speed_quality(model_id: str) -> tuple[int, int]:
    m = model_id.lower()
    # Flagship / reasoning tier
    if any(x in m for x in ["deep-research", "o1-pro", "o3-pro", "opus", "ultra"]):
        return 4, 10
    # Reasoning mid-tier
    if any(x in m for x in ["reasoning-pro", "reasoning", "o4-mini", "o3-mini", "o1-mini"]):
        return 6, 9
    # Pro / mid-tier (check before flash/lite to catch gemini-X-pro)
    if re.search(r"-pro(-|$)", m) or any(x in m for x in ["sonnet", "fable", "gpt-4o", "gpt-4.1", "gpt-5"]):
        return 8, 9
    # Fast / cheap tier (flash, mini, lite, nano, haiku)
    if any(x in m for x in ["haiku", "flash", "mini", "nano", "lite"]):
        return 10, 7
    return 7, 8


def make_label(model_id: str) -> str:
    s = strip_version_suffix(model_id)

    brand_subs = [
        (r"^claude-",  "Claude "),
        (r"^gpt-",     "GPT-"),
        (r"^o(\d+)-",  r"O\1 "),
        (r"^o(\d+)$",  r"O\1"),
        (r"^gemini-",  "Gemini "),
        (r"^sonar",    "Sonar"),
        (r"^llama-",   "Llama "),
    ]
    for pattern, replacement in brand_subs:
        new_s = re.sub(pattern, replacement, s, flags=re.IGNORECASE, count=1)
        if new_s != s:
            s = new_s
            break

    # Convert digit-hyphen-digit to decimal: 4-5 → 4.5
    s = re.sub(r"(\d)-(\d)", r"\1.\2", s)
    s = s.replace("-", " ").replace("_", " ")

    words = []
    for w in s.split():
        if w.upper() in ("GPT", "API", "LLM"):
            words.append(w.upper())
        else:
            words.append(w.capitalize())
    return " ".join(words)


def load_existing_catalog() -> dict:
    ns: dict = {}
    exec(RATES_FILE.read_text(), ns)  # noqa: S102
    return ns["MODEL_CATALOG"]


def fetch_litellm_pricing() -> dict:
    print("Fetching pricing data from litellm…")
    try:
        with urlopen(LITELLM_URL, timeout=15) as resp:
            data = json.loads(resp.read())
        print(f"  Got {len(data)} entries.")
        return data
    except URLError as e:
        print(f"ERROR: Could not fetch pricing data: {e}")
        sys.exit(1)


def _make_model_entry(model_id: str, our_provider: str, meta: dict) -> dict | None:
    """Build a catalog entry for a model. Returns None if pricing is missing."""
    inp = meta.get("input_cost_per_token")
    out = meta.get("output_cost_per_token")
    if not inp or not out:
        return None
    speed, quality = infer_speed_quality(model_id)
    return {
        "provider":  our_provider,
        "in":        round(inp * 1_000_000, 4),
        "out":       round(out * 1_000_000, 4),
        "speed":     speed,
        "quality":   quality,
        "label":     make_label(model_id),
    }


def find_new_models(litellm_data: dict, existing: dict) -> list[dict]:
    candidates: dict[str, dict] = {}  # model_id → entry

    # ── pass 1: standard entries (no slash in key) ───────────────────────────
    for raw_id, meta in litellm_data.items():
        if "/" in raw_id:
            continue
        our_provider = PROVIDER_MAP.get(meta.get("litellm_provider", ""))
        if not our_provider:
            continue

        model_id = strip_version_suffix(raw_id)

        if model_id in existing or model_id in BLOCKLIST:
            continue
        if should_skip(model_id):
            continue
        if not is_current(model_id, our_provider):
            continue

        entry = _make_model_entry(model_id, our_provider, meta)
        if entry and model_id not in candidates:
            candidates[model_id] = entry

    # ── pass 2: perplexity/sonar models (stored as "perplexity/<id>") ────────
    for raw_id, meta in litellm_data.items():
        if not raw_id.startswith(PERPLEXITY_PREFIX):
            continue
        model_id = raw_id[len(PERPLEXITY_PREFIX):]
        if "/" in model_id:  # skip nested like vercel_ai_gateway/perplexity/sonar
            continue

        if model_id in existing or model_id in BLOCKLIST:
            continue
        if should_skip(model_id):
            continue
        if not is_current(model_id, "perplexity"):
            continue

        entry = _make_model_entry(model_id, "perplexity", meta)
        if entry and model_id not in candidates:
            candidates[model_id] = entry

    new_models = [{"model_id": mid, **entry} for mid, entry in candidates.items()
                  if mid not in existing]
    return sorted(new_models, key=lambda x: (x["provider"], x["model_id"]))


# ── file writer ───────────────────────────────────────────────────────────────

PROVIDER_ORDER = ["anthropic", "openai", "google", "perplexity"]


def write_rates_py(catalog: dict) -> None:
    by_provider: dict[str, list[tuple[str, dict]]] = {p: [] for p in PROVIDER_ORDER}
    for model_id, meta in catalog.items():
        p = meta.get("provider", "openai")
        if p in by_provider:
            by_provider[p].append((model_id, meta))

    lines = [
        '"""Model cost rates (USD per 1 million tokens) and quality metadata."""\n',
        "\n",
        "# provider → display label + color\n",
        "PROVIDER_META: dict[str, dict] = {\n",
        '    "anthropic":  {"label": "Anthropic",  "color": "orange"},\n',
        '    "openai":     {"label": "OpenAI",     "color": "emerald"},\n',
        '    "google":     {"label": "Google",     "color": "blue"},\n',
        '    "perplexity": {"label": "Perplexity", "color": "purple"},\n',
        "}\n",
        "\n",
        "# model_id → {provider, in_per_m, out_per_m, speed, quality, label}\n",
        "# speed/quality: 1-10 ratings\n",
        "MODEL_CATALOG: dict[str, dict] = {\n",
    ]

    for provider in PROVIDER_ORDER:
        entries = by_provider.get(provider, [])
        if not entries:
            continue
        lines.append(f"    # {provider.capitalize()}\n")
        max_len = max(len(mid) for mid, _ in entries)
        for model_id, meta in entries:
            pad = " " * (max_len - len(model_id) + 1)
            lines.append(
                f'    "{model_id}":{pad}'
                f'{{"provider": "{meta["provider"]}", '
                f'"in": {meta["in"]:<8}, '
                f'"out": {meta["out"]:<8}, '
                f'"speed": {meta["speed"]},  '
                f'"quality": {meta["quality"]},  '
                f'"label": "{meta["label"]}"}},\n'
            )

    lines += [
        "}\n",
        "\n",
        "\n",
        "def compute_cost(model: str, input_tokens: int, output_tokens: int) -> float:\n",
        '    """Return cost in USD. Returns 0.0 for unknown models."""\n',
        '    meta = MODEL_CATALOG.get(model)\n',
        "    if not meta:\n",
        "        return 0.0\n",
        '    return (input_tokens * meta["in"] + output_tokens * meta["out"]) / 1_000_000\n',
    ]

    RATES_FILE.write_text("".join(lines))


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    dry_run = "--dry-run" in sys.argv

    existing = load_existing_catalog()
    print(f"Existing catalog: {len(existing)} models")

    litellm_data = fetch_litellm_pricing()
    new_models = find_new_models(litellm_data, existing)

    if not new_models:
        print("\nCatalog is up to date — no new models found.")
        return

    print(f"\nFound {len(new_models)} new model(s):\n")
    for m in new_models:
        print(
            f"  + [{m['provider']:10}]  {m['model_id']:<42}  "
            f"${m['in']}/M in   ${m['out']}/M out   "
            f"speed={m['speed']}  quality={m['quality']}  \"{m['label']}\""
        )

    if dry_run:
        print("\n[dry-run] No changes written.")
        return

    merged = dict(existing)
    for m in new_models:
        model_id = m.pop("model_id")
        merged[model_id] = m

    write_rates_py(merged)
    print(f"\nWrote {RATES_FILE.relative_to(Path(__file__).parent.parent.parent)} "
          f"({len(merged)} models total)")


if __name__ == "__main__":
    main()
