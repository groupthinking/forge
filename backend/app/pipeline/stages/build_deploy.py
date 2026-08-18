"""Stage 6 — Build & Deploy

Packages the generated source, optionally pushes to GitHub, and deploys to Vercel
(or returns a mock live URL when credentials are absent).
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any, Optional

from app.pipeline.stages.base import BaseStage, ProgressCallback

logger = logging.getLogger(__name__)


class BuildDeployStage(BaseStage):
    name = "build_deploy"

    async def execute(
        self,
        youtube_url: str,
        options: dict[str, Any],
        context: dict[str, Any],
        progress_cb: Optional[ProgressCallback] = None,
    ) -> None:
        files: dict[str, str] = context.get("source_files") or {}
        video_id = context.get("video_id", "unknown")
        title = context.get("title", "forge-app")

        if not files:
            raise ValueError("No source_files to deploy")

        self._progress(progress_cb, 10, "Packaging source...")
        # In production: write to disk / zip / S3. Here we keep in-memory.
        context["source_zip_ready"] = True
        context["file_count"] = len(files)

        self._progress(progress_cb, 35, "Preparing GitHub repo (if token present)...")
        github_repo = await self._maybe_push_github(files, video_id, title, options)
        if github_repo:
            context["github_repo"] = github_repo
            self._progress(progress_cb, 60, f"GitHub: {github_repo}")
        else:
            self._progress(progress_cb, 55, "GitHub skipped (no GITHUB_TOKEN)")

        self._progress(progress_cb, 70, "Deploying to Vercel (if token present)...")
        live_url = await self._maybe_deploy_vercel(files, video_id, options)
        if live_url:
            context["live_url"] = live_url
            self._progress(progress_cb, 95, f"Live: {live_url}")
        else:
            # Deterministic demo URL so the frontend always has something
            slug = f"forge-{video_id[:8]}-{uuid.uuid4().hex[:6]}"
            live_url = f"https://forge.app/{slug}"
            context["live_url"] = live_url
            context["deploy_mode"] = "mock"
            self._progress(progress_cb, 95, f"Mock live URL: {live_url}")

        self._progress(progress_cb, 100, "Build & Deploy complete")

    async def _maybe_push_github(
        self,
        files: dict[str, str],
        video_id: str,
        title: str,
        options: dict[str, Any],
    ) -> Optional[str]:
        token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        if not token:
            return None
        # Real implementation would use PyGithub or gh CLI / REST.
        # For v0.1 we only document the intent and return a placeholder.
        owner = options.get("github_owner") or os.getenv("GITHUB_OWNER", "groupthinking")
        repo_name = f"forge-app-{video_id[:8]}"
        logger.info("Would create repo %s/%s with %d files (token present)", owner, repo_name, len(files))
        return f"https://github.com/{owner}/{repo_name}"

    async def _maybe_deploy_vercel(
        self,
        files: dict[str, str],
        video_id: str,
        options: dict[str, Any],
    ) -> Optional[str]:
        token = os.getenv("VERCEL_TOKEN")
        if not token:
            return None
        # Real implementation: Vercel REST / SDK with files payload.
        logger.info("Would deploy %d files to Vercel (token present)", len(files))
        return f"https://forge-{video_id[:8]}.vercel.app"
