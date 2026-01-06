from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Union

@dataclass
class OutText:
    kind: Literal["text"] = "text"
    text: str = ""

@dataclass
class OutPhoto:
    kind: Literal["photo"] = "photo"
    path: str = ""      # local path inside repo/container
    caption: str = ""

Action = Union[OutText, OutPhoto]
