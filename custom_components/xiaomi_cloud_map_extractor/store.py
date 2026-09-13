from dataclasses import asdict
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.storage import Store

from .connector.xiaomi_cloud.connector import XiaomiCloudConnectorConfig
from .const import STORAGE_VERSION, DOMAIN


async def save_connector_config(
    hass: HomeAssistant, mac: str, config: XiaomiCloudConnectorConfig
) -> None:
    store = _create_store(hass, mac)
    connector_config = asdict(config)
    await store.async_save({"connector_config": connector_config})


async def restore_connector_config(
    hass: HomeAssistant, mac: str
) -> XiaomiCloudConnectorConfig | None:
    connector_config = await _restore_from_xiaomi_miot(hass)
    if connector_config is not None:
        return XiaomiCloudConnectorConfig.from_dict(connector_config)

    store = _create_store(hass, mac)
    stored_data = await store.async_load()
    if stored_data is None or (connector_config := stored_data.get("connector_config", None)) is None:
        return None
    return XiaomiCloudConnectorConfig.from_dict(connector_config)


def _create_store(hass: HomeAssistant, mac: str) -> Store:
    store = Store(hass, STORAGE_VERSION, f"{DOMAIN}_{format_mac(mac)}")
    return store


async def _restore_from_xiaomi_miot(hass: HomeAssistant) -> dict | None:
    for entry in hass.config_entries.async_entries("xiaomi_miot"):
        data = entry.data or {}
        user_id = str(data.get("user_id") or "")
        server = data.get("server_country") or "cn"
        auth_store = Store(hass, 1, f"xiaomi_miot/auth-{user_id}-{server}.json")
        auth_data = (await auth_store.async_load() or {}).get("data", {})
        service_token = auth_data.get("service_token") or data.get("service_token")
        ssecurity = auth_data.get("ssecurity") or data.get("ssecurity")
        user_id = str(auth_data.get("user_id") or user_id)
        if not (service_token and ssecurity and user_id):
            continue
        return {
            "username": auth_data.get("username") or data.get("username"),
            "password": data.get("password"),
            "server": auth_data.get("server_country") or server,
            "user_id": user_id,
            "c_user_id": user_id,
            "service_token": service_token,
            "expiration": (datetime.now() + timedelta(days=30)).isoformat(),
            "ssecurity": ssecurity,
            "device_id": auth_data.get("device_id") or data.get("device_id"),
        }
    return None
