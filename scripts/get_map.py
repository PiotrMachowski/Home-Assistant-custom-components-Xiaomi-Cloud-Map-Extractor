import miio
import time
import io
from .xiaomi_cloud_connector import XiaomiCloudConnector
from .const import *

# ********* CONFIGURATION *********

vacuum_ip = ""
token = ""
username = ""
password = ""
country = ""

draw = [
    "charger",
    "path",
    "goto_path",
    "predicted_path",
    "no_go_zones",
    "no_mopping_zones",
    "vacuum_position",
    "virtual_walls",
    "zones"
]

colors = {
    "color_path": (255, 0, 0, 127),
    "color_goto_path": (0, 255, 0),
    "color_predicted_path": (0, 0, 255),
    "color_zones": (0x1F, 0x6A, 0xFC),
    "color_zones_outline": (0x25, 0x74, 0xB5, 0x60),
}

room_colors = {
    1: (255, 0, 0),
    2: (0, 255, 0),
    3: (0, 0, 255),
    4: (0, 255, 255),
    5: (255, 0, 255)
}

texts = [
    {
        "text": "Room1",
        "x": 25,
        "y": 25,
        "color": (255, 0, 0, 127)
    },
    {
        "text": "Room2",
        "x": 75,
        "y": 75,
        "color": (0, 255, 0)
    }
]

sizes = {
    "charger_radius": 4,
    "vacuum_radius": 4
}

scale = 1
rotate = 0
trim_left = 5
trim_right = 10.5
trim_bottom = 0
trim_top = 15

# ********* CONFIGURATION END *********

processed_colors = {**colors}
for room_number, color in room_colors.items():
    processed_colors[f"{COLOR_ROOM_PREFIX}{room_number}"] = color

map_name = "retry"
if not (vacuum_ip == "" or token == ""):
    vacuum = miio.Vacuum(vacuum_ip, token)
    counter = 10
    while map_name == "retry" and counter > 0:
        time.sleep(0.1)
        map_name = vacuum.map()[0]
        counter = counter - 1

connector = XiaomiCloudConnector(username, password)
logged = connector.login()
if not logged:
    print("Failed to log in")
if map_name != "retry":
    print("Retrieved map name: " + map_name)
    raw_map = connector.get_raw_map_data(country, map_name)
    raw_file = open("map_data.gz", "wb")
    raw_file.write(raw_map)
    raw_file.close()
    map_data = connector.get_map(country, map_name, {}, CONF_AVAILABLE_DRAWABLES, [], sizes,
                                 {
                                     CONF_SCALE: scale,
                                     CONF_ROTATE: rotate,
                                     CONF_TRIM: {
                                         CONF_LEFT: trim_left,
                                         CONF_RIGHT: trim_right,
                                         CONF_TOP: trim_top,
                                         CONF_BOTTOM: trim_bottom
                                     }})
    map_data.image.data.save("map_data.png")
    img_byte_arr = io.BytesIO()
    map_data.image.data.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    print(img_byte_arr)
else:
    print("Failed to get map name")
