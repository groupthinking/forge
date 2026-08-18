"""Stage 4 — Synthesize

Codegen: turns the PRD JSON into a full Next.js monorepo source tree.
Uses LLM for generation + deterministic templates for scaffolding.
"""

from __future__ import annotations

import json
import logging
import os
import textwrap
from typing import Any, Optional

from app.pipeline.stages.base import BaseStage, ProgressCallback

logger = logging.getLogger(__name__)


class SynthesizeStage(BaseStage):
    name = "synthesize"

    async def execute(
        self,
        youtube_url: str,
        options: dict[str, Any],
        context: dict[str, Any],
        progress_cb: Optional[ProgressCallback] = None,
    ) -> None:
        prd = context.get("prd") or {}
        title = context.get("title", "Forge App")
        video_id = context.get("video_id", "unknown")

        self._progress(progress_cb, 10, "Scaffolding Next.js project structure...")

        # Deterministic high-quality scaffold (LLM can refine later)
        files = self._scaffold_nextjs(prd, title, video_id)

        self._progress(progress_cb, 55, f"Generated {len(files)} source files")

        # Optional LLM polish of page.tsx / components
        if options.get("llm_codegen", True):
            self._progress(progress_cb, 65, "LLM polish of primary screens...")
            polished = await self._llm_polish(prd, files.get("app/page.tsx", ""))
            if polished:
                files["app/page.tsx"] = polished

        context["source_files"] = files
        context["synthesize_source"] = {"file_count": len(files), "root": "app/"}
        self._progress(progress_cb, 100, f"Synthesize complete — {len(files)} files ready")

    def _scaffold_nextjs(self, prd: dict, title: str, video_id: str) -> dict[str, str]:
        """Produce a minimal but real Next.js 15 + Tailwind app from PRD."""
        intent = prd.get("intent", f"App from video {video_id}")
        stories = prd.get("user_stories", [])
        screens = prd.get("screens", [{"name": "Home", "route": "/"}])
        stack = prd.get("tech_stack", {})

        safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in title)[:60] or "ForgeApp"

        package_json = json.dumps(
            {
                "name": f"forge-{video_id[:8]}",
                "version": "0.1.0",
                "private": True,
                "scripts": {
                    "dev": "next dev",
                    "build": "next build",
                    "start": "next start",
                    "lint": "next lint",
                },
                "dependencies": {
                    "next": "15.5.0",
                    "react": "19.0.0",
                    "react-dom": "19.0.0",
                    "lucide-react": "^0.454.0",
                    "framer-motion": "^11.11.0",
                },
                "devDependencies": {
                    "typescript": "^5.6.0",
                    "@types/react": "^19.0.0",
                    "@types/node": "^22.0.0",
                    "tailwindcss": "^3.4.0",
                    "postcss": "^8.4.0",
                    "autoprefixer": "^10.4.0",
                },
            },
            indent=2,
        )

        page_tsx = textwrap.dedent(
            f'''\
            "use client";

            import {{ motion }} from "framer-motion";

            export default function Home() {{
              return (
                <main className="min-h-screen bg-zinc-950 text-white flex flex-col items-center justify-center p-8">
                  <motion.div
                    initial={{{{ opacity: 0, y: 20 }}}}
                    animate={{{{ opacity: 1, y: 0 }}}}
                    className="max-w-2xl text-center space-y-6"
                  >
                    <h1 className="text-4xl font-bold tracking-tight">{safe_title}</h1>
                    <p className="text-zinc-400 text-lg">{intent}</p>
                    <ul className="text-left space-y-2 text-sm text-zinc-300">
                      {chr(10).join(f'                      <li>• {{s}}</li>' for s in (stories[:5] or ["Primary feature ready"]))}
                    </ul>
                    <button className="mt-6 px-6 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 font-medium transition">
                      Get Started
                    </button>
                    <p className="text-xs text-zinc-600">Forged from YouTube · video_id={video_id}</p>
                  </motion.div>
                </main>
              );
            }}
            '''
        )

        layout = textwrap.dedent(
            f'''\
            import type {{ Metadata }} from "next";
            import "./globals.css";

            export const metadata: Metadata = {{
              title: "{safe_title}",
              description: "{intent[:120]}",
            }};

            export default function RootLayout({{ children }}: {{ children: React.ReactNode }}) {{
              return (
                <html lang="en">
                  <body className="antialiased">{children}</body>
                </html>
              );
            }}
            '''
        )

        globals_css = textwrap.dedent(
            """\
            @tailwind base;
            @tailwind components;
            @tailwind utilities;

            body {
              @apply bg-zinc-950 text-white;
            }
            """
        )

        tailwind = textwrap.dedent(
            """\
            import type { Config } from "tailwindcss";

            const config: Config = {
              content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
              theme: { extend: {} },
              plugins: [],
            };
            export default config;
            """
        )

        tsconfig = json.dumps(
            {
                "compilerOptions": {
                    "target": "ES2017",
                    "lib": ["dom", "dom.iterable", "esnext"],
                    "allowJs": True,
                    "skipLibCheck": True,
                    "strict": True,
                    "noEmit": True,
                    "esModuleInterop": True,
                    "module": "esnext",
                    "moduleResolution": "bundler",
                    "resolveJsonModule": True,
                    "isolatedModules": True,
                    "jsx": "preserve",
                    "incremental": True,
                    "plugins": [{"name": "next"}],
                    "paths": {"@/*": ["./*"]},
                },
                "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
                "exclude": ["node_modules"],
            },
            indent=2,
        )

        readme = f"""# {safe_title}

Generated by FORGE from YouTube video `{video_id}`.

## Intent
{intent}

## Stack
{json.dumps(stack, indent=2)}

## Run locally
```bash
npm install
npm run dev
```
"""

        return {
            "package.json": package_json,
            "tsconfig.json": tsconfig,
            "tailwind.config.ts": tailwind,
            "postcss.config.mjs": 'export default { plugins: { tailwindcss: {}, autoprefixer: {} } };\n',
            "next.config.ts": 'import type { NextConfig } from "next";\nconst nextConfig: NextConfig = {};\nexport default nextConfig;\n',
            "app/layout.tsx": layout,
            "app/page.tsx": page_tsx,
            "app/globals.css": globals_css,
            "README.md": readme,
            ".gitignore": "node_modules\n.next\n.env*\n",
        }

    async def _llm_polish(self, prd: dict, current_page: str) -> Optional[str]:
        """Optional second LLM pass to improve the home page."""
        # Keep v0.1 simple — return current. Future: call Grok with PRD + page.
        return None
