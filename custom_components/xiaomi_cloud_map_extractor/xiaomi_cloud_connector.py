import base64
import gzip
import zlib
import hashlib
import hmac
import json
import os
import random
import requests
import time

from .const import *
from .map_data_parser import MapDataParser


class XiaomiCloudDevice:

    def __init__(self, connector, country):
        self._connector = connector
        self._country = country

    def get_map(self, map_name, colors, drawables, texts, sizes, image_config, store_response=False):
        response = self.get_raw_map_data(map_name)
        if response is None:
            return None, False
        map_stored = False
        if store_response:
            file1 = open("/tmp/map_data.gz", "wb")
            file1.write(response)
            file1.close()
            map_stored = True
        map_data = self.decode_map(response, colors, drawables, texts, sizes, image_config)
        map_data.map_name = map_name
        return map_data, map_stored

    def get_raw_map_data(self, map_name):
        if map_name is None:
            return None
        map_url = self.get_map_url(map_name)
        if map_url is not None:
            try:
                response = self._connector._session.get(map_url, timeout=10)
            except:
                response = None
            if response is not None and response.status_code == 200:
                return response.content
        return None


class XiaomiCloudDeviceV1(XiaomiCloudDevice):

    def __init__(self, connector, country):
        super(XiaomiCloudDeviceV1, self).__init__(connector, country)

    def get_map_url(self, map_name):
        url = self._connector.get_api_url(self._country) + "/home/getmapfileurl"
        params = {
            "data": '{"obj_name":"' + map_name + '"}'
        }
        api_response = self._connector.execute_api_call(url, params)
        if api_response is None or "result" not in api_response or "url" not in api_response["result"]:
            return None
        return api_response["result"]["url"]

    def decode_map(self, raw_map, colors, drawables, texts, sizes, image_config):
        unzipped = gzip.decompress(raw_map)
        return MapDataParser.parse(unzipped, colors, drawables, texts, sizes, image_config)


class XiaomiCloudDeviceV2(XiaomiCloudDevice):

    def __init__(self, connector, country, user_id, device_id):
        super(XiaomiCloudDeviceV2, self).__init__(connector, country)
        self._user_id = int(user_id)
        self._device_id = int(device_id)

    def get_map_url(self, map_name):
        url = self._connector.get_api_url(self._country) + '/v2/home/get_interim_file_url'
        params = {
            "data": '{"obj_name":"%d/%d/%s"}' % (self._user_id, self._device_id, map_name)
        }
        api_response = self._connector.execute_api_call(url, params)
        if api_response is None or "result" not in api_response or "url" not in api_response["result"]:
            return None
        return api_response["result"]["url"]

    def decode_map(self, raw_map, colors, drawables, texts, sizes, image_config):
        unzipped = zlib.decompress(raw_map)
        return MapDataParser.parse(unzipped, colors, drawables, texts, sizes, image_config)


# noinspection PyBroadException
class XiaomiCloudConnector:
    V2_MODELS = ['viomi.vacuum.v6']

    def __init__(self, username, password):
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

    def login_step_1(self):
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

    def login_step_2(self):
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
        successful = response is not None and response.status_code == 200 and "ssecurity" in self.to_json(
            response.text) and len(str(self.to_json(response.text)["ssecurity"])) > 4
        if successful:
            json_resp = self.to_json(response.text)
            self._ssecurity = json_resp["ssecurity"]
            self._userId = json_resp["userId"]
            self._cUserId = json_resp["cUserId"]
            self._passToken = json_resp["passToken"]
            self._location = json_resp["location"]
            self._code = json_resp["code"]
        return successful

    def login_step_3(self):
        headers = {
            "User-Agent": self._agent,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        try:
            response = self._session.get(self._location, headers=headers, timeout=10)
        except:
            response = None
        if response is not None and response.status_code == 200:
            self._serviceToken = response.cookies.get("serviceToken")
        return response.status_code == 200

    def login(self):
        self._session.close()
        self._session = requests.session()
        self._agent = self.generate_agent()
        self._device_id = self.generate_device_id()
        self._session.cookies.set("sdkVersion", "accountsdk-18.8.15", domain="mi.com")
        self._session.cookies.set("sdkVersion", "accountsdk-18.8.15", domain="xiaomi.com")
        self._session.cookies.set("deviceId", self._device_id, domain="mi.com")
        self._session.cookies.set("deviceId", self._device_id, domain="xiaomi.com")
        return self.login_step_1() and self.login_step_2() and self.login_step_3()

    def get_country_for_device(self, ip_address, token):
        for country in CONF_AVAILABLE_COUNTRIES:
            devices = self.get_devices(country)
            if devices is None:
                continue
            found = list(filter(
                lambda d: d["localip"] == ip_address and d["token"] == token,
                devices["result"]["list"]))
            if len(found) > 0:
                return country
        return None

    def get_devices(self, country):
        url = self.get_api_url(country) + "/home/device_list"
        params = {
            "data": '{"getVirtualModel":false,"getHuamiDevices":0}'
        }
        return self.execute_api_call(url, params)

    def get_device(self, **kwargs):
        for k in list(kwargs.keys()):
            if kwargs[k] is None or kwargs[k] == '':
                del kwargs[k]
        if 'country' in kwargs:
            if kwargs.get('new_proto', False):
                return XiaomiCloudDeviceV1(self, kwargs['country'])
            if 'user_id' in kwargs and 'device_id' in kwargs:
                return XiaomiCloudDeviceV2(self, kwargs['country'], kwargs['user_id'], kwargs['device_id'])
            available_countries = [kwargs['country']]
        else:
            available_countries = CONF_AVAILABLE_COUNTRIES
        for country in available_countries:
            devices = self.get_devices(country)
            if devices is None or 'result' not in devices or 'list' not in devices['result']:
                continue
            for device in devices['result']['list']:
                if 'user_id' in kwargs and device['uid'] != kwargs['user_id']:
                    continue
                if 'device_id' in kwargs and device['did'] != kwargs['device_id']:
                    continue
                if 'ip_address' in kwargs and device['localip'] != kwargs['ip_address']:
                    continue
                if 'token' in kwargs and device['token'] != kwargs['token']:
                    continue
                if kwargs.get('new_proto', device['model'] in XiaomiCloudConnector.V2_MODELS):
                    return XiaomiCloudDeviceV2(self, country, device['uid'], device['did'])
                else:
                    return XiaomiCloudDeviceV1(self, country)
        return None

    def execute_api_call(self, url, params):
        headers = {
            "Accept-Encoding": "gzip",
            "User-Agent": self._agent,
            "Content-Type": "application/x-www-form-urlencoded",
            "x-xiaomi-protocal-flag-cli": "PROTOCAL-HTTP2"
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
        signature = self.generate_signature(url.replace("/app", ""), signed_nonce, nonce, params)
        fields = {
            "signature": signature,
            "_nonce": nonce,
            "data": params["data"]
        }
        try:
            response = self._session.post(url, headers=headers, cookies=cookies, params=fields, timeout=10)
        except:
            response = None
        if response is not None and response.status_code == 200:
            return response.json()
        return None

    def get_api_url(self, country):
        return "https://" + ("" if country == "cn" else (country + ".")) + "api.io.mi.com/app"

    def signed_nonce(self, nonce):
        hash_object = hashlib.sha256(base64.b64decode(self._ssecurity) + base64.b64decode(nonce))
        return base64.b64encode(hash_object.digest()).decode('utf-8')

    @staticmethod
    def generate_nonce(millis):
        nonce_bytes = os.urandom(8) + (int(millis / 60000)).to_bytes(4, byteorder='big')
        return base64.b64encode(nonce_bytes).decode()

    @staticmethod
    def generate_agent():
        agent_id = "".join(map(lambda i: chr(i), [random.randint(65, 69) for _ in range(13)]))
        return f"Android-7.1.1-1.0.0-ONEPLUS A3010-136-{agent_id} APP/xiaomi.smarthome APPV/62830"

    @staticmethod
    def generate_device_id():
        return "".join(map(lambda i: chr(i), [random.randint(97, 122) for _ in range(6)]))

    @staticmethod
    def generate_signature(url, signed_nonce, nonce, params):
        signature_params = [url.split("com")[1], signed_nonce, nonce]
        for k, v in params.items():
            signature_params.append(f"{k}={v}")
        signature_string = "&".join(signature_params)
        signature = hmac.new(base64.b64decode(signed_nonce), msg=signature_string.encode(), digestmod=hashlib.sha256)
        return base64.b64encode(signature.digest()).decode()

    @staticmethod
    def to_json(response_text):
        return json.loads(response_text.replace("&&&START&&&", ""))
