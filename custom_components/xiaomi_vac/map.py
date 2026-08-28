"""Fetch + decrypt + parse a vacuum map into a PNG and the plug-and-play
attribute contract the card consumes. Synchronous; run in an executor."""
from __future__ import annotations

import hashlib
import io
import logging
from dataclasses import dataclass, field

from PIL import Image, ImageChops
from vacuum_map_parser_base.config.color import ColorsPalette
from vacuum_map_parser_base.config.drawable import Drawable
from vacuum_map_parser_base.config.image_config import ImageConfig
from vacuum_map_parser_base.config.size import Sizes
from vacuum_map_parser_ijai.map_data_parser import IjaiMapDataParser

from . import map_vector
from .cloud.connector import XiaomiCloud
from .map_parsers import (
    dreame_decrypt_cloud_blob,
    dreame_extract_enckey,
    has_ijai_grid,
    make_parser,
    map_url_endpoint,
    unpack_kwargs,
)

# MIoT property that carries `<object_path>,<enckey>` for cloud-encrypted dreame maps.
# Verified against Tasshack's dreame-vacuum 2026-07-03 (siid=6/piid=3 = OBJECT_NAME).
_DREAME_ENCKEY_SIID = 6
_DREAME_ENCKEY_PIID = 3

_LOGGER = logging.getLogger(__name__)


def _patch_parse_rooms() -> None:
    """Work around an upstream crash on NON-ACTIVE maps (multi-map).

    `IjaiMapDataParser._parse_rooms` looks up the entry in `mapInfo` whose
    `mapHeadId` equals the active map's, purely to log its name. On a stored,
    non-active map that id matches nothing, so `current_map` is left unbound and
    the method raises `UnboundLocalError` BEFORE the room-naming loop runs —
    killing the whole parse. The naming loop itself reads `roomDataInfo` and does
    not need `current_map` at all, so we drop in a version that guards the lookup.
    Pinned dep (vacuum-map-parser-ijai==0.1.1); bug still present in 0.1.1,
    revisit if upstream fixes it.
    """
    parser_cls = IjaiMapDataParser

    @staticmethod
    def _parse_rooms(map_data_rooms: dict) -> None:
        rm = parser_cls.robot_map
        map_id = rm.mapHead.mapHeadId
        current_map = next((m for m in rm.mapInfo if m.mapHeadId == map_id), None)
        if current_map is not None:
            _LOGGER.debug("map#%d: %s", current_map.mapHeadId, current_map.mapName)
        for r in rm.roomDataInfo:
            if map_data_rooms is not None and r.roomId in map_data_rooms:
                map_data_rooms[r.roomId].name = r.roomName
                map_data_rooms[r.roomId].pos_x = r.roomNamePost.x
                map_data_rooms[r.roomId].pos_y = r.roomNamePost.y

    parser_cls._parse_rooms = _parse_rooms


_patch_parse_rooms()

_DRAWABLES = [
    Drawable.PATH, Drawable.CHARGER, Drawable.VACUUM_POSITION,
    Drawable.ROOM_NAMES, Drawable.NO_GO_AREAS, Drawable.VIRTUAL_WALLS,
]


class SessionExpired(Exception):
    """The cloud session no longer returns a map URL (token likely expired)."""


@dataclass
class MapResult:
    image_png: bytes
    attributes: dict
    vector: dict  # ACTIVE map's grid + vector overlays (back-compat)
    # Physical map id (mapHeadId) this render belongs to; None when the brand's
    # blob carries no id of its own (non-ijai — the coordinator's map-list
    # metadata is the id source of truth in that case).
    map_id: int | None = None
    # sha256 of the pre-render unpacked map bytes; lets the coordinator's cache
    # skip rewriting storage when a poll yields byte-identical content.
    content_hash: str | None = None
    # All maps the device lists, each a vector dict tagged with map_id/map_name/
    # active. Always contains at least the active map; extra entries appear only
    # when the device actually has more than one map.
    maps: list = field(default_factory=list)


def _od(obj):
    return obj.as_dict() if obj is not None else None


def _autocrop(img: Image.Image, pad: int = 20) -> tuple[Image.Image, int, int]:
    """Crop the uniform background margin off the map.

    Returns the cropped image and the (left, top) offset removed, so callers
    can shift pixel-space data (calibration points) to keep it aligned.
    """
    rgb = img.convert("RGB")
    bg = Image.new("RGB", rgb.size, rgb.getpixel((0, 0)))
    bbox = ImageChops.difference(rgb, bg).getbbox()
    if not bbox:
        return img, 0, 0
    left = max(0, bbox[0] - pad)
    top = max(0, bbox[1] - pad)
    right = min(img.width, bbox[2] + pad)
    bottom = min(img.height, bbox[3] + pad)
    return img.crop((left, top, right, bottom)), left, top


class MapFetcher:
    """Owns the map parser; pulls the active map and builds the contract."""

    def __init__(self, cloud: XiaomiCloud, *, server: str, user_id: str,
                 device_id: str, model: str, mac: str, wifi_sn: str, parser_brand: str):
        self._cloud = cloud
        self._server = server
        self._user_id = str(user_id)
        self._device_id = str(device_id)
        self._model = model
        self._mac = mac
        self._wifi_sn = wifi_sn
        self._brand = parser_brand
        self._parser = make_parser(
            self._brand, model, ColorsPalette(), Sizes(), _DRAWABLES, ImageConfig(), []
        )
        # Inputs for parser.unpack_map; the brand decides which are used.
        self._unpack_kw = unpack_kwargs(
            self._brand, wifi_sn=self._wifi_sn, owner_id=self._user_id,
            device_id=self._device_id, model=self._model, device_mac=self._mac,
        )
        self._endpoint = map_url_endpoint(self._brand)
        self._ijai_grid = has_ijai_grid(self._brand)
        # Dreame cloud enckey polled from siid=6/piid=3 on first fetch; None for
        # unencrypted models or until the property is successfully read.
        self._enckey: str | None = None
        self._enckey_polled = False

    def _get_dreame_enckey(self) -> str | None:
        """Poll siid=6/piid=3 for the dreame cloud map encryption key."""
        resp = self._cloud.cloud_get_prop(
            self._server, self._device_id, _DREAME_ENCKEY_SIID, _DREAME_ENCKEY_PIID)
        try:
            val = resp["result"][0]["value"]
            return dreame_extract_enckey(val)
        except (TypeError, KeyError, IndexError):
            return None

    def _unpack(self, raw: bytes) -> bytes:
        """Brand-dispatch: return decompressed map bytes ready for parser.parse().

        dreame with enckey: if the parser has a model-specific IV, delegate to
        parser.unpack_map (it applies AES-CBC with that IV). Otherwise use the
        Tasshack zero-IV chain via dreame_decrypt_cloud_blob.
        xiaomi: bypasses parser.unpack_map (vacuum_map_parser_xiaomi's own
        decrypt() is broken for this whole model family, see
        xiaomi_json_decrypt.py) and decrypts locally instead. Returns a JSON
        *string*, not bytes, same contract as the upstream decrypt() this
        replaces (parser.parse() only accepts str or dict).
        All other paths go through parser.unpack_map normally.
        """
        if self._brand == "dreame" and self._enckey is not None:
            from vacuum_map_parser_dreame.map_data_parser import DreameMapDataParser
            if DreameMapDataParser.IVs.get(self._model) is not None:
                return self._parser.unpack_map(raw, enckey=self._enckey)
            return dreame_decrypt_cloud_blob(raw, self._enckey)
        if self._brand == "xiaomi":
            from .xiaomi_json_decrypt import decrypt_xiaomi_json_map
            return decrypt_xiaomi_json_map(raw, self._model, self._device_id)
        return self._parser.unpack_map(raw, **self._unpack_kw)

    def fetch(self, slot: str = "0") -> MapResult | None:
        """Fetch + decrypt + parse one cloud upload slot ("0" or "1").

        Returns None for anything that isn't a readable render: an
        undecryptable ("Key B") blob, a corrupt/incomplete one, or an empty
        map. Raises SessionExpired when the cloud won't even hand back a URL
        (token likely dead) — the coordinator handles renewal.
        """
        if self._brand == "dreame" and not self._enckey_polled:
            self._enckey = self._get_dreame_enckey()
            self._enckey_polled = True
            _LOGGER.debug("dreame enckey poll: %s",
                          "found" if self._enckey else "not found (unencrypted or unavailable)")
        url = self._cloud.map_url(self._server, self._device_id, slot, self._endpoint)
        if not url:
            # No URL usually means the cloud session expired; let the
            # coordinator try a token refresh.
            raise SessionExpired()
        raw = self._cloud.download(url)
        if not raw:
            # Not per-slot actionable; the coordinator raises UpdateFailed when
            # every fallback (both slots + cache) comes up empty.
            _LOGGER.debug("Map download failed (slot %s)", slot)
            return None

        try:
            unpacked = self._unpack(raw)
        except Exception as ex:  # noqa: BLE001
            # Decrypt/decompress failed: a corrupt blob OR (routinely, per the
            # map-reliability plan) an undecryptable "Key B" blob at this slot.
            # Never crash the coordinator — it falls back to the other slot or
            # the cache. A stale dreame enckey also lands here: drop it so the
            # next fetch re-polls siid=6/piid=3.
            if self._brand == "dreame" and self._enckey is not None:
                _LOGGER.debug("dreame decrypt failed; will re-poll enckey next fetch: %s", ex)
                self._enckey = None
                self._enckey_polled = False
            _LOGGER.debug("Could not decrypt map at slot %s: %s", slot, ex)
            return None
        try:
            md = self._parser.parse(unpacked)
            vector = map_vector.vector_map(md, unpacked, ijai_grid=self._ijai_grid)
        except Exception as ex:  # noqa: BLE001
            # Decrypted fine but the parser rejected the frame (corrupt or
            # unexpected layout). The key material is good — keep the enckey.
            _LOGGER.debug("Parser rejected map frame at slot %s: %s", slot, ex)
            return None
        if md.image is None or md.image.is_empty:
            _LOGGER.debug("Parsed map at slot %s is empty", slot)
            return None

        cropped, off_x, off_y = _autocrop(md.image.data)
        buf = io.BytesIO()
        cropped.save(buf, format="PNG")

        # Shift calibration map-pixels by the cropped-away margin so the card
        # overlay still maps vacuum coordinates to the right place.
        calibration = md.calibration() or []
        for cp in calibration:
            cp["map"]["x"] -= off_x
            cp["map"]["y"] -= off_y

        attributes = {
            "calibration_points": calibration,
            "rooms": [{"id": rid, **r.as_dict()} for rid, r in (md.rooms or {}).items()],
            "charger": _od(md.charger),
            "vacuum_position": _od(md.vacuum_position),
            "vacuum_room": md.vacuum_room,
            "vacuum_room_name": md.vacuum_room_name,
            "zones": [_od(z) for z in (md.zones or [])],
            "no_go_areas": [_od(a) for a in (md.no_go_areas or [])],
            "no_mopping_areas": [_od(a) for a in (md.no_mopping_areas or [])],
            "walls": [_od(w) for w in (md.walls or [])],
            "image_width": cropped.width,
            "image_height": cropped.height,
        }
        return MapResult(
            image_png=buf.getvalue(),
            attributes=attributes,
            vector=vector,
            map_id=vector.get("map_id"),
            # xiaomi's _unpack returns a str (JSON text), every other brand bytes.
            content_hash=hashlib.sha256(
                unpacked.encode("utf-8") if isinstance(unpacked, str) else unpacked
            ).hexdigest(),
        )
