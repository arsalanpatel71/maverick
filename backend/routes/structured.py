from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.structured import SchemaBuilder, StructuredParser

router = APIRouter(prefix="/structured", tags=["structured"])


class SchemaPreviewRequest(BaseModel):
    name: str
    json_schema: dict


class SchemaPreviewResponse(BaseModel):
    openai_format: dict
    google_format: dict
    instruction_block: str


@router.post("/preview-schema", response_model=SchemaPreviewResponse)
def preview_schema(body: SchemaPreviewRequest) -> SchemaPreviewResponse:
    """Preview how a JSON schema will be formatted for each LLM provider."""
    return SchemaPreviewResponse(
        openai_format=SchemaBuilder.to_openai_format(body.name, body.json_schema),
        google_format=SchemaBuilder.to_google_format(body.json_schema),
        instruction_block=SchemaBuilder.to_instruction_block(body.name, body.json_schema),
    )


class ParseRequest(BaseModel):
    content: str


@router.post("/parse")
def parse_response(body: ParseRequest) -> dict:
    """Parse a JSON string from an LLM response (handles markdown code blocks)."""
    try:
        return StructuredParser.parse(body.content)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
