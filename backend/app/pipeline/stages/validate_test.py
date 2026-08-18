"""Stage 5 — Validate + Test

Runs static checks on generated source:
  - TypeScript / JSON validity
  - Required files present
  - Basic lint heuristics
  - (Future) tsc + Playwright in isolated container
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from app.pipeline.stages.base import BaseStage, ProgressCallback

logger = logging.getLogger(__name__)

REQUIRED_FILES = [
    "package.json",
    "app/page.tsx",
    "app/layout.tsx",
    "README.md",
]


class ValidateTestStage(BaseStage):
    name = "validate_test"

    async def execute(
        self,
        youtube_url: str,
        options: dict[str, Any],
        context: dict[str, Any],
        progress_cb: Optional[ProgressCallback] = None,
    ) -> None:
        files: dict[str, str] = context.get("source_files") or {}
        if not files:
            raise ValueError("No source_files in context — Synthesize must run first")

        self._progress(progress_cb, 15, "Checking required files...")
        missing = [f for f in REQUIRED_FILES if f not in files]
        if missing:
            raise ValueError(f"Generated project missing files: {missing}")

        self._progress(progress_cb, 40, "Validating package.json...")
        try:
            pkg = json.loads(files["package.json"])
            if "dependencies" not in pkg or "next" not in pkg.get("dependencies", {}):
                raise ValueError("package.json missing next dependency")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid package.json: {e}") from e

        self._progress(progress_cb, 65, "Scanning for secrets / dangerous patterns...")
        findings = self._secret_scan(files)
        if findings:
            # Soft fail for now — log and attach, do not hard-fail v0.1
            logger.warning("Secret-scan findings: %s", findings)
            context["validate_findings"] = findings

        self._progress(progress_cb, 85, "Heuristic code quality checks...")
        # Ensure page.tsx has export default
        page = files.get("app/page.tsx", "")
        if "export default" not in page:
            raise ValueError("app/page.tsx has no default export")

        context["validate_ok"] = True
        context["validate_report"] = {
            "files_checked": len(files),
            "required_ok": True,
            "secret_findings": findings,
        }
        self._progress(progress_cb, 100, "Validation passed")

    def _secret_scan(self, files: dict[str, str]) -> list[str]:
        """Very light pattern scan — real production should use gitleaks."""
        patterns = [
            ("sk-", "possible OpenAI key"),
            ("xai-", "possible xAI key"),
            ("AIza", "possible Google API key"),
            ("-----BEGIN", "private key block"),
            ("aws_secret", "AWS secret"),
        ]
        hits: list[str] = []
        for path, content in files.items():
            lower = content.lower()
            for needle, label in patterns:
                if needle.lower() in lower:
                    hits.append(f"{path}: {label}")
        return hits
