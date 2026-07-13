import asyncio
import json
import logging
from typing import Any, TYPE_CHECKING
from uuid import uuid4

from capsules.models import FILE_FORMATS

if TYPE_CHECKING:
    from settings import Settings

logger = logging.getLogger(__name__)

CREATE_CAPSULE_TOOL: dict = {
    "name": "create_capsule",
    "description": (
        "Create or update a named, persistent data capsule. "
        "Use this for any output the user may want to reference, download, or reuse: "
        "generated code, data tables, reports, analyses, markdown documents, or images. "
        "Inline formats (text/code/json/markdown/image) are stored directly. "
        "File formats (csv/xlsx/pdf/docx/pptx) require file_output=true to be rendered and uploaded for download."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "format_type": {
                "type": "string",
                "enum": ["text", "code", "json", "markdown", "data", "image", "csv", "xlsx", "pdf", "docx", "pptx"],
                "description": "Format of the capsule content.",
            },
            "name": {
                "type": "string",
                "description": "Short descriptive name (e.g. 'Q3 Sales Report', 'Auth Module').",
            },
            "description": {
                "type": "string",
                "description": "One-sentence summary of what this capsule contains.",
            },
            "data": {
                "type": "object",
                "properties": {
                    "content": {
                        "description": (
                            "The capsule payload. "
                            "text/code/markdown/json: a string. "
                            "image: a base64 data URI. "
                            "csv/xlsx: a JSON array of row objects. "
                            "pdf/docx: a markdown string. "
                            "pptx: a JSON array of {title, content} slide objects."
                        ),
                    },
                },
                "required": ["content"],
            },
            "language": {
                "type": "string",
                "description": "Programming language for code capsules (e.g. 'python', 'typescript', 'sql').",
            },
            "file_output": {
                "type": "boolean",
                "description": "For file formats: render and upload a downloadable file. Defaults to false.",
            },
            "capsule_id": {
                "type": "string",
                "description": "Existing capsule ID to update in place. Omit to create a new one.",
            },
        },
        "required": ["format_type", "name", "description", "data"],
    },
}


async def execute_create_capsule(
    tool_input: dict,
    *,
    agent_id: str,
    session_id: str | None,
    user_id: str | None,
    settings: "Settings",
) -> dict[str, Any]:
    from capsules.store import CapsuleStore

    fmt = tool_input.get("format_type", "text")
    name = tool_input.get("name", "Untitled")
    description = tool_input.get("description", "")
    data_obj = tool_input.get("data") or {}
    content = data_obj.get("content", "")
    language = tool_input.get("language")
    file_output = bool(tool_input.get("file_output", False))
    capsule_id = tool_input.get("capsule_id") or str(uuid4())

    metadata: dict[str, Any] = {}
    if language:
        metadata["language"] = language

    if fmt in FILE_FORMATS and file_output:
        try:
            file_bytes, content_type, ext = await _render_file(fmt, content)
            from capsules.s3 import upload_bytes_async, generate_presigned_url_async
            s3_key = f"capsules/{user_id or 'anon'}/{capsule_id}{ext}"
            await upload_bytes_async(file_bytes, s3_key, content_type, settings)
            file_url = await generate_presigned_url_async(s3_key, settings)
            metadata["file_url"] = file_url
            metadata["file_name"] = f"{name}{ext}"
            metadata["file_type"] = content_type
            metadata["s3_key"] = s3_key
        except Exception as e:
            logger.exception("File rendering failed for capsule %s", capsule_id)
            return {"success": False, "error": f"File rendering failed: {e}", "capsule_id": capsule_id}

    store = CapsuleStore()
    record = await asyncio.to_thread(
        store.save,
        agent_id=agent_id,
        session_id=session_id,
        user_id=user_id,
        format_type=fmt,
        name=name,
        description=description,
        data=content,
        metadata=metadata,
        capsule_id=capsule_id,
    )

    result: dict[str, Any] = {
        "success": True,
        "capsule_id": record.capsule_id,
        "name": record.name,
        "format_type": record.format_type,
    }
    if metadata.get("file_url"):
        result["file_url"] = metadata["file_url"]
        result["note"] = "File URL expires in 1 hour."

    return result


async def _render_file(fmt: str, content: Any) -> tuple[bytes, str, str]:
    from capsules import file_processors

    if fmt == "csv":
        raw = await asyncio.to_thread(file_processors.render_csv, content)
        return raw, "text/csv", ".csv"
    elif fmt == "xlsx":
        raw = await asyncio.to_thread(file_processors.render_xlsx, content)
        return raw, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx"
    elif fmt == "pdf":
        raw = await asyncio.to_thread(file_processors.render_pdf, str(content))
        return raw, "application/pdf", ".pdf"
    elif fmt == "docx":
        raw = await asyncio.to_thread(file_processors.render_docx, str(content))
        return raw, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".docx"
    elif fmt == "pptx":
        raw = await asyncio.to_thread(file_processors.render_pptx, content)
        return raw, "application/vnd.openxmlformats-officedocument.presentationml.presentation", ".pptx"
    else:
        raise ValueError(f"Unsupported file format: {fmt}")
