from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from agents.schemas import ManagedAgent


def build_agent_system_prompt(role: str, goal: str, instructions: str) -> str:
    return (
        f"## Role\n{role.strip()}\n\n"
        f"## Goal\n{goal.strip()}\n\n"
        f"## Instructions\n{instructions.strip()}"
    )


def build_manager_system_prompt(role: str, goal: str, instructions: str, managed_agents: list[ManagedAgent]) -> str:
    base = build_agent_system_prompt(role, goal, instructions)
    agent_lines = "\n".join(
        f"- **{a.name}** (id: `{a.id}`)\n  {a.usage_description}"
        for a in managed_agents
    )
    return (
        f"{base}\n\n"
        f"## Available Agents\n"
        f"You can delegate tasks to the following agents:\n\n"
        f"{agent_lines}\n\n"
        f"## Routing Instructions\n"
        f"When you need to delegate, respond with ONLY a JSON block — no other text:\n"
        f'{{"delegate": [{{"agent_id": "<id>", "task": "<what you need from this agent>"}}]}}\n\n'
        f"You may delegate to multiple agents in one step by including multiple entries.\n"
        f"If you can answer the user directly without delegation, respond normally."
    )


def _strip_frontmatter(content: str) -> str:
    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            return content[end + 3:].strip()
    return content.strip()


def format_skills_catalog(base_system: str, skills: list[dict]) -> str:
    """Inject a skill catalog (names + descriptions only) and instruct the LLM to call
    get_skill_content to fetch full instructions before using a skill."""
    if not skills:
        return base_system
    lines = [
        f"- **{s['name']}** (ID: `{s['_id']}`) — {s.get('description', '').strip()}"
        for s in skills
    ]
    catalog = "\n".join(lines)
    return (
        f"{base_system}\n\n"
        f"## Available Skills\n\n"
        f"You have access to the following skills. "
        f"When the user's request matches a skill's purpose, call `get_skill_content` with that skill's ID "
        f"to read its full instructions before proceeding.\n\n"
        f"{catalog}"
    )


def append_skills(base_system: str, skills: list[dict]) -> str:
    """Inject full skill content directly into the system prompt (fallback for non-Anthropic providers)."""
    if not skills:
        return base_system
    blocks = [f"### {s['name']}\n{_strip_frontmatter(s['content'])}" for s in skills]
    return f"{base_system}\n\n## Active Skills\n\n" + "\n\n---\n\n".join(blocks)


_CAPSULE_TOOL_RULES = """
## File & Document Creation
You have a `create_capsule` tool that generates real downloadable files (docx, pdf, xlsx, pptx, csv, etc.).
- When the user asks for any file or document format, call `create_capsule` with `file_output: true` immediately — do not wait.
- NEVER say you cannot create, generate, or download files.
- NEVER tell the user to copy-paste content into Word, Google Docs, or any other app.
- After a successful tool call, write one short confirmation sentence (e.g. "Your report is ready as a .docx file.") and nothing else.
"""

_NO_FILE_DISCLAIMER_RULES = """
## Output Rules
- When the user asks for a document, spreadsheet, presentation, or any other file format, generate the complete content directly without any preamble.
- NEVER say you cannot create, generate, or produce files.
- NEVER instruct the user to copy-paste content into Word, Google Docs, or similar apps.
- NEVER explain your limitations around file creation. Just produce the content.
"""


def append_capsule_tool_rules(base_system: str) -> str:
    return f"{base_system}\n\n{_CAPSULE_TOOL_RULES.strip()}"


def append_no_file_disclaimer_rules(base_system: str) -> str:
    return f"{base_system}\n\n{_NO_FILE_DISCLAIMER_RULES.strip()}"


def append_extra_prompt(base_system: str, extra_prompt: dict[str, str]) -> str:
    """Append per-request variables to the system prompt (chat-only, not stored on the agent)."""
    if not extra_prompt:
        return base_system
    lines = "\n".join(
        f"- **{key}**: {value.strip()}" for key, value in extra_prompt.items()
    )
    return (
        f"{base_system}\n\n"
        f"## Extra context\n"
        f"The following request-specific information may help you respond:\n\n"
        f"{lines}"
    )
