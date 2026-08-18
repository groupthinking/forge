"""Stage 2 — Hybrid Transcribe

Combines:
  - YouTube captions (youtube-transcript-api) as primary fast path
  - Whisper / OpenAI STT on downloaded audio as fallback
  - Optional vision OCR / frame description (Grok / Gemini vision) for UI text
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Optional

from app.pipeline.stages.base import BaseStage, ProgressCallback

logger = logging.getLogger(__name__)


class HybridTranscribeStage(BaseStage):
    name = "hybrid_transcribe"

    async def execute(
        self,
        youtube_url: str,
        options: dict[str, Any],
        context: dict[str, Any],
        progress_cb: Optional[ProgressCallback] = None,
    ) -> None:
        video_id = context.get("video_id")
        if not video_id:
            raise ValueError("video_id missing from context — Ingest must run first")

        self._progress(progress_cb, 10, "Fetching YouTube captions...")
        transcript = await self._get_captions(video_id)

        if transcript and len(transcript.strip()) > 80:
            context["transcript"] = transcript
            context["transcript_source"] = "youtube_captions"
            self._progress(progress_cb, 70, f"Captions OK ({len(transcript)} chars)")
        else:
            self._progress(progress_cb, 40, "Captions missing/short — falling back to STT...")
            audio_path = context.get("audio_path")
            if audio_path and os.path.exists(audio_path):
                transcript = await self._whisper_stt(audio_path)
                context["transcript"] = transcript or ""
                context["transcript_source"] = "whisper_stt"
            else:
                # Last resort: empty + flag
                context["transcript"] = context.get("description", "")
                context["transcript_source"] = "description_fallback"
                logger.warning("No captions and no audio — using description")

        self._progress(progress_cb, 85, "Optional vision pass for on-screen text...")
        # Vision OCR / UI description (best-effort, non-blocking for v0.1)
        ui_desc = await self._vision_ui_pass(context)
        if ui_desc:
            context["ui_description"] = ui_desc

        self._progress(progress_cb, 100, "Hybrid transcription complete")

    async def _get_captions(self, video_id: str) -> str:
        try:
            from youtube_transcript_api import YouTubeTranscriptApi

            def _fetch():
                try:
                    # New API style (0.6+)
                    ytt = YouTubeTranscriptApi()
                    fetched = ytt.fetch(video_id, languages=["en", "en-US", "en-GB"])
                    if hasattr(fetched, "to_raw_data"):
                        snippets = fetched.to_raw_data()
                    else:
                        snippets = list(fetched)
                    return " ".join(s.get("text", "") for s in snippets if s.get("text"))
                except Exception:
                    # Older style
                    transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=["en"])
                    return " ".join(t["text"] for t in transcript_list)

            return await asyncio.to_thread(_fetch)
        except Exception as e:
            logger.info("Captions unavailable for %s: %s", video_id, e)
            return ""

    async def _whisper_stt(self, audio_path: str) -> str:
        """Call OpenAI Whisper if key present, else return empty."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not set — skipping Whisper")
            return ""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=api_key)
            with open(audio_path, "rb") as f:
                result = await client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    response_format="text",
                )
            return str(result) if result else ""
        except Exception as e:
            logger.exception("Whisper STT failed: %s", e)
            return ""

    async def _vision_ui_pass(self, context: dict[str, Any]) -> str:
        """Placeholder for Grok/Gemini vision frame analysis.

        In production this would sample key frames and ask a vision model
        for on-screen text, buttons, layout description.
        """
        # v0.1: return a lightweight synthetic description from metadata
        title = context.get("title", "")
        desc = (context.get("description") or "")[:300]
        return f"UI inferred from title/description. Title: {title}. Snippet: {desc}"
