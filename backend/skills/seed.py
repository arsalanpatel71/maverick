"""No-op — skills are no longer seeded at startup.

The Anthropic skills catalog is served from builtin.py as a static list.
Users import skills on-demand via /skills/fetch-github or /skills/catalog.
"""


def seed_skills() -> None:
    pass
