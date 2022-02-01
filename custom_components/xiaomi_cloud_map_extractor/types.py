from typing import Any, Dict, List, Tuple, Union

Color = Union[Tuple[int, int, int], Tuple[int, int, int, int]]
Colors = Dict[str, Color]
Drawables = List[str]
Texts = List[Any]
Sizes = Dict[str, float]
ImageConfig = Dict[str, Any]
CalibrationPoints = List[Dict[str, Dict[str, Union[float, int]]]]
