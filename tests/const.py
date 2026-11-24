"""Test data shared across tests. Values are made up; none is a real device or account."""

from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_MAC,
    CONF_MODEL,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_TOKEN,
    CONF_USERNAME,
)

from custom_components.xiaomi_cloud_map_extractor.const import CONF_SERVER, CONF_USED_MAP_API

USERNAME = "user@example.com"
PASSWORD = "secret"
TOKEN = "0123456789abcdef0123456789abcdef"
HOST = "192.168.1.50"
MAC = "aa:bb:cc:dd:ee:ff"

VACUUM_DEVICE = {
    "device_id": "123456789",
    "name": "Living room vacuum",
    "model": "viomi.vacuum.v8",
    "token": TOKEN,
    "spec_type": "urn:miot-spec-v2:device:vacuum:0000A006:viomi-v8:1",
    "local_ip": HOST,
    "mac": MAC.upper(),
    "server": "de",
    "home_id": 1,
    "user_id": 2,
}

ENTRY_DATA = {
    CONF_HOST: HOST,
    CONF_TOKEN: TOKEN,
    CONF_DEVICE_ID: VACUUM_DEVICE["device_id"],
    CONF_MODEL: VACUUM_DEVICE["model"],
    CONF_MAC: MAC,
    CONF_NAME: VACUUM_DEVICE["name"],
    CONF_USERNAME: USERNAME,
    CONF_PASSWORD: PASSWORD,
    CONF_SERVER: "de",
    CONF_USED_MAP_API: "VIOMI",
}
