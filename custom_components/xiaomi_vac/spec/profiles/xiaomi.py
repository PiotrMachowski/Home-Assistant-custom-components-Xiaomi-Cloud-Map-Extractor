"""Xiaomi runtime profiles.

See docs/dev/module-notes.md for design rationale and verification status.
"""

from __future__ import annotations

from dataclasses import replace

from ..types import (
    Action,
    CleanHistoryCapability,
    ConsumablesCapability,
    CoreCapability,
    DndCapability,
    DreameConsumablesCapability,
    MapCapability,
    ModelProfile,
    PointZoneCapability,
    Prop,
    RoomCleanCapability,
    ScheduleCapability,
    SettingsCapability,
    VoiceCapability,
)


# --- Cores ------------------------------------------------------------------
# xiaomi is an ijai-engine rebrand: same siid/piid wiring as ijai but distinct
# label text per model, so no core is shared with ijai. d110ch shares C102CN's
# rich layout but a distinct core (different alarm/volume slots) -> split out.

# c101/c101eu/c103/d106gl
XIAOMI_CORE_C101 = CoreCapability(
    status=Prop(2, 1),
    fault=Prop(2, 2),
    mode=Prop(2, 4),
    battery=Prop(3, 1),
    fan_speed=Prop(7, 5),
    water_level=Prop(7, 6),
    sweep_type=Prop(2, 8),
    repeat=Prop(7, 1),
    alarm=Prop(4, 1),
    volume=Prop(4, 2),
    start=Action(2, 1),
    stop=Action(2, 2),
    charge=Action(3, 1),
    status_map={0: 'idle', 1: 'idle', 2: 'paused', 3: 'returning', 4: 'docked', 5: 'cleaning', 6: 'cleaning', 7: 'cleaning', 8: 'idle'},
    fan_speeds={'silent': 0, 'standard': 1, 'medium': 2, 'turbo': 3},
    water_levels={'low': 0, 'mid': 1, 'hig': 2},
    modes={'sweep': 0, 'sweep_and_mop': 1, 'mop': 2, 'sweep_then_mop': 3},
    sweep_types={'global': 0, 'mop': 1, 'edge': 2, 'area': 3, 'point': 4, 'remote': 5, 'explore': 6, 'room': 7, 'floor': 8},
)

# b106bk/b106eu/c104
XIAOMI_CORE_B106BK = CoreCapability(
    status=Prop(2, 1),
    fault=Prop(2, 2),
    mode=Prop(2, 4),
    battery=Prop(3, 1),
    fan_speed=Prop(7, 5),
    water_level=Prop(7, 6),
    sweep_type=Prop(2, 8),
    repeat=Prop(7, 1),
    alarm=Prop(4, 1),
    volume=Prop(4, 2),
    start=Action(2, 1),
    stop=Action(2, 2),
    charge=Action(3, 1),
    status_map={0: 'idle', 1: 'idle', 2: 'paused', 3: 'returning', 4: 'docked', 5: 'cleaning', 6: 'cleaning', 7: 'cleaning', 8: 'idle'},
    fan_speeds={'slient': 0, 'standard': 1, 'medium': 2, 'turbo': 3},
    water_levels={'low': 0, 'mid': 1, 'high': 2},
    modes={'sweep': 0, 'sweepandmop': 1, 'mop': 2},
    sweep_types={'global': 0, 'mop': 1, 'corner': 2, 'area': 3, 'point': 4, 'man': 5, 'explore': 6, 'roomprefer': 7, 'materialprefer': 8},
)

# b112/b112bk/b112gl
XIAOMI_CORE_B112 = CoreCapability(
    status=Prop(2, 1),
    fault=Prop(2, 2),
    mode=Prop(2, 4),
    battery=Prop(3, 1),
    fan_speed=Prop(7, 5),
    water_level=Prop(7, 6),
    sweep_type=Prop(2, 8),
    repeat=Prop(7, 1),
    alarm=Prop(4, 1),
    volume=Prop(4, 2),
    start=Action(2, 1),
    stop=Action(2, 2),
    charge=Action(3, 1),
    status_map={0: 'idle', 1: 'idle', 2: 'paused', 3: 'returning', 4: 'docked', 5: 'cleaning', 6: 'cleaning', 7: 'cleaning', 8: 'idle'},
    fan_speeds={'close': 0, 'one': 1, 'two': 2, 'three': 3, 'forth': 4},
    water_levels={'close': 0, 'one': 1, 'two': 2, 'three': 3},
    modes={'sweep': 0, 'sweep_and_mop': 1, 'mop': 2},
    sweep_types={'global': 0, 'edge': 2, 'point': 4, 'remote': 5},
)

# c102cn/c102gl/d103cn — lean core (no fan/water/sweep value tables in spec).
XIAOMI_CORE_C102CN = CoreCapability(
    status=Prop(2, 1),
    fault=Prop(2, 2),
    mode=Prop(2, 3),
    battery=Prop(3, 1),
    start=Action(2, 1),
    stop=Action(2, 2),
    charge=Action(3, 1),
    status_map={1: 'idle', 2: 'paused', 3: 'returning', 4: 'docked', 5: 'cleaning', 6: 'cleaning', 7: 'cleaning', 8: 'idle'},
    modes={'silent': 0, 'basic': 1, 'strong': 2, 'full_speed': 3},
)

# b108gl — mode/sweep on siid 2 (different slots than the b/c-engine).
XIAOMI_CORE_B108GL = CoreCapability(
    status=Prop(2, 1),
    fault=Prop(2, 2),
    mode=Prop(2, 16),
    battery=Prop(3, 1),
    sweep_type=Prop(2, 4),
    alarm=Prop(4, 1),
    volume=Prop(4, 2),
    start=Action(2, 1),
    stop=Action(2, 2),
    charge=Action(3, 1),
    status_map={1: 'idle', 2: 'paused', 3: 'returning', 4: 'docked', 5: 'cleaning', 6: 'cleaning', 7: 'cleaning', 8: 'idle'},
    modes={'silent': 1, 'basic': 2, 'strong': 3},
    sweep_types={'global': 1, 'maping': 5, 'gocharging': 6, 'remotecontrol': 7, 'selectroom': 8, 'customclean': 9, 'area': 4},
)

# d110ch — shares C102CN's rich layout but alarm/volume live on siid 22.
XIAOMI_CORE_D110CH = CoreCapability(
    status=Prop(2, 1),
    fault=Prop(2, 2),
    mode=Prop(2, 3),
    battery=Prop(3, 1),
    alarm=Prop(22, 1),
    volume=Prop(22, 2),
    start=Action(2, 1),
    stop=Action(2, 2),
    charge=Action(3, 1),
    status_map={1: 'idle', 2: 'paused', 3: 'returning', 4: 'docked', 5: 'cleaning', 6: 'cleaning', 7: 'cleaning', 8: 'idle'},
    modes={'silent': 0, 'basic': 1, 'strong': 2, 'full_speed': 3},
)


# xiaomi.vacuum.b106bk, xiaomi.vacuum.b106eu
XIAOMI_B106BK = ModelProfile(
    profile_id='xiaomi.b106bk',
    brand='xiaomi',
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:xiaomi-b106bk:1",),
    core=XIAOMI_CORE_B106BK,
    map=MapCapability(
        service=10,
        map_num=Prop(10, 3),
        current_map_id=Prop(10, 2),
        get_map_list=Action(10, 1, out_piids=(4,)),
        upload_by_mapid=Action(10, 2, in_piid=6, out_piids=(6, 7, 18)),
        upload_by_mapid_ii=Action(10, 14, in_piid=6, out_piids=(6, 7, 18, 21)),
        set_current_map=Action(10, 3, in_piid=6),
        point_zone=PointZoneCapability(
            service=9,
            zone_points=Prop(9, 2),
            target_point=Prop(9, 5),
            set_zone_point=Action(9, 8, in_piid=2, out_piids=(7, 8, 9)),
            start_zone_clean=Action(9, 3),
            start_point_clean=Action(9, 9, in_piid=5, out_piids=(7, 8, 9)),
            legacy_start_point_clean=Action(9, 1),
            pause_point_clean=Action(9, 2, in_piid=4),
            pause_zone_clean=Action(9, 4, in_piid=4),
            restrict_points=Prop(9, 3),
            set_virtual_wall=Action(9, 6, in_piid=3, out_piids=(7, 8, 9)),
            beauty_point=Prop(9, 6),
            set_beauty_wall=Action(9, 5, in_piid=6, out_piids=(7, 8, 9)),
            map_type=Prop(9, 8),
        ),
        map_list=Prop(10, 4),
        remember_state=Prop(10, 1),
        has_new_map=Prop(10, 19),
        del_map=Action(10, 4, in_piid=6),
        rename_map=Action(10, 5, in_piids=(6, 8)),
        build_new_map=Action(10, 11, in_piid=14),
        reset_map=Action(10, 10),
        current_path=Prop(10, 5),
        start_cleaning_point=Prop(10, 15),
        end_cleaning_point=Prop(10, 16),
        get_current_path=Action(10, 12, in_piids=(15, 16), out_piids=(5,)),
        room_id_name_list=Prop(10, 17),
        split_points=Prop(10, 12),
        arrange_room_ids=Prop(10, 11),
        get_map_room_list=Action(10, 13, in_piid=2, out_piids=(17,)),
        rename_room=Action(10, 7, in_piids=(6, 9, 10), out_piids=(6, 7, 18)),
        arrange_room=Action(10, 8, in_piids=(6, 11, 13), out_piids=(6, 7, 18)),
        split_room=Action(10, 9, in_piids=(6, 9, 12, 13), out_piids=(6, 7, 18)),
        mijia_room_list=Prop(10, 22),
        set_mijia_room_list=Action(10, 18, in_piids=(6, 22)),
    ),
    room_clean=RoomCleanCapability(
        room_ids=Prop(2, 10),
        start=Action(2, 7, in_piid=10),
        clean_room_ids=Prop(7, 24),
        clean_room_mode=Prop(7, 25),
        clean_room_oper=Prop(7, 26),
        set_room_clean=Action(7, 3, in_piids=(24, 25, 26)),
    ),
    schedule=ScheduleCapability(
        service=8,
        add=Action(8, 1, in_piids=(1, 2, 3, 4, 5, 6, 11, 14, 12, 16)),
        delete=Action(8, 2, in_piid=1),
        get=Action(8, 3, out_piids=(15,)),
        add_iii=Action(8, 6, in_piids=(1, 2, 3, 4, 5, 6, 11, 12, 14, 16, 17, 19), out_piids=(20,)),
        order_id=Prop(8, 1),
        enable=Prop(8, 2),
        day=Prop(8, 3),
        hour=Prop(8, 4),
        minute=Prop(8, 5),
        repeat=Prop(8, 6),
        clean_way=Prop(8, 7),
        suction=Prop(8, 8),
        water=Prop(8, 9),
        twice_clean=Prop(8, 10),
        mapid=Prop(8, 11),
        room_count=Prop(8, 12),
        room_data=Prop(8, 13),
        orderdata=Prop(8, 15),
    ),
    settings=SettingsCapability(
        mop_route=Prop(7, 7),
        shake_shift=Prop(7, 50),
        tank_shake=Prop(7, 48),
        direction=Prop(7, 16),
        dirt_recognize=Prop(7, 35),
        pet_recognize=Prop(7, 36),
        ai_recognize=Prop(7, 42),
        carpet_booster=Prop(7, 44),
        carpet_avoid=Prop(7, 47),
        map_encrypt=Prop(7, 55),
        multi_prop_vacuum=Prop(7, 45),
    ),
    consumables=ConsumablesCapability(
        side_brush_hours=Prop(7, 9),
        main_brush_hours=Prop(7, 11),
        hypa_hours=Prop(7, 13),
        mop_hours=Prop(7, 15),
        door_state=Prop(7, 3),
        cloth_state=Prop(7, 4),
        reset_consumable=Action(7, 1, in_piid=17),
    ),
    clean_history=CleanHistoryCapability(
        start_time=Prop(7, 27),
        use_time=Prop(7, 28),
        clean_area=Prop(7, 29),
        map_url=Prop(7, 30),
        clean_mode=Prop(7, 31),
        clean_way=Prop(7, 32),
        current_map=Prop(7, 33),
        task_status=Prop(7, 37),
    ),
    dnd=DndCapability(
        service=12,
        set_notdisturb=Action(12, 1, in_piids=(1, 2, 3, 4, 5, 6)),
        enable=Prop(12, 1),
        start_hour=Prop(12, 2),
        start_minute=Prop(12, 3),
        end_hour=Prop(12, 4),
        end_minute=Prop(12, 5),
        timezone=Prop(12, 6),
    ),
    voice=VoiceCapability(
        service=14,
        download_voice=Action(14, 1, in_piids=(1, 5, 6)),
        get_download_status=Action(14, 2, out_piids=(1, 2, 3, 4)),
        target_voice=Prop(14, 1),
        cur_voice=Prop(14, 2),
        download_status=Prop(14, 3),
        download_progress=Prop(14, 4),
        voice_url=Prop(14, 5),
    ),
)

# xiaomi.vacuum.b108gl
XIAOMI_B108GL = ModelProfile(
    profile_id='xiaomi.b108gl',
    brand='xiaomi',
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:xiaomi-b108gl:1",),
    core=XIAOMI_CORE_B108GL,
    voice=VoiceCapability(
        service=14,
        download_voice=Action(14, 1, in_piids=(1, 5, 6)),
        get_download_status=Action(14, 2, out_piids=(1, 2, 3, 4)),
        target_voice=Prop(14, 1),
        cur_voice=Prop(14, 2),
        download_status=Prop(14, 3),
        download_progress=Prop(14, 4),
        voice_url=Prop(14, 5),
    ),
)

# xiaomi.vacuum.b112, xiaomi.vacuum.b112bk, xiaomi.vacuum.b112gl
XIAOMI_B112 = ModelProfile(
    profile_id='xiaomi.b112',
    brand='xiaomi',
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:xiaomi-b112:1",),
    core=XIAOMI_CORE_B112,
    map=MapCapability(
        service=10,
        map_num=Prop(10, 3),
        current_map_id=Prop(10, 2),
        get_map_list=Action(10, 1, out_piids=(4,)),
        upload_by_mapid=Action(10, 2, in_piid=6, out_piids=(6, 7, 18)),
        upload_by_mapid_ii=Action(10, 14, in_piid=6, out_piids=(6, 7, 18, 21)),
        set_current_map=Action(10, 3, in_piid=6),
        point_zone=PointZoneCapability(
            service=9,
            zone_points=Prop(9, 2),
            target_point=Prop(9, 5),
            set_zone_point=Action(9, 8, in_piid=2, out_piids=(7, 8, 9)),
            start_zone_clean=Action(9, 3),
            legacy_start_point_clean=Action(9, 1),
            pause_point_clean=Action(9, 2, in_piid=4),
            pause_zone_clean=Action(9, 4, in_piid=4),
            restrict_points=Prop(9, 3),
            set_virtual_wall=Action(9, 6, in_piid=3, out_piids=(7, 8, 9)),
            beauty_point=Prop(9, 6),
            set_beauty_wall=Action(9, 5, in_piid=6, out_piids=(7, 8, 9)),
            map_type=Prop(9, 8),
        ),
        map_list=Prop(10, 4),
        remember_state=Prop(10, 1),
        has_new_map=Prop(10, 19),
        del_map=Action(10, 4, in_piid=6),
        rename_map=Action(10, 5, in_piids=(6, 8)),
        build_new_map=Action(10, 11, in_piid=14),
        reset_map=Action(10, 10),
        current_path=Prop(10, 5),
        start_cleaning_point=Prop(10, 15),
        end_cleaning_point=Prop(10, 16),
        get_current_path=Action(10, 12, in_piids=(15, 16), out_piids=(5,)),
        room_id_name_list=Prop(10, 17),
        split_points=Prop(10, 12),
        arrange_room_ids=Prop(10, 11),
        get_map_room_list=Action(10, 13, in_piid=2, out_piids=(17,)),
        rename_room=Action(10, 7, in_piids=(6, 9, 10), out_piids=(6, 7, 18)),
        arrange_room=Action(10, 8, in_piids=(6, 11, 13), out_piids=(6, 7, 18)),
        split_room=Action(10, 9, in_piids=(6, 9, 12, 13), out_piids=(6, 7, 18)),
    ),
    schedule=ScheduleCapability(
        service=8,
        add=Action(8, 1, in_piids=(1, 2, 3, 4, 5, 6, 11, 14, 12, 7, 8, 9, 17, 19)),
        delete=Action(8, 2, in_piid=1),
        get=Action(8, 3, out_piids=(15,)),
        order_id=Prop(8, 1),
        enable=Prop(8, 2),
        day=Prop(8, 3),
        hour=Prop(8, 4),
        minute=Prop(8, 5),
        repeat=Prop(8, 6),
        clean_way=Prop(8, 7),
        suction=Prop(8, 8),
        water=Prop(8, 9),
        twice_clean=Prop(8, 10),
        mapid=Prop(8, 11),
        room_count=Prop(8, 12),
        room_data=Prop(8, 13),
        orderdata=Prop(8, 15),
    ),
    settings=SettingsCapability(
        mop_route=Prop(7, 7),
        direction=Prop(7, 16),
        multi_prop_vacuum=Prop(7, 45),
    ),
    consumables=ConsumablesCapability(
        side_brush_hours=Prop(7, 9),
        main_brush_hours=Prop(7, 11),
        hypa_hours=Prop(7, 13),
        mop_hours=Prop(7, 15),
        door_state=Prop(7, 3),
        cloth_state=Prop(7, 4),
        reset_consumable=Action(7, 1, in_piid=17),
    ),
    clean_history=CleanHistoryCapability(
        start_time=Prop(7, 27),
        use_time=Prop(7, 28),
        clean_area=Prop(7, 29),
        map_url=Prop(7, 30),
        clean_mode=Prop(7, 31),
        clean_way=Prop(7, 32),
        current_map=Prop(7, 33),
        task_status=Prop(7, 37),
    ),
    dnd=DndCapability(
        service=12,
        set_notdisturb=Action(12, 1, in_piids=(1, 2, 3, 4, 5, 6)),
        enable=Prop(12, 1),
        start_hour=Prop(12, 2),
        start_minute=Prop(12, 3),
        end_hour=Prop(12, 4),
        end_minute=Prop(12, 5),
        timezone=Prop(12, 6),
    ),
    voice=VoiceCapability(
        service=14,
        download_voice=Action(14, 1, in_piids=(1, 5, 6)),
        get_download_status=Action(14, 2, out_piids=(1, 2, 3, 4)),
        target_voice=Prop(14, 1),
        cur_voice=Prop(14, 2),
        download_status=Prop(14, 3),
        download_progress=Prop(14, 4),
        voice_url=Prop(14, 5),
    ),
)

# xiaomi.vacuum.c101, xiaomi.vacuum.c103
XIAOMI_C101 = ModelProfile(
    profile_id='xiaomi.c101',
    brand='xiaomi',
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:xiaomi-c101:2",),
    core=XIAOMI_CORE_C101,
    map=MapCapability(
        service=10,
        map_num=Prop(10, 3),
        current_map_id=Prop(10, 2),
        get_map_list=Action(10, 1, out_piids=(4,)),
        upload_by_mapid=Action(10, 2, in_piid=6, out_piids=(6, 7, 18)),
        upload_by_mapid_ii=Action(10, 14, in_piid=6, out_piids=(6, 7, 18, 21)),
        set_current_map=Action(10, 3, in_piid=6),
        point_zone=PointZoneCapability(
            service=9,
            zone_points=Prop(9, 2),
            target_point=Prop(9, 5),
            set_zone_point=Action(9, 8, in_piid=2, out_piids=(7, 8, 9)),
            start_zone_clean=Action(9, 3),
            start_point_clean=Action(9, 9, in_piid=5, out_piids=(7, 8, 9)),
            legacy_start_point_clean=Action(9, 1),
            pause_point_clean=Action(9, 2, in_piid=4),
            pause_zone_clean=Action(9, 4, in_piid=4),
            restrict_points=Prop(9, 3),
            set_virtual_wall=Action(9, 6, in_piid=3, out_piids=(7, 8, 9)),
            beauty_point=Prop(9, 6),
            set_beauty_wall=Action(9, 5, in_piid=6, out_piids=(7, 8, 9)),
            map_type=Prop(9, 8),
        ),
        map_list=Prop(10, 4),
        remember_state=Prop(10, 1),
        has_new_map=Prop(10, 19),
        del_map=Action(10, 4, in_piid=6),
        rename_map=Action(10, 5, in_piids=(6, 8)),
        build_new_map=Action(10, 11, in_piid=14),
        reset_map=Action(10, 10),
        current_path=Prop(10, 5),
        start_cleaning_point=Prop(10, 15),
        end_cleaning_point=Prop(10, 16),
        get_current_path=Action(10, 12, in_piids=(15, 16), out_piids=(5,)),
        room_id_name_list=Prop(10, 17),
        split_points=Prop(10, 12),
        arrange_room_ids=Prop(10, 11),
        get_map_room_list=Action(10, 13, in_piid=2, out_piids=(17,)),
        rename_room=Action(10, 7, in_piids=(6, 9, 10), out_piids=(6, 7, 18)),
        split_room=Action(10, 9, in_piids=(6, 9, 12, 13), out_piids=(6, 7, 18)),
        mijia_room_list=Prop(10, 22),
        set_mijia_room_list=Action(10, 18, in_piids=(6, 22)),
    ),
    room_clean=RoomCleanCapability(
        room_ids=Prop(2, 10),
        start=Action(2, 7, in_piid=10),
        clean_room_ids=Prop(7, 24),
        clean_room_mode=Prop(7, 25),
        clean_room_oper=Prop(7, 26),
        set_room_clean=Action(7, 3, in_piids=(24, 25, 26)),
    ),
    schedule=ScheduleCapability(
        service=8,
        add=Action(8, 1, in_piids=(1, 2, 3, 4, 5, 6, 11, 14, 12, 16)),
        delete=Action(8, 2, in_piid=1),
        get=Action(8, 3, out_piids=(15,)),
        order_id=Prop(8, 1),
        enable=Prop(8, 2),
        day=Prop(8, 3),
        hour=Prop(8, 4),
        minute=Prop(8, 5),
        repeat=Prop(8, 6),
        clean_way=Prop(8, 7),
        suction=Prop(8, 8),
        water=Prop(8, 9),
        twice_clean=Prop(8, 10),
        mapid=Prop(8, 11),
        room_count=Prop(8, 12),
        room_data=Prop(8, 13),
        orderdata=Prop(8, 15),
    ),
    settings=SettingsCapability(
        mop_route=Prop(7, 7),
        shake_shift=Prop(7, 50),
        tank_shake=Prop(7, 48),
        direction=Prop(7, 16),
        dirt_recognize=Prop(7, 35),
        pet_recognize=Prop(7, 36),
        ai_recognize=Prop(7, 42),
        carpet_booster=Prop(7, 44),
        carpet_avoid=Prop(7, 47),
        map_encrypt=Prop(7, 55),
        multi_prop_vacuum=Prop(7, 45),
    ),
    consumables=ConsumablesCapability(
        side_brush_hours=Prop(7, 9),
        main_brush_hours=Prop(7, 11),
        hypa_hours=Prop(7, 13),
        mop_hours=Prop(7, 15),
        door_state=Prop(7, 3),
        cloth_state=Prop(7, 4),
        reset_consumable=Action(7, 1, in_piid=17),
    ),
    clean_history=CleanHistoryCapability(
        start_time=Prop(7, 27),
        use_time=Prop(7, 28),
        clean_area=Prop(7, 29),
        map_url=Prop(7, 30),
        clean_mode=Prop(7, 31),
        clean_way=Prop(7, 32),
        current_map=Prop(7, 33),
        task_status=Prop(7, 37),
    ),
    dnd=DndCapability(
        service=12,
        set_notdisturb=Action(12, 1, in_piids=(1, 2, 3, 4, 5, 6)),
        enable=Prop(12, 1),
        start_hour=Prop(12, 2),
        start_minute=Prop(12, 3),
        end_hour=Prop(12, 4),
        end_minute=Prop(12, 5),
        timezone=Prop(12, 6),
    ),
    voice=VoiceCapability(
        service=14,
        download_voice=Action(14, 1, in_piids=(1, 2), out_piids=(2,)),
        target_voice=Prop(14, 1),
        cur_voice=Prop(14, 2),
    ),
)

# xiaomi.vacuum.c101eu, xiaomi.vacuum.d106gl
XIAOMI_C101EU = ModelProfile(
    profile_id='xiaomi.c101eu',
    brand='xiaomi',
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:xiaomi-c101eu:2",),
    core=XIAOMI_CORE_C101,
    map=MapCapability(
        service=10,
        map_num=Prop(10, 3),
        current_map_id=Prop(10, 2),
        get_map_list=Action(10, 1, out_piids=(4,)),
        upload_by_mapid=Action(10, 2, in_piid=6, out_piids=(6, 7, 18)),
        upload_by_mapid_ii=Action(10, 14, in_piid=6, out_piids=(6, 7, 18, 21)),
        set_current_map=Action(10, 3, in_piid=6),
        point_zone=PointZoneCapability(
            service=9,
            zone_points=Prop(9, 2),
            target_point=Prop(9, 5),
            set_zone_point=Action(9, 8, in_piid=2, out_piids=(7, 8, 9)),
            start_zone_clean=Action(9, 3),
            start_point_clean=Action(9, 9, in_piid=5, out_piids=(7, 8, 9)),
            legacy_start_point_clean=Action(9, 1),
            pause_point_clean=Action(9, 2, in_piid=4),
            pause_zone_clean=Action(9, 4, in_piid=4),
            restrict_points=Prop(9, 3),
            set_virtual_wall=Action(9, 6, in_piid=3, out_piids=(7, 8, 9)),
            beauty_point=Prop(9, 6),
            set_beauty_wall=Action(9, 5, in_piid=6, out_piids=(7, 8, 9)),
            map_type=Prop(9, 8),
        ),
        map_list=Prop(10, 4),
        remember_state=Prop(10, 1),
        has_new_map=Prop(10, 19),
        del_map=Action(10, 4, in_piid=6),
        rename_map=Action(10, 5, in_piids=(6, 8)),
        build_new_map=Action(10, 11, in_piid=14),
        reset_map=Action(10, 10),
        current_path=Prop(10, 5),
        start_cleaning_point=Prop(10, 15),
        end_cleaning_point=Prop(10, 16),
        get_current_path=Action(10, 12, in_piids=(15, 16), out_piids=(5,)),
        room_id_name_list=Prop(10, 17),
        split_points=Prop(10, 12),
        arrange_room_ids=Prop(10, 11),
        get_map_room_list=Action(10, 13, in_piid=2, out_piids=(17,)),
        rename_room=Action(10, 7, in_piids=(6, 9, 10), out_piids=(6, 7, 18)),
        split_room=Action(10, 9, in_piids=(6, 9, 12, 13), out_piids=(6, 7, 18)),
        mijia_room_list=Prop(10, 22),
        set_mijia_room_list=Action(10, 18, in_piids=(6, 22)),
    ),
    room_clean=RoomCleanCapability(
        room_ids=Prop(2, 10),
        start=Action(2, 7, in_piid=10),
        clean_room_ids=Prop(7, 24),
        clean_room_mode=Prop(7, 25),
        clean_room_oper=Prop(7, 26),
        set_room_clean=Action(7, 3, in_piids=(24, 25, 26)),
    ),
    schedule=ScheduleCapability(
        service=8,
        add=Action(8, 1, in_piids=(1, 2, 3, 4, 5, 6, 11, 14, 12, 16)),
        delete=Action(8, 2, in_piid=1),
        get=Action(8, 3, out_piids=(15,)),
        order_id=Prop(8, 1),
        enable=Prop(8, 2),
        day=Prop(8, 3),
        hour=Prop(8, 4),
        minute=Prop(8, 5),
        repeat=Prop(8, 6),
        clean_way=Prop(8, 7),
        suction=Prop(8, 8),
        water=Prop(8, 9),
        twice_clean=Prop(8, 10),
        mapid=Prop(8, 11),
        room_count=Prop(8, 12),
        room_data=Prop(8, 13),
        orderdata=Prop(8, 15),
    ),
    settings=SettingsCapability(
        mop_route=Prop(7, 7),
        shake_shift=Prop(7, 50),
        tank_shake=Prop(7, 48),
        direction=Prop(7, 16),
        dirt_recognize=Prop(7, 35),
        pet_recognize=Prop(7, 36),
        ai_recognize=Prop(7, 42),
        carpet_booster=Prop(7, 44),
        carpet_avoid=Prop(7, 47),
        map_encrypt=Prop(7, 55),
        multi_prop_vacuum=Prop(7, 45),
    ),
    consumables=ConsumablesCapability(
        side_brush_hours=Prop(7, 9),
        main_brush_hours=Prop(7, 11),
        hypa_hours=Prop(7, 13),
        mop_hours=Prop(7, 15),
        door_state=Prop(7, 3),
        cloth_state=Prop(7, 4),
        reset_consumable=Action(7, 1, in_piid=17),
    ),
    clean_history=CleanHistoryCapability(
        start_time=Prop(7, 27),
        use_time=Prop(7, 28),
        clean_area=Prop(7, 29),
        map_url=Prop(7, 30),
        clean_mode=Prop(7, 31),
        clean_way=Prop(7, 32),
        current_map=Prop(7, 33),
        task_status=Prop(7, 37),
    ),
    dnd=DndCapability(
        service=12,
        set_notdisturb=Action(12, 1, in_piids=(1, 2, 3, 4, 5, 6)),
        enable=Prop(12, 1),
        start_hour=Prop(12, 2),
        start_minute=Prop(12, 3),
        end_hour=Prop(12, 4),
        end_minute=Prop(12, 5),
        timezone=Prop(12, 6),
    ),
    voice=VoiceCapability(
        service=14,
        download_voice=Action(14, 1, in_piids=(1, 5, 6)),
        get_download_status=Action(14, 2, out_piids=(1, 2, 3, 4)),
        target_voice=Prop(14, 1),
        cur_voice=Prop(14, 2),
        download_status=Prop(14, 3),
        download_progress=Prop(14, 4),
        voice_url=Prop(14, 5),
    ),
)

# xiaomi.vacuum.c102cn, xiaomi.vacuum.c102gl, xiaomi.vacuum.d103cn, xiaomi.vacuum.d110ch
XIAOMI_C102CN = ModelProfile(
    profile_id='xiaomi.c102cn',
    brand='xiaomi',
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:xiaomi-c102cn:1",),
    core=XIAOMI_CORE_C102CN,
    room_clean=RoomCleanCapability(
        room_ids=Prop(2, 4),
        start=Action(2, 3, in_piid=4),
    ),
)

# xiaomi.vacuum.c104
XIAOMI_C104 = ModelProfile(
    profile_id='xiaomi.c104',
    brand='xiaomi',
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:xiaomi-c104:2",),
    core=XIAOMI_CORE_B106BK,
    map=MapCapability(
        service=10,
        map_num=Prop(10, 3),
        current_map_id=Prop(10, 2),
        get_map_list=Action(10, 1, out_piids=(4,)),
        upload_by_mapid=Action(10, 2, in_piid=6, out_piids=(6, 7, 18)),
        upload_by_mapid_ii=Action(10, 14, in_piid=6, out_piids=(6, 7, 18, 21)),
        set_current_map=Action(10, 3, in_piid=6),
        point_zone=PointZoneCapability(
            service=9,
            zone_points=Prop(9, 2),
            target_point=Prop(9, 5),
            set_zone_point=Action(9, 8, in_piid=2, out_piids=(7, 8, 9)),
            start_zone_clean=Action(9, 3),
            start_point_clean=Action(9, 9, in_piid=5, out_piids=(7, 8, 9)),
            legacy_start_point_clean=Action(9, 1),
            pause_point_clean=Action(9, 2, in_piid=4),
            pause_zone_clean=Action(9, 4, in_piid=4),
            restrict_points=Prop(9, 3),
            set_virtual_wall=Action(9, 6, in_piid=3, out_piids=(7, 8, 9)),
            beauty_point=Prop(9, 6),
            set_beauty_wall=Action(9, 5, in_piid=6, out_piids=(7, 8, 9)),
            map_type=Prop(9, 8),
        ),
        map_list=Prop(10, 4),
        remember_state=Prop(10, 1),
        has_new_map=Prop(10, 19),
        del_map=Action(10, 4, in_piid=6),
        rename_map=Action(10, 5, in_piids=(6, 8)),
        build_new_map=Action(10, 11, in_piid=14),
        reset_map=Action(10, 10),
        current_path=Prop(10, 5),
        start_cleaning_point=Prop(10, 15),
        end_cleaning_point=Prop(10, 16),
        get_current_path=Action(10, 12, in_piids=(15, 16), out_piids=(5,)),
        room_id_name_list=Prop(10, 17),
        split_points=Prop(10, 12),
        arrange_room_ids=Prop(10, 11),
        get_map_room_list=Action(10, 13, in_piid=2, out_piids=(17,)),
        rename_room=Action(10, 7, in_piids=(6, 9, 10), out_piids=(6, 7, 18)),
        arrange_room=Action(10, 8, in_piids=(6, 11, 13), out_piids=(6, 7, 18)),
        split_room=Action(10, 9, in_piids=(6, 9, 12, 13), out_piids=(6, 7, 18)),
        mijia_room_list=Prop(10, 22),
        set_mijia_room_list=Action(10, 18, in_piids=(6, 22)),
    ),
    room_clean=RoomCleanCapability(
        room_ids=Prop(2, 10),
        start=Action(2, 7, in_piid=10),
        clean_room_ids=Prop(7, 24),
        clean_room_mode=Prop(7, 25),
        clean_room_oper=Prop(7, 26),
        set_room_clean=Action(7, 3, in_piids=(24, 25, 26)),
    ),
    schedule=ScheduleCapability(
        service=8,
        add=Action(8, 1, in_piids=(1, 2, 3, 4, 5, 6, 11, 14, 12, 16)),
        delete=Action(8, 2, in_piid=1),
        get=Action(8, 3, out_piids=(15,)),
        order_id=Prop(8, 1),
        enable=Prop(8, 2),
        day=Prop(8, 3),
        hour=Prop(8, 4),
        minute=Prop(8, 5),
        repeat=Prop(8, 6),
        clean_way=Prop(8, 7),
        suction=Prop(8, 8),
        water=Prop(8, 9),
        twice_clean=Prop(8, 10),
        mapid=Prop(8, 11),
        room_count=Prop(8, 12),
        room_data=Prop(8, 13),
        orderdata=Prop(8, 15),
    ),
    settings=SettingsCapability(
        mop_route=Prop(7, 7),
        shake_shift=Prop(7, 50),
        tank_shake=Prop(7, 48),
        direction=Prop(7, 16),
        dirt_recognize=Prop(7, 35),
        pet_recognize=Prop(7, 36),
        ai_recognize=Prop(7, 42),
        carpet_booster=Prop(7, 44),
        carpet_avoid=Prop(7, 47),
        map_encrypt=Prop(7, 55),
        multi_prop_vacuum=Prop(7, 45),
    ),
    consumables=ConsumablesCapability(
        side_brush_hours=Prop(7, 9),
        main_brush_hours=Prop(7, 11),
        hypa_hours=Prop(7, 13),
        mop_hours=Prop(7, 15),
        door_state=Prop(7, 3),
        cloth_state=Prop(7, 4),
        reset_consumable=Action(7, 1, in_piid=17),
    ),
    clean_history=CleanHistoryCapability(
        start_time=Prop(7, 27),
        use_time=Prop(7, 28),
        clean_area=Prop(7, 29),
        map_url=Prop(7, 30),
        clean_mode=Prop(7, 31),
        clean_way=Prop(7, 32),
        current_map=Prop(7, 33),
        task_status=Prop(7, 37),
    ),
    dnd=DndCapability(
        service=12,
        set_notdisturb=Action(12, 1, in_piids=(1, 2, 3, 4, 5, 6)),
        enable=Prop(12, 1),
        start_hour=Prop(12, 2),
        start_minute=Prop(12, 3),
        end_hour=Prop(12, 4),
        end_minute=Prop(12, 5),
        timezone=Prop(12, 6),
    ),
)

# xiaomi.vacuum.d110ch — identical RICH layout to C102CN, distinct core
# (alarm/volume on siid 22). Split so it doesn't inherit C102CN's slots.
XIAOMI_D110CH = replace(
    XIAOMI_C102CN,
    profile_id='xiaomi.d110ch',
    core=XIAOMI_CORE_D110CH,
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:xiaomi-d110ch:2",),
)

# ov21gl / ov71gl — new-generation layout: mode/fan_speed/water_level on siid 2
# (no siid 7 at all), charging_state on siid 3, alarm/volume on siid 4,
# locate on siid 6. ov71gl is byte-identical in every CoreCapability field.
# Map format: vacuum-map-parser-xiaomi (JSON). ov71gl/ov31gl/ov81gl/e101gb
# are explicitly listed in the upstream README (PiotrMachowski, verified
# 2026-07-03). ov21gl is absent from both parser READMEs but is assumed
# xiaomi-JSON by spec-generation family resemblance; see map_parsers.py.
# None of these are hardware-verified.
XIAOMI_CORE_OV21GL = CoreCapability(
    status=Prop(2, 2),
    fault=Prop(2, 3),
    mode=Prop(2, 4),
    sweep_type=Prop(2, 5),
    fan_speed=Prop(2, 9),
    water_level=Prop(2, 10),
    battery=Prop(3, 1),
    charging_state=Prop(3, 2),
    alarm=Prop(4, 1),
    volume=Prop(4, 2),
    start=Action(2, 1),
    stop=Action(2, 2),
    pause=Action(2, 7),
    charge=Action(3, 1),
    locate=Action(6, 1),
    status_map={
        1: 'idle',
        2: 'docked',
        3: 'docked',
        4: 'cleaning',
        5: 'paused',
        6: 'returning',
        7: 'returning',
        8: 'cleaning',
        9: 'docked',
        10: 'cleaning',
        11: 'idle',
        12: 'docked',
        13: 'returning',
        14: 'docked',
        15: 'error',
        16: 'cleaning',
        17: 'cleaning',
        18: 'paused',
        19: 'returning',
        20: 'returning',
        21: 'returning',
        22: 'cleaning',
        23: 'docked',
        24: 'returning',
    },
    fan_speeds={'silent': 1, 'basic': 2, 'strong': 3, 'full_speed': 4},
    water_levels={'off': 0, 'level1': 1, 'level2': 2, 'level3': 3},
    modes={'sweep': 1, 'mop': 2, 'sweep_mop': 3, 'sweep_before_mopping': 4},
    sweep_types={
        'global': 1,
        'zone': 2,
        'area': 3,
        'edge': 4,
        'costum': 5,
        'point': 6,
        'custom_area': 7,
        'appointment': 8,
        'linkage': 9,
        'fast': 10,
        'ai_hosting': 11,
    },
)

# xiaomi.vacuum.ov21gl
# No `map=` MapCapability: multi-map is unsupported by design for this
# generation — device.map_list() returns [] (see map_parsers.py / device.py).
# Consumables (2026-08-06): hardware-confirmed by a real ov21gl owner
# (letitbe-dull/xiaomi-vac#20 comment, tomasloksa) — this model has NO
# detergent/mop-solution-tank service at all; instead the mop PAD itself
# carries a life-level (siid 9), unlike ov42gl's separate detergent(18)+
# no-mop-pad layout. Do not copy this consumables block onto ov71gl/ov43gb
# (still unverified aliases, see the family-resemblance note above) without
# separate confirmation.
XIAOMI_OV21GL = ModelProfile(
    profile_id='xiaomi.ov21gl',
    brand='xiaomi',
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:xiaomi-ov21gl:2",),
    core=XIAOMI_CORE_OV21GL,
    room_clean=RoomCleanCapability(
        room_ids=Prop(2, 15),
        start=Action(2, 16, in_piid=15),
    ),
    consumables=DreameConsumablesCapability(
        main_brush_life=Prop(12, 1), main_brush_left_time=Prop(12, 2),
        side_brush_life=Prop(13, 1), side_brush_left_time=Prop(13, 2),
        filter_life=Prop(14, 1), filter_left_time=Prop(14, 2),
        mop_life=Prop(9, 1), mop_left_time=Prop(9, 2),
        dust_bag_life=Prop(19, 1), dust_bag_left_time=Prop(19, 2),
    ),
)

# xiaomi.vacuum.ov71gl — identical core spec layout to ov21gl, but consumables
# are unverified on this alias — explicitly cleared so it doesn't silently
# inherit ov21gl's hardware-confirmed siid/piid table via replace().
XIAOMI_OV71GL = replace(
    XIAOMI_OV21GL,
    profile_id='xiaomi.ov71gl',
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:xiaomi-ov71gl:1",),
    consumables=None,
)

# xiaomi.vacuum.ov43gb — identical core spec layout to ov21gl, consumables
# unverified (see ov71gl note above).
XIAOMI_OV43GB = replace(
    XIAOMI_OV21GL,
    profile_id='xiaomi.ov43gb',
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:xiaomi-ov43gb:2",),
    consumables=None,
)

# xiaomi.vacuum.ov42gl (Xiaomi Robot Vacuum H50 Pro) — identical spec layout
# to ov21gl. Unlike ov71gl/ov43gb (unverified aliases), this one is confirmed
# against a real device's spec cache AND the public MIoT spec DB: every
# siid/piid/aiid in the vendored ov42gl spec matches ov21gl's core exactly,
# and the public value-lists for status (all 24 codes), fan_speed (piid 2/9,
# despite the generic "mode" MIoT type), water_level (piid 2/10), mode
# (piid 2/4, "Sweep Mop Type"), and sweep_type (piid 2/5) match ov21gl's
# tables 1:1.
XIAOMI_OV42GL = replace(
    XIAOMI_OV21GL,
    profile_id='xiaomi.ov42gl',
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:xiaomi-ov42gl:2",),
    # Consumables (2026-08-01): read straight off the live device's own cached
    # MIoT spec (.storage/xiaomi_home/miot_specs/...xiaomi-ov42gl:1_en.dict),
    # hardware-confirmed for THIS model — not extended to ov71gl/ov43gb (only
    # aliased on spec-family grounds, unverified) or ov21gl. Main/side brush
    # are two separate brush-cleaner service instances (siid 12/13); filter
    # siid 14; detergent (mop-solution tank) siid 18; dust bag siid 19 — each
    # exposes life-level (piid 1, %) + left-time (piid 2 or 4, hours).
    consumables=DreameConsumablesCapability(
        main_brush_life=Prop(12, 1), main_brush_left_time=Prop(12, 2),
        side_brush_life=Prop(13, 1), side_brush_left_time=Prop(13, 2),
        filter_life=Prop(14, 1), filter_left_time=Prop(14, 2),
        detergent_life=Prop(18, 1), detergent_left_time=Prop(18, 4),
        dust_bag_life=Prop(19, 1), dust_bag_left_time=Prop(19, 2),
    ),
)

# c107/d101/d102ev/d102gl/d109gl: same siid/piid layout as ov21gl, but their
# sweep-type value list stops at 7. status_map keeps the full ov21gl table —
# codes 22-24 are simply never reported by the shorter-spec models.
XIAOMI_CORE_C107 = replace(
    XIAOMI_CORE_OV21GL,
    sweep_types={
        'global': 1,
        'zone': 2,
        'area': 3,
        'edge': 4,
        'costum': 5,
        'point': 6,
        'custom_area': 7,
    },
)

# xiaomi.vacuum.c107 — consumables unverified on this family (see ov71gl note
# above), explicitly cleared so it and its d10x aliases below don't silently
# inherit ov21gl's hardware-confirmed siid/piid table via replace().
XIAOMI_C107 = replace(
    XIAOMI_OV21GL,
    profile_id='xiaomi.c107',
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:xiaomi-c107:2",),
    core=XIAOMI_CORE_C107,
    consumables=None,
)

# xiaomi.vacuum.d101 — identical spec layout to c107
XIAOMI_D101 = replace(
    XIAOMI_C107,
    profile_id='xiaomi.d101',
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:xiaomi-d101:3",),
)

# xiaomi.vacuum.d102ev — identical spec layout to c107
XIAOMI_D102EV = replace(
    XIAOMI_C107,
    profile_id='xiaomi.d102ev',
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:xiaomi-d102ev:1",),
)

# xiaomi.vacuum.d102gl — identical spec layout to c107
XIAOMI_D102GL = replace(
    XIAOMI_C107,
    profile_id='xiaomi.d102gl',
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:xiaomi-d102gl:1",),
)

# xiaomi.vacuum.d109gl — identical spec layout to c107
XIAOMI_D109GL = replace(
    XIAOMI_C107,
    profile_id='xiaomi.d109gl',
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:xiaomi-d109gl:2",),
)
