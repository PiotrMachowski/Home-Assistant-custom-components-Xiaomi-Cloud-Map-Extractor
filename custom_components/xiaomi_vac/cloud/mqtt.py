"""MIoT cloud MQTT client for real-time device events."""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import ssl
from collections.abc import Awaitable, Callable
from concurrent.futures import Future
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import paho.mqtt.client as mqtt

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# The OAuth2 app id doubles as the MQTT username.
_APP_ID = "2882303761520251711"

_MQTT_PORT = 8883
_MQTT_KEEPALIVE = 60
_RECONNECT_MIN = 2
_RECONNECT_MAX = 60

_RC_NOT_AUTHORIZED = 5

# Home Assistant's own package_constraints.txt pins the paho-mqtt version, so
# whatever manifest.json requests, the runtime library is whatever HA ships —
# 2.1.0 as of HA 2026.7.3 (was 1.6.1 in HA 2025.1). The callback signatures
# below target the CallbackAPIVersion.VERSION2 API paho-mqtt 2.x calls back
# with: (client, userdata, flags, reason_code, properties).

_TOPIC_PROPERTIES_CHANGED = "properties_changed"
_TOPIC_EVENT_OCCURED = "event_occured"


def broker_host(region: str) -> str:
    """Return the MIoT MQTT broker host for an account region."""
    return f"{region}-ha.mqtt.io.mi.com"


@dataclass(frozen=True)
class MqttMessage:
    """Parsed MIoT device message surfaced to the integration."""

    kind: str  # "property" | "event" | "other"
    topic: str
    siid: int | None = None
    piid: int | None = None
    eiid: int | None = None
    value: Any = None
    arguments: Any = None


# force=True asks the provider to refresh before returning the token.
TokenProvider = Callable[[bool], Awaitable[str]]
MessageCallback = Callable[[MqttMessage], Awaitable[None]]


class MiotMqttClient:
    """Holds the MIoT cloud MQTT subscription for one config entry.

    Modelled on Xiaomi's `MipsCloudClient` from `ha_xiaomi_home/miot/miot_mips.py`.
    Verified end-to-end in `.scripts/map_mqtt_probe.py`.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        region: str,
        did: str,
        client_device_id: str,
        access_token: str,
        token_provider: TokenProvider,
        on_message: MessageCallback,
        tls_verify: bool = True,
    ) -> None:
        self._hass = hass
        self._did = did
        self._token = access_token
        self._token_provider = token_provider
        self._on_message = on_message
        self._client_id = client_device_id
        self._host = broker_host(region)
        self._tls_verify = tls_verify
        self._client: mqtt.Client | None = None
        self._started = False
        self._refresh_future: Future[Any] | None = None

    async def async_start(self) -> None:
        """Start the MQTT client and its network loop."""
        if self._started:
            return
        # _build_client loads system CA certs (blocking) — build off-loop.
        client = await self._hass.async_add_executor_job(
            self._build_client, self._token
        )
        # connect_async only queues the target; the socket is opened by the
        # loop_start() thread. Safe on the event loop.
        client.connect_async(self._host, _MQTT_PORT, _MQTT_KEEPALIVE)
        client.loop_start()
        self._client = client
        self._started = True
        _LOGGER.debug(
            "MQTT client started for did=%s on %s (verify=%s)",
            self._did, self._host, self._tls_verify,
        )

    async def async_stop(self) -> None:
        """Stop the MQTT client and join its network loop cleanly."""
        client = self._client
        self._client = None
        self._started = False
        if self._refresh_future is not None and not self._refresh_future.done():
            self._refresh_future.cancel()
        self._refresh_future = None
        if client is None:
            return
        await self._hass.async_add_executor_job(self._shutdown_sync, client)
        _LOGGER.debug("MQTT client stopped for did=%s", self._did)

    # --- paho callbacks (network thread) ---------------------------------

    def _on_connect(
        self, client: mqtt.Client, _u: Any, _flags: Any, rc: Any, _props: Any = None,
    ) -> None:
        if rc == 0:
            _LOGGER.debug("MQTT connected as %s", self._client_id)
            # The broker ACL rejects a single `device/{did}/#`, so subscribe
            # the three legs explicitly.
            for leg in ("up", "down", "state"):
                client.subscribe(f"device/{self._did}/{leg}/#")
            return
        if rc == _RC_NOT_AUTHORIZED:
            _LOGGER.debug("MQTT auth rejected (rc=5) — refreshing token")
            self._schedule_token_refresh()
            return
        _LOGGER.debug("MQTT connect failed rc=%s", rc)

    def _on_disconnect(
        self, _client: mqtt.Client, _u: Any, _flags: Any, rc: Any = None, _props: Any = None,
    ) -> None:
        # Auto-reconnect is handled by paho's own loop; just log at debug.
        _LOGGER.debug("MQTT disconnected rc=%s", rc)

    def _on_paho_message(
        self, _client: mqtt.Client, _u: Any, msg: mqtt.MQTTMessage,
    ) -> None:
        parsed = _parse_message(msg.topic, msg.payload)
        if parsed is None:
            return
        # Cross the thread boundary without blocking the network loop.
        self._hass.loop.call_soon_threadsafe(self._dispatch, parsed)

    # --- HA event loop side ----------------------------------------------

    def _dispatch(self, message: MqttMessage) -> None:
        try:
            coro = self._on_message(message)
        except Exception:  # noqa: BLE001
            _LOGGER.exception("MQTT message handler raised")
            return
        if coro is not None:
            self._hass.async_create_task(coro)

    def _schedule_token_refresh(self) -> None:
        # Called from the paho thread on rc=5. Coalesce concurrent triggers.
        existing = self._refresh_future
        if existing is not None and not existing.done():
            return
        self._refresh_future = asyncio.run_coroutine_threadsafe(
            self._refresh_and_reconnect(), self._hass.loop
        )

    async def _refresh_and_reconnect(self) -> None:
        try:
            new_token = await self._token_provider(True)
        except Exception:  # noqa: BLE001
            _LOGGER.exception("MQTT token refresh failed")
            return
        if not new_token or new_token == self._token:
            _LOGGER.debug("MQTT token refresh returned no change")
            return
        old = self._client
        if old is None:
            return
        # Rebuild rather than mutating a live client — avoids racing paho's
        # network thread on username_pw_set + reconnect.
        self._token = new_token
        fresh = await self._hass.async_add_executor_job(
            self._build_client, new_token
        )
        fresh.connect_async(self._host, _MQTT_PORT, _MQTT_KEEPALIVE)
        fresh.loop_start()
        self._client = fresh
        await self._hass.async_add_executor_job(self._shutdown_sync, old)
        _LOGGER.debug("MQTT reconnected with refreshed token")

    # --- helpers ---------------------------------------------------------

    def _build_client(self, token: str) -> mqtt.Client:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=self._client_id)
        client.username_pw_set(_APP_ID, token)
        if self._tls_verify:
            client.tls_set_context(ssl.create_default_context())
        else:
            client.tls_set(
                cert_reqs=ssl.CERT_NONE, tls_version=ssl.PROTOCOL_TLS_CLIENT,
            )
            client.tls_insecure_set(True)
        client.reconnect_delay_set(
            min_delay=_RECONNECT_MIN, max_delay=_RECONNECT_MAX
        )
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_paho_message
        return client

    @staticmethod
    def _shutdown_sync(client: mqtt.Client) -> None:
        with contextlib.suppress(Exception):
            client.disconnect()
        with contextlib.suppress(Exception):
            client.loop_stop()


def _parse_message(topic: str, payload: bytes) -> MqttMessage | None:
    """Turn a raw MIoT device topic + payload into a MqttMessage.

    Topic shapes (verified live in `.scripts/map_mqtt_probe.py`):
      device/{did}/up/properties_changed/{siid}/{piid}   value: <json>
      device/{did}/up/event_occured/{siid}/{eiid}        arguments: [...]
      device/{did}/state/*                               opaque
    Anything unfamiliar surfaces as kind="other" so callers can log or ignore.
    """
    parts = topic.split("/")
    if len(parts) < 4:
        return None
    try:
        body: Any = json.loads(payload.decode("utf-8", "replace")) if payload else {}
    except (ValueError, UnicodeDecodeError):
        body = {}

    kind_field = parts[3]
    if kind_field == _TOPIC_PROPERTIES_CHANGED and len(parts) >= 6:
        try:
            siid, piid = int(parts[4]), int(parts[5])
        except ValueError:
            return None
        value = body.get("value") if isinstance(body, dict) else None
        return MqttMessage(
            kind="property", topic=topic, siid=siid, piid=piid, value=value,
        )
    if kind_field == _TOPIC_EVENT_OCCURED and len(parts) >= 6:
        try:
            siid, eiid = int(parts[4]), int(parts[5])
        except ValueError:
            return None
        args = body.get("arguments") if isinstance(body, dict) else None
        return MqttMessage(
            kind="event", topic=topic, siid=siid, eiid=eiid, arguments=args,
        )
    return MqttMessage(kind="other", topic=topic, value=body)
