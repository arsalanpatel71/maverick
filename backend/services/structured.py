import json
import re
from typing import Any


class SchemaBuilder:
    @staticmethod
    def normalise(schema: dict) -> dict:
        """Resolve $ref inline and add additionalProperties: false on all objects."""
        defs = schema.get("$defs") or schema.get("definitions") or {}

        def _walk(node: Any) -> Any:
            if not isinstance(node, dict):
                return node
            if "$ref" in node:
                key = node["$ref"].split("/")[-1]
                return _walk(defs.get(key, {}))
            result = {k: _walk(v) for k, v in node.items() if k not in ("$defs", "definitions")}
            if result.get("type") == "object":
                result.setdefault("additionalProperties", False)
            return result

        return _walk(schema)

    @staticmethod
    def to_openai_format(name: str, schema: dict) -> dict:
        return {
            "type": "json_schema",
            "json_schema": {
                "name": name,
                "strict": True,
                "schema": SchemaBuilder.normalise(schema),
            },
        }

    @staticmethod
    def to_google_format(schema: dict) -> dict:
        return _to_gemini_schema(SchemaBuilder.normalise(schema))

    @staticmethod
    def to_instruction_block(name: str, schema: dict) -> str:
        return (
            f"\n\nRESPONSE FORMAT:\n"
            f"You MUST respond with valid JSON matching this schema ({name}):\n"
            f"{json.dumps(schema, indent=2)}\n"
            f"Output ONLY the JSON object — no markdown, no explanation."
        )


def _to_gemini_schema(node: Any) -> Any:
    if not isinstance(node, dict):
        return node
    _type_map = {
        "string": "STRING", "integer": "INTEGER", "number": "NUMBER",
        "boolean": "BOOLEAN", "array": "ARRAY", "object": "OBJECT",
    }
    out: dict = {}
    if "type" in node:
        out["type"] = _type_map.get(node["type"], node["type"].upper())
    if "description" in node:
        out["description"] = node["description"]
    if "enum" in node:
        out["enum"] = node["enum"]
    if node.get("type") == "object" and "properties" in node:
        out["properties"] = {k: _to_gemini_schema(v) for k, v in node["properties"].items()}
        if "required" in node:
            out["required"] = node["required"]
    if node.get("type") == "array" and "items" in node:
        out["items"] = _to_gemini_schema(node["items"])
    return out


class StructuredParser:
    @staticmethod
    def parse(content: str) -> dict:
        """Extract and parse JSON from an LLM response, handling markdown code blocks."""
        text = content.strip()
        m = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
        if m:
            text = m.group(1).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        idx = text.find("{")
        if idx != -1:
            try:
                return json.loads(text[idx:])
            except json.JSONDecodeError:
                pass
        raise ValueError(f"Could not extract JSON from response: {content[:300]!r}")
