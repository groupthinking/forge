# ADR-001: FORGE Pipeline Architecture

**Status:** Accepted  
**Date:** 2026-08-18  
**Deciders:** Grok + Hayden (groupthinking)  
**Related:** forge-spec §3–5, EventRelay ARCHITECTURE.md, agent-factory CONSOLIDATION.md

---

## Context

We need a production-grade path from “paste YouTube URL” to “live deployed web app” in < 4–6 minutes for simple tutorials. Prior work lives in:

- **EventRelay** — mature video ingest, SSRF, multi-provider STT, Gemini agents, MCP
- **agent-factory** — swarm orchestration, VideoPack/TaskEvents schemas, codegen + Docker verify + GitHub publisher
- **YOUTUBE-EXTENSION** — archived into EventRelay

**forge** is the new product surface. It must not re-invent the wheel, but it also must not force every user through the full EventRelay/agent-factory stack on day one.

## Decision

### 1. Six fixed sequential stages (from forge-spec)

| # | Stage | Responsibility | Primary tech |
|---|-------|----------------|--------------|
| 1 | **Ingest** | URL validation (SSRF), yt-dlp metadata + optional audio | yt-dlp, ssrf.py |
| 2 | **Hybrid Transcribe** | Captions first, Whisper fallback, vision UI notes | youtube-transcript-api, OpenAI Whisper, Grok/Gemini vision |
| 3 | **Analyze + Extract** | Multimodal LLM → structured PRD JSON | Grok → OpenAI → Gemini |
| 4 | **Synthesize** | PRD → full Next.js source tree (deterministic scaffold + optional LLM polish) | templates + LLM |
| 5 | **Validate + Test** | Required files, package.json, secret scan, export checks | pure Python (future: tsc + Playwright) |
| 6 | **Build & Deploy** | Package, optional GitHub push, Vercel deploy (or mock URL) | GitHub API, Vercel API |

Stages share a single mutable `context: dict` that accumulates artifacts. Fail-closed: any stage exception marks the job `failed` and stops the chain.

### 2. Orchestrator = thin sequential runner

`PipelineOrchestrator` is **not** a multi-agent swarm. It is a reliable stage runner with progress callbacks into the job store. Multi-agent complexity (CEO / Engineering agents) stays in **agent-factory** and can be called as optional sub-steps later (e.g. inside Synthesize for complex apps).

Rationale: forge’s SLA is latency and predictability. Swarms add coordination overhead that is unnecessary for the 80% “simple tutorial → CRUD app” case.

### 3. Security baseline from EventRelay

- Port the battle-tested SSRF guard (private IP, CGNAT, link-local, metadata, IPv4-mapped/NAT64/6to4) into Python.
- Only accept YouTube hosts for Ingest.
- Light secret scan on generated code before deploy.
- Future: gitleaks + Trivy + API-key auth + rate limit (copy EventRelay patterns).

### 4. Job store starts in-memory, ready for Redis/Postgres

`JobStore` is a simple dict today so the UI works immediately. Interfaces (`create_job`, `get_job`, `update_job`, `set_status`) are already stable for a Redis + Postgres swap without changing the orchestrator.

### 5. LLM provider order

1. **Grok (xAI)** via OpenAI-compatible `/v1` (primary — speed + vision)  
2. OpenAI GPT-4o-mini / Whisper  
3. Gemini  
4. Heuristic fallback (never crash the pipeline for missing keys)

Keys are optional; pipeline degrades gracefully to mock deploy URL + template PRD.

### 6. Deploy plane defaults

- Frontend: Vercel (already live)  
- Backend workers: Railway / Fly / Cloud Run (heavy yt-dlp + FFmpeg)  
- Generated apps: Vercel by default; user owns the GitHub repo 100%

### 7. Integration boundary with EventRelay / agent-factory

- **Schemas**: Prefer agent-factory VideoPack / TaskEvents for any cross-system events.  
- **Deep analysis**: Optional HTTP call to EventRelay `/api/v1/transcript-action` when user requests “full UVAI studio agents”.  
- **Complex codegen**: Optional handoff to agent-factory swarm for multi-file enterprise apps.  
- **No monorepo merge**: Keep repos separate; communicate via OpenAPI + shared schemas.

## Consequences

### Positive
- Clear SLA ownership per stage  
- Reuses EventRelay security IP without coupling  
- Frontend can ship against real progress events today  
- Degrades without API keys (demo mode)  
- Path to swarm sophistication without blocking v0.1

### Negative / Trade-offs
- Sequential stages = no parallel media processing yet (future: frame extraction // Whisper)  
- In-memory store = no horizontal scale until Redis  
- Deterministic scaffold is “good enough” for many tutorials but will need stronger LLM codegen for complex UIs  
- Mock deploy when tokens missing may confuse users (UI should label “demo URL”)

## Alternatives considered

1. **Full swarm from day 1** — rejected for latency and complexity.  
2. **Single LLM “one-shot” codegen** — rejected; hard to debug, no progress UX, weak validation.  
3. **Embed forge inside EventRelay** — rejected; product surface needs independent branding, deploy, and pricing.  
4. **Serverless-only (no yt-dlp)** — rejected; captions-only is too lossy for many tutorials.

## Implementation notes (this commit)

- `backend/app/pipeline/orchestrator.py` + 6 stage workers  
- `backend/app/security/ssrf.py`  
- `docs/DEPENDENCY_MAP.md`  
- This ADR  

Next: wire Redis job store, WebSocket progress, real Vercel/GitHub push, and optional EventRelay agent callout.

---

**Review cadence:** Revisit after first 50 real forges or when multi-agent codegen lands.
