"""Types for integration."""
from typing import Any, Union

Color = Union[tuple[int, int, int], tuple[int, int, int, int]]
Colors = dict[str, Color]
Drawables = list[str]
Texts = list[Any]
Sizes = dict[str, float]
ImageConfig = dict[str, Any]
CalibrationPoints = list[dict[str, dict[str, Union[float, int]]]]
