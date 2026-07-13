from fastapi import APIRouter, HTTPException

from agents.schemas import AgentProvider
from services.models.llm_info import LLMProviderModels
from services.llm_catalog import CATALOG

router = APIRouter(prefix="/llm-info", tags=["LLM info"])


@router.get(
    "/providers",
    response_model=list[LLMProviderModels],
    summary="List models per provider",
    description="Curated model ids for building agents; not live-fetched—verify against each provider’s documentation.",
)
def list_llm_provider_models() -> list[LLMProviderModels]:
    return [
        LLMProviderModels(provider=provider, models=models)
        for provider, models in CATALOG.items()
    ]


@router.get("/providers/{provider}", response_model=LLMProviderModels)
def get_llm_provider_models(provider: AgentProvider) -> LLMProviderModels:
    models = CATALOG.get(provider)
    if models is None:
        raise HTTPException(status_code=404, detail="Unknown provider")
    return LLMProviderModels(provider=provider, models=models)
