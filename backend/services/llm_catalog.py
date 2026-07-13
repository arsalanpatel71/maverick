"""LLM model catalog — built automatically from credits/rates.py.

Run scripts/update_models.py to add new models; this file needs no manual edits.
"""
from agents.schemas import AgentProvider
from credits.rates import MODEL_CATALOG
from services.models.llm_info import LLMModelEntry

_PROVIDER_KEY = {
    "anthropic":  AgentProvider.anthropic,
    "openai":     AgentProvider.openai,
    "google":     AgentProvider.google,
    "perplexity": AgentProvider.perplexity,
}

_grouped: dict[AgentProvider, list[LLMModelEntry]] = {p: [] for p in AgentProvider}

for _model_id, _meta in MODEL_CATALOG.items():
    _provider = _PROVIDER_KEY.get(_meta["provider"])
    if _provider:
        _grouped[_provider].append(LLMModelEntry(id=_model_id, description=_meta["label"]))

CATALOG: dict[AgentProvider, list[LLMModelEntry]] = _grouped
