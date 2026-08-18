# FORGE Dependency Map

**Generated:** 2026-08-18  
**Scope:** EventRelay · agent-factory · forge · forge-spec · archived YOUTUBE-EXTENSION

---

## 1. Repository Roles

| Repo | Visibility | Role | Status |
|------|------------|------|--------|
| **forge** | public | Product surface: Next.js UI + FastAPI pipeline workers (YouTube → live app) | Active (v0.1) |
| **forge-spec** | public | Full product + technical specification (source of truth for stages/API) | Active |
| **EventRelay** | public | Agentic video capture / event extraction / MCP platform (YOUTUBE-EXTENSION consolidated here) | Active (platform) |
| **agent-factory** | private | Canonical multi-agent swarm, schemas (VideoPack/TaskEvents), code gen / verify / GitHub publisher | Active (orchestrator brain) |
| YOUTUBE-EXTENSION | private | [ARCHIVED] → EventRelay | Archived |
| .agent-orchestrator | private | [ARCHIVED] → agent-factory/swarm | Archived |
| MultiAgent | private | [ARCHIVED] → agent-factory | Archived |
| buiz-swarm | public | [ARCHIVED] → agent-factory/swarm | Archived |

---

## 2. Runtime Dependency Graph

```
┌──────────────────── forge (frontend) ────────────────────┐
│  Next.js 15 · React 19 · Framer Motion · Tailwind        │
│  POST /v1/forge/process  ←→  forge backend               │
└────────────────────────────┬─────────────────────────────┘
                             │ HTTPS
┌────────────────────────────▼─────────────────────────────┐
│  forge backend (FastAPI)                                 │
│  · PipelineOrchestrator                                  │
│  · Stage workers (ingest → build_deploy)                 │
│  · SSRF guard (from EventRelay patterns)                 │
│  · JobStore (in-memory → Redis/Postgres)                 │
└───┬──────────────┬──────────────┬──────────────┬─────────┘
    │              │              │              │
    ▼              ▼              ▼              ▼
 yt-dlp      youtube-     OpenAI /      GitHub / Vercel
 + FFmpeg    transcript-  Grok (xAI) /  (deploy plane)
             api          Gemini

Optional deep integration (future):
  forge ──calls──▶ EventRelay /api/v1/transcript-action  (richer agents)
  forge ──calls──▶ agent-factory swarm  (CEO / Eng agents for complex codegen)
  forge ──uses──▶ agent-factory schemas (VideoPack, TaskEvents)
```

---

## 3. Shared Concepts (cross-repo)

| Concept | Primary home | Consumers |
|---------|--------------|-----------|
| VideoPack schema | agent-factory/schemas | EventRelay, forge (future) |
| TaskEvents schema | agent-factory/schemas | EventRelay agents, forge jobs |
| SSRF public-URL guard | EventRelay `ssrf-guard.ts` | forge `security/ssrf.py` (ported) |
| yt-dlp + transcript pipeline | EventRelay + agent-factory | forge Ingest + HybridTranscribe |
| Multi-agent swarm | agent-factory/swarm | EventRelay agents, forge synthesize (future) |
| Code generation + Docker verify | agent-factory/services | forge Synthesize + Validate |
| GitHub publisher | agent-factory/services/github_publisher | forge BuildDeploy |
| OpenAPI / eventrelay.openapi.json | EventRelay | forge API alignment |
| Gitleaks + Trivy + CodeRabbit | EventRelay | forge (to be added) |

---

## 4. Data / Event Flow (end-to-end)

1. User pastes YouTube URL in **forge** UI  
2. Frontend `POST /v1/forge/process` → backend creates `ForgeJob`  
3. Background `PipelineOrchestrator.run()` executes stages sequentially  
4. Artifacts accumulate in shared `context` dict (transcript → PRD → source_files → live_url)  
5. Frontend polls `GET /v1/forge/{id}` (or future WebSocket) for stage progress  
6. On complete: `live_url` + optional `github_repo` returned  

Future: emit CloudEvents / TaskEvents into agent-factory Redis stream for swarm handoff.

---

## 5. Package / Library Dependencies (forge backend)

From `backend/requirements.txt`:

- **fastapi / uvicorn / pydantic** — API surface  
- **yt-dlp / youtube-transcript-api** — ingest + captions  
- **openai / google-genai** — LLM (Grok via OpenAI-compatible base_url, Gemini)  
- **redis / sqlalchemy / alembic** — production job store (not yet wired)  
- **httpx / aiofiles / orjson / structlog** — HTTP + logging  

No direct npm dependency on EventRelay or agent-factory (HTTP/schema only).

---

## 6. Security Touchpoints

| Control | EventRelay | agent-factory | forge |
|---------|------------|---------------|-------|
| SSRF guard | ✅ strong TS | partial | ✅ ported Python |
| Gitleaks | ✅ | dependabot | TODO |
| Trivy container scan | ✅ | — | TODO |
| Auth (API key / unauth fail-closed) | ✅ | basic | TODO (rate-limit + key) |
| Secret scan in generated code | — | — | ✅ light scan in Validate |
| ALLOW_UNAUTHENTICATED fail-closed | ✅ | — | planned |

---

## 7. Deployment Plane

| Component | Host |
|-----------|------|
| forge frontend | Vercel |
| forge backend | Railway / Fly / Cloud Run (planned) |
| EventRelay frontend | Vercel |
| EventRelay backend | Cloud Run (deploy-cloud-run.yml) |
| agent-factory | Docker Compose / k8s |

---

## 8. Consolidation Intent (from user)

- YOUTUBE-EXTENSION fully archived into **EventRelay**  
- Agent definitions / swarm → **agent-factory**  
- Productized “YouTube → live app” experience → **forge** (uses the two platforms above)  
- Spec lives in **forge-spec** + Notion  

This map is the living contract. Update when a new stage, shared schema, or service is introduced.
