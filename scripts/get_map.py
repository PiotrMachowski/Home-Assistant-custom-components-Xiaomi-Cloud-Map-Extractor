import logging
import miio
import time
import io
from .xiaomi_cloud_connector import XiaomiCloudConnector
from .xiaomi_cloud_vacuum import XiaomiCloudVacuum
from .const import *

# ********* CONFIGURATION *********

vacuum_ip = ""
token = ""
username = ""
password = ""
country = ""
map_name = "0"  # if the vacuum_ip is empty, the map name query will be skipped (userful for Xiaomi Mi Robot Vacuum Mop Pro (STYJ02YM) / Viomi V2 Pro / etc.) and this value will be used

draw = [
    "charger",
    "goto_path",
    "no_go_zones",
    "no_mopping_zones",
    "path",
    "predicted_path",
    "vacuum_position",
    "virtual_walls",
    "zones"
]

colors = {
    "color_path": (255, 0, 0, 127),
    "color_goto_path": (0, 255, 0),
    "color_predicted_path": (0, 0, 255),
    "color_zones": (0x1F, 0x6A, 0xFC, 128),
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
        "color": (255, 0, 0, 127),
        "font": "FreeSans.ttf",
        "font_size": 25
    },
    {
        "text": "Room2",
        "x": 75,
        "y": 75,
        "color": (0, 255, 0),
        "font": None,  # use default one
        "font_size": 0
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

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
logging.getLogger('PIL.PngImagePlugin').setLevel(logging.WARNING)

processed_colors = {**colors}
for room_number, color in room_colors.items():
    processed_colors[f"{COLOR_ROOM_PREFIX}{room_number}"] = color

if not (vacuum_ip == "" or token == ""):
    vacuum = miio.Vacuum(vacuum_ip, token)
    map_name = "retry"
    counter = 10
    while map_name == "retry" and counter > 0:
        time.sleep(0.1)
        map_name = vacuum.map()[0]
        counter = counter - 1

connector = XiaomiCloudConnector(username, password)
logged = connector.login()
if not logged:
    print("Failed to log in")
    exit(1)
if map_name != "retry":
    country, user_id, device_id, model = connector.get_device_details(vacuum_ip, token, country)
    device = XiaomiCloudVacuum.create(connector, country, user_id, device_id, model)
    if device is None:
        print("Device not found")
        exit(1)
    print("Retrieved map name: " + map_name)
    raw_map = device.get_raw_map_data(map_name)
    raw_file = open("map_data.gz", "wb")
    raw_file.write(raw_map)
    raw_file.close()
    map_data = device.get_map(map_name, processed_colors, draw, texts, sizes,
                              {
                                  CONF_SCALE: scale,
                                  CONF_ROTATE: rotate,
                                  CONF_TRIM: {
                                      CONF_LEFT: trim_left,
                                      CONF_RIGHT: trim_right,
                                      CONF_TOP: trim_top,
                                      CONF_BOTTOM: trim_bottom
                                  }})[0]
    map_data.image.data.save("map_data.png")
    img_byte_arr = io.BytesIO()
    map_data.image.data.save(img_byte_arr, format='PNG')
    #img_byte_arr = img_byte_arr.getvalue()
    #print(img_byte_arr)
else:
    print("Failed to get map name")
