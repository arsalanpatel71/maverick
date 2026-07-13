# Sales Lead Agentic Platform

> Status: Planned — Apollo-first MVP, expandable to LinkedIn, Reddit, Google SERP  
> Goal: Turn a product description into a ranked, enriched, personalised lead list automatically

---

## Why Build This

Most sales teams spend 60–70% of outreach time on list building — deciding who to target, finding emails, deciding what to say. The actual sending takes minutes. This platform inverts that: the AI handles discovery, enrichment, and first-draft personalisation so the rep focuses only on approving and sending.

The difference from a simple Apollo search:
- **You don't need to know Apollo filter syntax.** Describe your product in plain English and the ICP agent derives the right parameters.
- **Intent signals change the quality completely.** A cold ICP match scores 40–60. Someone who just posted "we're drowning in contract review" scores 80–100 and writes their own outreach opener.
- **Everything is captured as context for outreach.** The intent post, the company news, the job listing — all of it feeds into the email draft. That's personalisation that currently requires 30 minutes per lead in Clay.

---

## Full Agentic Flow

```
User types:
  "I sell an AI contract review tool for law firms. Find 30 leads in the US."

Step 1 — ICP Agent
  LLM reads the description → extracts structured Apollo search params
  Detects "30" → sets limit = 30

Step 2 — Discovery (Apollo now, multi-source later)
  Apollo people search with the extracted params
  Retry loop until limit met or 2 retries exhausted

Step 3 — Enrichment  [Phase 2]
  Apollo /people endpoint → email, phone, seniority
  NeverBounce → verify emails, drop invalid
  LLM scrapes company site → pain point summary

Step 4 — Scoring  [Phase 2]
  ICP fit score 0–100 per lead
  Intent signal boost (+30–40 points if intent source found)
  Ranked list

Step 5 — Outreach  [Phase 3]
  LLM writes personalised email per lead
  Intent signal leads get line-specific opener from their actual post
  Draft stored, ready to approve + send
```

---

## Discovery: Two Tracks

Once LinkedIn and intent sources are wired in, discovery runs two tracks in parallel and merges at scoring.

### Track 1 — ICP Match (score 40–60)
Who *should* need this based on their profile.

| Source | Filter | Status |
|---|---|---|
| Apollo people search | title, industry, company size, location, seniority | **NOW** |
| Apollo company search | tech stack, keywords, funding | Next |
| Google SERP | "companies using X", niche directories | Next |

### Track 2 — Intent Signals (score 80–100)
Who *is actively looking* based on what they're publicly saying.

| Source | Signal type | Status |
|---|---|---|
| LinkedIn post search | "we're scaling support", "anyone tried X?", hiring announcements | Next |
| Reddit | r/[niche] "what tool for X?" | Future |
| Google AI mode | "looking for X solution", review sites | Next |
| Twitter/X | pain point venting, asking for recs | Future |

**Why intent signals matter more:**  
Cold ICP match is a guess. Intent signal is a fact — this person, right now, has the problem your product solves. Your open rate on intent-signal outreach is typically 3–4× higher than cold ICP match because (a) the problem is fresh in their mind and (b) the opener references something they actually said.

---

## ICP Agent

The ICP agent is a regular Maverick agent with a `ResponseSchema` configured. It takes a freeform product description and returns structured Apollo-compatible search parameters.

### What It Extracts

| Field | What the LLM derives | Example |
|---|---|---|
| `icp_summary` | One-line buyer description | "General Counsel at 50–200 person tech company" |
| `job_titles` | Specific titles (not generic) | ["General Counsel", "VP Legal", "Head of Legal"] |
| `industries` | Apollo industry names | ["Legal Services", "Computer Software", "Financial Services"] |
| `seniority_levels` | Apollo seniority enums | ["vp", "head", "director", "c_suite"] |
| `employee_ranges` | Apollo headcount ranges | ["51,200", "201,500"] |
| `keywords` | Buzzwords for Apollo keyword filter | ["contract management", "legal ops", "e-signature"] |
| `locations` | City/country names | ["United States"] |
| `linkedin_intent_queries` | 1 LinkedIn post search query | ["contract review backlog", "legal team overwhelmed"] |
| `limit` | Optional — only if user said a number | 30 (or omitted) |

### System Prompt

```
You are an ICP (Ideal Customer Profile) analysis agent. Given a product or
service the user wants to sell, you extract structured search parameters to
find the best potential buyers.

---

### Lead Limit
- If the user explicitly mentions a number of leads (e.g. "find me 50 leads",
  "get 20 contacts"), extract that number as `limit`.
- If the user does not mention a number, do not include `limit` — omit entirely.

---

### Apollo JSON Extraction
- Analyse the product the user wants to sell.
- Identify the most relevant job titles, industries, company sizes, seniority
  levels, and keywords that describe the ideal buyer.
- Be specific — "Manager" is not useful, prefer "VP of Engineering" or
  "Head of Procurement".
- Always return valid Apollo-compatible values for employee_ranges.

---

### LinkedIn Post Search Queries
- Generate 1 LinkedIn post search query.
- Do NOT use direct buying-intent queries like "I want to buy X".
- Think about what people post when they indirectly need the product.

Examples for office chairs:
  "new office expansion"
  "growing our team"

Examples for software services:
  "our support team is overwhelmed"
  "scaling customer support"
  "hiring support agents"

Guidelines:
- Keep each query under 20 words
- Focus on intent signals, pain points, growth events, or operational challenges
- Queries should sound like natural LinkedIn posts or announcements
- Avoid overly generic phrases
```

### JSON Schema (`ICPSearchParams`)

```json
{
  "type": "object",
  "properties": {
    "icp_summary":             { "type": "string" },
    "job_titles":              { "type": "array", "items": { "type": "string" } },
    "industries":              { "type": "array", "items": { "type": "string" } },
    "linkedin_intent_queries": {
      "type": "array",
      "description": "1 short LinkedIn post search query for intent signals.",
      "items": { "type": "string" }
    },
    "employee_ranges": {
      "type": "array",
      "items": {
        "type": "string",
        "enum": ["1,10","11,50","51,200","201,500","501,1000","1001,5000","5001,10000","10001,"]
      }
    },
    "seniority_levels": {
      "type": "array",
      "items": {
        "type": "string",
        "enum": ["owner","founder","c_suite","partner","vp","head","director","manager","senior","entry","intern"]
      }
    },
    "keywords":   { "type": "array", "items": { "type": "string" } },
    "locations":  { "type": "array", "items": { "type": "string" } },
    "limit":      { "type": "integer", "minimum": 1 }
  },
  "required": ["icp_summary","job_titles","industries","employee_ranges","seniority_levels","keywords"]
}
```

---

## Apollo Service

### API Details
- Endpoint: `POST https://api.apollo.io/api/v1/mixed_people/search`
- Auth: `X-Api-Key: {apollo_api_key}` header
- `per_page`: 25 (Apollo default page size)
- Results include: name, title, company, email (if enriched), linkedin_url, location, seniority, industry, employee_count

### Limit & Retry Logic

```
limit = extracted from ICP agent (optional)

If limit is NOT set:
  → fetch page 1 (25 results)
  → return all results immediately

If limit IS set:
  collected = []
  page = 1
  retries = 0

  while len(collected) < limit and retries < MAX_RETRIES (2):
    fetch page N from Apollo
    collected.extend(new results)
    page += 1
    retries += 1

  return collected[:limit] or all collected if under limit
```

**Key rule:** `limit` is a *minimum threshold*, not `per_page`. If we get 28 when limit was 25, return all 28. We only retry when we're *under* the limit, not when we just want exactly that number.

### Lead Schema

```python
class Lead(BaseModel):
    id: str | None
    name: str | None
    first_name: str | None
    last_name: str | None
    title: str | None
    company: str | None
    email: str | None
    email_status: str | None  # "verified", "unverified", "unavailable"
    linkedin_url: str | None
    location: str | None
    seniority: str | None
    industry: str | None
    employee_count: int | None
```

---

## Backend File Structure

```
backend/
  leads/
    __init__.py
    schemas.py          ← ICPSearchParams, Lead, LeadGenerateRequest/Response
    routes.py           ← POST /leads/generate
    services/
      __init__.py
      icp_agent.py      ← LLM call → ICPSearchParams (uses gpt-4o-mini)
      apollo.py         ← Apollo API · retry loop · Lead mapping

  settings.py           ← add: apollo_api_key: str = os.getenv("APOLLO_API_KEY", "")
  routes/__init__.py    ← add: from leads.routes import router as leads_router
                              app.include_router(leads_router)
```

**What's missing right now** (source files were reverted):

| File | Status |
|---|---|
| `leads/schemas.py` | Needs to be written |
| `leads/routes.py` | Needs to be written |
| `leads/services/icp_agent.py` | Needs to be written |
| `leads/services/apollo.py` | Needs to be written |
| `settings.py` — `apollo_api_key` | Needs to be added |
| `routes/__init__.py` — `leads_router` | Needs to be added |

The `leads/` directory and `__init__` files exist. The `.py` source files were deleted.

---

## API Endpoints

| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/leads/generate` | `{ "query": "I sell X..." }` | `{ "icp": ICPSearchParams, "leads": Lead[], "total": int }` |
| POST | `/leads/generate/stream` *(future)* | same | SSE stream of each step |

No `limit` in the request body. Limit is extracted by the ICP agent from the user's natural language query.

---

## Frontend Plan

A new page `/leads` with:

```
┌─────────────────────────────────────────────────────────┐
│  Generate Leads                                          │
│                                                          │
│  [text area: describe your product and who to target]   │
│                                [Generate →]             │
│                                                          │
│  ICP Summary:                                            │
│  "General Counsel at 50–200 person US tech company"      │
│                                                          │
│  Filters extracted:                                      │
│  titles · industries · seniority · size · location       │
│                                                          │
│  Leads found: 28                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Name · Title · Company · Email · LinkedIn · Score│    │
│  │ ...                                              │    │
│  └─────────────────────────────────────────────────┘    │
│  [Export CSV]  [Save to CRM]                             │
└─────────────────────────────────────────────────────────┘
```

Stream mode: show ICP extracted → leads found → enriched → scored as they complete (SSE).

---

## Enrichment Layer (Phase 2)

After discovery returns raw leads (name, title, company, LinkedIn URL):

| Step | Service | What we get |
|---|---|---|
| Email lookup | Apollo `/people/match` | Work email, direct phone |
| Email verify | NeverBounce API | `valid` / `invalid` / `disposable` — drop invalid |
| Company enrichment | Apollo company search | Funding, tech stack, headcount, recent news |
| Site scraping | LLM + Jina/Firecrawl | Pain points from their homepage/blog |

---

## Scoring Agent (Phase 2)

Scores each lead 0–100 based on:

| Signal | Score boost | Notes |
|---|---|---|
| ICP title match | +0–30 | Exact title = 30, similar = 15 |
| ICP industry match | +0–20 | |
| ICP size match | +0–15 | |
| Email verified | +10 | NeverBounce `valid` |
| Intent signal found | +30–40 | LinkedIn post / Reddit mention |
| Recent funding round | +10 | Crunchbase signal |
| Hiring for relevant role | +10 | Job listing for role that uses your product |

Threshold: leads below 40 are dropped by default.

---

## Outreach Agent (Phase 3)

Generates a personalised email per lead. Context passed in:
- Lead profile (title, company, seniority, industry)
- Company pain points (from site scrape)
- Intent signal post text (if found)
- ICP summary

Example output for an intent-signal lead:

```
Subject: Re: your post about contract review backlog

Hi Sarah,

Saw your post last week about the team being underwater on contract reviews.
[Product] does exactly that — it drafts, flags risks, and tracks versions
automatically, cutting review time by ~60%.

Worth a 15-minute call this week?
```

---

## Integration Roadmap

| Phase | What | Sources |
|---|---|---|
| **1 — NOW** | ICP extraction + Apollo discovery | Apollo People Search |
| **2 — Next** | Enrichment + scoring | Apollo /people, NeverBounce |
| **3 — Next** | Intent signal discovery | LinkedIn post search (RapidAPI), Google SERP AI |
| **4 — Future** | Outreach generation | LLM (using all collected context) |
| **5 — Future** | Reddit + ProductHunt signals | Reddit API, PH API |
| **6 — Future** | CRM sync | HubSpot / Salesforce API |

---

## How This Makes Maverick Better

### Before (current state)
Maverick is an agent builder. Users create an agent, give it instructions, maybe attach a RAG, and chat with it. It's a general-purpose tool.

### After (with lead platform)
Maverick becomes a **sales intelligence platform**. The agent infrastructure already handles the hardest parts — LLM calling, RAG retrieval, structured output, memory, traces. The lead platform builds on all of that:

1. **ICP Agent uses the existing ResponseSchema system** — no new LLM code needed. It's just an agent with structured output configured.

2. **RAG can be used for company context** — after enrichment, scraped company pages can be stored as RAG chunks attached to the outreach agent, so it can reference specific things from their site.

3. **Manager agent pattern applies to lead gen** — a manager agent could orchestrate: ICP agent → Apollo agent → enrichment agent → scoring agent → outreach agent, all using the existing delegation system.

4. **Traces give full auditability** — every lead generation run is traced. You can see exactly what Apollo returned, what the ICP agent extracted, how each lead was scored. This matters for debugging and for user trust.

5. **Guardrails protect the input** — user's product description is already sanitised through `check_input()` and `redact_input()` before reaching the LLM.

6. **Session memory means iterative refinement** — user can say "too many enterprise companies, focus on 50–200 person startups" and the agent remembers the original search and refines it.

7. **It differentiates from generic AI tools** — most AI tools (ChatGPT, Perplexity) can describe an ICP. None of them automatically hit Apollo, return verified leads, and surface the ones who are actively posting about the problem. That combination is the product.
