# Capsule Workflow

(Note: in the actual code this concept is still named `artifact`/`create_artifact`/`artifacts` collection — "capsule" is just the name we're using here to talk about it.)

## What gets stored where, and why

Two storage systems, used for two different things:

**MongoDB — the capsule record itself (always)**
```python
class Capsule(BaseModel):     # code name: Artifact
    capsule_id: str          # code name: artifact_id, uuid4
    user_id: str
    session_id: str
    data: Any                 # payload: text, or base64 for binary
    format_type: str          # text | code | json | markdown | data | matplotlib | plot | chart | image | pdf | csv | xlsx | docx | pptx
    name: str
    description: str
    metadata: Dict[str, Any]  # may contain file_url / file_name / file_type
    created_at: datetime
    updated_at: datetime
```
- Every capsule is a Mongo document in the `artifacts` collection. This is the source of truth: `capsule_id`, name, description, and the payload itself for text/code/json/markdown/image formats (stored inline, base64 for binary).
- **Why Mongo:** it's small, structured, needs to be queried by user/session/format and listed/updated/deleted by ID — a document store is the right fit, and it's cheap to keep indefinitely since payloads here are typically small (text/json/base64 images), not large files.

**S3 (object storage) — only for the 5 real file formats, and only if `file_output: true`**
- Formats: `pdf`, `csv`, `xlsx`, `docx`, `pptx`.
- Flow: file is rendered → uploaded to S3 at `file_outputs/{user_id}/{asset_id}{extension}` → a **presigned URL** is generated (`expires_in=3600`, i.e. 1 hour) → that presigned URL is passed through an internal URL-shortener → the short URL is what actually gets saved into `metadata.file_url` on the Mongo capsule.
- **Why S3, not Mongo:** these are real binary files (spreadsheets, documents) that can be much larger than a DB document should hold, and they need direct/streamable download links — S3 + presigned URL is the standard way to serve that without routing the file bytes through the API server. Mongo only ever holds a URL string pointing at it, never the file bytes.
- Everything else (images/plots/text/code/json) never touches S3 unless it happens to go through this same file-generation path — those stay inline in Mongo as base64/text.

## How it's used (create → fetch → update → delete)

1. **Create**: LLM calls the `create_artifact` tool (i.e. "create capsule") → (if file format + `file_output: true`) render file → upload to S3 → get presigned URL → shorten it → save everything as one Mongo document (`save_artifact`, upsert by fresh `capsule_id`).
2. **Fetch**: `get_artifact` / `get_all_artifacts` read straight from Mongo and return the stored `data` plus `metadata.file_url` if present. The URL returned is whatever was saved at creation time — **it is never regenerated on read**.
3. **Update**: `update_artifact` overwrites fields on the same Mongo document in place (`updated_at` bumped). If it's a file-backed capsule, this can re-render and re-upload a new file, replacing the old `file_url` in metadata — the previous S3 object is not cleaned up (see below).
4. **Delete**: `delete_artifact` does a `delete_one` on the Mongo document only:
   ```python
   result = await self.artifacts_collection.delete_one(
       {"artifact_id": capsule_id, "user_id": user_id, "session_id": session_id}
   )
   ```
   It does **not** touch S3. If the capsule had a `file_url`, the underlying S3 object is left behind — deleting the capsule only removes the metadata record, not the file.

## Expiry — the part that actually goes stale

- The **S3 presigned URL** is generated with `expires_in=3600` — it stops working **1 hour** after creation, full stop.
- The **short URL** wrapping it is meant to match that (there's a constant `URL_SHORTENER_TTL = 3600` documented "to match signed URL expiration") — but that constant is never actually passed anywhere; the shortener call doesn't set an explicit TTL. In practice the short link's usable lifetime is bounded by the presigned URL underneath it, which dies at 1 hour regardless.
- Since `metadata.file_url` is a static string saved once and never refreshed, **any capsule with a generated file becomes practically unreachable via `file_url` about an hour after creation** — even though the Mongo capsule record itself still exists forever (or until explicitly deleted) and the raw S3 object also still exists (S3 objects aren't auto-deleted by anything in this codebase — no lifecycle rule was found).
- Net effect: the *metadata* (name, description, inline data) is durable and permanent; the *downloadable file link* for pdf/csv/xlsx/docx/pptx capsules is short-lived (~1 hour) and there is no built-in way to regenerate it after the fact — a caller would have to re-run `create_artifact`/`update_artifact` to get a fresh link.

## Summary

| | Mongo (capsule doc) | S3 (file, only for pdf/csv/xlsx/docx/pptx) |
|---|---|---|
| What's stored | id, name, description, inline data, metadata | actual file bytes |
| Lifetime | indefinite, until deleted | indefinite — nothing deletes it, ever, including capsule deletion |
| Link lifetime | n/a (direct DB read) | presigned URL expires in 1 hour, never auto-refreshed |
| Deleted when capsule is deleted? | yes | no — orphaned object remains |
