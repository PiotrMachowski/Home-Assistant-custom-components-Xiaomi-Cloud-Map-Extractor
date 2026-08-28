"""Model to runtime profile registry.

See docs/dev/module-notes.md for design rationale and verification status.
"""

from __future__ import annotations

from .profiles.dreame import (
    DREAME_P2008,
    DREAME_P2009,
    DREAME_P2027,
    DREAME_P2036,
    DREAME_P2041,
    DREAME_P2114A,
    DREAME_P2114O,
    DREAME_P2149O,
    DREAME_P2150A,
    DREAME_R2205,
    DREAME_R2209,
    DREAME_R2210,
    DREAME_R2211O,
    DREAME_R2215,
    DREAME_R2216O,
    DREAME_R2228,
    DREAME_R2235A,
    DREAME_R2254,
    DREAME_R2257O,
)
from .profiles.ijai import (
    IJAI_V1,
    IJAI_V2,
    IJAI_V3,
    IJAI_V10,
    IJAI_V13,
    IJAI_V14,
    IJAI_V16,
    IJAI_V17,
)
from .profiles.roidmi import ROIDMI_R1B, ROIDMI_SDJ60, ROIDMI_V62
from .profiles.viomi import VIOMI_V12, VIOMI_V13, VIOMI_V15, VIOMI_V45
from .profiles.xiaomi import (
    XIAOMI_B106BK,
    XIAOMI_B108GL,
    XIAOMI_B112,
    XIAOMI_C101,
    XIAOMI_C101EU,
    XIAOMI_C102CN,
    XIAOMI_C104,
    XIAOMI_C107,
    XIAOMI_D101,
    XIAOMI_D102EV,
    XIAOMI_D102GL,
    XIAOMI_D109GL,
    XIAOMI_D110CH,
    XIAOMI_OV21GL,
    XIAOMI_OV42GL,
    XIAOMI_OV43GB,
    XIAOMI_OV71GL,
)
from .types import ModelProfile


MODEL_PROFILES: dict[str, ModelProfile] = {
    # --- ijai ---------------------------------------------------------------
    "ijai.vacuum.v1": IJAI_V1,
    "ijai.vacuum.v2": IJAI_V2,
    "ijai.vacuum.v3": IJAI_V3,
    "ijai.vacuum.v10": IJAI_V10,
    "ijai.vacuum.v13": IJAI_V13,
    "ijai.vacuum.v14": IJAI_V14,
    "ijai.vacuum.v15": IJAI_V14,  # Alias: spec-verified same layout as ijai.vacuum.v14.
    "ijai.vacuum.v16": IJAI_V16,
    "ijai.vacuum.v17": IJAI_V17,
    "ijai.vacuum.v18": IJAI_V17,  # Alias: spec-verified same layout as ijai.vacuum.v17.
    "ijai.vacuum.v19": IJAI_V17,  # Alias: spec-verified same layout as ijai.vacuum.v17.
    # --- xiaomi (ijai-engine rebrands) --------------------------------------
    "xiaomi.vacuum.b106bk": XIAOMI_B106BK,
    "xiaomi.vacuum.b106eu": XIAOMI_B106BK,  # Alias: spec-verified same layout as xiaomi.vacuum.b106bk.
    "xiaomi.vacuum.b108gl": XIAOMI_B108GL,
    "xiaomi.vacuum.b112": XIAOMI_B112,
    "xiaomi.vacuum.b112bk": XIAOMI_B112,  # Alias: spec-verified same layout as xiaomi.vacuum.b112.
    "xiaomi.vacuum.b112gl": XIAOMI_B112,  # Alias: spec-verified same layout as xiaomi.vacuum.b112.
    "xiaomi.vacuum.c101": XIAOMI_C101,
    "xiaomi.vacuum.c101eu": XIAOMI_C101EU,
    "xiaomi.vacuum.c102cn": XIAOMI_C102CN,
    "xiaomi.vacuum.c102gl": XIAOMI_C102CN,  # Alias: spec-verified same layout as xiaomi.vacuum.c102cn.
    "xiaomi.vacuum.c103": XIAOMI_C101,  # Alias: spec-verified same layout as xiaomi.vacuum.c101.
    "xiaomi.vacuum.c104": XIAOMI_C104,
    "xiaomi.vacuum.c107": XIAOMI_C107,
    "xiaomi.vacuum.d101": XIAOMI_D101,
    "xiaomi.vacuum.d102ev": XIAOMI_D102EV,
    "xiaomi.vacuum.d102gl": XIAOMI_D102GL,
    "xiaomi.vacuum.d103cn": XIAOMI_C102CN,  # Alias: spec-verified same layout as xiaomi.vacuum.c102cn.
    "xiaomi.vacuum.d106gl": XIAOMI_C101EU,  # Alias: spec-verified same layout as xiaomi.vacuum.c101eu.
    "xiaomi.vacuum.d109gl": XIAOMI_D109GL,
    "xiaomi.vacuum.d110ch": XIAOMI_D110CH,
    "xiaomi.vacuum.ov21gl": XIAOMI_OV21GL,
    "xiaomi.vacuum.ov42gl": XIAOMI_OV42GL,
    "xiaomi.vacuum.ov43gb": XIAOMI_OV43GB,
    "xiaomi.vacuum.ov71gl": XIAOMI_OV71GL,
    # --- viomi --------------------------------------------------------------
    "viomi.vacuum.v12": VIOMI_V12,
    "viomi.vacuum.v13": VIOMI_V13,
    "viomi.vacuum.v15": VIOMI_V15,
    "viomi.vacuum.v17": VIOMI_V15,  # Alias: spec-verified same layout as viomi.vacuum.v15.
    "viomi.vacuum.v18": VIOMI_V15,  # Alias: spec-verified same layout as viomi.vacuum.v15.
    "viomi.vacuum.v19": VIOMI_V13,  # Alias: spec-verified same layout as viomi.vacuum.v13.
    "viomi.vacuum.v22": VIOMI_V15,  # Alias: spec-verified same layout as viomi.vacuum.v15.
    "viomi.vacuum.v23": VIOMI_V15,  # Alias: spec-verified same layout as viomi.vacuum.v15.
    "viomi.vacuum.v24": VIOMI_V15,  # Alias: spec-verified same layout as viomi.vacuum.v15.
    "viomi.vacuum.v35": VIOMI_V13,  # Alias: spec-verified same layout as viomi.vacuum.v13.
    "viomi.vacuum.v38": VIOMI_V15,  # Alias: spec-verified same layout as viomi.vacuum.v15.
    "viomi.vacuum.v40": VIOMI_V15,  # Alias: spec-verified same layout as viomi.vacuum.v15.
    "viomi.vacuum.v45": VIOMI_V45,
    # --- roidmi -------------------------------------------------------------
    "roidmi.vacuum.r1b": ROIDMI_R1B,
    "roidmi.vacuum.sdj60": ROIDMI_SDJ60,
    "roidmi.vacuum.v60": ROIDMI_R1B,  # Alias: spec-verified same layout as roidmi.vacuum.r1b.
    "roidmi.vacuum.v62": ROIDMI_V62,
    "roidmi.vacuum.v66": ROIDMI_R1B,  # Alias: spec-verified same layout as roidmi.vacuum.r1b.
    # --- dreame (full rich caps: blob map / brush+filter+mop+detergent /
    #     vacuum-extend / clean-logs / do-not-disturb / audio) -----------------
    "dreame.vacuum.p2008": DREAME_P2008,
    "dreame.vacuum.p2009": DREAME_P2009,
    "dreame.vacuum.p2027": DREAME_P2027,
    "dreame.vacuum.p2028": DREAME_P2009,  # Alias: spec-verified same layout as dreame.vacuum.p2009.
    "dreame.vacuum.p2028a": DREAME_P2009,  # Alias: spec-verified same layout as dreame.vacuum.p2009.
    "dreame.vacuum.p2029": DREAME_P2009,  # Alias: spec-verified same layout as dreame.vacuum.p2009.
    "dreame.vacuum.p2036": DREAME_P2036,
    "dreame.vacuum.p2041": DREAME_P2041,
    "dreame.vacuum.p2041o": DREAME_P2041,  # Alias: spec-verified same layout as dreame.vacuum.p2041.
    "dreame.vacuum.p2114a": DREAME_P2114A,
    "dreame.vacuum.p2114o": DREAME_P2114O,
    "dreame.vacuum.p2140": DREAME_P2036,  # Alias: spec-verified same layout as dreame.vacuum.p2036.
    "dreame.vacuum.p2140a": DREAME_P2036,  # Alias: spec-verified same layout as dreame.vacuum.p2036.
    "dreame.vacuum.p2140o": DREAME_P2041,  # Alias: spec-verified same layout as dreame.vacuum.p2041.
    "dreame.vacuum.p2140p": DREAME_P2036,  # Alias: spec-verified same layout as dreame.vacuum.p2036.
    "dreame.vacuum.p2148o": DREAME_P2036,  # Alias: spec-verified same layout as dreame.vacuum.p2036.
    "dreame.vacuum.p2149o": DREAME_P2149O,
    "dreame.vacuum.p2150a": DREAME_P2150A,
    "dreame.vacuum.p2150b": DREAME_P2009,  # Alias: spec-verified same layout as dreame.vacuum.p2009.
    "dreame.vacuum.p2150o": DREAME_P2036,  # Alias: spec-verified same layout as dreame.vacuum.p2036.
    "dreame.vacuum.p2157": DREAME_P2036,  # Alias: spec-verified same layout as dreame.vacuum.p2036.
    "dreame.vacuum.p2187": DREAME_P2009,  # Alias: spec-verified same layout as dreame.vacuum.p2009.
    "dreame.vacuum.p2259": DREAME_P2009,  # Alias: spec-verified same layout as dreame.vacuum.p2009.
    "dreame.vacuum.r2104": DREAME_P2027,  # Alias: spec-verified same layout as dreame.vacuum.p2027.
    "dreame.vacuum.r2205": DREAME_R2205,
    "dreame.vacuum.r2209": DREAME_R2209,
    "dreame.vacuum.r2210": DREAME_R2210,
    "dreame.vacuum.r2211o": DREAME_R2211O,
    "dreame.vacuum.r2215": DREAME_R2215,
    "dreame.vacuum.r2216o": DREAME_R2216O,
    "dreame.vacuum.r2228": DREAME_R2228,
    "dreame.vacuum.r2228o": DREAME_R2215,  # Alias: spec-verified same layout as dreame.vacuum.r2215.
    "dreame.vacuum.r2228z": DREAME_R2215,  # Alias: spec-verified same layout as dreame.vacuum.r2215.
    "dreame.vacuum.r2232a": DREAME_R2215,  # Alias: spec-verified same layout as dreame.vacuum.r2215.
    "dreame.vacuum.r2233": DREAME_R2215,  # Alias: spec-verified same layout as dreame.vacuum.r2215.
    "dreame.vacuum.r2235": DREAME_R2215,  # Alias: spec-verified same layout as dreame.vacuum.r2215.
    "dreame.vacuum.r2235a": DREAME_R2235A,
    "dreame.vacuum.r2246": DREAME_R2215,  # Alias: spec-verified same layout as dreame.vacuum.r2215.
    "dreame.vacuum.r2247": DREAME_R2215,  # Alias: spec-verified same layout as dreame.vacuum.r2215.
    "dreame.vacuum.r2254": DREAME_R2254,
    "dreame.vacuum.r2257o": DREAME_R2257O,
    "dreame.vacuum.r2312": DREAME_R2235A,  # Alias: spec-verified same layout as dreame.vacuum.r2235a.
}


def get_profile(model: str) -> ModelProfile | None:
    return MODEL_PROFILES.get(model)


def card_baseline_gaps(profile: ModelProfile | None) -> tuple[str, ...]:
    """Return missing card-baseline features for a profile.

    Map rendering is best-effort and intentionally not gated here.
    """
    if profile is None:
        return ("profile",)
    core = profile.core
    if core is None:
        return ("core",)

    gaps: list[str] = []
    if core.status is None or not core.status_map:
        gaps.append("state")
    if core.start is None:
        gaps.append("start")
    if core.stop is None:
        gaps.append("stop")
    if core.charge is None:
        gaps.append("return_home")
    if core.battery is None:
        gaps.append("battery")
    if core.fan_speed is None or not core.fan_speeds:
        gaps.append("fan_speed")
    if core.water_level is None or not core.water_levels:
        gaps.append("water_level")
    if core.locate is None and core.alarm is None:
        gaps.append("locate")
    room = profile.room_clean
    has_simple_room_clean = (
        room is not None and room.start is not None and room.room_ids is not None
    )
    has_set_room_clean = (
        room is not None
        and room.set_room_clean is not None
        and room.clean_room_ids is not None
        and room.clean_room_mode is not None
        and room.clean_room_oper is not None
    )
    if not has_simple_room_clean and not has_set_room_clean:
        gaps.append("room_clean")
    return tuple(gaps)


def supports_card_baseline(profile: ModelProfile | None) -> bool:
    return not card_baseline_gaps(profile)


def is_supported(model: str) -> bool:
    """A model is onboardable iff it satisfies the bundled-card baseline.

    This keeps models that only partially resolve from creating an entry that
    renders a broken control surface.
    """
    return supports_card_baseline(get_profile(model))
