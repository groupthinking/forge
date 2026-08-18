"""Stage 3 — Analyze + Extract

Multimodal LLM turn that produces a structured PRD-like JSON:
  - intent / problem statement
  - user stories
  - data model
  - screens / flows
  - tech stack recommendation
  - acceptance criteria
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

from app.pipeline.stages.base import BaseStage, ProgressCallback

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are FORGE Analyze agent. Given a YouTube tutorial transcript + metadata,
extract a complete product requirements document as strict JSON.

Return ONLY valid JSON with this schema:
{
  "intent": "one sentence product intent",
  "problem": "problem being solved",
  "user_stories": ["As a ... I want ... so that ..."],
  "data_model": [{"name": "Entity", "fields": ["id", "..."]}],
  "screens": [{"name": "Home", "components": ["header", "..."], "route": "/"}],
  "flows": [{"name": "happy path", "steps": ["..."]}],
  "tech_stack": {
    "frontend": "Next.js 15 + React 19 + Tailwind",
    "backend": "FastAPI or Next.js API routes",
    "db": "Postgres / SQLite",
    "deploy": "Vercel"
  },
  "acceptance_criteria": ["..."]
}
"""


class AnalyzeExtractStage(BaseStage):
    name = "analyze_extract"

    async def execute(
        self,
        youtube_url: str,
        options: dict[str, Any],
        context: dict[str, Any],
        progress_cb: Optional[ProgressCallback] = None,
    ) -> None:
        transcript = context.get("transcript", "")
        title = context.get("title", "")
        description = context.get("description", "")
        ui_desc = context.get("ui_description", "")

        if not transcript and not description:
            raise ValueError("No transcript or description available for analysis")

        self._progress(progress_cb, 15, "Building analysis prompt...")

        user_content = f"""TITLE: {title}

DESCRIPTION:
{description[:2000]}

TRANSCRIPT (first 12k chars):
{transcript[:12000]}

UI / ON-SCREEN NOTES:
{ui_desc}

Produce the PRD JSON now."""

        self._progress(progress_cb, 35, "Calling multimodal LLM...")
        prd = await self._call_llm(user_content, options)

        # Validate shape lightly
        if not isinstance(prd, dict) or "intent" not in prd:
            logger.warning("LLM returned non-PRD shape — synthesizing minimal PRD")
            prd = self._fallback_prd(title, transcript, description)

        context["prd"] = prd
        context["analyze_extract_prd"] = prd
        self._progress(progress_cb, 100, f"PRD ready — intent: {prd.get('intent', '')[:80]}")

    async def _call_llm(self, user_content: str, options: dict[str, Any]) -> dict[str, Any]:
        """Prefer Grok (xAI) → OpenAI → heuristic fallback."""
        # 1. xAI / Grok
        xai_key = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")
        if xai_key:
            try:
                return await self._openai_compatible(
                    base_url="https://api.x.ai/v1",
                    api_key=xai_key,
                    model=options.get("model", "grok-2-latest"),
                    user_content=user_content,
                )
            except Exception as e:
                logger.warning("Grok call failed: %s", e)

        # 2. OpenAI
        oai_key = os.getenv("OPENAI_API_KEY")
        if oai_key:
            try:
                return await self._openai_compatible(
                    base_url="https://api.openai.com/v1",
                    api_key=oai_key,
                    model=options.get("model", "gpt-4o-mini"),
                    user_content=user_content,
                )
            except Exception as e:
                logger.warning("OpenAI call failed: %s", e)

        # 3. Gemini
        gem_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if gem_key:
            try:
                return await self._gemini(gem_key, user_content)
            except Exception as e:
                logger.warning("Gemini call failed: %s", e)

        logger.warning("No LLM keys available — using heuristic PRD")
        return {}

    async def _openai_compatible(
        self,
        base_url: str,
        api_key: str,
        model: str,
        user_content: str,
    ) -> dict[str, Any]:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        resp = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        text = resp.choices[0].message.content or "{}"
        return json.loads(text)

    async def _gemini(self, api_key: str, user_content: str) -> dict[str, Any]:
        try:
            from google import genai

            client = genai.Client(api_key=api_key)
            resp = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=SYSTEM_PROMPT + "\n\n" + user_content,
                config={"response_mime_type": "application/json"},
            )
            return json.loads(resp.text or "{}")
        except Exception:
            # Older google-generativeai
            import google.generativeai as genai

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            resp = model.generate_content(
                SYSTEM_PROMPT + "\n\n" + user_content,
                generation_config={"response_mime_type": "application/json"},
            )
            return json.loads(resp.text or "{}")

    def _fallback_prd(self, title: str, transcript: str, description: str) -> dict[str, Any]:
        return {
            "intent": f"Build an app inspired by: {title or 'YouTube tutorial'}",
            "problem": description[:200] or "User wants a working app from the video",
            "user_stories": [
                "As a user I want to paste a URL and get a working web app",
                "As a user I want the UI to match the tutorial aesthetic",
            ],
            "data_model": [{"name": "Item", "fields": ["id", "title", "created_at"]}],
            "screens": [
                {"name": "Home", "components": ["header", "list", "cta"], "route": "/"},
                {"name": "Detail", "components": ["header", "content"], "route": "/item/[id]"},
            ],
            "flows": [{"name": "happy path", "steps": ["land", "interact", "complete"]}],
            "tech_stack": {
                "frontend": "Next.js 15 + React 19 + Tailwind",
                "backend": "Next.js API routes",
                "db": "SQLite / Postgres",
                "deploy": "Vercel",
            },
            "acceptance_criteria": [
                "App loads without errors",
                "Primary CTA works",
                "Responsive layout",
            ],
        }
