"""Module for transforming coordinates."""
from vacuum_map_parser_base.map_data import Point
from typing import Any

class Transformer: # pylint: disable=E1101
    """Class for transforming coordinates."""

    def __init__(self, robotmap: Any):
        self.map_head = robotmap.mapHead
        self.to_image_multiplier = Point(self.map_head.sizeX/(self.map_head.maxX - self.map_head.minX),
                                         self.map_head.sizeY/(self.map_head.maxY - self.map_head.minY))

    def map_to_image(self, pt: Point) -> Point:
        return Point((pt.x - self.map_head.minX) * self.to_image_multiplier.x,
                     (pt.y - self.map_head.minY) * self.to_image_multiplier.y)

    def image_to_map_x(self, x: int) -> float:
        return x/self.to_image_multiplier.x + self.map_head.minX

    def image_to_map_y(self, y: int) -> float:
        return y/self.to_image_multiplier.y + self.map_head.minY
