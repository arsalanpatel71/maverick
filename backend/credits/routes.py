"""Credits routes: balance, usage breakdown, model catalog."""
import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from agents.services.agent_store import traces_collection
from auth.dependencies import get_current_user, get_user_store, require_admin
from credits.rates import MODEL_CATALOG, PROVIDER_META
from users.store import PERIOD_SECONDS, UserStore

router = APIRouter(prefix="/credits", tags=["credits"])


@router.get("/me")
async def my_balance(
    user: dict = Depends(get_current_user),
    store: UserStore = Depends(get_user_store),
):
    doc = await asyncio.to_thread(store.check_and_reset_period, user["id"])
    if not doc:
        raise HTTPException(status_code=404, detail="User not found")
    limit = doc.get("credits_limit", 10.0)
    used = doc.get("credits_used", 0.0)
    period = doc.get("credits_period", "monthly")
    period_start = doc.get("credits_period_start") or doc.get("created_at") or datetime.now(timezone.utc)
    if period_start.tzinfo is None:
        period_start = period_start.replace(tzinfo=timezone.utc)
    secs = PERIOD_SECONDS.get(period, PERIOD_SECONDS["monthly"])
    next_reset_at = period_start.timestamp() + secs
    return {
        "credits_limit": limit,
        "credits_used": round(used, 6),
        "credits_period": period,
        "next_reset_at": next_reset_at,
        "percent_used": round((used / limit * 100) if limit > 0 else 0, 1),
    }


@router.get("/usage")
async def my_usage(
    days: int = Query(30, ge=1, le=90),
    user: dict = Depends(get_current_user),
):
    return await _usage_for_user(user["id"], days)


@router.get("/admin/usage")
async def all_usage(
    days: int = Query(30, ge=1, le=90),
    _: dict = Depends(require_admin),
    store: UserStore = Depends(get_user_store),
):
    col = traces_collection()
    since = datetime.now(timezone.utc).timestamp() - days * 86400

    def _query():
        return list(col.find(
            {"created_at": {"$gt": datetime.fromtimestamp(since, tz=timezone.utc)},
             "user_id": {"$exists": True}},
            {"events": 0},
        ).sort("created_at", -1).limit(2000))

    traces = await asyncio.to_thread(_query)

    user_ids = list({t["user_id"] for t in traces if t.get("user_id")})
    user_map = {}
    for uid in user_ids:
        doc = await asyncio.to_thread(store.get_by_id, uid)
        if doc:
            user_map[uid] = {"id": uid, "email": doc["email"], "name": doc["name"]}

    rows = []
    for t in traces:
        usage = t.get("usage") or {}
        rows.append({
            "trace_id": t["_id"],
            "user": user_map.get(t.get("user_id"), {}),
            "agent_id": t.get("agent_id"),
            "model": t.get("model"),
            "provider": t.get("provider"),
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "cost_usd": t.get("cost_usd", 0.0),
            "created_at": t.get("created_at"),
        })

    return {"rows": rows, "total_cost": round(sum(r["cost_usd"] for r in rows), 6)}


@router.get("/catalog")
async def model_catalog():
    return [
        {
            "model_id": model_id,
            "label": meta["label"],
            "provider": meta["provider"],
            "provider_label": PROVIDER_META.get(meta["provider"], {}).get("label", meta["provider"]),
            "provider_color": PROVIDER_META.get(meta["provider"], {}).get("color", "slate"),
            "in_per_m": meta["in"],
            "out_per_m": meta["out"],
            "speed": meta["speed"],
            "quality": meta["quality"],
        }
        for model_id, meta in MODEL_CATALOG.items()
    ]


async def _usage_for_user(user_id: str, days: int) -> dict:
    col = traces_collection()
    since = datetime.now(timezone.utc).timestamp() - days * 86400

    def _query():
        return list(col.find(
            {"user_id": user_id,
             "created_at": {"$gt": datetime.fromtimestamp(since, tz=timezone.utc)}},
            {"events": 0},
        ).sort("created_at", -1).limit(1000))

    traces = await asyncio.to_thread(_query)

    by_model: dict[str, dict] = {}
    by_provider: dict[str, dict] = {}
    total_cost = 0.0
    total_in = 0
    total_out = 0

    for t in traces:
        usage = t.get("usage") or {}
        model = t.get("model", "unknown")
        provider = t.get("provider", "unknown")
        cost = t.get("cost_usd", 0.0)
        inp = usage.get("input_tokens", 0)
        out = usage.get("output_tokens", 0)

        total_cost += cost
        total_in += inp
        total_out += out

        if model not in by_model:
            by_model[model] = {"model": model, "provider": provider, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "calls": 0}
        by_model[model]["input_tokens"] += inp
        by_model[model]["output_tokens"] += out
        by_model[model]["cost_usd"] += cost
        by_model[model]["calls"] += 1

        if provider not in by_provider:
            by_provider[provider] = {"provider": provider, "cost_usd": 0.0, "calls": 0}
        by_provider[provider]["cost_usd"] += cost
        by_provider[provider]["calls"] += 1

    recent = [
        {
            "trace_id": t["_id"],
            "agent_id": t.get("agent_id"),
            "model": t.get("model"),
            "provider": t.get("provider"),
            "input_tokens": (t.get("usage") or {}).get("input_tokens", 0),
            "output_tokens": (t.get("usage") or {}).get("output_tokens", 0),
            "cost_usd": t.get("cost_usd", 0.0),
            "created_at": t.get("created_at"),
        }
        for t in traces[:50]
    ]

    return {
        "total_cost_usd": round(total_cost, 6),
        "total_input_tokens": total_in,
        "total_output_tokens": total_out,
        "by_model": sorted(by_model.values(), key=lambda x: x["cost_usd"], reverse=True),
        "by_provider": sorted(by_provider.values(), key=lambda x: x["cost_usd"], reverse=True),
        "recent_traces": recent,
    }
