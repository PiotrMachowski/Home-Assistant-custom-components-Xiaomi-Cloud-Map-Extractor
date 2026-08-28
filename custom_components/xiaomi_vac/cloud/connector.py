"""Synchronous Xiaomi cloud connector (login + map blob download).

See docs/dev/module-notes.md for design rationale.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import random
import re
import time
from typing import Callable
from urllib.parse import parse_qs, urlparse

import requests

try:
    from Crypto.Cipher import ARC4
except ModuleNotFoundError:  # pragma: no cover
    from Cryptodome.Cipher import ARC4

_LOGGER = logging.getLogger(__name__)

SERVERS = ["cn", "de", "us", "ru", "tw", "sg", "in", "i2"]


class TwoFactorRequired(Exception):
    """Raised when the caller did not supply a 2FA code callback."""


class CaptchaRequired(Exception):
    """Raised when the caller did not supply a captcha callback."""


class XiaomiCloud:
    def __init__(self, username: str, password: str = ""):
        # password is only needed for the interactive login (begin_login). Session
        # restore + passToken renewal never use it, so it defaults to empty.
        self._u = username
        self._p = password
        self._s = requests.session()
        self._agent = _agent()
        self._device_id = "".join(chr(random.randint(97, 122)) for _ in range(6))
        self._sign = None
        self.ssecurity = None
        self.user_id = None
        self.service_token = None
        self.pass_token = None  # long-lived; used to renew the session
        # resumable-login scratch state
        self.captcha_image: bytes | None = None
        self.login_error: str = ""  # Xiaomi's desc from the last failed login
        self._fields: dict = {}
        self._2fa_ctx: str | None = None
        self._lp_url: str | None = None

    # --- QR login -------------------------------------------------------
    def qr_begin(self) -> tuple[bytes, str]:
        """Start QR login. Returns (QR image bytes, login URL).

        Must mirror the full two-step flow: serviceLogin (for _sign / qs /
        callback / serviceParam) then longPolling/loginUrl with all params.
        A minimal request yields a QR the Mi Home app rejects (error :70036),
        and we must serve Xiaomi's QR image (re-encoding it ourselves fails too).
        """
        h = {"User-Agent": self._agent}
        self._s.cookies.set("sdkVersion", "accountsdk-18.8.15", domain="mi.com")
        self._s.cookies.set("sdkVersion", "accountsdk-18.8.15", domain="xiaomi.com")
        self._s.cookies.set("deviceId", self._device_id, domain="mi.com")
        self._s.cookies.set("deviceId", self._device_id, domain="xiaomi.com")

        r = self._s.get(
            "https://account.xiaomi.com/pass/serviceLogin?sid=xiaomiio&_json=true",
            headers=h, timeout=10,
        )
        j = _to_json(r.text)
        service_param = parse_qs(urlparse(j.get("location", "")).query).get("serviceParam", [""])[0]
        data = {
            "_qrsize": "480",
            "qs": j.get("qs", "%3Fsid%3Dxiaomiio%26_json%3Dtrue"),
            "bizDeviceType": "",
            "callback": j.get("callback", "https://sts.api.io.mi.com/sts"),
            "_json": "true",
            "theme": "",
            "sid": "xiaomiio",
            "needTheme": "false",
            "showActiveX": "false",
            "serviceParam": service_param,
            "_local": "zh_CN",
            "_sign": j["_sign"],
            "_dc": str(int(time.time() * 1000)),
        }
        r = self._s.get("https://account.xiaomi.com/longPolling/loginUrl",
                        params=data, headers=h, timeout=10)
        jj = _to_json(r.text)
        self._lp_url = jj["lp"]
        png = self._s.get(jj["qr"], headers=h, timeout=10).content
        return png, jj["loginUrl"]

    def qr_poll(self, timeout: int = 25) -> str:
        """Long-poll once for QR scan completion. Returns 'ok'|'waiting'|'fail'."""
        try:
            r = self._s.get(self._lp_url, headers={"User-Agent": self._agent}, timeout=timeout)
        except requests.exceptions.Timeout:
            return "waiting"
        if r.status_code != 200:
            return "waiting"
        j = _to_json(r.text)
        if j.get("code") != 0:
            return "waiting"
        self.user_id = j["userId"]
        self.ssecurity = j["ssecurity"]
        self.pass_token = j.get("passToken", self.pass_token)
        loc = j["location"]
        r = self._s.get(loc, headers={"User-Agent": self._agent}, timeout=10)
        self.service_token = r.cookies.get("serviceToken")
        return "ok" if self.service_token else "fail"

    # --- device discovery ----------------------------------------------
    def list_vacuums(self) -> list[dict]:
        """List all vacuum devices across servers with localip + token.

        Returns every device whose model string contains ``.vacuum.``; brand
        filtering (supported vs. unsupported) is left to the caller.
        """
        found: dict[str, dict] = {}  # keyed by did to dedupe across servers
        for srv in SERVERS:
            resp = self._call(self._api_url(srv) + "/home/device_list",
                              {"data": '{"getVirtualModel":false,"getHuamiDevices":0}'})
            if not resp:
                continue
            for d in resp.get("result", {}).get("list", []):
                model = d.get("model", "")
                did = d.get("did")
                if did in found or ".vacuum." not in model:
                    continue
                found[did] = {
                    "name": d.get("name"), "did": did, "model": model,
                    "mac": d.get("mac", ""), "localip": d.get("localip", ""),
                    "token": d.get("token", ""), "server": srv,
                }
        return list(found.values())

    def restore_session(self, user_id, ssecurity, service_token, pass_token=None) -> None:
        """Reuse a session captured at config-flow time (no re-login)."""
        self.user_id = user_id
        self.ssecurity = ssecurity
        self.service_token = service_token
        self.pass_token = pass_token

    def refresh(self) -> bool:
        """Renew ssecurity + serviceToken using the long-lived passToken.

        No password / captcha / 2FA. Returns True if a fresh session was minted.
        """
        if not self.pass_token or not self.user_id:
            return False
        h = {"User-Agent": self._agent}
        self._s.cookies.set("userId", str(self.user_id), domain="xiaomi.com")
        self._s.cookies.set("passToken", self.pass_token, domain="xiaomi.com")
        try:
            r = self._s.get(
                "https://account.xiaomi.com/pass/serviceLogin?sid=xiaomiio&_json=true",
                headers=h, cookies={"userId": str(self.user_id)}, timeout=10,
            )
            j = _to_json(r.text)
            if "ssecurity" not in j or not j.get("location"):
                return False
            self.ssecurity = j["ssecurity"]
            self.pass_token = j.get("passToken", self.pass_token)
            r2 = self._s.get(j["location"], headers=h, timeout=10)
            token = r2.cookies.get("serviceToken")
        except Exception:  # noqa: BLE001
            return False
        if token:
            self.service_token = token
            return True
        return False

    # --- login: resumable state machine ---------------------------------
    # States returned by begin_login/submit_*: "ok" | "captcha" | "2fa" | "fail".
    # On "captcha", self.captcha_image holds PNG bytes to show the user.
    def begin_login(self) -> str:
        self._s.cookies.set("sdkVersion", "accountsdk-18.8.15", domain="mi.com")
        self._s.cookies.set("sdkVersion", "accountsdk-18.8.15", domain="xiaomi.com")
        self._s.cookies.set("deviceId", self._device_id, domain="mi.com")
        self._s.cookies.set("deviceId", self._device_id, domain="xiaomi.com")
        r = self._s.get(
            "https://account.xiaomi.com/pass/serviceLogin?sid=xiaomiio&_json=true",
            headers={"User-Agent": self._agent}, cookies={"userId": self._u}, timeout=10,
        )
        self._sign = _to_json(r.text)["_sign"]
        self._fields = {
            "sid": "xiaomiio",
            "hash": hashlib.md5(self._p.encode()).hexdigest().upper(),
            "callback": "https://sts.api.io.mi.com/sts",
            "qs": "%3Fsid%3Dxiaomiio%26_json%3Dtrue",
            "user": self._u, "_sign": self._sign, "_json": "true",
        }
        return self._resolve(self._auth2(self._fields))

    def submit_captcha(self, code: str) -> str:
        self._fields["captCode"] = code
        self._fields["_sign"] = self._sign
        return self._resolve(self._auth2(self._fields))

    def submit_2fa(self, code: str) -> str:
        if not self._finish_email_2fa(code):
            return "fail"
        return "ok"

    def _resolve(self, j: dict) -> str:
        """Inspect an auth2 response; finalise on success, else say what's needed."""
        if "ssecurity" in j:
            self.ssecurity = j["ssecurity"]
            self.user_id = j["userId"]
            self.pass_token = j.get("passToken", self.pass_token)
            r = self._s.get(j["location"], headers={"User-Agent": self._agent}, timeout=10)
            self.service_token = r.cookies.get("serviceToken")
            return "ok" if self.service_token else "fail"
        if j.get("code") == 87001 and j.get("captchaUrl"):
            cap = j["captchaUrl"]
            if cap.startswith("/"):
                cap = "https://account.xiaomi.com" + cap
            self.captcha_image = self._s.get(
                cap, headers={"User-Agent": self._agent}, timeout=10).content
            return "captcha"
        if j.get("notificationUrl"):
            self._start_email_2fa(j["notificationUrl"])
            return "2fa"
        self.login_error = str(j.get("desc") or "")
        _LOGGER.error("Xiaomi account sign-in rejected: %s", self.login_error or j)
        return "fail"

    def login(
        self,
        captcha_cb: Callable[[bytes], str] | None = None,
        twofa_cb: Callable[[], str] | None = None,
    ) -> bool:
        """Blocking convenience wrapper (CLI/tests) over the state machine."""
        state = self.begin_login()
        for _ in range(6):
            if state == "ok":
                return True
            if state == "fail":
                return False
            if state == "captcha":
                if not captcha_cb:
                    raise CaptchaRequired()
                state = self.submit_captcha(captcha_cb(self.captcha_image))
            elif state == "2fa":
                if not twofa_cb:
                    raise TwoFactorRequired()
                state = self.submit_2fa(twofa_cb())
        return state == "ok"

    def _auth2(self, fields) -> dict:
        r = self._s.post(
            "https://account.xiaomi.com/pass/serviceLoginAuth2",
            headers={"User-Agent": self._agent}, params=fields, timeout=10,
        )
        return _to_json(r.text)

    def _start_email_2fa(self, notification_url: str) -> None:
        h = {"User-Agent": self._agent, "Content-Type": "application/x-www-form-urlencoded"}
        self._s.get(notification_url, headers=h, timeout=10)
        self._2fa_ctx = parse_qs(urlparse(notification_url).query)["context"][0]
        self._s.get(
            "https://account.xiaomi.com/identity/list",
            params={"sid": "xiaomiio", "context": self._2fa_ctx, "_locale": "en_US"},
            headers=h, timeout=10,
        )
        self._s.post(
            "https://account.xiaomi.com/identity/auth/sendEmailTicket",
            params={"_dc": str(int(time.time() * 1000)), "sid": "xiaomiio",
                    "context": self._2fa_ctx, "mask": "0", "_locale": "en_US"},
            data={"retry": "0", "icode": "", "_json": "true",
                  "ick": self._s.cookies.get("ick", "")},
            headers=h, timeout=10,
        )

    def _any_domain_cookie(self, name: str) -> str | None:
        """Find a cookie by name regardless of which domain set it."""
        for c in self._s.cookies:
            if c.name == name:
                return c.value
        return None

    def _finish_email_2fa(self, code: str) -> bool:
        h = {"User-Agent": self._agent, "Content-Type": "application/x-www-form-urlencoded"}
        context = self._2fa_ctx
        # Xiaomi frequently drops a reused keep-alive socket on this POST
        # (RemoteDisconnected). requests does not auto-retry POSTs, so do it
        # here — the code isn't consumed until the server actually responds.
        r = None
        for attempt in range(3):
            try:
                r = self._s.post(
                    "https://account.xiaomi.com/identity/auth/verifyEmail",
                    params={"_flag": "8", "_json": "true", "sid": "xiaomiio",
                            "context": context, "mask": "0", "_locale": "en_US"},
                    data={"_flag": "8", "ticket": code, "trust": "false", "_json": "true",
                          "ick": self._s.cookies.get("ick", "")},
                    headers=h, timeout=10,
                )
                break
            except requests.exceptions.ConnectionError:
                if attempt == 2:
                    raise
                time.sleep(1.5)
        if r is None:
            return False
        if r.status_code != 200:
            return False
        finish = None
        try:
            finish = r.json().get("location")
        except Exception:  # noqa: BLE001
            m = re.search(r'https://account\.xiaomi\.com/identity/result/check\?[^"\']+', r.text)
            finish = m.group(0) if m else None
        if not finish:
            r0 = self._s.get(
                "https://account.xiaomi.com/identity/result/check",
                params={"sid": "xiaomiio", "context": context, "_locale": "en_US"},
                headers=h, allow_redirects=False, timeout=10,
            )
            finish = r0.headers.get("Location") or (r0.url if "serviceLoginAuth2/end" in r0.url else None)
        if not finish:
            return False
        if "identity/result/check" in finish:
            r = self._s.get(finish, headers=h, allow_redirects=False, timeout=10)
            end_url = r.headers.get("Location")
        else:
            end_url = finish
        if not end_url:
            return False
        r = self._s.get(end_url, headers=h, allow_redirects=False, timeout=10)
        if r.status_code == 200 and "Xiaomi Account - Tips" in r.text:
            r = self._s.get(end_url, headers=h, allow_redirects=False, timeout=10)
        ext = r.headers.get("extension-pragma")
        if ext:
            try:
                self.ssecurity = json.loads(ext).get("ssecurity") or self.ssecurity
            except Exception:  # noqa: BLE001
                pass
        if not self.ssecurity:
            return False
        sts = r.headers.get("Location")
        if not sts and r.text:
            idx = r.text.find("https://sts.api.io.mi.com/sts")
            if idx != -1:
                end = r.text.find('"', idx)
                sts = r.text[idx: end if end != -1 else idx + 300]
        if not sts:
            return False
        r = self._s.get(sts, headers=h, allow_redirects=True, timeout=10)
        self.service_token = self._s.cookies.get("serviceToken", domain=".sts.api.io.mi.com")
        self.user_id = self.user_id or self._s.cookies.get("userId", domain=".xiaomi.com")
        # Unlike password/QR login, 2FA never returns passToken in a JSON body,
        # so this cookie is the only source. Pinning the lookup to domain=
        # ".xiaomi.com" silently returns None if Xiaomi actually scoped the
        # cookie elsewhere for this flow, which permanently breaks refresh()
        # (#12: 2FA login, map session expired immediately) — match by name
        # across every domain instead of guessing one.
        self.pass_token = self.pass_token or self._any_domain_cookie("passToken")
        for d in (".api.io.mi.com", ".io.mi.com", ".mi.com"):
            self._s.cookies.set("serviceToken", self.service_token, domain=d)
        return bool(self.service_token)

    # --- API ------------------------------------------------------------
    def _api_url(self, server: str) -> str:
        return "https://" + ("" if server == "cn" else server + ".") + "api.io.mi.com/app"

    def _call(self, url: str, params: dict) -> dict | None:
        h = {"Accept-Encoding": "identity", "User-Agent": self._agent,
             "Content-Type": "application/x-www-form-urlencoded",
             "x-xiaomi-protocal-flag-cli": "PROTOCAL-HTTP2",
             "MIOT-ENCRYPT-ALGORITHM": "ENCRYPT-RC4"}
        ck = {"userId": str(self.user_id), "serviceToken": str(self.service_token),
              "yetAnotherServiceToken": str(self.service_token), "locale": "en_GB",
              "channel": "MI_APP_STORE"}
        nonce = base64.b64encode(os.urandom(8) + int(time.time() * 1000 / 60000).to_bytes(4, "big")).decode()
        sn = self._signed_nonce(nonce)
        params["rc4_hash__"] = _enc_sig(url, sn, params)
        for k, v in params.items():
            params[k] = _enc_rc4(sn, v)
        params.update({"signature": _enc_sig(url, sn, params),
                       "ssecurity": self.ssecurity, "_nonce": nonce})
        r = self._s.post(url, headers=h, cookies=ck, params=params, timeout=10)
        if r.status_code != 200:
            return None
        return json.loads(_dec_rc4(self._signed_nonce(params["_nonce"]), r.text))

    def _signed_nonce(self, nonce: str) -> str:
        h = hashlib.sha256(base64.b64decode(self.ssecurity) + base64.b64decode(nonce))
        return base64.b64encode(h.digest()).decode()

    def find_device(self, token: str, server: str | None = None):
        """Return (server, did, model, name) for the device with this token."""
        for srv in ([server] if server else SERVERS):
            resp = self._call(self._api_url(srv) + "/home/device_list",
                              {"data": '{"getVirtualModel":false,"getHuamiDevices":0}'})
            if not resp:
                continue
            for d in resp["result"]["list"]:
                if str(d.get("token", "")).casefold() == str(token).casefold():
                    return srv, d["did"], d.get("model"), d.get("name")
        return None, None, None, None

    def cloud_action(self, server: str, did: str, siid: int, aiid: int, in_params: list):
        """Call a MIoT action via the cloud (avoids local -9999 ack timeouts)."""
        url = self._api_url(server) + "/miotspec/action"
        body = {"params": {"did": str(did), "siid": siid, "aiid": aiid, "in": list(in_params)}}
        return self._call(url, {"data": json.dumps(body)})

    def cloud_get_prop(self, server: str, did: str, siid: int, piid: int):
        url = self._api_url(server) + "/miotspec/prop/get"
        body = {"params": [{"did": str(did), "siid": siid, "piid": piid}]}
        return self._call(url, {"data": json.dumps(body)})

    def map_url(self, server: str, did: str, map_name: str = "0",
                endpoint: str = "get_interim_file_url_pro") -> str | None:
        """Mint a signed download URL for one map object.

        Tries the alternate endpoint (get_interim_file_url vs. _pro) on ANY
        failure, not just code -8 — some brands (observed live: 3irobotic-
        manufactured xiaomi.* models like ov42gl) reject the "wrong" endpoint
        for their account with other codes too (e.g. -6 "invalid config for
        fds"), and there's no complete list of which codes mean "wrong
        endpoint" vs. an actual dead object/session. Always trying both is
        more robust than chasing individual error codes.
        """
        obj = f"{self.user_id}/{did}/{map_name}"
        resp = self._try_map_url(server, obj, endpoint)
        if resp is not None:
            return resp

        alt = ("get_interim_file_url" if endpoint == "get_interim_file_url_pro"
               else "get_interim_file_url_pro")
        alt_resp = self._try_map_url(server, obj, alt)
        if alt_resp is not None:
            _LOGGER.debug("map_url: %s failed, succeeded with %s", endpoint, alt)
            return alt_resp
        return None

    def _try_map_url(self, server: str, obj_name: str, endpoint: str) -> str | None:
        resp = self._call(self._api_url(server) + f"/v2/home/{endpoint}",
                          {"data": f'{{"obj_name":"{obj_name}"}}'})
        try:
            return resp["result"]["url"]
        except (TypeError, KeyError):
            return None

    def download(self, url: str) -> bytes | None:
        r = self._s.get(url, timeout=15)
        return r.content if r.status_code == 200 else None


# --- crypto/util helpers ------------------------------------------------
def _agent() -> str:
    aid = "".join(chr(random.randint(65, 69)) for _ in range(13))
    rt = "".join(chr(random.randint(97, 122)) for _ in range(18))
    return f"{rt}-{aid} APP/com.xiaomi.mihome APPV/10.5.201"


def _to_json(text: str) -> dict:
    return json.loads(text.replace("&&&START&&&", ""))


def _enc_rc4(pw: str, payload: str) -> str:
    r = ARC4.new(base64.b64decode(pw))
    r.encrypt(bytes(1024))
    return base64.b64encode(r.encrypt(payload.encode())).decode()


def _dec_rc4(pw: str, payload: str) -> bytes:
    r = ARC4.new(base64.b64decode(pw))
    r.encrypt(bytes(1024))
    return r.encrypt(base64.b64decode(payload))


def _enc_sig(url: str, signed_nonce: str, params: dict) -> str:
    sp = ["POST", url.split("com")[1].replace("/app/", "/")]
    sp += [f"{k}={v}" for k, v in params.items()]
    sp.append(signed_nonce)
    return base64.b64encode(hashlib.sha1("&".join(sp).encode()).digest()).decode()
