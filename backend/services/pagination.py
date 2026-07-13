"""Pagination utilities for FastAPI list endpoints."""
from dataclasses import dataclass
from typing import Any

from fastapi import Query
from pydantic import BaseModel


class PageMeta(BaseModel):
    total: int
    page: int
    page_size: int
    pages: int


class PagedResponse(BaseModel):
    items: list[Any]
    meta: PageMeta


@dataclass
class PageParams:
    page: int
    page_size: int


def get_page_params(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> PageParams:
    return PageParams(page=page, page_size=page_size)


def paginate(items: list, params: PageParams) -> PagedResponse:
    total = len(items)
    pages = max(1, (total + params.page_size - 1) // params.page_size)
    start = (params.page - 1) * params.page_size
    return PagedResponse(
        items=items[start : start + params.page_size],
        meta=PageMeta(total=total, page=params.page, page_size=params.page_size, pages=pages),
    )
