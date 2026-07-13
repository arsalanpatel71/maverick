"""Fetch and parse SKILL.md files from GitHub URLs."""
import re

import httpx
import yaml


def github_url_to_raw(url: str) -> str:
    """Convert a GitHub blob URL to a raw.githubusercontent.com URL."""
    pattern = r"https://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.+)"
    m = re.match(pattern, url)
    if m:
        owner, repo, branch, path = m.groups()
        return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
    return url


def _parse_frontmatter(content: str) -> tuple[str, str]:
    """Extract name and description from YAML frontmatter if present."""
    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            fm = yaml.safe_load(content[3:end].strip()) or {}
            return str(fm.get("name", "")), str(fm.get("description", ""))
    return "", ""


def _parse_heading_fallback(content: str, catalog_entry: dict | None) -> tuple[str, str]:
    """Fall back to the H1 heading as name when there's no frontmatter.

    If a catalog entry is provided (fetched via the catalog endpoint), use its
    pre-filled description rather than leaving it blank.
    """
    name = ""
    description = ""
    # Try to get name from catalog hint
    if catalog_entry:
        name = catalog_entry.get("name", "")
        description = catalog_entry.get("description", "")
    # Fall back to first # heading
    if not name:
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                name = stripped[2:].strip()
                break
    return name, description


async def fetch_skill_from_github(url: str, catalog_hint: dict | None = None) -> dict:
    """Fetch a SKILL.md from a GitHub URL and return parsed fields.

    Accepts both blob URLs (github.com/.../blob/...) and raw URLs.
    Raises ValueError on HTTP errors or if name cannot be determined.
    catalog_hint: an entry from ANTHROPIC_SKILLS_CATALOG to supply name/description
                  for skills that have no YAML frontmatter.
    """
    raw_url = github_url_to_raw(url)
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        resp = await client.get(raw_url)
    if resp.status_code == 404:
        raise ValueError(f"SKILL.md not found at {raw_url}")
    resp.raise_for_status()

    content = resp.text
    name, description = _parse_frontmatter(content)

    if not name or not description:
        fallback_name, fallback_desc = _parse_heading_fallback(content, catalog_hint)
        if not name:
            name = fallback_name
        if not description:
            description = fallback_desc

    if not name:
        raise ValueError("SKILL.md is missing a 'name' field and no heading could be parsed")
    if not description:
        raise ValueError("SKILL.md is missing a 'description' field in frontmatter")

    return {"name": name, "description": description, "content": content, "github_url": url}
