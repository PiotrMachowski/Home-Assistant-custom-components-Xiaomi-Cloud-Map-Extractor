"""Typed building blocks for runtime model profiles."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Prop:
    siid: int
    piid: int


@dataclass(frozen=True)
class Action:
    siid: int
    aiid: int
    in_piid: int | None = None
    # Some actions take several inputs (e.g. set-room-clean in[24,25,26]) or
    # return outputs. in_piid stays for the common single-input case.
    in_piids: tuple[int, ...] = ()
    out_piids: tuple[int, ...] = ()


@dataclass(frozen=True)
class PointZoneCapability:
    service: int
    zone_points: Prop
    target_point: Prop
    set_zone_point: Action
    start_zone_clean: Action
    start_point_clean: Action | None = None
    legacy_start_point_clean: Action | None = None
    pause_point_clean: Action | None = None
    pause_zone_clean: Action | None = None
    restrict_points: Prop | None = None
    set_virtual_wall: Action | None = None
    beauty_point: Prop | None = None
    set_beauty_wall: Action | None = None
    map_type: Prop | None = None


@dataclass(frozen=True)
class MapCapability:
    service: int
    map_num: Prop | None = None
    current_map_id: Prop | None = None
    get_map_list: Action | None = None
    upload_by_mapid: Action | None = None
    upload_by_mapid_ii: Action | None = None
    set_current_map: Action | None = None
    point_zone: PointZoneCapability | None = None
    # multi-map management
    map_list: Prop | None = None
    remember_state: Prop | None = None
    has_new_map: Prop | None = None
    del_map: Action | None = None
    rename_map: Action | None = None
    build_new_map: Action | None = None
    reset_map: Action | None = None
    # live trajectory
    current_path: Prop | None = None
    start_cleaning_point: Prop | None = None
    end_cleaning_point: Prop | None = None
    get_current_path: Action | None = None
    # rooms
    room_id_name_list: Prop | None = None
    split_points: Prop | None = None
    arrange_room_ids: Prop | None = None
    get_map_room_list: Action | None = None
    rename_room: Action | None = None
    arrange_room: Action | None = None
    split_room: Action | None = None
    mijia_room_list: Prop | None = None
    set_mijia_room_list: Action | None = None


@dataclass(frozen=True)
class RoomCleanCapability:
    room_ids: Prop | None = None
    start: Action | None = None
    # richer variant: explicit room ids + mode (global/edge) + operation
    clean_room_ids: Prop | None = None
    clean_room_mode: Prop | None = None
    clean_room_oper: Prop | None = None
    set_room_clean: Action | None = None


@dataclass(frozen=True)
class ScheduleCapability:
    """Timed/scheduled cleans (siid order)."""
    service: int
    # ijai adds via an `add` action; viomi's order service has only del/get and
    # schedules are written through the `orderdata` prop -> these stay None there.
    add: Action | None = None
    delete: Action | None = None
    get: Action | None = None
    add_iii: Action | None = None
    order_id: Prop | None = None
    enable: Prop | None = None
    day: Prop | None = None
    hour: Prop | None = None
    minute: Prop | None = None
    repeat: Prop | None = None
    clean_way: Prop | None = None
    suction: Prop | None = None
    water: Prop | None = None
    twice_clean: Prop | None = None
    mapid: Prop | None = None
    room_count: Prop | None = None
    room_data: Prop | None = None
    orderdata: Prop | None = None


@dataclass(frozen=True)
class SettingsCapability:
    """Read/write feature toggles and mop/drive controls."""
    mop_route: Prop | None = None
    shake_shift: Prop | None = None
    tank_shake: Prop | None = None
    direction: Prop | None = None
    dirt_recognize: Prop | None = None
    pet_recognize: Prop | None = None
    ai_recognize: Prop | None = None
    carpet_booster: Prop | None = None
    carpet_avoid: Prop | None = None
    map_encrypt: Prop | None = None
    multi_prop_vacuum: Prop | None = None


@dataclass(frozen=True)
class ConsumablesCapability:
    """Lifetime hours and accessory presence (siid sweep)."""
    side_brush_hours: Prop | None = None
    main_brush_hours: Prop | None = None
    hypa_hours: Prop | None = None
    mop_hours: Prop | None = None
    door_state: Prop | None = None
    cloth_state: Prop | None = None
    reset_consumable: Action | None = None


@dataclass(frozen=True)
class CleanHistoryCapability:
    """Last-clean record fields, carried by the clean-end event."""
    start_time: Prop | None = None
    use_time: Prop | None = None
    clean_area: Prop | None = None
    map_url: Prop | None = None
    clean_mode: Prop | None = None
    clean_way: Prop | None = None
    current_map: Prop | None = None
    task_status: Prop | None = None


@dataclass(frozen=True)
class DndCapability:
    """Do-not-disturb / quiet hours (siid disturb)."""
    service: int
    # ijai exposes a set-notdisturb action; viomi folds dnd props into its order
    # service with no dedicated action -> stays None there.
    set_notdisturb: Action | None = None
    enable: Prop | None = None
    start_hour: Prop | None = None
    start_minute: Prop | None = None
    end_hour: Prop | None = None
    end_minute: Prop | None = None
    timezone: Prop | None = None


@dataclass(frozen=True)
class VoiceCapability:
    """Voice-pack download/switch (siid language)."""
    service: int
    download_voice: Action
    get_download_status: Action | None = None
    target_voice: Prop | None = None
    cur_voice: Prop | None = None
    download_status: Prop | None = None
    download_progress: Prop | None = None
    voice_url: Prop | None = None


# --- dreame-native rich caps -------------------------------------------------
# dreame exposes its feature families on different services/types than ijai, so
# these mirror the ijai-shaped caps above but match dreame's MIoT vocabulary.
# All fields Optional; an absent member stays None. Nothing consumes these yet
# (only map/room_clean are read at runtime) — they carry the spec data forward
# for the per-brand map decode and card-parity baseline.


@dataclass(frozen=True)
class DreameMapCapability:
    """Blob-model map service (siid map): a single map-data blob fetched via
    map-req/update-map, not ijai's map-list catalogue."""
    service: int
    map_data: Prop | None = None
    frame_info: Prop | None = None
    object_name: Prop | None = None
    map_extend_data: Prop | None = None
    robot_time: Prop | None = None
    result_code: Prop | None = None
    mult_map_state: Prop | None = None
    mult_map_info: Prop | None = None
    map_req: Action | None = None
    update_map: Action | None = None


@dataclass(frozen=True)
class DreameConsumablesCapability:
    """Per-accessory life as percent + remaining time, each on its own service
    with a reset action (brush-cleaner x2 = main+side, filter, mop, detergent).
    Unlike ijai's lifetime-hours model. main/side brush split by service order
    (first brush-cleaner instance = main); the two carry identical labels so the
    split is by siid, not hardware-verified."""
    main_brush_life: Prop | None = None
    main_brush_left_time: Prop | None = None
    reset_main_brush: Action | None = None
    side_brush_life: Prop | None = None
    side_brush_left_time: Prop | None = None
    reset_side_brush: Action | None = None
    filter_life: Prop | None = None
    filter_left_time: Prop | None = None
    reset_filter: Action | None = None
    mop_life: Prop | None = None
    mop_left_time: Prop | None = None
    reset_mop: Action | None = None
    detergent_life: Prop | None = None
    detergent_left_time: Prop | None = None
    reset_detergent: Action | None = None
    # dust-bag service (its own siid, e.g. xiaomi.ov42gl's siid 19): added
    # 2026-08-01 for a xiaomi-brand profile that reuses this dataclass's
    # percent+hours shape (not a dreame-only concept, just modeled here
    # first) — every other field stays untouched, so existing dreame
    # profiles are unaffected.
    dust_bag_life: Prop | None = None
    dust_bag_left_time: Prop | None = None
    reset_dust_bag: Action | None = None


@dataclass(frozen=True)
class DreameDndCapability:
    """Do-not-disturb (siid do-not-disturb): enable + single HH:MM start/end
    string props, no action."""
    service: int
    enable: Prop | None = None
    start_time: Prop | None = None
    end_time: Prop | None = None


@dataclass(frozen=True)
class DreameSettingsCapability:
    """vacuum-extend service: cleaning/mop modes + feature toggles. cleaning_mode
    (suction) and mop_mode (water) also feed the dreame fan/water selects in the
    card-parity baseline.

    cleaning_mode duplicates core.fan_speed and mop_mode duplicates
    core.water_level in every dreame profile (verified 02-07-2026): the
    runtime intentionally drives fan/water via core.* only, and these fields
    stay as spec mirrors (see tests/pure/test_dreame_redundancy.py)."""
    service: int
    cleaning_mode: Prop | None = None
    mop_mode: Prop | None = None
    waterbox_status: Prop | None = None
    task_status: Prop | None = None
    break_point_restart: Prop | None = None
    carpet_press: Prop | None = None
    child_lock: Prop | None = None


@dataclass(frozen=True)
class DreameCleanHistoryCapability:
    """Lifetime totals from the clean-logs service (not ijai's per-clean record)."""
    service: int
    first_clean_time: Prop | None = None
    total_clean_time: Prop | None = None
    total_clean_times: Prop | None = None
    total_clean_area: Prop | None = None


@dataclass(frozen=True)
class DreameAudioCapability:
    """audio service: voice-pack props + locate (position) / play-sound. Carries
    the dreame locate path (ijai locates via the alarm prop).

    locate duplicates core.locate in every dreame profile that has it
    (verified 02-07-2026): the runtime drives locate via core.locate only,
    and this field stays as a spec mirror (see
    tests/pure/test_dreame_redundancy.py)."""
    service: int
    voice_packet_id: Prop | None = None
    voice_change_state: Prop | None = None
    set_voice: Prop | None = None
    locate: Action | None = None
    play_sound: Action | None = None


@dataclass(frozen=True)
class DreameScheduleCapability:
    """Scheduled cleans on the time service: timer blob + delete action."""
    service: int
    time_zone: Prop | None = None
    timer_clean: Prop | None = None
    timer_id: Prop | None = None
    delete_timer: Action | None = None


@dataclass(frozen=True)
class CoreCapability:
    """Core vacuum service: live telemetry, controls, and their value tables.

    Lean by design (decision 2026-06-25): consumable life and clean-area/time
    are NOT carried here — they come from ConsumablesCapability /
    CleanHistoryCapability and are parked ("coming soon") at launch. A field is
    ``None``/empty when the model's spec lacks it; entities are built per what
    exists. ``core is None`` on a profile = rich-reference only, not runnable.
    """
    # telemetry props (None = this model lacks it)
    status: Prop | None = None
    fault: Prop | None = None
    mode: Prop | None = None
    battery: Prop | None = None
    charging_state: Prop | None = None   # dreame has it, ijai does not
    fan_speed: Prop | None = None
    water_level: Prop | None = None
    sweep_type: Prop | None = None       # dreame has none -> stays None
    repeat: Prop | None = None
    alarm: Prop | None = None
    volume: Prop | None = None
    # actions
    start: Action | None = None
    stop: Action | None = None
    pause: Action | None = None          # real pause; None -> caller falls back to stop
    charge: Action | None = None
    locate: Action | None = None
    # value tables (empty = entity not built for this model)
    status_map: dict[int, str] = field(default_factory=dict)   # raw int -> HA activity
    fan_speeds: dict[str, int] = field(default_factory=dict)    # label -> raw
    water_levels: dict[str, int] = field(default_factory=dict)
    modes: dict[str, int] = field(default_factory=dict)
    sweep_types: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelProfile:
    profile_id: str
    brand: str
    core: CoreCapability | None = None
    # Each rich slot holds whichever brand shape the spec mapped (ijai-shaped or
    # the dreame-native variant); consumers isinstance-check where they care.
    map: MapCapability | DreameMapCapability | None = None
    room_clean: RoomCleanCapability | None = None
    schedule: ScheduleCapability | DreameScheduleCapability | None = None
    settings: SettingsCapability | DreameSettingsCapability | None = None
    consumables: ConsumablesCapability | DreameConsumablesCapability | None = None
    clean_history: CleanHistoryCapability | DreameCleanHistoryCapability | None = None
    dnd: DndCapability | DreameDndCapability | None = None
    voice: VoiceCapability | DreameAudioCapability | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)
    # Cap on properties per get_properties call; None = send all at once.
    # Set to a small value for devices that reject large batches.
    max_properties: int | None = None
