"""Model cost rates (USD per 1 million tokens) and quality metadata."""

# provider → display label + color
PROVIDER_META: dict[str, dict] = {
    "anthropic":  {"label": "Anthropic",  "color": "orange"},
    "openai":     {"label": "OpenAI",     "color": "emerald"},
    "google":     {"label": "Google",     "color": "blue"},
    "perplexity": {"label": "Perplexity", "color": "purple"},
}

# model_id → {provider, in_per_m, out_per_m, speed, quality, label}
# speed/quality: 1-10 ratings
MODEL_CATALOG: dict[str, dict] = {
    # Anthropic
    "claude-haiku-4-5":  {"provider": "anthropic", "in": 0.8     , "out": 4.0     , "speed": 10,  "quality": 7,  "label": "Claude Haiku 4.5"},
    "claude-sonnet-4-6": {"provider": "anthropic", "in": 3.0     , "out": 15.0    , "speed": 8,  "quality": 9,  "label": "Claude Sonnet 4.6"},
    "claude-opus-4-8":   {"provider": "anthropic", "in": 15.0    , "out": 75.0    , "speed": 5,  "quality": 10,  "label": "Claude Opus 4.8"},
    "claude-3-7-sonnet": {"provider": "anthropic", "in": 3.0     , "out": 15.0    , "speed": 8,  "quality": 9,  "label": "Claude 3.7 Sonnet"},
    "claude-fable-5":    {"provider": "anthropic", "in": 10.0    , "out": 50.0    , "speed": 8,  "quality": 9,  "label": "Claude Fable 5"},
    "claude-opus-4":     {"provider": "anthropic", "in": 15.0    , "out": 75.0    , "speed": 4,  "quality": 10,  "label": "Claude Opus 4"},
    "claude-opus-4-1":   {"provider": "anthropic", "in": 15.0    , "out": 75.0    , "speed": 4,  "quality": 10,  "label": "Claude Opus 4.1"},
    "claude-opus-4-5":   {"provider": "anthropic", "in": 5.0     , "out": 25.0    , "speed": 4,  "quality": 10,  "label": "Claude Opus 4.5"},
    "claude-opus-4-6":   {"provider": "anthropic", "in": 5.0     , "out": 25.0    , "speed": 4,  "quality": 10,  "label": "Claude Opus 4.6"},
    "claude-opus-4-7":   {"provider": "anthropic", "in": 5.0     , "out": 25.0    , "speed": 4,  "quality": 10,  "label": "Claude Opus 4.7"},
    "claude-sonnet-4":   {"provider": "anthropic", "in": 3.0     , "out": 15.0    , "speed": 8,  "quality": 9,  "label": "Claude Sonnet 4"},
    "claude-sonnet-4-5": {"provider": "anthropic", "in": 3.0     , "out": 15.0    , "speed": 8,  "quality": 9,  "label": "Claude Sonnet 4.5"},
    "claude-sonnet-5":   {"provider": "anthropic", "in": 2.0     , "out": 10.0    , "speed": 8,  "quality": 9,  "label": "Claude Sonnet 5"},
    "claude-4-opus":     {"provider": "anthropic", "in": 15.0    , "out": 75.0    , "speed": 4,  "quality": 10,  "label": "Claude 4 Opus"},
    "claude-4-sonnet":   {"provider": "anthropic", "in": 3.0     , "out": 15.0    , "speed": 8,  "quality": 9,  "label": "Claude 4 Sonnet"},
    # Openai
    "gpt-4o-mini":  {"provider": "openai", "in": 0.15    , "out": 0.6     , "speed": 10,  "quality": 7,  "label": "GPT-4o Mini"},
    "gpt-4o":       {"provider": "openai", "in": 2.5     , "out": 10.0    , "speed": 7,  "quality": 9,  "label": "GPT-4o"},
    "gpt-4.1":      {"provider": "openai", "in": 2.0     , "out": 8.0     , "speed": 8,  "quality": 9,  "label": "GPT-4.1"},
    "o4-mini":      {"provider": "openai", "in": 1.1     , "out": 4.4     , "speed": 7,  "quality": 9,  "label": "o4-mini"},
    "o3":           {"provider": "openai", "in": 10.0    , "out": 40.0    , "speed": 4,  "quality": 10,  "label": "o3"},
    "gpt-4.1-mini": {"provider": "openai", "in": 0.4     , "out": 1.6     , "speed": 10,  "quality": 7,  "label": "GPT 4.1 Mini"},
    "gpt-4.1-nano": {"provider": "openai", "in": 0.1     , "out": 0.4     , "speed": 10,  "quality": 7,  "label": "GPT 4.1 Nano"},
    "gpt-5":        {"provider": "openai", "in": 1.25    , "out": 10.0    , "speed": 8,  "quality": 9,  "label": "GPT 5"},
    "gpt-5-mini":   {"provider": "openai", "in": 0.25    , "out": 2.0     , "speed": 10,  "quality": 7,  "label": "GPT 5 Mini"},
    "gpt-5-nano":   {"provider": "openai", "in": 0.05    , "out": 0.4     , "speed": 10,  "quality": 7,  "label": "GPT 5 Nano"},
    "gpt-5.1":      {"provider": "openai", "in": 1.25    , "out": 10.0    , "speed": 8,  "quality": 9,  "label": "GPT 5.1"},
    "gpt-5.2":      {"provider": "openai", "in": 1.75    , "out": 14.0    , "speed": 8,  "quality": 9,  "label": "GPT 5.2"},
    "gpt-5.4":      {"provider": "openai", "in": 2.5     , "out": 15.0    , "speed": 8,  "quality": 9,  "label": "GPT 5.4"},
    "gpt-5.4-mini": {"provider": "openai", "in": 0.75    , "out": 4.5     , "speed": 10,  "quality": 7,  "label": "GPT 5.4 Mini"},
    "gpt-5.4-nano": {"provider": "openai", "in": 0.2     , "out": 1.25    , "speed": 10,  "quality": 7,  "label": "GPT 5.4 Nano"},
    "gpt-5.5":      {"provider": "openai", "in": 5.0     , "out": 30.0    , "speed": 8,  "quality": 9,  "label": "GPT 5.5"},
    "o1-pro":       {"provider": "openai", "in": 150.0   , "out": 600.0   , "speed": 4,  "quality": 10,  "label": "O1 Pro"},
    "o3-mini":      {"provider": "openai", "in": 1.1     , "out": 4.4     , "speed": 10,  "quality": 7,  "label": "O3 Mini"},
    "o3-pro":       {"provider": "openai", "in": 20.0    , "out": 80.0    , "speed": 4,  "quality": 10,  "label": "O3 Pro"},
    "gpt-5-pro":    {"provider": "openai", "in": 15.0    , "out": 120.0   , "speed": 8,  "quality": 9,  "label": "GPT 5 Pro"},
    "gpt-5.2-pro":  {"provider": "openai", "in": 21.0    , "out": 168.0   , "speed": 8,  "quality": 9,  "label": "GPT 5.2 Pro"},
    "gpt-5.4-pro":  {"provider": "openai", "in": 30.0    , "out": 180.0   , "speed": 8,  "quality": 9,  "label": "GPT 5.4 Pro"},
    "gpt-5.5-pro":  {"provider": "openai", "in": 30.0    , "out": 180.0   , "speed": 8,  "quality": 9,  "label": "GPT 5.5 Pro"},
    # Google
    "gemini-2.0-flash":              {"provider": "google", "in": 0.1     , "out": 0.4     , "speed": 10,  "quality": 7,  "label": "Gemini 2.0 Flash"},
    "gemini-2.5-pro":                {"provider": "google", "in": 1.25    , "out": 10.0    , "speed": 6,  "quality": 9,  "label": "Gemini 2.5 Pro"},
    "gemini-1.5-pro":                {"provider": "google", "in": 1.25    , "out": 5.0     , "speed": 7,  "quality": 8,  "label": "Gemini 1.5 Pro"},
    "gemini-2.0-flash-lite":         {"provider": "google", "in": 0.075   , "out": 0.3     , "speed": 10,  "quality": 7,  "label": "Gemini 2.0 Flash Lite"},
    "gemini-2.5-flash":              {"provider": "google", "in": 0.3     , "out": 2.5     , "speed": 10,  "quality": 7,  "label": "Gemini 2.5 Flash"},
    "gemini-2.5-flash-lite":         {"provider": "google", "in": 0.1     , "out": 0.4     , "speed": 10,  "quality": 7,  "label": "Gemini 2.5 Flash Lite"},
    "gemini-3-flash-preview":        {"provider": "google", "in": 0.5     , "out": 3.0     , "speed": 10,  "quality": 7,  "label": "Gemini 3 Flash Preview"},
    "gemini-3-pro-preview":          {"provider": "google", "in": 2.0     , "out": 12.0    , "speed": 8,  "quality": 9,  "label": "Gemini 3 Pro Preview"},
    "gemini-3.1-flash-lite":         {"provider": "google", "in": 0.25    , "out": 1.5     , "speed": 10,  "quality": 7,  "label": "Gemini 3.1 Flash Lite"},
    "gemini-3.1-flash-lite-preview": {"provider": "google", "in": 0.25    , "out": 1.5     , "speed": 10,  "quality": 7,  "label": "Gemini 3.1 Flash Lite Preview"},
    "gemini-3.1-pro-preview":        {"provider": "google", "in": 2.0     , "out": 12.0    , "speed": 8,  "quality": 9,  "label": "Gemini 3.1 Pro Preview"},
    "gemini-3.5-flash":              {"provider": "google", "in": 1.5     , "out": 9.0     , "speed": 10,  "quality": 7,  "label": "Gemini 3.5 Flash"},
    # Perplexity
    "sonar":               {"provider": "perplexity", "in": 1.0     , "out": 1.0     , "speed": 9,  "quality": 8,  "label": "Sonar"},
    "sonar-pro":           {"provider": "perplexity", "in": 3.0     , "out": 15.0    , "speed": 7,  "quality": 9,  "label": "Sonar Pro"},
    "sonar-reasoning":     {"provider": "perplexity", "in": 1.0     , "out": 5.0     , "speed": 6,  "quality": 9,  "label": "Sonar Reasoning"},
    "sonar-deep-research": {"provider": "perplexity", "in": 2.0     , "out": 8.0     , "speed": 4,  "quality": 10,  "label": "Sonar Deep Research"},
    "sonar-reasoning-pro": {"provider": "perplexity", "in": 2.0     , "out": 8.0     , "speed": 6,  "quality": 9,  "label": "Sonar Reasoning Pro"},
}


def compute_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Return cost in USD. Returns 0.0 for unknown models."""
    meta = MODEL_CATALOG.get(model)
    if not meta:
        return 0.0
    return (input_tokens * meta["in"] + output_tokens * meta["out"]) / 1_000_000
