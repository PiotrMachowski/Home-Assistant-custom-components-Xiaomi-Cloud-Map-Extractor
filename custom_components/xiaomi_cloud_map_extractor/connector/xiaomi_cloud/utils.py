import base64
import hashlib
import hmac
import json
import os
import random

from Crypto.Cipher import ARC4


def generate_nonce(millis: int):
    nonce_bytes = os.urandom(8) + (int(millis / 60000)).to_bytes(4, byteorder='big')
    return base64.b64encode(nonce_bytes).decode()


def generate_agent() -> str:
    agent_id = "".join(
        map(lambda i: chr(i), [random.randint(65, 69) for _ in range(13)])
    )
    random_text = "".join(map(lambda i: chr(i), [random.randint(97, 122) for _ in range(18)]))
    return f"{random_text}-{agent_id} APP/com.xiaomi.mihome APPV/10.5.201"


def generate_device_id() -> str:
    return "".join((chr(random.randint(97, 122)) for _ in range(6)))


def generate_signature(url, signed_nonce: str, nonce: str, params: dict[str, str]) -> str:
    signature_params = [url.split("com")[1], signed_nonce, nonce]
    for k, v in params.items():
        signature_params.append(f"{k}={v}")
    signature_string = "&".join(signature_params)
    signature = hmac.new(base64.b64decode(signed_nonce), msg=signature_string.encode(), digestmod=hashlib.sha256)
    return base64.b64encode(signature.digest()).decode()


def generate_enc_signature(url, method: str, signed_nonce: str, params: dict[str, str]) -> str:
    signature_params = [str(method).upper(), url.split("com")[1].replace("/app/", "/")]
    for k, v in params.items():
        signature_params.append(f"{k}={v}")
    signature_params.append(signed_nonce)
    signature_string = "&".join(signature_params)
    return base64.b64encode(hashlib.sha1(signature_string.encode('utf-8')).digest()).decode()


def generate_enc_params(url: str, method: str, signed_nonce: str, nonce: str, params: dict[str, str],
                        ssecurity: str) -> dict[str, str]:
    params['rc4_hash__'] = generate_enc_signature(url, method, signed_nonce, params)
    for k, v in params.items():
        params[k] = encrypt_rc4(signed_nonce, v)
    params.update({
        'signature': generate_enc_signature(url, method, signed_nonce, params),
        'ssecurity': ssecurity,
        '_nonce': nonce,
    })
    return params


def to_json(response_text: str) -> any:
    return json.loads(response_text.replace("&&&START&&&", ""))


def encrypt_rc4(password: str, payload: str) -> str:
    r = ARC4.new(base64.b64decode(password))
    r.encrypt(bytes(1024))
    return base64.b64encode(r.encrypt(payload.encode())).decode()


def decrypt_rc4(password: str, payload: str) -> bytes:
    r = ARC4.new(base64.b64decode(password))
    r.encrypt(bytes(1024))
    return r.encrypt(base64.b64decode(payload))
