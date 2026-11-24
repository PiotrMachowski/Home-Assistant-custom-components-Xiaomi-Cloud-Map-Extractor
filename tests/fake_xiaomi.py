"""A small in-memory stand-in for the Xiaomi account and Mi Home cloud endpoints.

The connector only uses a narrow slice of ``aiohttp.ClientSession`` (``get``, ``post``,
``cookie_jar`` and ``detach``), so this fake implements exactly that slice. It keeps a real
``aiohttp.CookieJar`` so cookies set by responses (``serviceToken``, ``passToken``, ``userId``)
behave the way they do against the real servers, and it records every request so tests can
assert what was (and was not) sent, e.g. that no password login happened.
"""

from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from http.cookies import SimpleCookie
from typing import Any

from aiohttp import CookieJar
from multidict import CIMultiDict
from yarl import URL

from custom_components.xiaomi_cloud_map_extractor.connector.xiaomi_cloud.utils import encrypt_rc4

ACCOUNT = "https://account.xiaomi.com"
SERVICE_LOGIN = f"{ACCOUNT}/pass/serviceLogin"
SERVICE_LOGIN_AUTH2 = f"{ACCOUNT}/pass/serviceLoginAuth2"
STS = "https://sts.api.io.mi.com/sts"
API = "https://de.api.io.mi.com/app"

USER_ID = "1615523263"
C_USER_ID = "cUser-abc"
SSECURITY = base64.b64encode(b"0123456789abcdef").decode()
NEW_SSECURITY = base64.b64encode(b"fedcba9876543210").decode()
PASS_TOKEN = "V1:pass-token-from-login"
THIRTY_DAYS = 30 * 24 * 60 * 60


@dataclass
class Request:
    method: str
    url: URL
    params: dict[str, str]
    cookies: dict[str, str]
    data: Any

    @property
    def endpoint(self) -> str:
        return str(self.url.with_query(None))


@dataclass
class FakeResponse:
    status: int = 200
    body: bytes | str = b""
    set_cookies: dict[str, tuple[str, int | None]] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    url: URL | None = None

    def __post_init__(self) -> None:
        self.cookies: SimpleCookie = SimpleCookie()
        for name, (value, max_age) in self.set_cookies.items():
            self.cookies[name] = value
            if max_age is not None:
                self.cookies[name]["max-age"] = str(max_age)
        self.headers = CIMultiDict(self.headers)
        self.content = self

    @property
    def _bytes(self) -> bytes:
        return self.body.encode() if isinstance(self.body, str) else self.body

    async def text(self) -> str:
        return self._bytes.decode(errors="replace")

    async def read(self) -> bytes:
        return self._bytes

    async def json(self) -> Any:
        return json.loads(self._bytes.decode().replace("&&&START&&&", ""))


def json_response(payload: Any, **kwargs: Any) -> FakeResponse:
    return FakeResponse(body="&&&START&&&" + json.dumps(payload), **kwargs)


Handler = Callable[[Request], FakeResponse]


class FakeXiaomiCloud:
    """Routes requests to handlers registered per endpoint (URL without query)."""

    def __init__(self) -> None:
        self.routes: dict[tuple[str, str], Handler] = {}
        self.requests: list[Request] = []
        self.valid_service_tokens: set[str] = set()
        self.ssecurity = SSECURITY

    # --- session factory -------------------------------------------------------------
    def session_creator(self) -> "FakeSession":
        return FakeSession(self)

    # --- routing ---------------------------------------------------------------------
    def on(self, method: str, endpoint: str, handler: Handler) -> None:
        self.routes[(method.upper(), endpoint)] = handler

    def calls(self, endpoint: str) -> list[Request]:
        return [r for r in self.requests if r.endpoint == endpoint]

    def dispatch(self, request: Request) -> FakeResponse:
        self.requests.append(request)
        handler = self.routes.get((request.method, request.endpoint))
        if handler is None:
            raise AssertionError(f"Unexpected request: {request.method} {request.url}")
        response = handler(request)
        if response.url is None:
            response.url = request.url
        return response

    # --- canned Xiaomi behaviour ------------------------------------------------------
    def encrypted_api(self, endpoint: str, result: Any | Callable[[Request], Any]) -> None:
        """Register an RC4-encrypted Mi Home API endpoint that checks the serviceToken."""

        def handler(request: Request) -> FakeResponse:
            if request.cookies.get("serviceToken") not in self.valid_service_tokens:
                return FakeResponse(status=401, body='{"code":3,"message":"auth err"}')
            nonce = request.params["_nonce"]
            signed_nonce = base64.b64encode(
                hashlib.sha256(base64.b64decode(request.params["ssecurity"]) + base64.b64decode(nonce)).digest()
            ).decode()
            payload = result(request) if callable(result) else result
            return FakeResponse(body=encrypt_rc4(signed_nonce, json.dumps(payload)))

        self.on("POST", f"{API}{endpoint}", handler)

    def sts_issuing(self, service_token: str) -> None:
        """The STS callback sets a fresh serviceToken cookie."""

        def handler(request: Request) -> FakeResponse:
            self.valid_service_tokens.add(service_token)
            return FakeResponse(body="ok", set_cookies={"serviceToken": (service_token, None)})

        self.on("GET", STS, handler)

    def pass_token_login(self, *, accepted: bool = True, new_ssecurity: str = NEW_SSECURITY) -> None:
        """serviceLogin answering a passToken cookie with a ready session (code 0) or a fresh sign."""

        def handler(request: Request) -> FakeResponse:
            if accepted and request.cookies.get("passToken") == PASS_TOKEN:
                return json_response(
                    {
                        "code": 0,
                        "userId": int(USER_ID),
                        "cUserId": C_USER_ID,
                        "ssecurity": new_ssecurity,
                        "passToken": PASS_TOKEN,
                        "location": f"{STS}?d=renewed",
                    },
                    set_cookies={"userId": (USER_ID, THIRTY_DAYS)},
                )
            return json_response({"code": 70016, "_sign": "sign-for-password-login", "qs": "%3Fsid"})

        self.on("GET", SERVICE_LOGIN, handler)

    def password_login(self, outcome: str = "ok") -> None:
        """serviceLoginAuth2: 'ok', 'captcha', 'two_factor' or 'invalid'."""

        def handler(request: Request) -> FakeResponse:
            if outcome == "ok":
                return json_response(
                    {
                        "code": 0,
                        "userId": int(USER_ID),
                        "cUserId": C_USER_ID,
                        "ssecurity": self.ssecurity,
                        "passToken": PASS_TOKEN,
                        "location": f"{STS}?d=password",
                    },
                    set_cookies={"userId": (USER_ID, THIRTY_DAYS), "passToken": (PASS_TOKEN, THIRTY_DAYS)},
                )
            if outcome == "captcha":
                return json_response({"code": 87001, "captchaUrl": "/pass/getCode?icodeType=login&0.918"})
            if outcome == "two_factor":
                return json_response(
                    {
                        "code": 0,
                        "notificationUrl": f"{ACCOUNT}/fe/service/identity/authStart?sid=xiaomiio&context=ctx123",
                    }
                )
            return json_response({"code": 70016, "desc": "wrong password"})

        self.on("POST", SERVICE_LOGIN_AUTH2, handler)
        self.on(
            "GET",
            f"{ACCOUNT}/pass/getCode",
            lambda r: FakeResponse(body=b"\xff\xd8\xff\xe0JFIF-captcha-image-bytes"),
        )
        self.on("GET", f"{ACCOUNT}/fe/service/identity/authStart", lambda r: FakeResponse(body="<html/>"))
        self.on("GET", f"{ACCOUNT}/identity/list", lambda r: FakeResponse(body="{}"))
        self.on(
            "POST", f"{ACCOUNT}/identity/auth/sendEmailTicket", lambda r: json_response({"code": 0})
        )

    def password_login_count(self) -> int:
        return len(self.calls(SERVICE_LOGIN_AUTH2))


class FakeSession:
    def __init__(self, cloud: FakeXiaomiCloud) -> None:
        self._cloud = cloud
        self.cookie_jar = CookieJar()

    def detach(self) -> None:
        pass

    async def get(self, url, **kwargs) -> FakeResponse:
        return self._request("GET", url, **kwargs)

    async def post(self, url, **kwargs) -> FakeResponse:
        return self._request("POST", url, **kwargs)

    def _request(self, method, url, *, params=None, cookies=None, data=None, **_kwargs) -> FakeResponse:
        url = URL(str(url))
        if params:
            url = url.update_query({k: str(v) for k, v in params.items()})
        sent_cookies = {k: m.value for k, m in self.cookie_jar.filter_cookies(url).items()}
        sent_cookies.update({k: str(v) for k, v in (cookies or {}).items()})
        request = Request(method, url, dict(url.query), sent_cookies, data)
        response = self._cloud.dispatch(request)
        self.cookie_jar.update_cookies(response.cookies, url)
        return response
