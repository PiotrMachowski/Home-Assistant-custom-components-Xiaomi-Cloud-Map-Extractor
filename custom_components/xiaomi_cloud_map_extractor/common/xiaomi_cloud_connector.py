import base64
import hashlib
import hmac
import json
import logging
import os
import random
import time
from typing import Any, Dict, NamedTuple, Optional, Tuple
from Crypto.Cipher import ARC4

import requests

from custom_components.xiaomi_cloud_map_extractor.const import *

_LOGGER = logging.getLogger(__name__)


class XiaomiHome(NamedTuple):
    homeid: int
    owner: int


class XiaomiDeviceInfo(NamedTuple):
    device_id: str
    name: str
    model: str
    token: str
    country: str
    home_id: int
    user_id: int


# noinspection PyBroadException
class XiaomiCloudConnector:

    def __init__(self, username: str, password: str):
        self.two_factor_auth_url = None
        self._username = username
        self._password = password
        self._agent = self.generate_agent()
        self._device_id = self.generate_device_id()
        self._session = requests.session()
        self._sign = None
        self._ssecurity = None
        self._userId = None
        self._cUserId = None
        self._passToken = None
        self._location = None
        self._code = None
        self._serviceToken = None

    def login_step_1(self) -> bool:
        url = "https://account.xiaomi.com/pass/serviceLogin?sid=xiaomiio&_json=true"
        headers = {
            "User-Agent": self._agent,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        cookies = {
            "userId": self._username
        }
        try:
            response = self._session.get(url, headers=headers, cookies=cookies, timeout=10)
        except:
            response = None
        successful = response is not None and response.status_code == 200 and "_sign" in self.to_json(response.text)
        if successful:
            self._sign = self.to_json(response.text)["_sign"]
        return successful

    def login_step_2(self) -> bool:
        url = "https://account.xiaomi.com/pass/serviceLoginAuth2"
        headers = {
            "User-Agent": self._agent,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        fields = {
            "sid": "xiaomiio",
            "hash": hashlib.md5(str.encode(self._password)).hexdigest().upper(),
            "callback": "https://sts.api.io.mi.com/sts",
            "qs": "%3Fsid%3Dxiaomiio%26_json%3Dtrue",
            "user": self._username,
            "_sign": self._sign,
            "_json": "true"
        }
        try:
            response = self._session.post(url, headers=headers, params=fields, timeout=10)
        except:
            response = None
        successful = response is not None and response.status_code == 200
        if successful:
            json_resp = self.to_json(response.text)
            successful = "ssecurity" in json_resp and len(str(json_resp["ssecurity"])) > 4
            if successful:
                self._ssecurity = json_resp["ssecurity"]
                self._userId = json_resp["userId"]
                self._cUserId = json_resp["cUserId"]
                self._passToken = json_resp["passToken"]
                self._location = json_resp["location"]
                self._code = json_resp["code"]
                self.two_factor_auth_url = None
            else:
                if "notificationUrl" in json_resp:
                    _LOGGER.error(
                        "Additional authentication required. " +
                        "Open following URL using device that has the same public IP, " +
                        "as your Home Assistant instance: %s ",
                        json_resp["notificationUrl"])
                    self.two_factor_auth_url = json_resp["notificationUrl"]
                    successful = None

        return successful

    def login_step_3(self) -> bool:
        headers = {
            "User-Agent": self._agent,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        try:
            response = self._session.get(self._location, headers=headers, timeout=10)
        except:
            response = None
        successful = response is not None and response.status_code == 200 and "serviceToken" in response.cookies
        if successful:
            self._serviceToken = response.cookies.get("serviceToken")
        return successful

    def login(self) -> bool:
        self._session.close()
        self._session = requests.session()
        self._agent = self.generate_agent()
        self._device_id = self.generate_device_id()
        self._session.cookies.set("sdkVersion", "accountsdk-18.8.15", domain="mi.com")
        self._session.cookies.set("sdkVersion", "accountsdk-18.8.15", domain="xiaomi.com")
        self._session.cookies.set("deviceId", self._device_id, domain="mi.com")
        self._session.cookies.set("deviceId", self._device_id, domain="xiaomi.com")
        return self.login_step_1() and self.login_step_2() and self.login_step_3()

    def get_raw_map_data(self, map_url) -> Optional[bytes]:
        if map_url is not None:
            try:
                response = self._session.get(map_url, timeout=10)
            except:
                response = None
            if response is not None and response.status_code == 200:
                return response.content
        return None

    def get_homes_iter(self, country: str):
        url = self.get_api_url(country) + "/v2/homeroom/gethome"
        params = {
            "data": json.dumps(
                {
                    "fg": True,
                    "fetch_share": True,
                    "fetch_share_dev": True,
                    "limit": 300,
                    "app_ver": 7,
                }
            )
        }

        if (response := self.execute_api_call_encrypted(url, params)) is None:
            return None

        if homelist := response["result"]["homelist"]:
            yield from (XiaomiHome(int(home["id"]), home["uid"]) for home in homelist)

        if homelist := response["result"]["share_home_list"]:
            yield from (XiaomiHome(int(home["id"]), home["uid"]) for home in homelist)

    def get_devices_from_home_iter(self, country: str, home_id: int, owner_id: int):
        url = self.get_api_url(country) + "/v2/home/home_device_list"
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
        if (response := self.execute_api_call_encrypted(url, params)) is None:
            return

        if (raw_devices := response["result"]["device_info"]) is None:
            return

        yield from (
            XiaomiDeviceInfo(
                device_id=device["did"],
                name=device["name"],
                model=device["model"],
                token=device["token"],
                country=country,
                user_id=owner_id,
                home_id=home_id,
            )
            for device in raw_devices
        )

    def get_devices_iter(self, country: Optional[str] = None):
        countries_to_check = CONF_AVAILABLE_COUNTRIES if country is None else [country]
        for _country in countries_to_check:
            homes = self.get_homes_iter(_country)
            for home in homes:
                devices = self.get_devices_from_home_iter(
                    _country, home.homeid, home.owner
                )
                yield from devices

    def get_device_details_from_home(self, token: str, country: Optional[str] = None):
        devices = self.get_devices_iter(country)
        matching_token = filter(lambda device: device.token == token, devices)
        if match := next(matching_token, None):
            return match.country, match.user_id, match.device_id, match.model

        return None, None, None, None

    def get_device_details(self, token: str,
                           country: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        countries_to_check = CONF_AVAILABLE_COUNTRIES
        if country is not None:
            countries_to_check = [country]
        for c in countries_to_check:
            devices = self.get_devices(c)
            if devices is None:
                continue
            found = list(filter(lambda d: str(d["token"]).casefold() == str(token).casefold(),
                                devices["result"]["list"]))
            if len(found) > 0:
                user_id = found[0]["uid"]
                device_id = found[0]["did"]
                model = found[0]["model"]
                return c, user_id, device_id, model
        return self.get_device_details_from_home(token, country)

    def get_devices(self, country: str) -> Any:
        url = self.get_api_url(country) + "/home/device_list"
        params = {
            "data": '{"getVirtualModel":false,"getHuamiDevices":0}'
        }
        return self.execute_api_call_encrypted(url, params)

    def execute_api_call_encrypted(self, url: str, params: Dict[str, str]) -> Any:
        headers = {
            "Accept-Encoding": "identity",
            "User-Agent": self._agent,
            "Content-Type": "application/x-www-form-urlencoded",
            "x-xiaomi-protocal-flag-cli": "PROTOCAL-HTTP2",
            "MIOT-ENCRYPT-ALGORITHM": "ENCRYPT-RC4",
        }
        cookies = {
            "userId": str(self._userId),
            "yetAnotherServiceToken": str(self._serviceToken),
            "serviceToken": str(self._serviceToken),
            "locale": "en_GB",
            "timezone": "GMT+02:00",
            "is_daylight": "1",
            "dst_offset": "3600000",
            "channel": "MI_APP_STORE"
        }
        millis = round(time.time() * 1000)
        nonce = self.generate_nonce(millis)
        signed_nonce = self.signed_nonce(nonce)
        fields = self.generate_enc_params(url, "POST", signed_nonce, nonce, params, self._ssecurity)

        try:
            response = self._session.post(url, headers=headers, cookies=cookies, params=fields, timeout=10)
        except:
            response = None
        if response is not None and response.status_code == 200:
            decoded = self.decrypt_rc4(self.signed_nonce(fields["_nonce"]), response.text)
            return json.loads(decoded)
        return None

    def get_api_url(self, country: str) -> str:
        return "https://" + ("" if country == "cn" else (country + ".")) + "api.io.mi.com/app"

    def signed_nonce(self, nonce: str) -> str:
        hash_object = hashlib.sha256(base64.b64decode(self._ssecurity) + base64.b64decode(nonce))
        return base64.b64encode(hash_object.digest()).decode('utf-8')

    @staticmethod
    def generate_nonce(millis: int):
        nonce_bytes = os.urandom(8) + (int(millis / 60000)).to_bytes(4, byteorder='big')
        return base64.b64encode(nonce_bytes).decode()

    @staticmethod
    def generate_agent() -> str:
        agent_id = "".join((chr(random.randint(65, 69)) for _ in range(13)))
        return f"Android-7.1.1-1.0.0-ONEPLUS A3010-136-{agent_id} APP/xiaomi.smarthome APPV/62830"

    @staticmethod
    def generate_device_id() -> str:
        return "".join((chr(random.randint(97, 122)) for _ in range(6)))

    @staticmethod
    def generate_signature(url, signed_nonce: str, nonce: str, params: Dict[str, str]) -> str:
        signature_params = [url.split("com")[1], signed_nonce, nonce]
        for k, v in params.items():
            signature_params.append(f"{k}={v}")
        signature_string = "&".join(signature_params)
        signature = hmac.new(base64.b64decode(signed_nonce), msg=signature_string.encode(), digestmod=hashlib.sha256)
        return base64.b64encode(signature.digest()).decode()

    @staticmethod
    def generate_enc_signature(url, method: str, signed_nonce: str, params: Dict[str, str]) -> str:
        signature_params = [str(method).upper(), url.split("com")[1].replace("/app/", "/")]
        for k, v in params.items():
            signature_params.append(f"{k}={v}")
        signature_params.append(signed_nonce)
        signature_string = "&".join(signature_params)
        return base64.b64encode(hashlib.sha1(signature_string.encode('utf-8')).digest()).decode()

    @staticmethod
    def generate_enc_params(url: str, method: str, signed_nonce: str, nonce: str, params: Dict[str, str],
                            ssecurity: str) -> Dict[str, str]:
        params['rc4_hash__'] = XiaomiCloudConnector.generate_enc_signature(url, method, signed_nonce, params)
        for k, v in params.items():
            params[k] = XiaomiCloudConnector.encrypt_rc4(signed_nonce, v)
        params.update({
            'signature': XiaomiCloudConnector.generate_enc_signature(url, method, signed_nonce, params),
            'ssecurity': ssecurity,
            '_nonce': nonce,
        })
        return params

    @staticmethod
    def to_json(response_text: str) -> Any:
        return json.loads(response_text.replace("&&&START&&&", ""))

    @staticmethod
    def encrypt_rc4(password: str, payload: str) -> str:
        r = ARC4.new(base64.b64decode(password))
        r.encrypt(bytes(1024))
        return base64.b64encode(r.encrypt(payload.encode())).decode()

    @staticmethod
    def decrypt_rc4(password: str, payload: str) -> bytes:
        r = ARC4.new(base64.b64decode(password))
        r.encrypt(bytes(1024))
        return r.encrypt(base64.b64decode(payload))
