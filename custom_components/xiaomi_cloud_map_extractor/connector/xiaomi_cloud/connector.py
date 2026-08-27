from __future__ import annotations
import asyncio
import base64
import datetime
import hashlib
import json
import locale
import logging
import time
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Optional, Self, Unpack, Any
from urllib.parse import parse_qs, urlparse

import tzlocal
from aiohttp import ClientSession, ClientResponse
from aiohttp.client import _RequestOptions, ClientTimeout
from aiohttp.typedefs import StrOrURL
from yarl import URL

from .const import AVAILABLE_SERVERS, SERVER_CN
from .utils import generate_agent, generate_device_id, to_json, generate_nonce, generate_enc_params, decrypt_rc4
from ..utils.exceptions import (
    TwoFactorAuthRequiredException,
    InvalidCredentialsException,
    FailedLoginException,
    FailedConnectionException,
    CaptchaRequiredException
)
from ..utils.dict_operations import path_extractor

_LOGGER = logging.getLogger(__name__)


@dataclass
class XiaomiCloudConnectorConfig:
    username: str | None
    password: str | None
    server: str
    user_id: str
    c_user_id: str
    service_token: str
    expiration: datetime.datetime
    ssecurity: str
    device_id: str

    @classmethod
    def from_dict(
        cls, data: dict[str, str] | XiaomiCloudConnectorConfig
    ) -> XiaomiCloudConnectorConfig:
        _LOGGER.debug("Restoring connector config...")
        if isinstance(data, XiaomiCloudConnectorConfig):
            return data
        expiration = data["expiration"]
        if expiration is not None:
            expiration = datetime.datetime.fromisoformat(expiration)
        return cls(**{**data, "expiration": expiration})


@dataclass
class XiaomiCloudHome:
    home_id: int
    owner: int


@dataclass
class XiaomiCloudDeviceInfo:
    device_id: str
    name: str
    model: str
    token: str
    spec_type: str
    local_ip: str | None
    mac: str | None
    server: str
    home_id: int
    user_id: int


@dataclass
class XiaomiCloudSessionData:
    session: ClientSession
    headers: dict[str, str]
    ssecurity: str | None = None
    userId: str | None = None
    cUserId: str | None = None
    serviceToken: str | None = None
    expiration: datetime.datetime | None = None

    def is_authenticated(self) -> bool:
        _LOGGER.debug("Authentication check: " + self.__repr__())
        return self.serviceToken is not None and self.expiration > datetime.datetime.now() + datetime.timedelta(days=1)

    async def get(self: Self, url: StrOrURL, **kwargs: Unpack[_RequestOptions]):
        passed_headers = kwargs.pop("headers", {})
        return await self.session.get(url, headers={**passed_headers, **self.headers}, **kwargs)

    async def post(self: Self, url: StrOrURL, **kwargs: Unpack[_RequestOptions]) -> ClientResponse:
        passed_headers = kwargs.pop("headers", {})
        return await self.session.post(url, headers={**passed_headers, **self.headers}, **kwargs)

    def apply_from_parameters(self):
        cookie_jar = self.session.cookie_jar
        domains = [
            "https://account.xiaomi.com",
            "https://api.io.mi.com",
            "https://sts.api.io.mi.com",
        ]
        cookies = {
            k: str(v)
            for k, v in {
                "serviceToken": self.serviceToken,
                "yetAnotherServiceToken": self.serviceToken,
                "userId": self.userId,
                "cUserId": self.cUserId,
            }.items()
            if v is not None
        }
        for domain in domains:
            cookie_jar.update_cookies(cookies, URL(domain))


# noinspection PyBroadException
class XiaomiCloudConnector:
    _username: str | None
    _password: str | None
    _long_polling_url: str | None
    _session_data: XiaomiCloudSessionData | None
    _locale: str
    _timezone: str
    _sign: str | None
    server: str | None

    def __init__(self: Self, session_creator: Callable[[], ClientSession], server: str | None = None):
        self._username = None
        self._password = None
        self._session_creator = session_creator
        self._locale = locale.getdefaultlocale()[0] or "en_GB"
        timezone = datetime.datetime.now(tzlocal.get_localzone()).strftime('%z')
        self._timezone = f"GMT{timezone[:-2]}:{timezone[-2:]}"
        self.server = server
        self._session_data = None
        self._long_polling_url = None
        self.device_id = generate_device_id()

    async def create_session(self: Self) -> None:
        if self._session_data is not None and self._session_data.session is not None:
            self._session_data.session.detach()
        agent = generate_agent()
        session = self._session_creator()
        cookies = {
            "sdkVerdion": "accountsdk-18.8.15",
            "deviceId": self.device_id
        }
        session.cookie_jar.update_cookies(cookies, response_url=URL("mi.com"))
        session.cookie_jar.update_cookies(cookies, response_url=URL("xiaomi.com"))
        headers = {"User-Agent": agent, "Content-Type": "application/x-www-form-urlencoded"}

        self._session_data = XiaomiCloudSessionData(session, headers)

    async def login_with_credentials(self: Self, username: str, password: str) -> str | None:
        self._username = username
        self._password = password
        _LOGGER.debug("Logging in...")
        await self.create_session()
        sign = await self._login_with_credentials_step_1()
        if not sign.startswith('http'):
            location = await self._login_with_credentials_step_2(sign)
        else:
            location = sign
        await self._login_with_credentials_step_3(location)
        _LOGGER.debug("Logged in.")
        return self._session_data.serviceToken

    async def _login_with_credentials_step_1(self: Self) -> str:
        _LOGGER.debug("Xiaomi cloud login - step 1")
        url = "https://account.xiaomi.com/pass/serviceLogin?sid=xiaomiio&_json=true"
        cookies = {
            "userId": self._username
        }

        try:
            response = await self._session_data.get(url, cookies=cookies)
            _LOGGER.debug("Xiaomi cloud login - step 1 status: %s", response.status)
            response_text = await response.text()
            _LOGGER.debug("Xiaomi cloud login - step 1 content: %s", response_text)
            response_json = to_json(response_text)
        except Exception:
            raise FailedLoginException()

        successful = response.status == 200 and "_sign" in response_json
        if successful:
            sign = response_json["_sign"]
            _LOGGER.debug("Xiaomi cloud login - step 1 sign: %s", sign)
            return sign

        _LOGGER.debug("Xiaomi cloud login - step 1 sign missing")
        return ""

    async def _login_with_credentials_step_2(self: Self, sign: str, captcha_code: str | None = None) -> str:
        _LOGGER.debug("Xiaomi cloud login - step 2")
        url = "https://account.xiaomi.com/pass/serviceLoginAuth2"
        params = {
            "sid": "xiaomiio",
            "hash": hashlib.md5(str.encode(self._password)).hexdigest().upper(),
            "callback": "https://sts.api.io.mi.com/sts",
            "qs": "%3Fsid%3Dxiaomiio%26_json%3Dtrue",
            "user": self._username,
            "_sign": sign,
            "_json": "true"
        }
        if captcha_code:
            params["captCode"] = captcha_code
        try:
            response = await self._session_data.post(url, params=params)
            _LOGGER.debug("Xiaomi cloud login - step 2 status: %s", response.status)
            response_text = await response.text()
            _LOGGER.debug("Xiaomi cloud login - step 2 content: %s", response_text)
            response_json = to_json(response_text)
        except Exception:
            raise InvalidCredentialsException()
        if response.status == 200:
            if "ssecurity" in response_json:
                location = response_json["location"]
                self._session_data.ssecurity = response_json["ssecurity"]
                self._session_data.userId = response_json["userId"]
                self._session_data.cUserId = response_json["cUserId"]
                max_age = int(response.cookies.get("userId").get("max-age"))
                self._session_data.expiration = datetime.datetime.now() + datetime.timedelta(seconds=max_age)
                self.two_factor_auth_url = None
                return location
            else:
                if (two_factor_url := response_json.get("notificationUrl", None)) is not None:
                    _LOGGER.warning(
                        "Additional authentication required. " +
                        "Open following URL using device that has the same public IP, " +
                        "as your Home Assistant instance: %s ",
                        two_factor_url)
                    await self._raise_two_factor_exception(two_factor_url)
                elif (captcha_url := response_json.get("captchaUrl", None)) is not None:
                    self._sign = sign
                    if captcha_url.startswith("/"):
                        captcha_url = "https://account.xiaomi.com" + response_json["captchaUrl"]
                    captcha_response = await self._session_data.get(captcha_url)
                    captcha_data = await captcha_response.read()
                    raise CaptchaRequiredException(captcha_url, captcha_data)
        raise InvalidCredentialsException()

    async def _login_with_credentials_step_3(self: Self, location: str) -> None:
        _LOGGER.debug("Xiaomi cloud login - step 3 (location: %s)", location)
        try:
            response = await self._session_data.get(location)
            _LOGGER.debug("Xiaomi cloud login - step 3 status: %s", response.status)
            response_text = await response.text()
            _LOGGER.debug("Xiaomi cloud login - step 3 content: %s", response_text)
        except Exception:
            raise InvalidCredentialsException()
        if response.status == 200 and "serviceToken" in response.cookies:
            self._session_data.serviceToken = response.cookies.get("serviceToken").value
        else:
            raise InvalidCredentialsException()

    async def login_with_qr_get_code(self: Self) -> tuple[bytes, str]:
        await self.create_session()

        resp = await self._session_data.get("https://account.xiaomi.com/pass/serviceLogin?sid=xiaomiio&_json=true")
        if resp.status != 200:
            _LOGGER.debug("Step 1 of QR login failed (code %s): %s", resp.status, await resp.text())
            raise FailedLoginException("Step 1 of QR login failed")

        # step 2
        json_resp = to_json(await resp.text())
        location = json_resp["location"]
        location_parsed = dict(URL(location).query)

        data = {
            "_qrsize": "480",
            "qs": json_resp["qs"],
            "bizDeviceType": "",
            "callback": json_resp["callback"],
            "_json": "true",
            "theme": "",
            "sid": "xiaomiio",
            "needTheme": "false",
            "showActiveX": "false",
            "serviceParam": location_parsed["serviceParam"],
            "_local": "zh_CN",
            "_sign": json_resp["_sign"],
            "_dc": str(int(time.time() * 1000)),
        }
        url = URL("https://account.xiaomi.com/longPolling/loginUrl").with_query(data)
        resp = await self._session_data.get(url)

        if resp.status != 200:
            _LOGGER.debug("Xiaomi cloud qr login - Failed to obtain the QR code URL (code %s): %s", resp.status, await resp.text())
            raise FailedLoginException('Failed to obtain the QR code URL')

        json_resp = to_json(await resp.text())
        if json_resp["code"] != 0:
            _LOGGER.debug("Xiaomi cloud qr login - QR code unavailable (code %s): %s", json_resp['code'], json_resp['desc'])
            raise FailedLoginException("QR code unavailable")

        _LOGGER.debug("Xiaomi cloud qr login - JSON response: %s", json_resp)
        qr_response = await self._session_data.get(json_resp["qr"])
        qr_data = await qr_response.read()
        self._long_polling_url = json_resp["lp"]

        return qr_data, await self._browser_login_url(json_resp["loginUrl"])

    async def _browser_login_url(self: Self, login_url: str) -> str:
        """
        Rewrites loginUrl so that a signed-out browser gets a sign-in page, by dropping the
        _json=true flag from the serviceLogin redirect that it carries.
        """
        try:
            response = await self._session_data.get(login_url, allow_redirects=False)
            location = response.headers.get("Location")
            if location is None:
                return login_url
            target = URL(location)
            if "_json" not in target.query:
                return login_url
            # callback and followup are left alone - they complete the long polling
            return str(target.with_query({k: v for k, v in target.query.items() if k != "_json"}))
        except Exception:
            _LOGGER.debug("Xiaomi cloud qr login - could not rewrite the login URL: %s", login_url)
            return login_url

    async def login_with_qr_wait_for_completion(self: Self) -> None:
        try:
            resp = await self._session_data.get(self._long_polling_url,
                                                timeout=ClientTimeout(total=60),
                                                headers={'Connection': 'keep-alive'})
        except asyncio.TimeoutError:
            _LOGGER.debug("Xiaomi cloud qr login - Timeout, please try again")
            raise FailedLoginException("Timeout, please try again")
        if resp.status != 200:
            _LOGGER.debug("Xiaomi cloud qr login - Long polling failed (code %s): %s", resp.status, await resp.text())
            raise FailedLoginException("Long polling failed, please try again")

        json_resp = to_json(await resp.text())
        max_age = int(resp.cookies.get("userId").get("max-age"))

        if json_resp['code'] != 0:
            _LOGGER.debug("Xiaomi cloud qr login - Long polling succeeded, but returned error %s: %s", json_resp['code'], json_resp['desc'])
            raise FailedLoginException("Long polling succeeded, but returned error")

        resp = await self._session_data.get(json_resp["location"])
        if resp.status != 200:
            _LOGGER.debug("Xiaomi cloud qr login - Failed to obtain last jump position %s: %s", resp.status, await resp.text())
            raise FailedLoginException("Failed to obtain last jump position")

        _LOGGER.debug("Xiaomi cloud qr login - JSON response polling: %s", json_resp)

        self._session_data.userId = json_resp["userId"]
        self._session_data.ssecurity = json_resp["ssecurity"]

        self._session_data.serviceToken = resp.cookies.get("serviceToken").value
        self._session_data.expiration = datetime.datetime.now() + datetime.timedelta(seconds=max_age)
        _LOGGER.debug("Xiaomi cloud qr login - session data: %s", self._session_data)

    async def continue_login_with_captcha(self: Self, captcha_code: str) -> str | None:
        _LOGGER.debug("Continuing login with captcha entered.")

        location = await self._login_with_credentials_step_2(self._sign, captcha_code)
        await self._login_with_credentials_step_3(location)

        _LOGGER.debug("Logged in.")
        return self._session_data.serviceToken

    async def _raise_two_factor_exception(self, notification_url: str) -> None:
        """
        Begins the 2FA email flow by starting the process and raising TwoFactorAuthRequiredException
        with data needed to continue the authentication.
        """
        agent = generate_agent()
        # 1) Open notificationUrl (authStart)
        headers = {
            "User-Agent": agent,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        _LOGGER.debug("Opening notificationUrl (authStart): %s", notification_url)
        # self._log_cookies("before authStart")  # Method not implemented
        r = await self._session_data.get(notification_url, headers=headers)
        _LOGGER.debug("authStart final URL: %s status=%s", r.url, r.status)

        # 2) Fetch identity options (list)
        context = parse_qs(urlparse(notification_url).query)["context"][0]
        list_params = {
            "sid": "xiaomiio",
            "context": context,
            "_locale": "en_US"
        }
        _LOGGER.debug("GET /identity/list params=%s", list_params)
        # self._log_cookies("before identity/list")  # Method not implemented
        r = await self._session_data.get("https://account.xiaomi.com/identity/list", params=list_params, headers=headers)
        _LOGGER.debug("identity/list status=%s", r.status)
        # self._log_cookies("after identity/list")  # Method not implemented

        # 3) Request email ticket
        send_params = {
            "_dc": str(int(time.time() * 1000)),
            "sid": "xiaomiio",
            "context": list_params["context"],
            "mask": "0",
            "_locale": "en_US"
        }
        send_data = {
            "retry": "0",
            "icode": "",
            "_json": "true",
            "ick": ""  # Cookie access would need proper implementation
        }
        _LOGGER.debug("sendEmailTicket POST url=https://account.xiaomi.com/identity/auth/sendEmailTicket params=%s", send_params)
        _LOGGER.debug("sendEmailTicket data=%s", send_data)
        # self._log_cookies("before sendEmailTicket")  # Method not implemented
        r = await self._session_data.post("https://account.xiaomi.com/identity/auth/sendEmailTicket",
                                          params=send_params, data=send_data, headers=headers)
        # self._log_cookies("after sendEmailTicket")  # Method not implemented
        try:
            jr = await r.json()
        except Exception:
            jr = {}
        _LOGGER.debug("sendEmailTicket response status=%s json=%s", r.status, jr)

        # 4) Ask user for the email code and verify
        _LOGGER.debug("Raising TwoFactorAuthRequiredException with url=%s, context=%s", notification_url, context)
        raise TwoFactorAuthRequiredException(
            url=notification_url,
            headers=headers,
            context=context
        )

    async def continue_login_with_two_factor(self, code: str, exception: TwoFactorAuthRequiredException) -> bool:
        """Continues the 2FA email flow with the provided verification code."""
        headers = exception.headers
        context = exception.context

        # Some endpoints are picky about Referer/Origin
        headers.setdefault("Referer", "https://account.xiaomi.com/identity/auth/sendEmailTicket")
        headers.setdefault("Origin", "https://account.xiaomi.com")

        # Grab 'ick' cookie if present – Xiaomi often validates it with the code
        try:
            ick_cookie = self._session_data.session.cookie_jar.filter_cookies(
                "https://account.xiaomi.com"
            ).get("ick")
            ick_value = ick_cookie.value if ick_cookie else ""
        except Exception:
            ick_value = ""

        verify_params = {
            "_flag": "8",
            "_json": "true",
            "sid": "xiaomiio",
            "context": context,
            "mask": "0",
            "_locale": "en_US"
        }
        verify_data = {
            "_flag": "8",
            "ticket": code,
            "trust": "false",
            "_json": "true",
            "ick": ick_value
        }
        # self._log_cookies("before verifyEmail")  # Method not implemented
        r = await self._session_data.post("https://account.xiaomi.com/identity/auth/verifyEmail",
                                          params=verify_params, data=verify_data, headers=headers)
        # self._log_cookies("after verifyEmail")  # Method not implemented
        if r.status != 200:
            _LOGGER.error("verifyEmail failed: status=%s body=%s", r.status, (await r.text())[:500])
            return False

        finish_loc = None
        try:
            jr = await r.json()
            _LOGGER.debug("verifyEmail response status=%s json=%s", r.status, jr)
            finish_loc = jr.get("location")
        except Exception:
            # Non-JSON or empty; try to extract from headers or body
            _LOGGER.debug("verifyEmail returned non-JSON, attempting fallback extraction.")
            finish_loc = r.headers.get("Location")
            text = await r.text()
            if not finish_loc and text:
                m = re.search(r'https://account\.xiaomi\.com/identity/result/check\?[^"\']+', text)
                if m:
                    finish_loc = m.group(0)

        # Fallback: directly hit result/check using existing identity_session/context
        if not finish_loc:
            _LOGGER.debug("Using fallback call to /identity/result/check")
            r0 = await self._session_data.get(
                "https://account.xiaomi.com/identity/result/check",
                params={"sid": "xiaomiio", "context": context, "_locale": "en_US"},
                headers=headers,
                allow_redirects=False
            )
            _LOGGER.debug("result/check (fallback) status=%s hop-> %s", r0.status, r0.headers.get("Location"))
            if r0.status in (301, 302) and r0.headers.get("Location"):
                finish_loc = r0.url if "serviceLoginAuth2/end" in str(r0.url) else r0.headers["Location"]

        if not finish_loc:
            _LOGGER.error("Unable to determine finish location after verifyEmail.")
            return False

        # self._log_cookies("before finish_2fa chain")  # Method not implemented

        # First hop: GET identity/result/check (do NOT follow redirects to inspect Location)
        if "identity/result/check" in finish_loc:
            r = await self._session_data.get(finish_loc, headers=headers, allow_redirects=False)
            _LOGGER.debug("result/check status=%s hop-> %s", r.status, r.headers.get("Location"))
            end_url = r.headers.get("Location")
        else:
            end_url = finish_loc

        if not end_url:
            _LOGGER.error("Could not find Auth2/end URL in finish chain.")
            return False

        # 6) Call Auth2/end WITHOUT redirects to capture 'extension-pragma' header containing ssecurity
        r = await self._session_data.get(end_url, headers=headers, allow_redirects=False)
        _LOGGER.debug("Auth2/end status=%s", r.status)
        text = await r.text()
        _LOGGER.debug("Auth2/end body(trunc)=%s", text[:200])
        # Some servers return 200 first (HTML 'Tips' page), then 302 on next call.
        if r.status == 200 and "Xiaomi Account - Tips" in text:
            r = await self._session_data.get(end_url, headers=headers, allow_redirects=False)
            _LOGGER.debug("Auth2/end(second) status=%s", r.status)

        ext_prag = r.headers.get("extension-pragma")
        if ext_prag:
            try:
                ep_json = json.loads(ext_prag)
                ssec = ep_json.get("ssecurity")
                psec = ep_json.get("psecurity")
                _LOGGER.debug("extension-pragma present. ssecurity=%s psecurity=%s", ssec, psec)
                if ssec:
                    self._session_data.ssecurity = ssec
            except Exception as e:
                _LOGGER.debug("Failed to parse extension-pragma: %s", e)

        if not self._session_data.ssecurity:
            _LOGGER.error("extension-pragma header missing ssecurity; cannot continue.")
            return False

        # 7) Find STS redirect and visit it (to set serviceToken cookie)
        sts_url = r.headers.get("Location")
        if not sts_url:
            text = await r.text()
            if text:
                idx = text.find("https://sts.api.io.mi.com/sts")
                if idx != -1:
                    end = text.find('"', idx)
                    if end == -1:
                        end = idx + 300
                    sts_url = text[idx:end]
        if not sts_url:
            _LOGGER.error("Auth2/end did not provide STS redirect.")
            return False

        r = await self._session_data.get(sts_url, headers=headers, allow_redirects=True)
        _LOGGER.debug("STS final URL: %s status=%s", r.url, r.status)
        # self._log_cookies("after STS")  # Method not implemented
        if r.status != 200:
            text = await r.text()
            _LOGGER.error("STS did not complete: status=%s body=%s", r.status, text[:200])
            return False

        # Extract serviceToken from cookie jar (use full URL for aiohttp CookieJar)
        try:
            sts_cookies = self._session_data.session.cookie_jar.filter_cookies(str(r.url))
            service_token = sts_cookies.get("serviceToken")
            if service_token:
                self._session_data.serviceToken = service_token.value
        except BaseException:
            pass
        found = bool(self._session_data.serviceToken)
        text = await r.text()
        _LOGGER.debug("STS body (trunc)=%s", text[:20])
        if not found:
            _LOGGER.error("Could not parse serviceToken; cannot complete login.")
            return False
        _LOGGER.debug("STS did not return JSON; assuming 'ok' style response and relying on cookies.")
        _LOGGER.debug("extract_service_token: found=%s", found)

        # Mirror serviceToken to API domains expected by Mi Cloud
        # self.install_service_token_cookies(self._serviceToken)  # Method not implemented

        # Update ids from cookies if available
        user_id_cookie = self._session_data.session.cookie_jar.filter_cookies(
            "https://account.xiaomi.com"
        ).get("userId") or self._session_data.session.cookie_jar.filter_cookies(
            "https://sts.api.io.mi.com"
        ).get(
            "userId"
        )
        if user_id_cookie:
            self._session_data.userId = user_id_cookie.value

        cuserId_cookie = self._session_data.session.cookie_jar.filter_cookies(
            "https://account.xiaomi.com"
        ).get("cUserId") or self._session_data.session.cookie_jar.filter_cookies(
            "https://sts.api.io.mi.com"
        ).get(
            "cUserId"
        )
        if cuserId_cookie:
            self._session_data.cUserId = cuserId_cookie.value

        max_age = next(
            (
                int(cookie.get("max-age", 0))
                for cookie in self._session_data.session.cookie_jar
                if cookie.key == "userId" and cookie.get("max-age") is not None
            ),
            0,
        )
        if max_age == 0:
            max_age = next(
                (
                    int(cookie.get("expires", 0))
                    for cookie in self._session_data.session.cookie_jar
                    if cookie.key == "userId" and cookie.get("expires") is not None
                ),
                0,
            ) - int(datetime.datetime.now().timestamp())
        if max_age <= 0:
            max_age = 20 * 24 * 60 * 60
        self._session_data.expiration = datetime.datetime.now() + datetime.timedelta(
            seconds=max_age
        )

        return True

    def is_authenticated(self: Self) -> bool:
        return self._session_data is not None and self._session_data.is_authenticated()

    async def get_raw_map_data(self: Self, map_url: str | None) -> bytes | None:
        if map_url is not None:
            try:
                _LOGGER.debug("Downloading raw map from \"%s\"...", map_url)
                response = await self._session_data.session.get(map_url)
            except Exception:
                _LOGGER.debug("Downloading the map failed.")
                return None
            if response.status == 200:
                _LOGGER.debug("Downloaded raw map, status: (%d).", response.status)
                data = await response.content.read()
                _LOGGER.debug("Downloaded raw map (%d).", len(data))
                return data
            else:
                _LOGGER.debug("Downloading the map failed. Status: (%d).", response.status)
                _LOGGER.debug("Downloading the map failed. Text: (%s).", await response.text())

        return None

    async def _get_homes(self: Self, server: str) -> list[XiaomiCloudHome]:
        url = self.get_api_url(server) + "/v2/homeroom/gethome"
        params = {
            "data": '{"fg": true, "fetch_share": true, "fetch_share_dev": true, "limit": 300, "app_ver": 7}'
        }

        homes = []
        try:
            homes_response = await self.execute_api_call_encrypted(url, params)
        except Exception as e:
            _LOGGER.debug("Error when retrieving homes from server %s: %s", server, e)
            homes_response = None
        if homes_response is None:
            return homes
        if homes_list := path_extractor(homes_response, "result.homelist"):
            homes.extend([XiaomiCloudHome(int(home["id"]), home["uid"]) for home in homes_list])
        if homes_list := path_extractor(homes_response, "result.share_home_list"):
            homes.extend([XiaomiCloudHome(int(home["id"]), home["uid"]) for home in homes_list])
        return homes

    async def _get_devices_from_home(
        self: Self, server: str, home_id: int, owner_id: int
    ) -> list[XiaomiCloudDeviceInfo]:
        url = self.get_api_url(server) + "/v2/home/home_device_list"
        params = {
            "data": json.dumps(
                {
                    "home_id": home_id,
                    "home_owner": owner_id,
                    "limit": 200,
                    "get_split_device": True,
                    "support_smart_home": True,
                }
            )
        }
        try:
            if (response := await self.execute_api_call_encrypted(url, params)) is None:
                return []
        except FailedConnectionException | TimeoutError as e:
            _LOGGER.error("Failed to get devices from home: %s", e)
            return []

        if (raw_devices := response["result"]["device_info"]) is None:
            return []
        return [
            XiaomiCloudDeviceInfo(
                device_id=device["did"],
                name=device["name"],
                model=device["model"],
                token=device.get("token", ""),
                spec_type=device.get("spec_type", ""),
                local_ip=device.get("localip", None),
                mac=device.get("mac", None),
                server=server,
                user_id=owner_id,
                home_id=home_id,
            )
            for device in raw_devices
        ]

    async def get_devices(self: Self, server: Optional[str] = None) -> list[XiaomiCloudDeviceInfo]:
        countries_to_check = AVAILABLE_SERVERS if server is None else [server]
        device_coro_list = [self._get_devices_from_server(server) for server in countries_to_check]
        device_lists = await asyncio.gather(*device_coro_list)
        return [device for device_list in device_lists for device in device_list]

    async def _get_devices_from_server(self: Self, server: str) -> list[XiaomiCloudDeviceInfo]:
        homes = await self._get_homes(server)
        device_coro_list = [self._get_devices_from_home(server, home.home_id, home.owner) for home in homes]
        device_lists = await asyncio.gather(*device_coro_list)
        return [device for device_list in device_lists for device in device_list]

    async def get_device_details(self: Self, device_id: str, server: Optional[str] = None) -> XiaomiCloudDeviceInfo | None:
        devices = await self.get_devices(server)
        matching_device = filter(lambda device: device.device_id == device_id, devices)
        return next(matching_device, None)

    async def get_other_info(self: Self, device_id: str, method: str, parameters: dict) -> Any:
        url = self.get_api_url() + "/v2/home/rpc/" + device_id
        params = {
            "data": json.dumps({"method": method, "params": parameters}, separators=(",", ":"))
        }
        return await self.execute_api_call_encrypted(url, params)

    async def execute_api_call_encrypted(self: Self, url: str, params: dict[str, str]) -> Any:
        headers = {
            "Accept-Encoding": "identity",
            "x-xiaomi-protocal-flag-cli": "PROTOCAL-HTTP2",
            "MIOT-ENCRYPT-ALGORITHM": "ENCRYPT-RC4",
        }
        cookies = {
            k: str(v)
            for k, v in {
                "userId": self._session_data.userId,
                "cUserId": self._session_data.cUserId,
                "yetAnotherServiceToken": self._session_data.serviceToken,
                "serviceToken": self._session_data.serviceToken,
                "locale": self._locale,
                "timezone": self._timezone,
                "is_daylight": time.daylight,
                "dst_offset": time.localtime().tm_isdst * 60 * 60 * 1000,
                "channel": "MI_APP_STORE",
            }.items()
            if v is not None
        }
        millis = round(time.time() * 1000)
        nonce = generate_nonce(millis)
        signed_nonce = self._signed_nonce(nonce)
        fields = generate_enc_params(url, "POST", signed_nonce, nonce, params, self._session_data.ssecurity)

        try:
            _LOGGER.debug("Request URL: %s", url)
            response = await self._session_data.post(url, headers=headers, cookies=cookies, params=fields)
            response_text = await response.text()
            _LOGGER.debug("API response: %s", response_text)
        except Exception as e:
            raise FailedConnectionException(e)
        if response.status == 200:
            decoded = decrypt_rc4(self._signed_nonce(fields["_nonce"]), response_text)
            return json.loads(decoded)
        if response.status in [401, 403]:
            raise FailedLoginException()
        else:
            return None

    def get_api_url(self: Self, server: str | None = None) -> str:
        if server is None:
            server = self.server
        return "https://" + ("" if server == SERVER_CN else (server + ".")) + "api.io.mi.com/app"

    def _signed_nonce(self: Self, nonce: str) -> str:
        hash_object = hashlib.sha256(base64.b64decode(self._session_data.ssecurity) + base64.b64decode(nonce))
        return base64.b64encode(hash_object.digest()).decode()

    def to_config(self: Self) -> XiaomiCloudConnectorConfig:
        return XiaomiCloudConnectorConfig(
            self._username,
            self._password,
            self.server,
            self._session_data.userId,
            self._session_data.cUserId,
            self._session_data.serviceToken,
            self._session_data.expiration,
            self._session_data.ssecurity,
            self.device_id
        )

    @staticmethod
    async def from_config(config: XiaomiCloudConnectorConfig, session_creator: Callable[[], ClientSession]):
        connector = XiaomiCloudConnector(session_creator,
                                         server=config.server)
        connector._username = config.username
        connector._password = config.password
        connector.device_id = config.device_id

        await connector.create_session()

        connector._session_data.userId = config.user_id
        connector._session_data.cUserId = config.c_user_id
        connector._session_data.serviceToken = config.service_token
        connector._session_data.ssecurity = config.ssecurity
        connector._session_data.expiration = config.expiration

        connector._session_data.apply_from_parameters()

        return connector
