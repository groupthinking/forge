# Deep-Dive Audit: EventRelay + agent-factory

**Date:** 2026-08-18  
**Auditor:** Grok (xAI)  
**Scope:** Security · Code quality · Structure · Architecture  
**Context:** YOUTUBE-EXTENSION archived into EventRelay; forge is the new product surface that reuses patterns from both repos.

---

## 1. Executive Summary

| Repo | Security posture | Code quality | Structure | Architecture maturity |
|------|------------------|--------------|-----------|-----------------------|
| **EventRelay** | Strong (SSRF, gitleaks, Trivy, fail-closed auth) | High (tests, skills, pre-commit) | Large monorepo, well-documented | Production-oriented hybrid AI platform |
| **agent-factory** | Good (dependabot, Next security patches, production-check) | High (79% coverage, Black/flake8, schemas) | Clean consolidation of 6 repos | Solid multi-agent swarm + video pipeline |

Both repos are production-ready building blocks. **forge** now scaffolds real workers that port EventRelay SSRF and agent-factory orchestration patterns without creating a hard monorepo dependency.

---

## 2. EventRelay — Detailed Findings

### 2.1 Security ✅ Strong

**Highlights**
- **SSRF guard** (`apps/web/src/lib/ssrf-guard.ts`) is exceptional: private IPv4/IPv6, CGNAT, link-local, IPv4-mapped, NAT64 (`64:ff9b::/96`), 6to4 (`2002::/16`), fail-closed DNS, no oracle leakage. Multiple dedicated unit tests (`ssrf-guard*.test.ts`).
- **Gitleaks** (`.gitleaks.toml`) with allowlist for lockfile digests and vendored docs.
- **Trivy** container scanning in CI; `.trivyignore` for accepted risks.
- **Auth fail-closed**: without `ALLOW_UNAUTHENTICATED=1` or `EVENTRELAY_API_KEY`, non-public routes return 503.
- **SECURITY.md** with reporting path, secret handling, incident response.
- **Pre-commit** + CodeRabbit config present.
- **.env.example** comprehensive (10k+ chars of documented vars).

**Gaps / Recommendations**
1. Ensure production never sets `ALLOW_UNAUTHENTICATED=1` (document in LAUNCH_CHECKLIST).
2. Add rate limiting on `/api/video` and realtime session endpoints (partially present via billing/turnstile).
3. Consider pinning resolved IPs for fetch (TOCTOU note already documented in the guard).
4. Rotate keys quarterly (already in SECURITY.md).

### 2.2 Code Quality ✅ High

- Heavy test suite under `apps/web/src/lib/__tests__/` (SSRF, pipeline, billing, transcription, accessibility…).
- `.agents/skills` for React best practices, TDD, Firebase, systematic debugging.
- Python: `pyproject.toml` with ruff/mypy/pytest; `uv.lock` for reproducible installs.
- TypeScript strict, Vitest, Next.js App Router.
- Clear Conventional Commits + CONTRIBUTING + AGENTS.md.

**Minor issues**
- Repo size is large (~1.1M); consider splitting MCP servers / heavy media tooling if CI time becomes painful.
- Some architecture docs (ARCHITECTURE.md) describe a slightly idealized layout vs current `apps/` + `src/` hybrid — keep docs in sync with `git ls-files`.

### 2.3 Structure

```
EventRelay/
├── apps/web/          # Next.js frontend + API routes
├── src/               # FastAPI / youtube_extension backend
├── mcp-servers/       # MCP capability nodes
├── openapi/           # OpenAPI specs
├── .agents/skills/    # Agent skills (React, TDD, etc.)
├── infrastructure/    # Docker, Cloud Run
├── tests/
├── docs/
└── supabase/ dataconnect/
```

Monorepo with Turbo. YOUTUBE-EXTENSION functionality fully absorbed (transcript-action, Gemini agents, studio UI).

### 2.4 Architecture

- Hybrid AI: Gemini (personality/strategy) + OpenAI Responses (strict JSON schema events) + Whisper/STT fallback.
- Realtime voice (WebRTC → OpenAI Realtime) gated carefully.
- Pipeline: URL → transcript → multi-agent analysis → structured events → actions.
- MCP bridge for external tools (Vercel, etc.).
- EventRelay is the **platform**; forge is a specialized product that can optionally call into it.

---

## 3. agent-factory — Detailed Findings

### 3.1 Security ✅ Good

- Dependabot enabled.
- Next.js upgraded past known SSRF/cache-poisoning CVEs (see PRODUCTION_READINESS_REPORT).
- `production-check.sh` runs vulnerability scan.
- No public security advisories open.
- Dockerfiles present; secrets via `.env.example`.

**Gaps**
1. No dedicated SSRF guard as strong as EventRelay’s (video URLs should be validated the same way).
2. Recommend adding gitleaks + Trivy to match EventRelay.
3. GitHub token scopes should be least-privilege for the publisher service.

### 3.2 Code Quality ✅ High

- **55 tests, 79% coverage** (backend).
- Black + flake8 (88-char), full type hints on critical paths.
- Schema validation scripts + JSON Schema for VideoPack / TaskEvents.
- PRODUCTION_READINESS_REPORT.md + PRODUCTION.md + CHANGELOG.
- Swarm agents (CEO, Engineering, Marketing, Support) with clear base class and MCP client.

### 3.3 Structure

```
agent-factory/
├── swarm/                 # Multi-agent orchestrator (from buiz-swarm + .agent-orchestrator)
│   ├── core/              # swarm_orchestrator, agent_core, mcp_client
│   ├── agents/            # base + specialized
│   └── definitions/       # .md agent prompts
├── backend/               # FastAPI video + task API
├── frontend/              # Next.js dashboard
├── services/              # code_generation, code_verification, github_publisher
├── schemas/               # VideoPack, TaskEvents, entities
├── docs/ + scripts/
└── infra/docker/
```

Clean consolidation of 6 prior repos (documented in CONSOLIDATION.md).

### 3.4 Architecture

- SwarmOrchestrator with priority queues and capability matching.
- Video pipeline: validate → transcript → event extraction.
- Services for codegen → Docker verify → GitHub publish (exactly what forge BuildDeploy needs long-term).
- Shared schemas are the integration contract for forge / EventRelay.

---

## 4. Cross-Repo Recommendations for forge

| Priority | Action | Source pattern |
|----------|--------|----------------|
| P0 | Port SSRF to Python (done in this commit) | EventRelay ssrf-guard.ts |
| P0 | Six-stage sequential orchestrator (done) | forge-spec + agent-factory orchestrator |
| P1 | Wire Redis + Postgres job store | agent-factory database_service |
| P1 | WebSocket stage progress | EventRelay pipeline stream |
| P1 | Real Vercel + GitHub push | agent-factory github_publisher + services |
| P2 | Optional EventRelay transcript-action callout | EventRelay API |
| P2 | Optional swarm handoff for complex PRDs | agent-factory swarm |
| P2 | gitleaks + Trivy CI | EventRelay .github |
| P3 | VideoPack / TaskEvents schema adoption | agent-factory schemas |

---

## 5. Risk Register (forge-specific)

| Risk | Mitigation |
|------|------------|
| yt-dlp / FFmpeg heavy → OOM on serverless | Run workers on Railway/Fly/Cloud Run with disk; frontend stays on Vercel |
| LLM cost runaway | Per-job token cap + options.max_tokens; free tier limits |
| Generated code with secrets | Validate stage secret scan + future gitleaks on artifact |
| YouTube ToS / copyright | Explicit notice; rate limit; no re-upload of original media |
| SSRF via malicious URL | YouTube-host allowlist + private IP block (done) |

---

## 6. Verdict

- **EventRelay** is the secure, battle-tested **platform** for video intelligence and agent execution.  
- **agent-factory** is the **orchestration brain** + schema home + codegen/verify/publish services.  
- **forge** is the **product** that reuses both: real workers scaffolded, SSRF ported, dependency map + ADR published.  

No critical security blockers found. Proceed with Redis store, live deploy plane, and progressive EventRelay/agent-factory integration.

---

*This audit was performed via live GitHub tree + file contents (no local clone). Re-run after major merges.*
