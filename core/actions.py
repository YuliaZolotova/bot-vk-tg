from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OutText:
    text: str


@dataclass(frozen=True)
class OutPhoto:
    """Send a local image file.

    `path` must be an absolute path or a path relative to the project root.
    """

    path: str
    caption: str = ""

