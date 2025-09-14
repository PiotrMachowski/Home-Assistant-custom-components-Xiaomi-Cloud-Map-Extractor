import asyncio
import base64
import datetime
import hashlib
import json
import locale
import logging
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Optional, Self, Unpack
from urllib.parse import urlparse, parse_qs

import tzlocal
from aiohttp import ClientSession, ClientResponse
from aiohttp.client import _RequestOptions
from aiohttp.typedefs import StrOrURL
from yarl import URL

from .const import AVAILABLE_SERVERS, SERVER_CN
from .utils import generate_agent, generate_device_id, to_json, generate_nonce, generate_enc_params, decrypt_rc4
from ..utils.exceptions import (
    TwoFactorAuthRequiredException,
    InvalidCredentialsException,
    FailedLoginException,
    FailedConnectionException,
    CaptchaRequiredException,
)

_LOGGER = logging.getLogger(__name__)


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
    cUserId: str | None = None
    ssecurity: str | None = None
    userId: str | None = None
    serviceToken: str | None = None
    expiration: datetime.datetime | None = None

    def is_authenticated(self) -> bool:
        return (
            self.ssecurity is not None
            and self.userId is not None
            and self.serviceToken is not None
            and (self.expiration is None or self.expiration > datetime.datetime.now())
        )

    async def get(self: Self, url: StrOrURL, **kwargs: Unpack[_RequestOptions]):
        passed_headers = kwargs.pop("headers", {})
        return await self.session.get(url, headers={**passed_headers, **self.headers}, **kwargs)

    async def post(self: Self, url: StrOrURL, **kwargs: Unpack[_RequestOptions]) -> ClientResponse:
        passed_headers = kwargs.pop("headers", {})
        return await self.session.post(url, headers={**passed_headers, **self.headers}, **kwargs)


# noinspection PyBroadException
class XiaomiCloudConnector:
    _username: str
    _password: str
    _session_data: XiaomiCloudSessionData | None
    _locale: str
    _timezone: str
    server: str | None

    def __init__(self: Self, session_creator: Callable[[], ClientSession], username: str, password: str,
                 server: str | None = None):
        self._username = username
        self._password = password
        self._session_creator = session_creator
        self._locale = locale.getdefaultlocale()[0] or "en_GB"
        # Use a default timezone to avoid blocking calls during initialization
        # This will be set properly when needed during API calls
        self._timezone = "GMT+00:00"  # Default to UTC
        self.server = server
        self._session_data = None
        self.two_factor_auth_url = None

    async def create_session(self: Self) -> None:
        if self._session_data is not None and self._session_data.session is not None:
            self._session_data.session.detach()
        agent = generate_agent()
        device_id = generate_device_id()
        session = self._session_creator()
        cookies = {
            "sdkVerdion": "accountsdk-18.8.15",
            "deviceId": device_id
        }
        session.cookie_jar.update_cookies(cookies, response_url=URL("mi.com"))
        session.cookie_jar.update_cookies(cookies, response_url=URL("xiaomi.com"))
        headers = {"User-Agent": agent, "Content-Type": "application/x-www-form-urlencoded"}

        self._session_data = XiaomiCloudSessionData(session, headers)

    def get_session_artifacts(self: Self) -> dict | None:
        """Return Xiaomi session artifacts if available for persistence."""
        if self._session_data and self._session_data.ssecurity and self._session_data.serviceToken:
            return {
                "ssecurity": self._session_data.ssecurity,
                "serviceToken": self._session_data.serviceToken,
                "userId": self._session_data.userId,
                "cUserId": self._session_data.cUserId,
            }
        return None

    async def adopt_session_artifacts(
        self: Self,
        ssecurity: str | None,
        service_token: str | None,
        user_id: str | None,
        cuser_id: str | None,
    ) -> None:
        """Adopt provided Xiaomi session artifacts into a fresh session to avoid re-login."""
        # Ensure session exists
        if self._session_data is None:
            await self.create_session()
        # Store values
        self._session_data.ssecurity = ssecurity or self._session_data.ssecurity
        self._session_data.serviceToken = service_token or self._session_data.serviceToken
        self._session_data.userId = user_id or self._session_data.userId
        self._session_data.cUserId = cuser_id or self._session_data.cUserId
        # Mirror cookies across domains commonly checked by Mi Cloud
        try:
            jar = self._session_data.session.cookie_jar
            for domain in [
                "https://account.xiaomi.com",
                "https://api.io.mi.com",
                "https://sts.api.io.mi.com",
            ]:
                if self._session_data.serviceToken:
                    jar.update_cookies({"serviceToken": self._session_data.serviceToken}, response_url=URL(domain))
                    jar.update_cookies({"yetAnotherServiceToken": self._session_data.serviceToken}, response_url=URL(domain))
                if self._session_data.userId:
                    jar.update_cookies({"userId": str(self._session_data.userId)}, response_url=URL(domain))
                if self._session_data.cUserId:
                    jar.update_cookies({"cUserId": str(self._session_data.cUserId)}, response_url=URL(domain))
        except Exception:
            pass

    def _get_timezone(self: Self) -> str:
        """Get timezone string in format required by Xiaomi API."""
        try:
            # Try to get timezone safely - if it fails, use UTC
            import time
            timezone_offset = time.timezone if time.daylight == 0 else time.altzone
            hours, remainder = divmod(abs(timezone_offset), 3600)
            minutes = remainder // 60
            sign = '-' if timezone_offset > 0 else '+'
            return f"GMT{sign}{hours:02d}:{minutes:02d}"
        except Exception:
            return "GMT+00:00"  # Fallback to UTC

    async def _login_step_1(self: Self) -> str:
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
        except:
            raise FailedLoginException()

        successful = response.status == 200 and "_sign" in response_json
        if successful:
            sign = response_json["_sign"]
            _LOGGER.debug("Xiaomi cloud login - step 1 sign: %s", sign)
            return sign

        _LOGGER.debug("Xiaomi cloud login - step 1 sign missing")
        return ""

    async def _login_step_2(self: Self, sign: str) -> str:
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
        if sign:
            params["_sign"] = sign
        try:
            response = await self._session_data.post(url, params=params)
            _LOGGER.debug("Xiaomi cloud login - step 2 status: %s", response.status)
            response_text = await response.text()
            _LOGGER.debug("Xiaomi cloud login - step 2 content: %s", response_text)
            response_json = to_json(response_text)
        except:
            raise InvalidCredentialsException()
        _LOGGER.error("LOGIN_STEP_2: Response status=%s", response.status)
        if response.status == 200:
            _LOGGER.error("LOGIN_STEP_2: Response keys=%s", list(response_json.keys()) if response_json else "None")
            # CAPTCHA required
            if response_json and response_json.get("captchaUrl"):
                captcha_url = response_json.get("captchaUrl")
                if isinstance(captcha_url, str) and captcha_url.startswith("/"):
                    captcha_url = f"https://account.xiaomi.com{captcha_url}"
                _LOGGER.error("LOGIN_STEP_2: captchaUrl found, CAPTCHA required: %s", captcha_url)
                raise CaptchaRequiredException(captcha_url=captcha_url or "", sign=sign)
            if "ssecurity" in response_json:
                _LOGGER.error("LOGIN_STEP_2: ssecurity found, login successful")
                self._session_data.cUserId = response_json["cUserId"]
                location = response_json["location"]
                self._session_data.ssecurity = response_json["ssecurity"]
                self._session_data.userId = response_json["userId"]
                max_age = int(response.cookies.get("userId").get("max-age"))
                self._session_data.expiration = datetime.datetime.now() + datetime.timedelta(seconds=max_age)
                self.two_factor_auth_url = None
                return location
            else:
                if "notificationUrl" in response_json and response_json["notificationUrl"]:
                    _LOGGER.error("LOGIN_STEP_2: notificationUrl found, 2FA required")
                    _LOGGER.error("LOGIN_STEP_2: NotificationUrl: %s", response_json["notificationUrl"])
                    # Start the 2FA flow and raise exception with session data
                    _LOGGER.error("LOGIN_STEP_2: About to call _prepare_2fa_flow")
                    await self._prepare_2fa_flow(response_json["notificationUrl"])
                    # This line will never be reached due to exception
                    _LOGGER.error("LOGIN_STEP_2: ERROR - This should never be reached after _prepare_2fa_flow")
                    raise InvalidCredentialsException()
                else:
                    _LOGGER.error("LOGIN_STEP_2: no ssecurity and no notificationUrl found")
                    _LOGGER.error("LOGIN_STEP_2: Response JSON: %s", response_json)
        raise InvalidCredentialsException()

    async def continue_login_with_captcha(self: Self, sign: str, captcha_code: str) -> str | None:
        """Retry login step 2 including the CAPTCHA code.

        Returns location string if login succeeds and should continue to step 3.
        May raise TwoFactorAuthRequiredException to start the 2FA flow.
        Raises InvalidCredentialsException if captcha is invalid or other error.
        """
        _LOGGER.debug("Login step 2 retry with captcha")
        url = "https://account.xiaomi.com/pass/serviceLoginAuth2"
        params = {
            "sid": "xiaomiio",
            "hash": hashlib.md5(str.encode(self._password)).hexdigest().upper(),
            "callback": "https://sts.api.io.mi.com/sts",
            "qs": "%3Fsid%3Dxiaomiio%26_json%3Dtrue",
            "user": self._username,
            "_sign": sign,
            "_json": "true",
            # Captcha answer field; Xiaomi expects this key on login retry
            "captCode": captcha_code,
        }

        try:
            response = await self._session_data.post(url, params=params)
            _LOGGER.debug("login_step_2 (captcha retry) status=%s", response.status)
            response_text = await response.text()
            _LOGGER.debug("login_step_2 (captcha retry) body=%s", response_text[:1000])
            response_json = to_json(response_text)
        except Exception as e:
            _LOGGER.error("Login failed during captcha retry: %s", e)
            raise InvalidCredentialsException()

        if response.status != 200:
            _LOGGER.error("Login failed even after captcha. status=%s", response.status)
            raise InvalidCredentialsException()

        # Invalid captcha commonly returns code 87001
        if response_json and response_json.get("code") == 87001:
            _LOGGER.error("Invalid captcha provided (code 87001)")
            raise InvalidCredentialsException()

        if response_json and response_json.get("captchaUrl"):
            _LOGGER.error("CAPTCHA still required after retry")
            raise InvalidCredentialsException()

        if response_json and "ssecurity" in response_json:
            self._session_data.cUserId = response_json.get("cUserId")
            location = response_json.get("location")
            self._session_data.ssecurity = response_json.get("ssecurity")
            self._session_data.userId = response_json.get("userId")
            try:
                max_age = int(response.cookies.get("userId").get("max-age"))
                self._session_data.expiration = datetime.datetime.now() + datetime.timedelta(seconds=max_age)
            except Exception:
                pass
            self.two_factor_auth_url = None
            return location

        if response_json and response_json.get("notificationUrl"):
            notification_url = response_json.get("notificationUrl")
            _LOGGER.error("2FA required after captcha: %s", notification_url)
            await self._prepare_2fa_flow(notification_url)
            _LOGGER.error("continue_login_with_captcha: unexpected flow after _prepare_2fa_flow")
            raise InvalidCredentialsException()

        _LOGGER.error("Unexpected response after captcha retry: %s", response_json)
        raise InvalidCredentialsException()

    # -------------------- 2FA handling -------------------- #

    async def _prepare_2fa_flow(self, notification_url: str) -> None:
        """
        Prepares the 2FA email flow by starting the process and raising TwoFactorAuthRequiredException
        with the session data needed to continue the authentication.
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
        # Store session state and raise exception for Home Assistant to handle
        session_state = {
            "headers": headers,
            "list_params": list_params,
            "send_params": send_params,
            "context": context
        }
        _LOGGER.debug("Raising TwoFactorAuthRequiredException with url=%s, context=%s", notification_url, context)
        raise TwoFactorAuthRequiredException(
            url=notification_url,
            session_data=session_state,
            context=context
        )

    async def continue_2fa_email_flow(self, code: str, session_data: dict, context: str) -> bool:
        """Continue the 2FA email flow with the provided verification code."""
        headers = session_data["headers"]
        list_params = session_data["list_params"]
        
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
        except Exception:
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
        user_id_cookie = self._session_data.session.cookie_jar.filter_cookies("https://account.xiaomi.com").get("userId") or \
                        self._session_data.session.cookie_jar.filter_cookies("https://sts.api.io.mi.com").get("userId")
        if user_id_cookie:
            self._session_data.userId = user_id_cookie.value
            
        cuserId_cookie = self._session_data.session.cookie_jar.filter_cookies("https://account.xiaomi.com").get("cUserId") or \
                        self._session_data.session.cookie_jar.filter_cookies("https://sts.api.io.mi.com").get("cUserId")
        if cuserId_cookie:
            self._session_data.cUserId = cuserId_cookie.value
        return True

    async def _login_step_3(self: Self, location: str) -> None:
        _LOGGER.debug("Xiaomi cloud login - step 3 (location: %s)", location)
        try:
            response = await self._session_data.get(location)
            _LOGGER.debug("Xiaomi cloud login - step 3 status: %s", response.status)
            response_text = await response.text()
            _LOGGER.debug("Xiaomi cloud login - step 3 content: %s", response_text)
        except:
            raise InvalidCredentialsException()
        if response.status == 200 and "serviceToken" in response.cookies:
            self._session_data.serviceToken = response.cookies.get("serviceToken").value
        else:
            raise InvalidCredentialsException()

    async def login(self: Self) -> str | None:
        _LOGGER.error("LOGIN_START: Beginning login process")
        _LOGGER.error("LOGIN_STEP: Creating session")
        await self.create_session()
        _LOGGER.error("LOGIN_STEP: Session created, starting step 1")
        sign = await self._login_step_1()
        _LOGGER.error("LOGIN_STEP: Step 1 completed, sign: %s", sign)
        if not sign.startswith('http'):
            _LOGGER.error("LOGIN_STEP: Sign is not URL, proceeding to step 2")
            location = await self._login_step_2(sign)
            _LOGGER.error("LOGIN_STEP: Step 2 completed, location: %s", location)
        else:
            _LOGGER.error("LOGIN_STEP: Sign is URL, using as location")
            location = sign
        _LOGGER.error("LOGIN_STEP: Proceeding to step 3 with location: %s", location)
        await self._login_step_3(location)
        _LOGGER.error("LOGIN_STEP: Logged in successfully.")
        return self._session_data.serviceToken

    def is_authenticated(self: Self) -> bool:
        return self._session_data is not None and self._session_data.is_authenticated()

    async def get_raw_map_data(self: Self, map_url: str | None) -> bytes | None:
        if map_url is not None:
            try:
                _LOGGER.debug("Downloading raw map from \"%s\"...", map_url)
                response = await self._session_data.session.get(map_url)
            except:
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

        homes_response = await self.execute_api_call_encrypted(url, params)
        if homes_response is None:
            return homes
        if homelist := homes_response["result"].get("homelist", None):
            homes.extend([XiaomiCloudHome(int(home["id"]), home["uid"]) for home in homelist])
        if homelist := homes_response["result"].get("share_home_list", None):
            homes.extend([XiaomiCloudHome(int(home["id"]), home["uid"]) for home in homelist])
        return homes

    async def _get_devices_from_home(self: Self, server: str, home_id: int, owner_id: int) -> list[
        XiaomiCloudDeviceInfo]:
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
        if (response := await self.execute_api_call_encrypted(url, params)) is None:
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

    async def get_device_details(self: Self, token: str, server: Optional[str] = None) -> XiaomiCloudDeviceInfo | None:
        devices = await self.get_devices(server)
        matching_token = filter(lambda device: device.token == token, devices)
        return next(matching_token, None)

    async def get_other_info(self: Self, device_id: str, method: str, parameters: dict) -> any:
        url = self.get_api_url('sg') + "/v2/home/rpc/" + device_id
        params = {
            "data": json.dumps({"method": method, "params": parameters}, separators=(",", ":"))
        }
        return await self.execute_api_call_encrypted(url, params)

    async def execute_api_call_encrypted(self: Self, url: str, params: dict[str, str]) -> any:
        headers = {
            "Accept-Encoding": "identity",
            "x-xiaomi-protocal-flag-cli": "PROTOCAL-HTTP2",
            "MIOT-ENCRYPT-ALGORITHM": "ENCRYPT-RC4",
        }
        # Build cookies, skipping missing values
        cookies = {
            "locale": self._locale,
            "timezone": self._get_timezone(),
            "is_daylight": str(time.daylight),
            "dst_offset": str(time.localtime().tm_isdst * 60 * 60 * 1000),
            "channel": "MI_APP_STORE",
        }
        if self._session_data.userId:
            cookies["userId"] = str(self._session_data.userId)
        if self._session_data.serviceToken:
            cookies["serviceToken"] = str(self._session_data.serviceToken)
            cookies["yetAnotherServiceToken"] = str(self._session_data.serviceToken)
        if self._session_data.cUserId:
            cookies["cUserId"] = str(self._session_data.cUserId)
        millis = round(time.time() * 1000)
        nonce = generate_nonce(millis)
        signed_nonce = self._signed_nonce(nonce)
        fields = generate_enc_params(url, "POST", signed_nonce, nonce, params, self._session_data.ssecurity)

        try:
            response = await self._session_data.post(url, headers=headers, cookies=cookies, params=fields)
            response_text = await response.text()
        except Exception as e:
            raise FailedConnectionException(e)
        if response.status == 200:
            decoded = decrypt_rc4(self._signed_nonce(fields["_nonce"]), response_text)
            return json.loads(decoded)
        if response.status in [401, 403]:
            _LOGGER.error("MI API unauthorized: %s for %s", response.status, url)
            raise FailedLoginException()
        _LOGGER.error("MI API call failed: status=%s url=%s body=%s", response.status, url, response_text[:300])
        return None

    def get_api_url(self: Self, server: str | None = None) -> str:
        if server is None:
            server = self.server
        return "https://" + ("" if server == SERVER_CN else (server + ".")) + "api.io.mi.com/app"

    def _signed_nonce(self: Self, nonce: str) -> str:
        hash_object = hashlib.sha256(base64.b64decode(self._session_data.ssecurity) + base64.b64decode(nonce))
        return base64.b64encode(hash_object.digest()).decode()
