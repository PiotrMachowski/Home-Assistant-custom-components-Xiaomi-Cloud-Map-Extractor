from __future__ import annotations
from typing import Any

Color = tuple[int, int, int] | tuple[int, int, int, int]
Colors = dict[str, Color]
Drawables = list[str]
Texts = list[Any]
Sizes = dict[str, float]
ImageConfig = dict[str, Any]
CalibrationPoints = list[dict[str, dict[str, float | int]]]
