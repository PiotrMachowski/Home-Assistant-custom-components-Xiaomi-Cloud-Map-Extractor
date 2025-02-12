import io

from vacuum_map_parser_base.map_data import MapData


def to_image(map_data: MapData) -> bytes:
    img_byte_arr = io.BytesIO()
    map_data.image.data.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()
