import asyncio
import base64
import datetime
import hashlib
import json
import locale
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Optional, Self, Unpack

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
    FailedConnectionException
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
    ssecurity: str | None = None
    userId: str | None = None
    serviceToken: str | None = None
    expiration: datetime.datetime | None = None

    def is_authenticated(self) -> bool:
        return self.serviceToken is not None and self.expiration > datetime.datetime.now() - datetime.timedelta(days=1)

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
        timezone = datetime.datetime.now(tzlocal.get_localzone()).strftime('%z')
        self._timezone = f"GMT{timezone[:-2]}:{timezone[-2:]}"
        self.server = server
        self._session_data = None

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
        if response.status == 200:
            if "ssecurity" in response_json:
                location = response_json["location"]
                self._session_data.ssecurity = response_json["ssecurity"]
                self._session_data.userId = response_json["userId"]
                max_age = int(response.cookies.get("userId").get("max-age"))
                self._session_data.expiration = datetime.datetime.now() + datetime.timedelta(seconds=max_age)
                self.two_factor_auth_url = None
                return location
            else:
                if "notificationUrl" in response_json:
                    _LOGGER.error(
                        "Additional authentication required. " +
                        "Open following URL using device that has the same public IP, " +
                        "as your Home Assistant instance: %s ",
                        response_json["notificationUrl"])
                    raise TwoFactorAuthRequiredException(response_json["notificationUrl"])
        raise InvalidCredentialsException()

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
        _LOGGER.debug("Logging in...")
        await self.create_session()
        sign = await self._login_step_1()
        if not sign.startswith('http'):
            location = await self._login_step_2(sign)
        else:
            location = sign
        await self._login_step_3(location)
        _LOGGER.debug("Logged in.")
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
        cookies = {
            "userId": str(self._session_data.userId),
            "yetAnotherServiceToken": str(self._session_data.serviceToken),
            "serviceToken": str(self._session_data.serviceToken),
            "locale": self._locale,
            "timezone": self._timezone,
            "is_daylight": str(time.daylight),
            "dst_offset": str(time.localtime().tm_isdst * 60 * 60 * 1000),
            "channel": "MI_APP_STORE"
        }
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
