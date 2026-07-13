"""Skills CRUD + GitHub import routes."""
import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from auth.dependencies import get_current_user, get_optional_user
from services.pagination import PageParams, PagedResponse, get_page_params, paginate
from skills.builtin import ANTHROPIC_SKILLS_CATALOG
from skills.fetcher import fetch_skill_from_github
from skills.schemas import GithubFetchRequest, SkillCreate, SkillResponse, SkillUpdate
from skills.store import SkillStore


class CatalogEntry(BaseModel):
    name: str
    description: str
    github_url: str
    imported: bool
    skill_id: str | None = None  # DB _id when already imported

router = APIRouter(prefix="/skills", tags=["skills"])


def get_skill_store() -> SkillStore:
    return SkillStore()


def _to_response(doc: dict) -> SkillResponse:
    return SkillResponse(
        id=doc["_id"],
        name=doc["name"],
        description=doc["description"],
        content=doc["content"],
        source=doc.get("source", "custom"),
        github_url=doc.get("github_url"),
        owner_id=doc.get("owner_id"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


@router.get("/catalog", response_model=PagedResponse)
async def get_catalog(
    q: str | None = Query(None, description="Filter catalog by name or description"),
    paging: PageParams = Depends(get_page_params),
    store: SkillStore = Depends(get_skill_store),
) -> PagedResponse:
    """Return the Anthropic skills catalog with search, pagination, and imported flag."""
    url_to_skill = {
        d["github_url"]: d["_id"]
        for d in await asyncio.to_thread(store.list_all, None)
        if d.get("github_url")
    }
    entries = ANTHROPIC_SKILLS_CATALOG
    if q and q.strip():
        term = q.strip().lower()
        entries = [
            e for e in entries
            if term in e["name"].lower() or term in e["description"].lower()
        ]
    items = [
        CatalogEntry(
            name=entry["name"],
            description=entry["description"],
            github_url=entry["github_url"],
            imported=entry["github_url"] in url_to_skill,
            skill_id=url_to_skill.get(entry["github_url"]),
        )
        for entry in entries
    ]
    return paginate(items, paging)


@router.get("/", response_model=PagedResponse)
async def list_skills(
    q: str | None = Query(None, description="Filter by name or description"),
    paging: PageParams = Depends(get_page_params),
    store: SkillStore = Depends(get_skill_store),
    _: dict | None = Depends(get_optional_user),
) -> PagedResponse:
    docs = await asyncio.to_thread(store.list_all, q)
    return paginate([_to_response(d) for d in docs], paging)


@router.get("/{skill_id}", response_model=SkillResponse)
async def get_skill(
    skill_id: str,
    store: SkillStore = Depends(get_skill_store),
) -> SkillResponse:
    doc = await asyncio.to_thread(store.get, skill_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    return _to_response(doc)


@router.post("/", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
async def create_skill(
    body: SkillCreate,
    user: dict = Depends(get_current_user),
    store: SkillStore = Depends(get_skill_store),
) -> SkillResponse:
    if await asyncio.to_thread(store.name_exists, body.name):
        raise HTTPException(status_code=409, detail=f"A skill named '{body.name}' already exists")
    doc = await asyncio.to_thread(
        store.create,
        name=body.name,
        description=body.description,
        content=body.content,
        source="github" if body.github_url else "custom",
        github_url=body.github_url,
        owner_id=user["id"],
    )
    return _to_response(doc)


@router.patch("/{skill_id}", response_model=SkillResponse)
async def update_skill(
    skill_id: str,
    body: SkillUpdate,
    user: dict = Depends(get_current_user),
    store: SkillStore = Depends(get_skill_store),
) -> SkillResponse:
    doc = await asyncio.to_thread(store.get, skill_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    if doc.get("source") == "builtin":
        raise HTTPException(status_code=403, detail="Built-in skills cannot be modified")
    if doc.get("owner_id") and doc["owner_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="You do not own this skill")
    updated = await asyncio.to_thread(store.update, skill_id, body.model_dump(exclude_unset=True))
    return _to_response(updated)


@router.delete("/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill(
    skill_id: str,
    user: dict = Depends(get_current_user),
    store: SkillStore = Depends(get_skill_store),
) -> None:
    doc = await asyncio.to_thread(store.get, skill_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    if doc.get("source") == "builtin":
        raise HTTPException(status_code=403, detail="Built-in skills cannot be deleted")
    if doc.get("owner_id") and doc["owner_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="You do not own this skill")
    await asyncio.to_thread(store.delete, skill_id)


@router.post("/fetch-github", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
async def import_from_github(
    body: GithubFetchRequest,
    user: dict = Depends(get_current_user),
    store: SkillStore = Depends(get_skill_store),
) -> SkillResponse:
    """Fetch a SKILL.md from a GitHub URL, parse it, and save as a custom skill."""
    catalog_hint = next(
        (e for e in ANTHROPIC_SKILLS_CATALOG if e["github_url"] == body.url), None
    )
    try:
        parsed = await fetch_skill_from_github(body.url, catalog_hint=catalog_hint)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch from GitHub: {e}")

    if await asyncio.to_thread(store.name_exists, parsed["name"]):
        raise HTTPException(
            status_code=409,
            detail=f"A skill named '{parsed['name']}' already exists. Delete it first to reimport.",
        )

    doc = await asyncio.to_thread(
        store.create,
        name=parsed["name"],
        description=parsed["description"],
        content=parsed["content"],
        source="github",
        github_url=parsed["github_url"],
        owner_id=user["id"],
    )
    return _to_response(doc)
