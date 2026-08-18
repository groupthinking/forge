"""Base class for all FORGE pipeline stages."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Optional

ProgressCallback = Callable[[int, str], None]


class BaseStage(ABC):
    """Abstract stage worker.

    Subclasses implement `execute`. They receive a shared `context` dict
    that accumulates artifacts across stages and a progress callback.
    """

    name: str = "base"

    @abstractmethod
    async def execute(
        self,
        youtube_url: str,
        options: dict[str, Any],
        context: dict[str, Any],
        progress_cb: Optional[ProgressCallback] = None,
    ) -> None:
        """Run the stage. Mutate `context` with new artifacts."""
        ...

    def _progress(self, progress_cb: Optional[ProgressCallback], p: int, msg: str) -> None:
        if progress_cb:
            progress_cb(p, msg)
