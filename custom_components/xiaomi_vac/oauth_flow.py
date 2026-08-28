"""OAuth webhook link helpers for Xiaomi account linking."""
from __future__ import annotations

from dataclasses import dataclass
from html import escape
import asyncio
import uuid

from aiohttp import web
from aiohttp.hdrs import METH_GET
from homeassistant.components.webhook import (
    async_generate_path as webhook_async_generate_path,
    async_register as webhook_async_register,
    async_unregister as webhook_async_unregister,
)
from homeassistant.core import HomeAssistant

from .cloud.oauth import OAUTH_REDIRECT_URI, build_authorize_url, oauth_state
from .const import DOMAIN

_OAUTH_LINKS = "oauth_links"


@dataclass(frozen=True)
class OAuthCodeResult:
    """OAuth callback code plus the redirect URI used to mint it."""

    code: str
    redirect_uri: str


class OAuthCodeLink:
    """One-shot OAuth callback link backed by a Home Assistant webhook."""

    def __init__(self, hass: HomeAssistant, device_id: str) -> None:
        self.hass = hass
        self.device_id = device_id
        self.webhook_id = f"{DOMAIN}_oauth_{uuid.uuid4().hex}"
        self.redirect_uri = f"{OAUTH_REDIRECT_URI}{webhook_async_generate_path(self.webhook_id)}"
        self.authorize_url = build_authorize_url(
            device_id, redirect_uri=self.redirect_uri
        )
        self.state = oauth_state(device_id)
        self.future: asyncio.Future[OAuthCodeResult] = hass.loop.create_future()
        self._registered = False

    def register(self) -> None:
        """Register the callback webhook for this OAuth attempt."""
        if self._registered:
            return
        self.hass.data.setdefault(DOMAIN, {}).setdefault(_OAUTH_LINKS, {})[
            self.webhook_id
        ] = self
        webhook_async_register(
            self.hass,
            domain=DOMAIN,
            name="Xiaomi Vacuum OAuth callback",
            webhook_id=self.webhook_id,
            handler=_handle_oauth_webhook,
            allowed_methods=(METH_GET,),
        )
        self._registered = True

    def unregister(self) -> None:
        """Remove the callback webhook."""
        if not self._registered:
            return
        self.hass.data.get(DOMAIN, {}).get(_OAUTH_LINKS, {}).pop(
            self.webhook_id, None
        )
        webhook_async_unregister(self.hass, webhook_id=self.webhook_id)
        self._registered = False

    async def async_wait_code(self) -> OAuthCodeResult:
        """Wait until Xiaomi redirects back with an auth code."""
        try:
            return await self.future
        finally:
            self.unregister()


def _oauth_response(title: str, content: str, *, success: bool) -> web.Response:
    colour = "#1f8f4d" if success else "#b42318"
    body = f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>{escape(title)}</title></head>
<body style="font-family: system-ui, sans-serif; margin: 3rem; max-width: 40rem;">
<h1 style="color: {colour};">{escape(title)}</h1>
<p>{escape(content)}</p>
<button onclick="window.close()">Close</button>
</body>
</html>"""
    return web.Response(body=body, content_type="text/html")


async def _handle_oauth_webhook(
    hass: HomeAssistant, webhook_id: str, request: web.Request
) -> web.Response:
    """Receive Xiaomi's OAuth redirect and wake the waiting flow."""
    link = hass.data.get(DOMAIN, {}).get(_OAUTH_LINKS, {}).get(webhook_id)
    if not isinstance(link, OAuthCodeLink):
        return _oauth_response(
            "Authentication failed",
            "This OAuth link is no longer active. Return to Home Assistant and try again.",
            success=False,
        )

    code = request.query.get("code")
    state = request.query.get("state")
    if not code or state != link.state:
        return _oauth_response(
            "Authentication failed",
            "The Xiaomi OAuth response was not valid. Return to Home Assistant and try again.",
            success=False,
        )

    if not link.future.done():
        link.future.set_result(
            OAuthCodeResult(code=code, redirect_uri=link.redirect_uri)
        )
    return _oauth_response(
        "Authentication complete",
        "You can close this page and return to Home Assistant.",
        success=True,
    )
