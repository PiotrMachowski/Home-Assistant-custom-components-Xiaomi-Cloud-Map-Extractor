"""Decrypt a Xiaomi "version 2" JSON-enveloped cloud map blob.

Bypasses `vacuum_map_parser_xiaomi.aes_decryptor.decrypt()`, which is broken
for every model in `_XIAOMI_JSON_MAP_PROFILES` (map_parsers.py): it uses the
full MIoT model string (always 20 chars for this family, e.g.
"xiaomi.vacuum.ov42gl") directly as the AES key, which pycryptodome rejects
outright (`ValueError: Incorrect AES key length`). It also never unwraps the
`{"version":2,"data":"<base64>"}` envelope this cloud endpoint returns before
handing bytes to AES — it expects a bare hex-ciphertext string instead.

Reverse-engineered 2026-07-31 from the real Xiaomi Home Android app's
dynamically-downloaded RN plugin (`com.xiaomi.robovac` bundle, readable
un-minified crypto section): the AES key is derived from only the model
string's LAST 16 characters (`Device.model.slice(-16)` in the app's JS) —
exactly one AES-128 key length, unlike the raw 20-char string. Verified
against a real captured blob for xiaomi.vacuum.ov42gl (produced valid JSON
map data end to end).
"""
from __future__ import annotations

import base64
import hashlib
import json
import zlib

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

_IV = b"ABCDEF1234123412"


def decrypt_xiaomi_json_map(raw: bytes, model: str, device_id: str) -> str:
    """Decrypt+decompress a version-2 Xiaomi cloud map blob to its JSON text.

    `raw` is the exact bytes downloaded from the cloud map URL: a JSON
    envelope `{"version":2,"data":"<base64 ciphertext>"}`. Raises ValueError/
    KeyError/zlib.error/UnicodeDecodeError on anything that doesn't match
    this shape or fails to decrypt — callers should treat any exception here
    as "undecryptable blob", same as an upstream decrypt failure.
    """
    envelope = json.loads(raw)
    if envelope.get("version") != 2:
        raise ValueError(f"unsupported xiaomi map blob version: {envelope.get('version')!r}")

    ciphertext = base64.b64decode(envelope["data"])

    model_key = model[-16:].encode("latin1")
    original_work = model_key + device_id.encode("latin1")
    enc_key = AES.new(model_key, AES.MODE_CBC, _IV).encrypt(pad(original_work, AES.block_size))
    decrypt_key = hashlib.md5(enc_key).digest()

    plaintext = unpad(AES.new(decrypt_key, AES.MODE_CBC, _IV).decrypt(ciphertext), AES.block_size)
    return zlib.decompress(plaintext).decode("utf-8")
