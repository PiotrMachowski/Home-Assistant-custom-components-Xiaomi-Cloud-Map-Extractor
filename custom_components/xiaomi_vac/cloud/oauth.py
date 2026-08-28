"""MIoT OAuth helpers for Xiaomi cloud MQTT authentication."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import partial
import hashlib
import json
import time
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode
import uuid

import requests

from ..const import (
    CONF_OAUTH_ACCESS_TOKEN,
    CONF_OAUTH_DEVICE_ID,
    CONF_OAUTH_EXPIRES_TS,
    CONF_OAUTH_REFRESH_TOKEN,
    CONF_OAUTH_REGION,
    CONF_OAUTH_REDIRECT_URI,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

OAUTH_APP_ID = "2882303761520251711"
OAUTH_AUTHORIZE_URL = "https://account.xiaomi.com/oauth2/authorize"
OAUTH_API_HOST = "ha.api.io.mi.com"
OAUTH_REDIRECT_URI = "http://homeassistant.local:8123"
OAUTH_TOKEN_REFRESH_RATIO = 0.7
OAUTH_REGIONS = ("cn", "de", "us", "ru", "sg", "in", "i2")


class XiaomiOAuthError(Exception):
    """Raised when Xiaomi OAuth token handling fails."""


@dataclass(frozen=True)
class OAuthTokenSet:
    """OAuth tokens plus the early-refresh timestamp."""

    access_token: str
    refresh_token: str
    expires_in: int
    expires_ts: int
    region: str


def generate_oauth_device_id() -> str:
    """Return a stable MIoT OAuth device id for one config entry."""
    return f"ha.{uuid.uuid4().hex[:16]}"


def oauth_state(device_id: str) -> str:
    """Return Xiaomi's required OAuth state value for a device id."""
    return hashlib.sha1(f"d={device_id}".encode()).hexdigest()


def build_authorize_url(
    device_id: str, *, redirect_uri: str = OAUTH_REDIRECT_URI
) -> str:
    """Build the Xiaomi OAuth authorize URL."""
    return (
        f"{OAUTH_AUTHORIZE_URL}?"
        + urlencode(
            {
                "client_id": OAUTH_APP_ID,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "device_id": device_id,
                "state": oauth_state(device_id),
                "skip_confirm": "true",
            }
        )
    )


def oauth_host(region: str) -> str:
    """Return the MIoT OAuth API host for a region."""
    return OAUTH_API_HOST if region == "cn" else f"{region}.{OAUTH_API_HOST}"


def resolve_region_from_code(code: str, fallback: str | None = None) -> str | None:
    """Resolve account region from a Xiaomi auth-code prefix."""
    code = code.strip()
    if len(code) >= 4 and code[:2].casefold() == "al":
        region = code[2:4].casefold()
        if region in OAUTH_REGIONS:
            return region
    if fallback and fallback in OAUTH_REGIONS:
        return fallback
    return None


def exchange_code(
    code: str,
    device_id: str,
    region: str,
    *,
    redirect_uri: str = OAUTH_REDIRECT_URI,
    session: requests.Session | None = None,
    now: float | None = None,
) -> OAuthTokenSet:
    """Exchange an OAuth code for MQTT access tokens."""
    return _get_token(
        region,
        {
            "client_id": int(OAUTH_APP_ID),
            "redirect_uri": redirect_uri,
            "code": code,
            "device_id": device_id,
        },
        session=session,
        now=now,
    )


def refresh_tokens(
    refresh_token: str,
    region: str,
    *,
    redirect_uri: str = OAUTH_REDIRECT_URI,
    session: requests.Session | None = None,
    now: float | None = None,
) -> OAuthTokenSet:
    """Refresh Xiaomi OAuth access tokens."""
    return _get_token(
        region,
        {
            "client_id": int(OAUTH_APP_ID),
            "redirect_uri": redirect_uri,
            "refresh_token": refresh_token,
        },
        session=session,
        now=now,
    )


def oauth_entry_updates(
    tokens: OAuthTokenSet,
    device_id: str,
    redirect_uri: str = OAUTH_REDIRECT_URI,
) -> dict[str, Any]:
    """Return config-entry data updates for OAuth tokens."""
    return {
        CONF_OAUTH_ACCESS_TOKEN: tokens.access_token,
        CONF_OAUTH_REFRESH_TOKEN: tokens.refresh_token,
        CONF_OAUTH_EXPIRES_TS: tokens.expires_ts,
        CONF_OAUTH_REGION: tokens.region,
        CONF_OAUTH_DEVICE_ID: device_id,
        CONF_OAUTH_REDIRECT_URI: redirect_uri,
    }


def oauth_needs_refresh(data: Mapping[str, Any], now: float | None = None) -> bool:
    """Return true when stored OAuth tokens should be refreshed."""
    if not data.get(CONF_OAUTH_REFRESH_TOKEN) or not data.get(CONF_OAUTH_REGION):
        return False
    return float(data.get(CONF_OAUTH_EXPIRES_TS, 0)) <= (now if now is not None else time.time())


def refreshed_oauth_entry_updates(
    data: Mapping[str, Any],
    *,
    force: bool = False,
    session: requests.Session | None = None,
    now: float | None = None,
) -> dict[str, Any] | None:
    """Return refreshed OAuth entry updates, or None if no refresh is due."""
    if not force and not oauth_needs_refresh(data, now):
        return None
    refresh_token = data.get(CONF_OAUTH_REFRESH_TOKEN)
    region = data.get(CONF_OAUTH_REGION)
    device_id = data.get(CONF_OAUTH_DEVICE_ID)
    redirect_uri = str(data.get(CONF_OAUTH_REDIRECT_URI) or OAUTH_REDIRECT_URI)
    if not refresh_token or not region or not device_id:
        return None
    tokens = refresh_tokens(
        str(refresh_token), str(region), redirect_uri=redirect_uri,
        session=session, now=now
    )
    return oauth_entry_updates(tokens, str(device_id), redirect_uri)


async def async_refresh_oauth_entry(
    hass: HomeAssistant, entry: ConfigEntry, *, force: bool = False
) -> bool:
    """Refresh OAuth tokens and persist them on a config entry."""
    updates = await hass.async_add_executor_job(
        partial(refreshed_oauth_entry_updates, entry.data, force=force)
    )
    if updates is None:
        return False
    hass.config_entries.async_update_entry(
        entry, data={**entry.data, **updates}
    )
    return True


def _get_token(
    region: str,
    data: dict[str, Any],
    *,
    session: requests.Session | None,
    now: float | None,
) -> OAuthTokenSet:
    http = session or requests
    try:
        response = http.get(
            f"https://{oauth_host(region)}/app/v2/ha/oauth/get_token",
            params={"data": json.dumps(data, separators=(",", ":"))},
            headers={"content-type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
    except requests.RequestException as err:
        raise XiaomiOAuthError(f"OAuth request failed: {err}") from err

    if response.status_code == 401:
        raise XiaomiOAuthError("OAuth request was unauthorized")
    if response.status_code != 200:
        raise XiaomiOAuthError(f"OAuth request failed with HTTP {response.status_code}")

    try:
        body = response.json()
    except ValueError as err:
        raise XiaomiOAuthError("OAuth response was not JSON") from err

    result = body.get("result") if body.get("code") == 0 else None
    if not isinstance(result, dict):
        raise XiaomiOAuthError("OAuth response did not include tokens")
    try:
        access_token = str(result["access_token"])
        refresh_token = str(result["refresh_token"])
        expires_in = int(result["expires_in"])
    except (KeyError, TypeError, ValueError) as err:
        raise XiaomiOAuthError("OAuth response had invalid token fields") from err

    issued_at = time.time() if now is None else now
    return OAuthTokenSet(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        expires_ts=int(issued_at + expires_in * OAUTH_TOKEN_REFRESH_RATIO),
        region=region,
    )
