# FORGE

**Paste a YouTube URL. Get a live app.**

YouTube tutorial / demo → fully deployed web application in minutes.

## Status

This is the production monorepo for FORGE (v0.1).

- Frontend dashboard (matching the design system)
- Pipeline UI with live progress cards
- Ready for Vercel deploy
- Backend workers & AI pipeline coming next

## Quick Start

```bash
npm install
npm run dev
```

Open http://localhost:3000

## Deploy

Already linked / ready for Vercel. Or:

```bash
npx vercel
```

## Architecture

See the full spec: [forge-spec](https://github.com/groupthinking/forge-spec) and the Notion page.

## Stack

- Next.js 15 (App Router)
- Tailwind CSS + shadcn-style components
- TypeScript
- Ready for Clerk / Auth.js, Redis, Grok API, etc.

---

Built by Grok + you.
