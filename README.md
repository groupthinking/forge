# FORGE

**Paste a YouTube URL. Get a live app.**

YouTube tutorial / demo → fully deployed web application in minutes.

## 🚀 Live Demo

**https://forge-n3oc73sh8-garv1.vercel.app**  
(also: https://forge-git-main-garv1.vercel.app)

## Status

v0.2 — Frontend complete · **Real backend pipeline workers live**

- ✅ Dashboard UI matching the design system
- ✅ Live progress cards
- ✅ **6-stage PipelineOrchestrator** (Ingest → Hybrid Transcribe → Analyze → Synthesize → Validate → Build & Deploy)
- ✅ SSRF guard (ported from EventRelay)
- ✅ yt-dlp + captions + Whisper/Grok/Gemini LLM path
- ✅ Deterministic Next.js scaffold + secret scan
- ✅ Dependency map + ADR-001
- ⏳ Redis job store + WebSocket progress + real Vercel/GitHub push next

## Quick Start

### Frontend
```bash
git clone https://github.com/groupthinking/forge.git
cd forge
npm install
npm run dev
```
Open http://localhost:3000

### Backend workers
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Optional keys for full power:
# export OPENAI_API_KEY=... XAI_API_KEY=... GEMINI_API_KEY=... GITHUB_TOKEN=... VERCEL_TOKEN=...
uvicorn app.main:app --reload --port 8000
```

Health: `curl localhost:8000/health`

Start a job:
```bash
curl -X POST localhost:8000/v1/forge/process \
  -H 'Content-Type: application/json' \
  -d '{"youtube_url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

Poll: `GET /v1/forge/{project_id}`

## Architecture & Spec

- Full product + technical spec: [forge-spec](https://github.com/groupthinking/forge-spec)
- **Dependency map** (EventRelay · agent-factory · forge): [docs/DEPENDENCY_MAP.md](docs/DEPENDENCY_MAP.md)
- **ADR-001 Pipeline Architecture**: [docs/ADR-001-pipeline-architecture.md](docs/ADR-001-pipeline-architecture.md)
- **Security/code-quality audit**: [docs/AUDIT-EventRelay-agent-factory.md](docs/AUDIT-EventRelay-agent-factory.md)

## Pipeline Stages

| Stage | What it does |
|-------|----------------|
| 1. Ingest | SSRF-safe YouTube URL → yt-dlp metadata + audio |
| 2. Hybrid Transcribe | Captions → Whisper fallback → vision UI notes |
| 3. Analyze + Extract | Multimodal LLM → structured PRD JSON |
| 4. Synthesize | PRD → full Next.js 15 source tree |
| 5. Validate + Test | Required files, package.json, secret scan |
| 6. Build & Deploy | Package → optional GitHub + Vercel (or mock live URL) |

## Stack

- Next.js 15.5 (App Router) + React 19 + Framer Motion + Tailwind
- FastAPI + yt-dlp + youtube-transcript-api + OpenAI/Grok/Gemini
- Deployed frontend on Vercel; workers on Railway/Fly/Cloud Run (planned)

## Related Repos

- [EventRelay](https://github.com/groupthinking/EventRelay) — agentic video platform (YOUTUBE-EXTENSION consolidated here)
- [agent-factory](https://github.com/groupthinking/agent-factory) — multi-agent swarm + schemas + codegen/verify/publish
- [forge-spec](https://github.com/groupthinking/forge-spec) — product & technical specification

---

Built by Grok + you.  
Repo: https://github.com/groupthinking/forge
