"""Stage 1 — Ingest

Downloads video metadata, audio, key frames, and description via yt-dlp.
Validates the URL is a public YouTube resource (SSRF-safe).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Optional

from app.pipeline.stages.base import BaseStage, ProgressCallback
from app.security.ssrf import assert_public_youtube_url

logger = logging.getLogger(__name__)

YOUTUBE_ID_RE = re.compile(
    r"(?:youtube\.com/(?:watch\?v=|embed/|shorts/)|youtu\.be/)([A-Za-z0-9_-]{11})"
)


class IngestStage(BaseStage):
    name = "ingest"

    async def execute(
        self,
        youtube_url: str,
        options: dict[str, Any],
        context: dict[str, Any],
        progress_cb: Optional[ProgressCallback] = None,
    ) -> None:
        self._progress(progress_cb, 5, "Validating YouTube URL...")
        url = await assert_public_youtube_url(youtube_url)

        video_id = self._extract_id(str(url))
        if not video_id:
            raise ValueError("Could not extract YouTube video ID")

        context["video_id"] = video_id
        context["youtube_url"] = str(url)
        self._progress(progress_cb, 15, f"Resolved video_id={video_id}")

        # Metadata extraction (yt-dlp in subprocess to keep event loop free)
        self._progress(progress_cb, 25, "Fetching metadata with yt-dlp...")
        meta = await self._fetch_metadata(str(url))
        context["metadata"] = meta
        context["title"] = meta.get("title", "Untitled")
        context["description"] = meta.get("description", "")[:4000]
        context["duration"] = meta.get("duration")
        context["channel"] = meta.get("channel") or meta.get("uploader")

        self._progress(progress_cb, 55, "Metadata captured")

        # Optional: download audio for Whisper (controlled by options)
        download_media = options.get("download_media", True)
        if download_media:
            self._progress(progress_cb, 65, "Preparing audio track...")
            audio_path = await self._download_audio(str(url), video_id)
            if audio_path:
                context["audio_path"] = audio_path
                self._progress(progress_cb, 90, "Audio ready")
            else:
                self._progress(progress_cb, 85, "Audio download skipped / failed (will use captions)")

        self._progress(progress_cb, 100, "Ingest complete")

    def _extract_id(self, url: str) -> Optional[str]:
        m = YOUTUBE_ID_RE.search(url)
        return m.group(1) if m else None

    async def _fetch_metadata(self, url: str) -> dict[str, Any]:
        """Run yt-dlp -J for JSON metadata."""
        cmd = [
            "yt-dlp",
            "--no-download",
            "--no-warnings",
            "-j",
            "--skip-download",
            url,
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=45)
            if proc.returncode != 0:
                logger.warning("yt-dlp metadata failed: %s", stderr.decode()[:500])
                # Fallback minimal meta
                return {"title": "Unknown", "id": self._extract_id(url)}
            return json.loads(stdout.decode())
        except FileNotFoundError:
            logger.warning("yt-dlp not installed — using minimal metadata")
            return {"title": "Unknown (yt-dlp missing)", "id": self._extract_id(url)}
        except Exception as e:
            logger.exception("Metadata fetch error")
            return {"title": "Unknown", "error": str(e)}

    async def _download_audio(self, url: str, video_id: str) -> Optional[str]:
        """Download best audio to a temp file. Returns path or None."""
        tmp_dir = Path(tempfile.gettempdir()) / "forge" / video_id
        tmp_dir.mkdir(parents=True, exist_ok=True)
        out_tmpl = str(tmp_dir / "audio.%(ext)s")

        cmd = [
            "yt-dlp",
            "-x",
            "--audio-format", "m4a",
            "--audio-quality", "5",
            "-o", out_tmpl,
            "--no-playlist",
            "--no-warnings",
            "--max-filesize", "100M",
            url,
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=120)
            # Find the resulting file
            for p in tmp_dir.glob("audio.*"):
                if p.is_file() and p.stat().st_size > 0:
                    return str(p)
            return None
        except Exception as e:
            logger.warning("Audio download failed: %s", e)
            return None
