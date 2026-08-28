"""Dreame runtime profiles.

See docs/dev/module-notes.md for design rationale and verification status.
"""

from __future__ import annotations

from ..types import (
    Action,
    CoreCapability,
    DreameAudioCapability,
    DreameCleanHistoryCapability,
    DreameConsumablesCapability,
    DreameDndCapability,
    DreameMapCapability,
    DreameScheduleCapability,
    DreameSettingsCapability,
    ModelProfile,
    Prop,
    RoomCleanCapability,
)


DREAME_P2008_CORE = CoreCapability(
    status=Prop(2, 1),  # status — "Working Status"
    fault=Prop(2, 2),  # fault — "Fault"
    mode=Prop(2, 3),  # mode — "Mode"
    battery=Prop(3, 1),  # battery-level — "Battery Level"
    charging_state=Prop(3, 2),  # charging-state — "Battery Charging Status"
    fan_speed=Prop(4, 4),  # cleaning-mode — "Cleaning Mode"
    water_level=Prop(4, 5),  # mop-mode — "Water Level Settings in Mopping Mode"
    volume=Prop(7, 1),  # volume — "Volume"
    start=Action(2, 1),  # start-sweep — "Start Cleaning"
    stop=Action(2, 2),  # stop-sweeping — "Pause"
    charge=Action(3, 1),  # start-charge — "Return to Charge"
    locate=Action(7, 1),  # position — "Locate My Robot"
    status_map={1: 'cleaning', 2: 'idle', 3: 'paused', 4: 'error', 5: 'returning', 6: 'docked'},
    modes={'silent': 0, 'basic': 1, 'strong': 2, 'full_speed': 3},
    fan_speeds={'quiet': 0, 'standard': 1, 'medium_gear': 2, 'strong': 3},
    water_levels={'low_water_level': 1, 'medium_water_level': 2, 'high_water_level': 3},
)


DREAME_P2008_MAP = DreameMapCapability(
    service=6,
    map_data=Prop(6, 1),  # map-data — "Map Data"
    frame_info=Prop(6, 2),  # frame-info — "Frame Information"
    object_name=Prop(6, 3),  # object-name — "Intermediate Map Data File Name on FDS"
    map_extend_data=Prop(6, 4),  # map-extend-data — "Map Editing Parameters"
    robot_time=Prop(6, 5),  # robot-time — "Host Current Timestamp"
    result_code=Prop(6, 6),  # result-code — "Map Editing Response Code"
    map_req=Action(6, 1, in_piid=2, out_piids=(1, 3, 5)),  # map-req — "Request Map Data"
    update_map=Action(6, 2, in_piid=4, out_piids=(6,)),  # update-map — "Update Map Information"
)


DREAME_P2008_ROOM_CLEAN = RoomCleanCapability(
    room_ids=Prop(2, 4),  # room-ids — "Mi Home Room ID Parameter"
    start=Action(2, 3, in_piid=4),  # start-room-sweep — "Clean Room"
)


DREAME_P2008_SCHEDULE = DreameScheduleCapability(
    service=8,
    time_zone=Prop(8, 1),  # time-zone — "Host Timezone Retrieval"
    timer_clean=Prop(8, 2),  # timer-clean — "Scheduled Reservation Cleaning"
    timer_id=Prop(8, 3),  # timer-id — "Reservation ID"
    delete_timer=Action(8, 1, in_piid=3),  # delete-timer — "Delete Scheduled Reservation"
)


DREAME_P2008_SETTINGS = DreameSettingsCapability(
    service=4,
    cleaning_mode=Prop(4, 4),  # cleaning-mode — "Cleaning Mode"
    mop_mode=Prop(4, 5),  # mop-mode — "Water Level Settings in Mopping Mode"
    waterbox_status=Prop(4, 6),  # waterbox-status — "Water Tank Status"
    task_status=Prop(4, 7),  # task-status — "Host Task Status"
    break_point_restart=Prop(4, 11),  # break-point-restart — "Resume Cleaning Switch"
    carpet_press=Prop(4, 12),  # carpet-press — "Carpet Boost Switch"
)


DREAME_P2008_CONSUMABLES = DreameConsumablesCapability(
    main_brush_life=Prop(9, 2),  # brush-life-level — "Cleaning Brush Remaining Life"
    main_brush_left_time=Prop(9, 1),  # brush-left-time — "Cleaning Brush Remaining Time"
    reset_main_brush=Action(9, 1),  # reset-brush-life — "Reset Cleaning Brush"
    side_brush_life=Prop(10, 2),  # brush-life-level — "Cleaning Brush Remaining Life"
    side_brush_left_time=Prop(10, 1),  # brush-left-time — "Cleaning Brush Remaining Time"
    reset_side_brush=Action(10, 1),  # reset-brush-life — "Reset Cleaning Brush"
    filter_life=Prop(11, 1),  # filter-life-level — "Filter Remaining Life"
    filter_left_time=Prop(11, 2),  # filter-left-time — "Filter Remaining Time"
    reset_filter=Action(11, 1),  # reset-filter-life — "Reset Filter"
)


DREAME_P2008_CLEAN_HISTORY = DreameCleanHistoryCapability(
    service=12,
    first_clean_time=Prop(12, 1),  # first-clean-time — "First Cleaning Start Time"
    total_clean_time=Prop(12, 2),  # total-clean-time — "Total Cleaning Time"
    total_clean_times=Prop(12, 3),  # total-clean-times — "Total Cleaning Count"
    total_clean_area=Prop(12, 4),  # total-clean-area — "Total Cleaning Area"
)


DREAME_P2008_DND = DreameDndCapability(
    service=5,
    enable=Prop(5, 1),  # enable — "Enable"
    start_time=Prop(5, 2),  # start-time — "Do Not Disturb Start Time"
    end_time=Prop(5, 3),  # end-time — "Do Not Disturb End Time"
)


DREAME_P2008_VOICE = DreameAudioCapability(
    service=7,
    voice_packet_id=Prop(7, 2),  # voice-packet-id — "Voice Pack ID"
    voice_change_state=Prop(7, 3),  # voice-change-state — "Voice Pack Switching Status"
    set_voice=Prop(7, 4),  # set-voice — "Set Personalized Voice"
    locate=Action(7, 1),  # position — "Locate My Robot"
    play_sound=Action(7, 2),  # play-sound — "Voice Preview"
)


DREAME_P2008 = ModelProfile(
    profile_id="dreame.p2008",
    brand="dreame",
    core=DREAME_P2008_CORE,
    map=DREAME_P2008_MAP,
    room_clean=DREAME_P2008_ROOM_CLEAN,
    schedule=DREAME_P2008_SCHEDULE,
    settings=DREAME_P2008_SETTINGS,
    consumables=DREAME_P2008_CONSUMABLES,
    clean_history=DREAME_P2008_CLEAN_HISTORY,
    dnd=DREAME_P2008_DND,
    voice=DREAME_P2008_VOICE,
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:dreame-p2008:2",),
)


DREAME_P2009_CORE = CoreCapability(
    status=Prop(2, 1),  # status — "Working Status"
    fault=Prop(2, 2),  # fault — "Fault"
    mode=Prop(2, 3),  # mode — "Mode"
    battery=Prop(3, 1),  # battery-level — "Battery Level"
    charging_state=Prop(3, 2),  # charging-state — "Battery Charging Status"
    fan_speed=Prop(4, 4),  # cleaning-mode — "Cleaning Mode"
    water_level=Prop(4, 5),  # mop-mode — "Water Level Settings in Mopping Mode"
    volume=Prop(7, 1),  # volume — "Volume"
    start=Action(2, 1),  # start-sweep — "Start Cleaning"
    stop=Action(2, 2),  # stop-sweeping — "Pause"
    charge=Action(3, 1),  # start-charge — "Return to Charge"
    locate=Action(7, 1),  # position — "Locate My Robot"
    status_map={1: 'cleaning', 2: 'idle', 3: 'paused', 4: 'error', 5: 'returning', 6: 'docked'},
    modes={'silent': 0, 'basic': 1, 'strong': 2, 'full_speed': 3},
    fan_speeds={'quiet': 0, 'standard': 1, 'medium_gear': 2, 'strong': 3},
    water_levels={'low': 1, 'medium': 2, 'high': 3},
)


DREAME_P2009_MAP = DreameMapCapability(
    service=6,
    map_data=Prop(6, 1),  # map-data — "Map Data"
    frame_info=Prop(6, 2),  # frame-info — "Frame Information"
    object_name=Prop(6, 3),  # object-name — "Intermediate Map Data File Name on FDS"
    map_extend_data=Prop(6, 4),  # map-extend-data — "Map Editing Parameters"
    robot_time=Prop(6, 5),  # robot-time — "Host Current Timestamp"
    result_code=Prop(6, 6),  # result-code — "Map Editing Response Code"
    mult_map_state=Prop(6, 7),  # mult-map-state — "Set Multi-layer Map Switch (1: Enable, 0: Disable)"
    mult_map_info=Prop(6, 8),  # mult-map-info — "Multi-layer Map Information"{\"object_name\":\"%s\",\"md5\":\"%s\"}""
    map_req=Action(6, 1, in_piid=2, out_piids=(1, 3, 5)),  # map-req — "Request Map Data"
    update_map=Action(6, 2, in_piid=4, out_piids=(6,)),  # update-map — "Update Map Information"
)


DREAME_P2009_ROOM_CLEAN = RoomCleanCapability(
    room_ids=Prop(2, 4),  # room-ids — "Mi Home Room ID Parameter"
    start=Action(2, 3, in_piid=4),  # start-room-sweep — "Clean Room"
)


DREAME_P2009_SCHEDULE = DreameScheduleCapability(
    service=8,
    time_zone=Prop(8, 1),  # time-zone — "Host Timezone Retrieval"
    timer_clean=Prop(8, 2),  # timer-clean — "Scheduled Reservation Cleaning"
    timer_id=Prop(8, 3),  # timer-id — "Reservation ID"
    delete_timer=Action(8, 1, in_piid=3),  # delete-timer — "Delete Scheduled Reservation"
)


DREAME_P2009_SETTINGS = DreameSettingsCapability(
    service=4,
    cleaning_mode=Prop(4, 4),  # cleaning-mode — "Cleaning Mode"
    mop_mode=Prop(4, 5),  # mop-mode — "Water Level Settings in Mopping Mode"
    waterbox_status=Prop(4, 6),  # waterbox-status — "Water Tank Status"
    task_status=Prop(4, 7),  # task-status — "Host Task Status"
    break_point_restart=Prop(4, 11),  # break-point-restart — "Resume Cleaning Switch"
    carpet_press=Prop(4, 12),  # carpet-press — "Carpet Boost Switch"
)


DREAME_P2009_CONSUMABLES = DreameConsumablesCapability(
    main_brush_life=Prop(9, 2),  # brush-life-level — "Cleaning Brush Remaining Life"
    main_brush_left_time=Prop(9, 1),  # brush-left-time — "Cleaning Brush Remaining Time"
    reset_main_brush=Action(9, 1),  # reset-brush-life — "Reset Cleaning Brush"
    side_brush_life=Prop(10, 2),  # brush-life-level — "Cleaning Brush Remaining Life"
    side_brush_left_time=Prop(10, 1),  # brush-left-time — "Cleaning Brush Remaining Time"
    reset_side_brush=Action(10, 1),  # reset-brush-life — "Reset Cleaning Brush"
    filter_life=Prop(11, 1),  # filter-life-level — "Filter Remaining Life"
    filter_left_time=Prop(11, 2),  # filter-left-time — "Filter Remaining Time"
    reset_filter=Action(11, 1),  # reset-filter-life — "Reset Filter"
)


DREAME_P2009_CLEAN_HISTORY = DreameCleanHistoryCapability(
    service=12,
    first_clean_time=Prop(12, 1),  # first-clean-time — "First Cleaning Start Time"
    total_clean_time=Prop(12, 2),  # total-clean-time — "Total Cleaning Time"
    total_clean_times=Prop(12, 3),  # total-clean-times — "Total Cleaning Count"
    total_clean_area=Prop(12, 4),  # total-clean-area — "Total Cleaning Area"
)


DREAME_P2009_DND = DreameDndCapability(
    service=5,
    enable=Prop(5, 1),  # enable — "Enable"
    start_time=Prop(5, 2),  # start-time — "Do Not Disturb Start Time"
    end_time=Prop(5, 3),  # end-time — "Do Not Disturb End Time"
)


DREAME_P2009_VOICE = DreameAudioCapability(
    service=7,
    voice_packet_id=Prop(7, 2),  # voice-packet-id — "Voice Pack ID"
    voice_change_state=Prop(7, 3),  # voice-change-state — "Voice Pack Switching Status"
    set_voice=Prop(7, 4),  # set-voice — "Set Personalized Voice"
    locate=Action(7, 1),  # position — "Locate My Robot"
    play_sound=Action(7, 2),  # play-sound — "Voice Preview"
)


DREAME_P2009 = ModelProfile(
    profile_id="dreame.p2009",
    brand="dreame",
    core=DREAME_P2009_CORE,
    map=DREAME_P2009_MAP,
    room_clean=DREAME_P2009_ROOM_CLEAN,
    schedule=DREAME_P2009_SCHEDULE,
    settings=DREAME_P2009_SETTINGS,
    consumables=DREAME_P2009_CONSUMABLES,
    clean_history=DREAME_P2009_CLEAN_HISTORY,
    dnd=DREAME_P2009_DND,
    voice=DREAME_P2009_VOICE,
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:dreame-p2009:2",),
)


DREAME_P2027_MAP = DreameMapCapability(
    service=6,
    map_data=Prop(6, 1),  # map-data — "Map Data"
    frame_info=Prop(6, 2),  # frame-info — "Frame Information"
    object_name=Prop(6, 3),  # object-name — "Intermediate Map Data File Name on FDS"
    map_extend_data=Prop(6, 4),  # map-extend-data — "Map Editing Parameters"
    robot_time=Prop(6, 5),  # robot-time — "Host Current Timestamp"
    result_code=Prop(6, 6),  # result-code — "Map Editing Response Code"
    mult_map_state=Prop(6, 7),  # mult-map-state — "Set Multi-layer Map Switch (1: Enable, 0: Disable)"
    mult_map_info=Prop(6, 8),  # mult-map-info — "Multi-layer Map Information"
    map_req=Action(6, 1, in_piid=2, out_piids=(1, 3, 5)),  # map-req — "Request Map Data"
    update_map=Action(6, 2, in_piid=4, out_piids=(6,)),  # update-map — "Update Map Information"
)


DREAME_P2027_ROOM_CLEAN = RoomCleanCapability(
    room_ids=Prop(2, 4),  # room-ids — "Mi Home Room ID Parameter"
    start=Action(2, 3, in_piid=4),  # start-room-sweep — "Clean Room"
)


DREAME_P2027_SCHEDULE = DreameScheduleCapability(
    service=8,
    time_zone=Prop(8, 1),  # time-zone — "Host Timezone Retrieval"
    timer_clean=Prop(8, 2),  # timer-clean — "Scheduled Reservation Cleaning"
    timer_id=Prop(8, 3),  # timer-id — "Reservation ID"
    delete_timer=Action(8, 1, in_piid=3),  # delete-timer — "Delete Scheduled Reservation"
)


DREAME_P2027_SETTINGS = DreameSettingsCapability(
    service=4,
    cleaning_mode=Prop(4, 4),  # cleaning-mode — "Cleaning Mode"
    mop_mode=Prop(4, 5),  # mop-mode — "Water Level Settings in Mopping Mode"
    waterbox_status=Prop(4, 6),  # waterbox-status — "Water Tank Status"
    task_status=Prop(4, 7),  # task-status — "Host Task Status"
    break_point_restart=Prop(4, 11),  # break-point-restart — "Resume Cleaning Switch"
    carpet_press=Prop(4, 12),  # carpet-press — "Carpet Boost Switch"
    child_lock=Prop(4, 27),  # child-lock — "Child Lock Switch (0: Off, 1: On)"
)


DREAME_P2027_CONSUMABLES = DreameConsumablesCapability(
    main_brush_life=Prop(9, 2),  # brush-life-level — "Cleaning Brush Remaining Life"
    main_brush_left_time=Prop(9, 1),  # brush-left-time — "Cleaning Brush Remaining Time"
    reset_main_brush=Action(9, 1),  # reset-brush-life — "Reset Cleaning Brush"
    side_brush_life=Prop(10, 2),  # brush-life-level — "Cleaning Brush Remaining Life"
    side_brush_left_time=Prop(10, 1),  # brush-left-time — "Cleaning Brush Remaining Time"
    reset_side_brush=Action(10, 1),  # reset-brush-life — "Reset Cleaning Brush"
    filter_life=Prop(11, 1),  # filter-life-level — "Filter Remaining Life"
    filter_left_time=Prop(11, 2),  # filter-left-time — "Filter Remaining Time"
    reset_filter=Action(11, 1),  # reset-filter-life — "Reset Filter"
    mop_life=Prop(18, 1),  # mop-life-level — "Mop Remaining Life"
    mop_left_time=Prop(18, 2),  # mop-left-time — "Mop Remaining Time"
    reset_mop=Action(18, 1),  # reset-mop-life — "Reset Mop"
)


DREAME_P2027_CLEAN_HISTORY = DreameCleanHistoryCapability(
    service=12,
    first_clean_time=Prop(12, 1),  # first-clean-time — "First Cleaning Start Time"
    total_clean_time=Prop(12, 2),  # total-clean-time — "Total Cleaning Time"
    total_clean_times=Prop(12, 3),  # total-clean-times — "Total Cleaning Count"
    total_clean_area=Prop(12, 4),  # total-clean-area — "Total Cleaning Area"
)


DREAME_P2027_DND = DreameDndCapability(
    service=5,
    enable=Prop(5, 1),  # enable — "Enable"
    start_time=Prop(5, 2),  # start-time — "Do Not Disturb Start Time"
    end_time=Prop(5, 3),  # end-time — "Do Not Disturb End Time"
)


DREAME_P2027_VOICE = DreameAudioCapability(
    service=7,
    voice_packet_id=Prop(7, 2),  # voice-packet-id — "Voice Pack ID"
    voice_change_state=Prop(7, 3),  # voice-change-state — "Voice Pack Switching Status"
    set_voice=Prop(7, 4),  # set-voice — "Set Personalized Voice"
    locate=Action(7, 1),  # position — "Locate My Robot"
    play_sound=Action(7, 2),  # play-sound — "Voice Preview"
)


DREAME_P2027 = ModelProfile(
    profile_id="dreame.p2027",
    brand="dreame",
    core=DREAME_P2009_CORE,
    map=DREAME_P2027_MAP,
    room_clean=DREAME_P2027_ROOM_CLEAN,
    schedule=DREAME_P2027_SCHEDULE,
    settings=DREAME_P2027_SETTINGS,
    consumables=DREAME_P2027_CONSUMABLES,
    clean_history=DREAME_P2027_CLEAN_HISTORY,
    dnd=DREAME_P2027_DND,
    voice=DREAME_P2027_VOICE,
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:dreame-p2027:3",),
)


DREAME_P2036_MAP = DreameMapCapability(
    service=6,
    map_data=Prop(6, 1),  # map-data — "Map Data"
    frame_info=Prop(6, 2),  # frame-info — "Frame Information"
    object_name=Prop(6, 3),  # object-name — "Intermediate Map Data File Name on FDS"
    map_extend_data=Prop(6, 4),  # map-extend-data — "Map Editing Parameters"
    robot_time=Prop(6, 5),  # robot-time — "Host Current Timestamp"
    result_code=Prop(6, 6),  # result-code — "Map Editing Response Code"
    map_req=Action(6, 1, in_piid=2, out_piids=(1, 3, 5)),  # map-req — "Request Map Data"
    update_map=Action(6, 2, in_piid=4, out_piids=(6,)),  # update-map — "Update Map Information"
)


DREAME_P2036_ROOM_CLEAN = RoomCleanCapability(
    room_ids=Prop(2, 4),  # room-ids — "Mi Home Room ID Parameter"
    start=Action(2, 3, in_piid=4),  # start-room-sweep — "Clean Room"
)


DREAME_P2036_SCHEDULE = DreameScheduleCapability(
    service=8,
    time_zone=Prop(8, 1),  # time-zone — "Host Timezone Retrieval"
    timer_clean=Prop(8, 2),  # timer-clean — "Scheduled Reservation Cleaning"
    timer_id=Prop(8, 3),  # timer-id — "Reservation ID"
    delete_timer=Action(8, 1, in_piid=3),  # delete-timer — "Delete Scheduled Reservation"
)


DREAME_P2036_SETTINGS = DreameSettingsCapability(
    service=4,
    cleaning_mode=Prop(4, 4),  # cleaning-mode — "Cleaning Mode"
    mop_mode=Prop(4, 5),  # mop-mode — "Water Level Settings in Mopping Mode"
    waterbox_status=Prop(4, 6),  # waterbox-status — "Water Tank Status"
    task_status=Prop(4, 7),  # task-status — "Host Task Status"
    break_point_restart=Prop(4, 11),  # break-point-restart — "Resume Cleaning Switch"
    carpet_press=Prop(4, 12),  # carpet-press — "Carpet Boost Switch"
)


DREAME_P2036_CONSUMABLES = DreameConsumablesCapability(
    main_brush_life=Prop(9, 2),  # brush-life-level — "Cleaning Brush Remaining Life"
    main_brush_left_time=Prop(9, 1),  # brush-left-time — "Cleaning Brush Remaining Time"
    reset_main_brush=Action(9, 1),  # reset-brush-life — "Reset Cleaning Brush"
    side_brush_life=Prop(10, 2),  # brush-life-level — "Cleaning Brush Remaining Life"
    side_brush_left_time=Prop(10, 1),  # brush-left-time — "Cleaning Brush Remaining Time"
    reset_side_brush=Action(10, 1),  # reset-brush-life — "Reset Cleaning Brush"
    filter_life=Prop(11, 1),  # filter-life-level — "Filter Remaining Life"
    filter_left_time=Prop(11, 2),  # filter-left-time — "Filter Remaining Time"
    reset_filter=Action(11, 1),  # reset-filter-life — "Reset Filter"
)


DREAME_P2036_CLEAN_HISTORY = DreameCleanHistoryCapability(
    service=12,
    first_clean_time=Prop(12, 1),  # first-clean-time — "First Cleaning Start Time"
    total_clean_time=Prop(12, 2),  # total-clean-time — "Total Cleaning Time"
    total_clean_times=Prop(12, 3),  # total-clean-times — "Total Cleaning Count"
    total_clean_area=Prop(12, 4),  # total-clean-area — "Total Cleaning Area"
)


DREAME_P2036_DND = DreameDndCapability(
    service=5,
    enable=Prop(5, 1),  # enable — "Enable"
    start_time=Prop(5, 2),  # start-time — "Do Not Disturb Start Time"
    end_time=Prop(5, 3),  # end-time — "Do Not Disturb End Time"
)


DREAME_P2036_VOICE = DreameAudioCapability(
    service=7,
    voice_packet_id=Prop(7, 2),  # voice-packet-id — "Voice Pack ID"
    voice_change_state=Prop(7, 3),  # voice-change-state — "Voice Pack Switching Status"
    set_voice=Prop(7, 4),  # set-voice — "Set Personalized Voice"
    locate=Action(7, 1),  # position — "Locate My Robot"
    play_sound=Action(7, 2),  # play-sound — "Voice Preview"
)


DREAME_P2036 = ModelProfile(
    profile_id="dreame.p2036",
    brand="dreame",
    core=DREAME_P2009_CORE,
    map=DREAME_P2036_MAP,
    room_clean=DREAME_P2036_ROOM_CLEAN,
    schedule=DREAME_P2036_SCHEDULE,
    settings=DREAME_P2036_SETTINGS,
    consumables=DREAME_P2036_CONSUMABLES,
    clean_history=DREAME_P2036_CLEAN_HISTORY,
    dnd=DREAME_P2036_DND,
    voice=DREAME_P2036_VOICE,
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:dreame-p2036:2",),
)


DREAME_P2041_MAP = DreameMapCapability(
    service=6,
    map_data=Prop(6, 1),  # map-data — "Map Data"
    frame_info=Prop(6, 2),  # frame-info — "Frame Information"
    object_name=Prop(6, 3),  # object-name — "Intermediate Map Data File Name on FDS"
    map_extend_data=Prop(6, 4),  # map-extend-data — "Map Editing Parameters"
    robot_time=Prop(6, 5),  # robot-time — "Host Current Timestamp"
    result_code=Prop(6, 6),  # result-code — "Map Editing Response Code"
    map_req=Action(6, 1, in_piid=2, out_piids=(1, 3, 5)),  # map-req — "Request Map Data"
    update_map=Action(6, 2, in_piid=4, out_piids=(6,)),  # update-map — "Update Map Information"
)


DREAME_P2041_SCHEDULE = DreameScheduleCapability(
    service=8,
    time_zone=Prop(8, 1),  # time-zone — "Host Timezone Retrieval"
    timer_clean=Prop(8, 2),  # timer-clean — "Scheduled Reservation Cleaning"
    timer_id=Prop(8, 3),  # timer-id — "Reservation ID, For Easy Extension, Use String, Comma Separate Each ID (e.g.: "3,15", "1,9,45"), Currently Each Command Uses One ID (e.g.: "2", "60")"
    delete_timer=Action(8, 1, in_piid=3),  # delete-timer — "Delete Scheduled Reservation"
)


DREAME_P2041_SETTINGS = DreameSettingsCapability(
    service=4,
    cleaning_mode=Prop(4, 4),  # cleaning-mode — "Cleaning Mode"
    mop_mode=Prop(4, 5),  # mop-mode — "Water Level Settings in Mopping Mode"
    waterbox_status=Prop(4, 6),  # waterbox-status — "Water Tank Status"
    task_status=Prop(4, 7),  # task-status — "Host Task Status"
    break_point_restart=Prop(4, 11),  # break-point-restart — "Resume Cleaning Switch"
    carpet_press=Prop(4, 12),  # carpet-press — "Carpet Boost Switch"
)


DREAME_P2041_CONSUMABLES = DreameConsumablesCapability(
    main_brush_life=Prop(9, 2),  # brush-life-level — "Cleaning Brush Remaining Life"
    main_brush_left_time=Prop(9, 1),  # brush-left-time — "Cleaning Brush Remaining Time"
    reset_main_brush=Action(9, 1),  # reset-brush-life — "Reset Cleaning Brush"
    side_brush_life=Prop(10, 2),  # brush-life-level — "Cleaning Brush Remaining Life"
    side_brush_left_time=Prop(10, 1),  # brush-left-time — "Cleaning Brush Remaining Time"
    reset_side_brush=Action(10, 1),  # reset-brush-life — "Reset Cleaning Brush"
    filter_life=Prop(11, 1),  # filter-life-level — "Filter Remaining Life"
    filter_left_time=Prop(11, 2),  # filter-left-time — "Filter Remaining Time"
    reset_filter=Action(11, 1),  # reset-filter-life — "Reset Filter"
)


DREAME_P2041_CLEAN_HISTORY = DreameCleanHistoryCapability(
    service=12,
    first_clean_time=Prop(12, 1),  # first-clean-time — "First Cleaning Start Time"
    total_clean_time=Prop(12, 2),  # total-clean-time — "Total Cleaning Time"
    total_clean_times=Prop(12, 3),  # total-clean-times — "Total Cleaning Count"
    total_clean_area=Prop(12, 4),  # total-clean-area — "Total Cleaning Area"
)


DREAME_P2041_DND = DreameDndCapability(
    service=5,
    enable=Prop(5, 1),  # enable — "Enable"
    start_time=Prop(5, 2),  # start-time — "Do Not Disturb Start Time"
    end_time=Prop(5, 3),  # end-time — "Do Not Disturb End Time"
)


DREAME_P2041_VOICE = DreameAudioCapability(
    service=7,
    voice_packet_id=Prop(7, 2),  # voice-packet-id — "Voice Pack ID"
    voice_change_state=Prop(7, 3),  # voice-change-state — "Voice Pack Switching Status"
    set_voice=Prop(7, 4),  # set-voice — "Set Personalized Voice"
    locate=Action(7, 1),  # position — "Locate My Robot"
    play_sound=Action(7, 2),  # play-sound — "Voice Preview"
)


DREAME_P2041 = ModelProfile(
    profile_id="dreame.p2041",
    brand="dreame",
    core=DREAME_P2009_CORE,
    map=DREAME_P2041_MAP,
    schedule=DREAME_P2041_SCHEDULE,
    settings=DREAME_P2041_SETTINGS,
    consumables=DREAME_P2041_CONSUMABLES,
    clean_history=DREAME_P2041_CLEAN_HISTORY,
    dnd=DREAME_P2041_DND,
    voice=DREAME_P2041_VOICE,
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:dreame-p2041:2",),
)


DREAME_P2114A_CORE = CoreCapability(
    status=Prop(2, 1),  # status — "Working Status"
    fault=Prop(2, 2),  # fault — "Fault"
    mode=Prop(2, 3),  # mode — "Mode"
    battery=Prop(3, 1),  # battery-level — "Battery Level"
    charging_state=Prop(3, 2),  # charging-state — "Battery Charging Status"
    fan_speed=Prop(4, 4),  # cleaning-mode — "Cleaning Mode"
    water_level=Prop(4, 5),  # mop-mode — "Water Level Settings in Mopping Mode"
    volume=Prop(7, 1),  # volume — "Volume"
    start=Action(2, 1),  # start-sweep — "Start Cleaning"
    stop=Action(2, 2),  # stop-sweeping — "Pause"
    charge=Action(3, 1),  # start-charge — "Return to Charge"
    locate=Action(7, 1),  # position — "Locate My Robot"
    status_map={1: 'cleaning', 2: 'idle', 3: 'paused', 4: 'error', 5: 'returning', 6: 'docked'},
    modes={'silent': 0, 'basic': 1, 'strong': 2, 'full_speed': 3},
    fan_speeds={'quiet': 0, 'standard': 1, 'medium': 2, 'strong': 3},
    water_levels={'low': 1, 'medium': 2, 'high': 3},
)


DREAME_P2114A_MAP = DreameMapCapability(
    service=6,
    map_data=Prop(6, 1),  # map-data — "Map Data"
    frame_info=Prop(6, 2),  # frame-info — "Frame Information"
    object_name=Prop(6, 3),  # object-name — "Intermediate Map Data File Name on FDS"
    map_extend_data=Prop(6, 4),  # map-extend-data — "Map Editing Parameters"
    robot_time=Prop(6, 5),  # robot-time — "Host Current Timestamp"
    result_code=Prop(6, 6),  # result-code — "Map Editing Response Code"
    mult_map_info=Prop(6, 8),  # mult-map-info — "Multi-layer Map Information"
    map_req=Action(6, 1, in_piid=2, out_piids=(1, 3, 5)),  # map-req — "Request Map Data"
    update_map=Action(6, 2, in_piid=4, out_piids=(6,)),  # update-map — "Update Map Information"
)


DREAME_P2114A_ROOM_CLEAN = RoomCleanCapability(
    room_ids=Prop(2, 4),  # room-ids — "Mi Home Room ID Parameter"
    start=Action(2, 3, in_piid=4),  # start-room-sweep — "Clean Room"
)


DREAME_P2114A_SCHEDULE = DreameScheduleCapability(
    service=8,
    time_zone=Prop(8, 1),  # time-zone — "Host Timezone Retrieval"
    timer_clean=Prop(8, 2),  # timer-clean — "Scheduled Reservation Cleaning"
    timer_id=Prop(8, 3),  # timer-id — "Reservation ID"
    delete_timer=Action(8, 1, in_piid=3),  # delete-timer — "Delete Scheduled Reservation"
)


DREAME_P2114A_SETTINGS = DreameSettingsCapability(
    service=4,
    cleaning_mode=Prop(4, 4),  # cleaning-mode — "Cleaning Mode"
    mop_mode=Prop(4, 5),  # mop-mode — "Water Level Settings in Mopping Mode"
    waterbox_status=Prop(4, 6),  # waterbox-status — "Water Tank Status"
    task_status=Prop(4, 7),  # task-status — "Host Task Status"
    break_point_restart=Prop(4, 11),  # break-point-restart — "Resume Cleaning Switch"
    carpet_press=Prop(4, 12),  # carpet-press — "Carpet Boost Switch"
    child_lock=Prop(4, 27),  # child-lock — "Child Lock"
)


DREAME_P2114A_CONSUMABLES = DreameConsumablesCapability(
    main_brush_life=Prop(9, 2),  # brush-life-level — "Cleaning Brush Remaining Life"
    main_brush_left_time=Prop(9, 1),  # brush-left-time — "Cleaning Brush Remaining Time"
    reset_main_brush=Action(9, 1),  # reset-brush-life — "Reset Cleaning Brush"
    side_brush_life=Prop(10, 2),  # brush-life-level — "Cleaning Brush Remaining Life"
    side_brush_left_time=Prop(10, 1),  # brush-left-time — "Cleaning Brush Remaining Time"
    reset_side_brush=Action(10, 1),  # reset-brush-life — "Reset Cleaning Brush"
    filter_life=Prop(11, 1),  # filter-life-level — "Filter Remaining Life"
    filter_left_time=Prop(11, 2),  # filter-left-time — "Filter Remaining Time"
    reset_filter=Action(11, 1),  # reset-filter-life — "Reset Filter"
    mop_life=Prop(18, 1),  # mop-life-level — "Mop Remaining Life"
    mop_left_time=Prop(18, 2),  # mop-left-time — "Mop Remaining Time"
    reset_mop=Action(18, 1),  # reset-mop-life — "Reset Mop"
)


DREAME_P2114A_CLEAN_HISTORY = DreameCleanHistoryCapability(
    service=12,
    first_clean_time=Prop(12, 1),  # first-clean-time — "First Cleaning Start Time"
    total_clean_time=Prop(12, 2),  # total-clean-time — "Total Cleaning Time"
    total_clean_times=Prop(12, 3),  # total-clean-times — "Total Cleaning Count"
    total_clean_area=Prop(12, 4),  # total-clean-area — "Total Cleaning Area"
)


DREAME_P2114A_DND = DreameDndCapability(
    service=5,
    enable=Prop(5, 1),  # enable — "Enable"
    start_time=Prop(5, 2),  # start-time — "Do Not Disturb Start Time"
    end_time=Prop(5, 3),  # end-time — "Do Not Disturb End Time"
)


DREAME_P2114A_VOICE = DreameAudioCapability(
    service=7,
    voice_packet_id=Prop(7, 2),  # voice-packet-id — "Voice Pack ID"
    voice_change_state=Prop(7, 3),  # voice-change-state — "Voice Pack Switching Status"
    set_voice=Prop(7, 4),  # set-voice — "Set Personalized Voice"
    locate=Action(7, 1),  # position — "Locate My Robot"
    play_sound=Action(7, 2),  # play-sound — "Voice Preview"
)


DREAME_P2114A = ModelProfile(
    profile_id="dreame.p2114a",
    brand="dreame",
    core=DREAME_P2114A_CORE,
    map=DREAME_P2114A_MAP,
    room_clean=DREAME_P2114A_ROOM_CLEAN,
    schedule=DREAME_P2114A_SCHEDULE,
    settings=DREAME_P2114A_SETTINGS,
    consumables=DREAME_P2114A_CONSUMABLES,
    clean_history=DREAME_P2114A_CLEAN_HISTORY,
    dnd=DREAME_P2114A_DND,
    voice=DREAME_P2114A_VOICE,
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:dreame-p2114a:2",),
)


DREAME_P2114O_MAP = DreameMapCapability(
    service=6,
    map_data=Prop(6, 1),  # map-data — "Map Data"
    frame_info=Prop(6, 2),  # frame-info — "Frame Information"
    object_name=Prop(6, 3),  # object-name — "Intermediate Map Data File Name on FDS"
    map_extend_data=Prop(6, 4),  # map-extend-data — "Map Editing Parameters"
    robot_time=Prop(6, 5),  # robot-time — "Host Current Timestamp"
    result_code=Prop(6, 6),  # result-code — "Map Editing Response Code"
    mult_map_info=Prop(6, 8),  # mult-map-info — "Multi-layer Map Information"
    map_req=Action(6, 1, in_piid=2, out_piids=(1, 3, 5)),  # map-req — "Request Map Data"
    update_map=Action(6, 2, in_piid=4, out_piids=(6,)),  # update-map — "Update Map Information"
)


DREAME_P2114O_ROOM_CLEAN = RoomCleanCapability(
    room_ids=Prop(2, 4),  # room-ids — "Mi Home Room ID Parameter"
    start=Action(2, 3, in_piid=4),  # start-room-sweep — "Clean Room"
)


DREAME_P2114O_SCHEDULE = DreameScheduleCapability(
    service=8,
    time_zone=Prop(8, 1),  # time-zone — "Host Timezone Retrieval"
    timer_clean=Prop(8, 2),  # timer-clean — "Scheduled Reservation Cleaning"
    timer_id=Prop(8, 3),  # timer-id — "Reservation ID"
    delete_timer=Action(8, 1, in_piid=3),  # delete-timer — "Delete Scheduled Reservation"
)


DREAME_P2114O_SETTINGS = DreameSettingsCapability(
    service=4,
    cleaning_mode=Prop(4, 4),  # cleaning-mode — "Cleaning Mode"
    mop_mode=Prop(4, 5),  # mop-mode — "Water Level Settings in Mopping Mode"
    waterbox_status=Prop(4, 6),  # waterbox-status — "Water Tank Status"
    task_status=Prop(4, 7),  # task-status — "Host Task Status"
    break_point_restart=Prop(4, 11),  # break-point-restart — "Resume Cleaning Switch"
    carpet_press=Prop(4, 12),  # carpet-press — "Carpet Boost Switch"
    child_lock=Prop(4, 27),  # child-lock — "Child Lock"
)


DREAME_P2114O_CONSUMABLES = DreameConsumablesCapability(
    main_brush_life=Prop(9, 2),  # brush-life-level — "Cleaning Brush Remaining Life"
    main_brush_left_time=Prop(9, 1),  # brush-left-time — "Cleaning Brush Remaining Time"
    reset_main_brush=Action(9, 1),  # reset-brush-life — "Reset Cleaning Brush"
    side_brush_life=Prop(10, 2),  # brush-life-level — "Cleaning Brush Remaining Life"
    side_brush_left_time=Prop(10, 1),  # brush-left-time — "Cleaning Brush Remaining Time"
    reset_side_brush=Action(10, 1),  # reset-brush-life — "Reset Cleaning Brush"
    filter_life=Prop(11, 1),  # filter-life-level — "Filter Remaining Life"
    filter_left_time=Prop(11, 2),  # filter-left-time — "Filter Remaining Time"
    reset_filter=Action(11, 1),  # reset-filter-life — "Reset Filter"
    mop_life=Prop(18, 1),  # mop-life-level — "Mop Remaining Life"
    mop_left_time=Prop(18, 2),  # mop-left-time — "Mop Remaining Time"
    reset_mop=Action(18, 1),  # reset-mop-life — "Reset Mop"
)


DREAME_P2114O_CLEAN_HISTORY = DreameCleanHistoryCapability(
    service=12,
    first_clean_time=Prop(12, 1),  # first-clean-time — "First Cleaning Start Time"
    total_clean_time=Prop(12, 2),  # total-clean-time — "Total Cleaning Time"
    total_clean_times=Prop(12, 3),  # total-clean-times — "Total Cleaning Count"
    total_clean_area=Prop(12, 4),  # total-clean-area — "Total Cleaning Area"
)


DREAME_P2114O_DND = DreameDndCapability(
    service=5,
    enable=Prop(5, 1),  # enable — "Enable"
    start_time=Prop(5, 2),  # start-time — "Do Not Disturb Start Time"
    end_time=Prop(5, 3),  # end-time — "Do Not Disturb End Time"
)


DREAME_P2114O_VOICE = DreameAudioCapability(
    service=7,
    voice_packet_id=Prop(7, 2),  # voice-packet-id — "Voice Pack ID"
    voice_change_state=Prop(7, 3),  # voice-change-state — "Voice Pack Switching Status"
    set_voice=Prop(7, 4),  # set-voice — "Set Personalized Voice"
    locate=Action(7, 1),  # position — "Locate My Robot"
    play_sound=Action(7, 2),  # play-sound — "Voice Preview"
)


DREAME_P2114O = ModelProfile(
    profile_id="dreame.p2114o",
    brand="dreame",
    core=DREAME_P2009_CORE,
    map=DREAME_P2114O_MAP,
    room_clean=DREAME_P2114O_ROOM_CLEAN,
    schedule=DREAME_P2114O_SCHEDULE,
    settings=DREAME_P2114O_SETTINGS,
    consumables=DREAME_P2114O_CONSUMABLES,
    clean_history=DREAME_P2114O_CLEAN_HISTORY,
    dnd=DREAME_P2114O_DND,
    voice=DREAME_P2114O_VOICE,
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:dreame-p2114o:2",),
)


DREAME_P2149O_CORE = CoreCapability(
    status=Prop(2, 1),  # status — "Working Status"
    fault=Prop(2, 2),  # fault — "Fault"
    mode=Prop(2, 3),  # mode — "Mode"
    battery=Prop(3, 1),  # battery-level — "Battery Level"
    charging_state=Prop(3, 2),  # charging-state — "Battery Charging Status"
    fan_speed=Prop(4, 4),  # cleaning-mode — "Cleaning Mode"
    water_level=Prop(4, 5),  # mop-mode — "Water Level Settings in Mopping Mode"
    volume=Prop(7, 1),  # volume — "Volume"
    start=Action(2, 1),  # start-sweep — "Start Cleaning"
    stop=Action(2, 2),  # stop-sweeping — "Pause"
    charge=Action(3, 1),  # start-charge — "Return to Charge"
    locate=Action(7, 1),  # position — "Locate My Robot"
    status_map={1: 'cleaning', 2: 'idle', 3: 'paused', 4: 'error', 5: 'returning', 6: 'docked'},
    modes={'silent': 0, 'basic': 1, 'strong': 2, 'full_speed': 3},
    fan_speeds={'mode_quiet': 0, 'mode_standard': 1, 'mode_medium': 2, 'mode_strong': 3},
    water_levels={'low': 1, 'medium': 2, 'high': 3},
)


DREAME_P2149O_MAP = DreameMapCapability(
    service=6,
    map_data=Prop(6, 1),  # map-data — "Map Data"
    frame_info=Prop(6, 2),  # frame-info — "Frame Information"
    object_name=Prop(6, 3),  # object-name — "Intermediate Map Data File Name on FDS"
    map_extend_data=Prop(6, 4),  # map-extend-data — "Map Editing Parameters"
    robot_time=Prop(6, 5),  # robot-time — "Host Current Timestamp"
    result_code=Prop(6, 6),  # result-code — "Map Editing Response Code"
    mult_map_info=Prop(6, 8),  # mult-map-info — "Multi-layer Map Information"
    map_req=Action(6, 1, in_piid=2, out_piids=(1, 3, 5)),  # map-req — "Request Map Data"
    update_map=Action(6, 2, in_piid=4, out_piids=(6,)),  # update-map — "Update Map Information"
)


DREAME_P2149O_ROOM_CLEAN = RoomCleanCapability(
    room_ids=Prop(2, 4),  # room-ids — "Mi Home Room ID Parameter"
    start=Action(2, 3, in_piid=4),  # start-room-sweep — "Clean Room"
)


DREAME_P2149O_SCHEDULE = DreameScheduleCapability(
    service=8,
    time_zone=Prop(8, 1),  # time-zone — "Host Timezone Retrieval"
    timer_clean=Prop(8, 2),  # timer-clean — "Scheduled Reservation Cleaning"
    timer_id=Prop(8, 3),  # timer-id — "Reservation ID"
    delete_timer=Action(8, 1, in_piid=3),  # delete-timer — "Delete Scheduled Reservation"
)


DREAME_P2149O_SETTINGS = DreameSettingsCapability(
    service=4,
    cleaning_mode=Prop(4, 4),  # cleaning-mode — "Cleaning Mode"
    mop_mode=Prop(4, 5),  # mop-mode — "Water Level Settings in Mopping Mode"
    waterbox_status=Prop(4, 6),  # waterbox-status — "Water Tank Status"
    task_status=Prop(4, 7),  # task-status — "Host Task Status"
    break_point_restart=Prop(4, 11),  # break-point-restart — "Resume Cleaning Switch"
    carpet_press=Prop(4, 12),  # carpet-press — "Carpet Boost Switch"
    child_lock=Prop(4, 27),  # child-lock — "Child Lock Switch (0: Off, 1: On)"
)


DREAME_P2149O_CONSUMABLES = DreameConsumablesCapability(
    main_brush_life=Prop(9, 2),  # brush-life-level — "Cleaning Brush Remaining Life"
    main_brush_left_time=Prop(9, 1),  # brush-left-time — "Cleaning Brush Remaining Time"
    reset_main_brush=Action(9, 1),  # reset-brush-life — "Reset Cleaning Brush"
    side_brush_life=Prop(10, 2),  # brush-life-level — "Cleaning Brush Remaining Life"
    side_brush_left_time=Prop(10, 1),  # brush-left-time — "Cleaning Brush Remaining Time"
    reset_side_brush=Action(10, 1),  # reset-brush-life — "Reset Cleaning Brush"
    filter_life=Prop(11, 1),  # filter-life-level — "Filter Remaining Life"
    filter_left_time=Prop(11, 2),  # filter-left-time — "Filter Remaining Time"
    reset_filter=Action(11, 1),  # reset-filter-life — "Reset Filter"
)


DREAME_P2149O_CLEAN_HISTORY = DreameCleanHistoryCapability(
    service=12,
    first_clean_time=Prop(12, 1),  # first-clean-time — "First Cleaning Start Time"
    total_clean_time=Prop(12, 2),  # total-clean-time — "Total Cleaning Time"
    total_clean_times=Prop(12, 3),  # total-clean-times — "Total Cleaning Count"
    total_clean_area=Prop(12, 4),  # total-clean-area — "Total Cleaning Area"
)


DREAME_P2149O_DND = DreameDndCapability(
    service=5,
    enable=Prop(5, 1),  # enable — "Enable"
    start_time=Prop(5, 2),  # start-time — "Do Not Disturb Start Time"
    end_time=Prop(5, 3),  # end-time — "Do Not Disturb End Time"
)


DREAME_P2149O_VOICE = DreameAudioCapability(
    service=7,
    voice_packet_id=Prop(7, 2),  # voice-packet-id — "Voice Pack ID"
    voice_change_state=Prop(7, 3),  # voice-change-state — "Voice Pack Switching Status"
    set_voice=Prop(7, 4),  # set-voice — "Set Personalized Voice"
    locate=Action(7, 1),  # position — "Locate My Robot"
    play_sound=Action(7, 2),  # play-sound — "Voice Preview"
)


DREAME_P2149O = ModelProfile(
    profile_id="dreame.p2149o",
    brand="dreame",
    core=DREAME_P2149O_CORE,
    map=DREAME_P2149O_MAP,
    room_clean=DREAME_P2149O_ROOM_CLEAN,
    schedule=DREAME_P2149O_SCHEDULE,
    settings=DREAME_P2149O_SETTINGS,
    consumables=DREAME_P2149O_CONSUMABLES,
    clean_history=DREAME_P2149O_CLEAN_HISTORY,
    dnd=DREAME_P2149O_DND,
    voice=DREAME_P2149O_VOICE,
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:dreame-p2149o:2",),
)


DREAME_P2150A_CORE = CoreCapability(
    status=Prop(2, 1),  # status — "Working Status"
    fault=Prop(2, 2),  # fault — "Fault"
    mode=Prop(2, 3),  # mode — "Mode"
    battery=Prop(3, 1),  # battery-level — "Battery Level"
    charging_state=Prop(3, 2),  # charging-state — "Battery Charging Status"
    fan_speed=Prop(4, 4),  # cleaning-mode — "Cleaning Mode"
    water_level=Prop(4, 5),  # mop-mode — "Water Level Settings in Mopping Mode"
    volume=Prop(7, 1),  # volume — "Volume"
    start=Action(2, 1),  # start-sweep — "Start Cleaning"
    stop=Action(2, 2),  # stop-sweeping — "Pause"
    charge=Action(3, 1),  # start-charge — "Return to Charge"
    locate=Action(7, 1),  # position — "Locate My Robot"
    status_map={1: 'cleaning', 2: 'idle', 3: 'paused', 4: 'error', 5: 'returning', 6: 'docked'},
    modes={'silent': 0, 'basic': 1, 'strong': 2, 'full_speed': 3},
    fan_speeds={'quiet': 0, 'standard': 1, 'strong': 2, 'ultra_strong': 3},
    water_levels={'low': 1, 'medium': 2, 'high': 3},
)


DREAME_P2150A_MAP = DreameMapCapability(
    service=6,
    map_data=Prop(6, 1),  # map-data — "Map Data"
    frame_info=Prop(6, 2),  # frame-info — "Frame Information"
    object_name=Prop(6, 3),  # object-name — "Intermediate Map Data File Name on FDS"
    map_extend_data=Prop(6, 4),  # map-extend-data — "Map Editing Parameters"
    robot_time=Prop(6, 5),  # robot-time — "Host Current Timestamp"
    result_code=Prop(6, 6),  # result-code — "Map Editing Response Code"
    mult_map_state=Prop(6, 7),  # mult-map-state — "Set Multi-layer Map Switch (1: Enable, 0: Disable)"
    mult_map_info=Prop(6, 8),  # mult-map-info — "Multi-layer Map Information"
    map_req=Action(6, 1, in_piid=2, out_piids=(1, 3, 5)),  # map-req — "Request Map Data"
    update_map=Action(6, 2, in_piid=4, out_piids=(6,)),  # update-map — "Update Map Information"
)


DREAME_P2150A_ROOM_CLEAN = RoomCleanCapability(
    room_ids=Prop(2, 4),  # room-ids — "Mi Home Room ID Parameter"
    start=Action(2, 3, in_piid=4),  # start-room-sweep — "Clean Room"
)


DREAME_P2150A_SCHEDULE = DreameScheduleCapability(
    service=8,
    time_zone=Prop(8, 1),  # time-zone — "Host Timezone Retrieval"
    timer_clean=Prop(8, 2),  # timer-clean — "Scheduled Reservation Cleaning"
    timer_id=Prop(8, 3),  # timer-id — "Reservation ID"
    delete_timer=Action(8, 1, in_piid=3),  # delete-timer — "Delete Scheduled Reservation"
)


DREAME_P2150A_SETTINGS = DreameSettingsCapability(
    service=4,
    cleaning_mode=Prop(4, 4),  # cleaning-mode — "Cleaning Mode"
    mop_mode=Prop(4, 5),  # mop-mode — "Water Level Settings in Mopping Mode"
    waterbox_status=Prop(4, 6),  # waterbox-status — "Water Tank Status"
    task_status=Prop(4, 7),  # task-status — "Host Task Status"
    break_point_restart=Prop(4, 11),  # break-point-restart — "Resume Cleaning Switch"
    carpet_press=Prop(4, 12),  # carpet-press — "Carpet Boost Switch"
)


DREAME_P2150A_CONSUMABLES = DreameConsumablesCapability(
    main_brush_life=Prop(9, 2),  # brush-life-level — "Cleaning Brush Remaining Life"
    main_brush_left_time=Prop(9, 1),  # brush-left-time — "Cleaning Brush Remaining Time"
    reset_main_brush=Action(9, 1),  # reset-brush-life — "Reset Cleaning Brush"
    side_brush_life=Prop(10, 2),  # brush-life-level — "Cleaning Brush Remaining Life"
    side_brush_left_time=Prop(10, 1),  # brush-left-time — "Cleaning Brush Remaining Time"
    reset_side_brush=Action(10, 1),  # reset-brush-life — "Reset Cleaning Brush"
    filter_life=Prop(11, 1),  # filter-life-level — "Filter Remaining Life"
    filter_left_time=Prop(11, 2),  # filter-left-time — "Filter Remaining Time"
    reset_filter=Action(11, 1),  # reset-filter-life — "Reset Filter"
)


DREAME_P2150A_CLEAN_HISTORY = DreameCleanHistoryCapability(
    service=12,
    first_clean_time=Prop(12, 1),  # first-clean-time — "First Cleaning Start Time"
    total_clean_time=Prop(12, 2),  # total-clean-time — "Total Cleaning Time"
    total_clean_times=Prop(12, 3),  # total-clean-times — "Total Cleaning Count"
    total_clean_area=Prop(12, 4),  # total-clean-area — "Total Cleaning Area"
)


DREAME_P2150A_DND = DreameDndCapability(
    service=5,
    enable=Prop(5, 1),  # enable — "Enable"
    start_time=Prop(5, 2),  # start-time — "Do Not Disturb Start Time"
    end_time=Prop(5, 3),  # end-time — "Do Not Disturb End Time"
)


DREAME_P2150A_VOICE = DreameAudioCapability(
    service=7,
    voice_packet_id=Prop(7, 2),  # voice-packet-id — "Voice Pack ID"
    voice_change_state=Prop(7, 3),  # voice-change-state — "Voice Pack Switching Status"
    set_voice=Prop(7, 4),  # set-voice — "Set Personalized Voice"
    locate=Action(7, 1),  # position — "Locate My Robot"
    play_sound=Action(7, 2),  # play-sound — "Voice Preview"
)


DREAME_P2150A = ModelProfile(
    profile_id="dreame.p2150a",
    brand="dreame",
    core=DREAME_P2150A_CORE,
    map=DREAME_P2150A_MAP,
    room_clean=DREAME_P2150A_ROOM_CLEAN,
    schedule=DREAME_P2150A_SCHEDULE,
    settings=DREAME_P2150A_SETTINGS,
    consumables=DREAME_P2150A_CONSUMABLES,
    clean_history=DREAME_P2150A_CLEAN_HISTORY,
    dnd=DREAME_P2150A_DND,
    voice=DREAME_P2150A_VOICE,
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:dreame-p2150a:2",),
)


DREAME_R2205_MAP = DreameMapCapability(
    service=6,
    map_data=Prop(6, 1),  # map-data — "Map Data"
    frame_info=Prop(6, 2),  # frame-info — "Frame Information"
    object_name=Prop(6, 3),  # object-name — "Intermediate Map Data File Name on FDS"
    map_extend_data=Prop(6, 4),  # map-extend-data — "Map Editing Parameters"
    robot_time=Prop(6, 5),  # robot-time — "Host Current Timestamp"
    result_code=Prop(6, 6),  # result-code — "Map Editing Response Code"
    mult_map_state=Prop(6, 7),  # mult-map-state — "Set Multi-layer Map Switch"
    mult_map_info=Prop(6, 8),  # mult-map-info — "Multi-layer Map Information"
    map_req=Action(6, 1, in_piid=2, out_piids=(1, 3, 5)),  # map-req — "Request Map Data"
    update_map=Action(6, 2, in_piid=4, out_piids=(6,)),  # update-map — "Update Map Information"
)


DREAME_R2205_ROOM_CLEAN = RoomCleanCapability(
    room_ids=Prop(2, 4),  # room-ids — "Mi Home Room ID Parameter"
    start=Action(2, 3, in_piid=4),  # start-room-sweep — "Clean Room"
)


DREAME_R2205_SCHEDULE = DreameScheduleCapability(
    service=8,
    time_zone=Prop(8, 1),  # time-zone — "Host Timezone Retrieval"
    timer_clean=Prop(8, 2),  # timer-clean — "Scheduled Reservation Cleaning"
    timer_id=Prop(8, 3),  # timer-id — "Reservation ID"
    delete_timer=Action(8, 1, in_piid=3),  # delete-timer — "Delete Scheduled Reservation"
)


DREAME_R2205_SETTINGS = DreameSettingsCapability(
    service=4,
    cleaning_mode=Prop(4, 4),  # cleaning-mode — "Cleaning Mode"
    mop_mode=Prop(4, 5),  # mop-mode — "Water Level Settings in Mopping Mode"
    waterbox_status=Prop(4, 6),  # waterbox-status — "Water Tank Status"
    task_status=Prop(4, 7),  # task-status — "Host Task Status"
    break_point_restart=Prop(4, 11),  # break-point-restart — "Resume Cleaning Switch"
    carpet_press=Prop(4, 12),  # carpet-press — "Carpet Boost Switch"
)


DREAME_R2205_CONSUMABLES = DreameConsumablesCapability(
    main_brush_life=Prop(9, 2),  # brush-life-level — "Cleaning Brush Remaining Life"
    main_brush_left_time=Prop(9, 1),  # brush-left-time — "Cleaning Brush Remaining Time"
    reset_main_brush=Action(9, 1),  # reset-brush-life — "Reset Cleaning Brush"
    side_brush_life=Prop(10, 2),  # brush-life-level — "Cleaning Brush Remaining Life"
    side_brush_left_time=Prop(10, 1),  # brush-left-time — "Cleaning Brush Remaining Time"
    reset_side_brush=Action(10, 1),  # reset-brush-life — "Reset Cleaning Brush"
    filter_life=Prop(11, 1),  # filter-life-level — "Filter Remaining Life"
    filter_left_time=Prop(11, 2),  # filter-left-time — "Filter Remaining Time"
    reset_filter=Action(11, 1),  # reset-filter-life — "Reset Filter"
)


DREAME_R2205_CLEAN_HISTORY = DreameCleanHistoryCapability(
    service=12,
    first_clean_time=Prop(12, 1),  # first-clean-time — "First Cleaning Start Time"
    total_clean_time=Prop(12, 2),  # total-clean-time — "Total Cleaning Time"
    total_clean_times=Prop(12, 3),  # total-clean-times — "Total Cleaning Count"
    total_clean_area=Prop(12, 4),  # total-clean-area — "Total Cleaning Area"
)


DREAME_R2205_DND = DreameDndCapability(
    service=5,
    enable=Prop(5, 1),  # enable — "Enable"
    start_time=Prop(5, 2),  # start-time — "Do Not Disturb Start Time"
    end_time=Prop(5, 3),  # end-time — "Do Not Disturb End Time"
)


DREAME_R2205_VOICE = DreameAudioCapability(
    service=7,
    voice_packet_id=Prop(7, 2),  # voice-packet-id — "Voice Pack ID"
    voice_change_state=Prop(7, 3),  # voice-change-state — "Voice Pack Switching Status"
    set_voice=Prop(7, 4),  # set-voice — "Set Personalized Voice"
    locate=Action(7, 1),  # position — "Locate My Robot"
    play_sound=Action(7, 2),  # play-sound — "Voice Preview"
)


DREAME_R2205 = ModelProfile(
    profile_id="dreame.r2205",
    brand="dreame",
    core=DREAME_P2114A_CORE,
    map=DREAME_R2205_MAP,
    room_clean=DREAME_R2205_ROOM_CLEAN,
    schedule=DREAME_R2205_SCHEDULE,
    settings=DREAME_R2205_SETTINGS,
    consumables=DREAME_R2205_CONSUMABLES,
    clean_history=DREAME_R2205_CLEAN_HISTORY,
    dnd=DREAME_R2205_DND,
    voice=DREAME_R2205_VOICE,
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:dreame-r2205:2",),
)


DREAME_R2209_MAP = DreameMapCapability(
    service=6,
    map_data=Prop(6, 1),  # map-data — "Map Data"
    frame_info=Prop(6, 2),  # frame-info — "Frame Information"
    object_name=Prop(6, 3),  # object-name — "Intermediate Map Data File Name on FDS"
    map_extend_data=Prop(6, 4),  # map-extend-data — "Map Editing Parameters"
    robot_time=Prop(6, 5),  # robot-time — "Host Current Timestamp"
    result_code=Prop(6, 6),  # result-code — "Map Editing Response Code"
    mult_map_info=Prop(6, 8),  # mult-map-info — "Multi-layer Map Information"
    map_req=Action(6, 1, in_piid=2, out_piids=(1, 3, 5)),  # map-req — "Request Map Data"
    update_map=Action(6, 2, in_piid=4, out_piids=(6,)),  # update-map — "Update Map Information"
)


DREAME_R2209_ROOM_CLEAN = RoomCleanCapability(
    room_ids=Prop(2, 4),  # room-ids — "Mi Home Room ID Parameter"
    start=Action(2, 3, in_piid=4),  # start-room-sweep — "Clean Room"
)


DREAME_R2209_SCHEDULE = DreameScheduleCapability(
    service=8,
    time_zone=Prop(8, 1),  # time-zone — "Host Timezone Retrieval"
    timer_clean=Prop(8, 2),  # timer-clean — "Scheduled Reservation Cleaning"
    timer_id=Prop(8, 3),  # timer-id — "Reservation ID"
    delete_timer=Action(8, 1, in_piid=3),  # delete-timer — "Delete Scheduled Reservation"
)


DREAME_R2209_SETTINGS = DreameSettingsCapability(
    service=4,
    cleaning_mode=Prop(4, 4),  # cleaning-mode — "Cleaning Mode"
    mop_mode=Prop(4, 5),  # mop-mode — "Water Level Settings in Mopping Mode"
    waterbox_status=Prop(4, 6),  # waterbox-status — "Water Tank Status"
    task_status=Prop(4, 7),  # task-status — "Host Task Status"
    break_point_restart=Prop(4, 11),  # break-point-restart — "Resume Cleaning Switch"
    carpet_press=Prop(4, 12),  # carpet-press — "Carpet Boost Switch"
)


DREAME_R2209_CONSUMABLES = DreameConsumablesCapability(
    main_brush_life=Prop(9, 2),  # brush-life-level — "Cleaning Brush Remaining Life"
    main_brush_left_time=Prop(9, 1),  # brush-left-time — "Cleaning Brush Remaining Time"
    reset_main_brush=Action(9, 1),  # reset-brush-life — "Reset Cleaning Brush"
    side_brush_life=Prop(10, 2),  # brush-life-level — "Cleaning Brush Remaining Life"
    side_brush_left_time=Prop(10, 1),  # brush-left-time — "Cleaning Brush Remaining Time"
    reset_side_brush=Action(10, 1),  # reset-brush-life — "Reset Cleaning Brush"
    filter_life=Prop(11, 1),  # filter-life-level — "Filter Remaining Life"
    filter_left_time=Prop(11, 2),  # filter-left-time — "Filter Remaining Time"
    reset_filter=Action(11, 1),  # reset-filter-life — "Reset Filter"
)


DREAME_R2209_CLEAN_HISTORY = DreameCleanHistoryCapability(
    service=12,
    first_clean_time=Prop(12, 1),  # first-clean-time — "First Cleaning Start Time"
    total_clean_time=Prop(12, 2),  # total-clean-time — "Total Cleaning Time"
    total_clean_times=Prop(12, 3),  # total-clean-times — "Total Cleaning Count"
    total_clean_area=Prop(12, 4),  # total-clean-area — "Total Cleaning Area"
)


DREAME_R2209_DND = DreameDndCapability(
    service=5,
    enable=Prop(5, 1),  # enable — "Enable"
    start_time=Prop(5, 2),  # start-time — "Do Not Disturb Start Time"
    end_time=Prop(5, 3),  # end-time — "Do Not Disturb End Time"
)


DREAME_R2209_VOICE = DreameAudioCapability(
    service=7,
    voice_packet_id=Prop(7, 2),  # voice-packet-id — "Voice Pack ID"
    voice_change_state=Prop(7, 3),  # voice-change-state — "Voice Pack Switching Status"
    set_voice=Prop(7, 4),  # set-voice — "Set Personalized Voice"
    locate=Action(7, 1),  # position — "Locate My Robot"
    play_sound=Action(7, 2),  # play-sound — "Voice Preview"
)


DREAME_R2209 = ModelProfile(
    profile_id="dreame.r2209",
    brand="dreame",
    core=DREAME_P2114A_CORE,
    map=DREAME_R2209_MAP,
    room_clean=DREAME_R2209_ROOM_CLEAN,
    schedule=DREAME_R2209_SCHEDULE,
    settings=DREAME_R2209_SETTINGS,
    consumables=DREAME_R2209_CONSUMABLES,
    clean_history=DREAME_R2209_CLEAN_HISTORY,
    dnd=DREAME_R2209_DND,
    voice=DREAME_R2209_VOICE,
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:dreame-r2209:2",),
)


DREAME_R2210_MAP = DreameMapCapability(
    service=6,
    map_data=Prop(6, 1),  # map-data — "Map Data"
    frame_info=Prop(6, 2),  # frame-info — "Frame Information"
    object_name=Prop(6, 3),  # object-name — "Intermediate Map Data File Name on FDS"
    map_extend_data=Prop(6, 4),  # map-extend-data — "Map Editing Parameters"
    robot_time=Prop(6, 5),  # robot-time — "Host Current Timestamp"
    result_code=Prop(6, 6),  # result-code — "Map Editing Response Code"
    map_req=Action(6, 1, in_piid=2, out_piids=(1, 3, 5)),  # map-req — "Request Map Data"
    update_map=Action(6, 2, in_piid=4, out_piids=(6,)),  # update-map — "Update Map Information"
)


DREAME_R2210_ROOM_CLEAN = RoomCleanCapability(
    room_ids=Prop(2, 4),  # room-ids — "Mi Home Room ID Parameter"
    start=Action(2, 3, in_piid=4),  # start-room-sweep — "Clean Room"
)


DREAME_R2210_SCHEDULE = DreameScheduleCapability(
    service=8,
    time_zone=Prop(8, 1),  # time-zone — "Host Timezone Retrieval"
    timer_clean=Prop(8, 2),  # timer-clean — "Scheduled Reservation Cleaning"
    timer_id=Prop(8, 3),  # timer-id — "Reservation ID"
    delete_timer=Action(8, 1, in_piid=3),  # delete-timer — "Delete Scheduled Reservation"
)


DREAME_R2210_SETTINGS = DreameSettingsCapability(
    service=4,
    cleaning_mode=Prop(4, 4),  # cleaning-mode — "Cleaning Mode"
    mop_mode=Prop(4, 5),  # mop-mode — "Water Level Settings in Mopping Mode"
    waterbox_status=Prop(4, 6),  # waterbox-status — "Water Tank Status"
    task_status=Prop(4, 7),  # task-status — "Host Task Status"
    break_point_restart=Prop(4, 11),  # break-point-restart — "Resume Cleaning Switch"
    carpet_press=Prop(4, 12),  # carpet-press — "Carpet Boost Switch"
    child_lock=Prop(4, 27),  # child-lock — "Child Lock"
)


DREAME_R2210_CONSUMABLES = DreameConsumablesCapability(
    main_brush_life=Prop(9, 2),  # brush-life-level — "Cleaning Brush Remaining Life"
    main_brush_left_time=Prop(9, 1),  # brush-left-time — "Cleaning Brush Remaining Time"
    reset_main_brush=Action(9, 1),  # reset-brush-life — "Reset Cleaning Brush"
    side_brush_life=Prop(10, 2),  # brush-life-level — "Cleaning Brush Remaining Life"
    side_brush_left_time=Prop(10, 1),  # brush-left-time — "Cleaning Brush Remaining Time"
    reset_side_brush=Action(10, 1),  # reset-brush-life — "Reset Cleaning Brush"
    filter_life=Prop(11, 1),  # filter-life-level — "Filter Remaining Life"
    filter_left_time=Prop(11, 2),  # filter-left-time — "Filter Remaining Time"
    reset_filter=Action(11, 1),  # reset-filter-life — "Reset Filter"
    mop_life=Prop(18, 1),  # mop-life-level — "Mop Remaining Life"
    mop_left_time=Prop(18, 2),  # mop-left-time — "Mop Remaining Time"
    reset_mop=Action(18, 1),  # reset-mop-life — "Reset Mop"
    detergent_life=Prop(20, 1),  # life-level — "Cleaning Solution Remaining Life"
    reset_detergent=Action(20, 1),  # reset-life — "Reset"
)


DREAME_R2210_CLEAN_HISTORY = DreameCleanHistoryCapability(
    service=12,
    first_clean_time=Prop(12, 1),  # first-clean-time — "First Cleaning Start Time"
    total_clean_time=Prop(12, 2),  # total-clean-time — "Total Cleaning Time"
    total_clean_times=Prop(12, 3),  # total-clean-times — "Total Cleaning Count"
    total_clean_area=Prop(12, 4),  # total-clean-area — "Total Cleaning Area"
)


DREAME_R2210_DND = DreameDndCapability(
    service=5,
    enable=Prop(5, 1),  # enable — "Enable"
    start_time=Prop(5, 2),  # start-time — "Do Not Disturb Start Time"
    end_time=Prop(5, 3),  # end-time — "Do Not Disturb End Time"
)


DREAME_R2210_VOICE = DreameAudioCapability(
    service=7,
    voice_packet_id=Prop(7, 2),  # voice-packet-id — "Voice Pack ID"
    voice_change_state=Prop(7, 3),  # voice-change-state — "Voice Pack Switching Status"
    set_voice=Prop(7, 4),  # set-voice — "Set Personalized Voice"
    locate=Action(7, 1),  # position — "Locate My Robot"
    play_sound=Action(7, 2),  # play-sound — "Voice Preview"
)


DREAME_R2210 = ModelProfile(
    profile_id="dreame.r2210",
    brand="dreame",
    core=DREAME_P2114A_CORE,
    map=DREAME_R2210_MAP,
    room_clean=DREAME_R2210_ROOM_CLEAN,
    schedule=DREAME_R2210_SCHEDULE,
    settings=DREAME_R2210_SETTINGS,
    consumables=DREAME_R2210_CONSUMABLES,
    clean_history=DREAME_R2210_CLEAN_HISTORY,
    dnd=DREAME_R2210_DND,
    voice=DREAME_R2210_VOICE,
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:dreame-r2210:1",),
)


DREAME_R2211O_MAP = DreameMapCapability(
    service=6,
    map_data=Prop(6, 1),  # map-data — "Map Data"
    frame_info=Prop(6, 2),  # frame-info — "Frame Information"
    object_name=Prop(6, 3),  # object-name — "Intermediate Map Data File Name on FDS"
    map_extend_data=Prop(6, 4),  # map-extend-data — "Map Editing Parameters"
    robot_time=Prop(6, 5),  # robot-time — "Host Current Timestamp"
    result_code=Prop(6, 6),  # result-code — "Map Editing Response Code"
    mult_map_info=Prop(6, 8),  # mult-map-info — "Multi-layer Map Information"
    map_req=Action(6, 1, in_piid=2, out_piids=(1, 3, 5)),  # map-req — "Request Map Data"
    update_map=Action(6, 2, in_piid=4, out_piids=(6,)),  # update-map — "Update Map Information"
)


DREAME_R2211O_ROOM_CLEAN = RoomCleanCapability(
    room_ids=Prop(2, 4),  # room-ids — "Mi Home Room ID Parameter"
    start=Action(2, 3, in_piid=4),  # start-room-sweep — "Clean Room"
)


DREAME_R2211O_SCHEDULE = DreameScheduleCapability(
    service=8,
    time_zone=Prop(8, 1),  # time-zone — "Host Timezone Retrieval"
    timer_clean=Prop(8, 2),  # timer-clean — "Scheduled Reservation Cleaning"
    timer_id=Prop(8, 3),  # timer-id — "Reservation ID"
    delete_timer=Action(8, 1, in_piid=3),  # delete-timer — "Delete Scheduled Reservation"
)


DREAME_R2211O_SETTINGS = DreameSettingsCapability(
    service=4,
    cleaning_mode=Prop(4, 4),  # cleaning-mode — "Cleaning Mode"
    mop_mode=Prop(4, 5),  # mop-mode — "Water Level Settings in Mopping Mode"
    waterbox_status=Prop(4, 6),  # waterbox-status — "Mop Installation Status"
    task_status=Prop(4, 7),  # task-status — "Host Task Status"
    break_point_restart=Prop(4, 11),  # break-point-restart — "Resume Cleaning Switch"
    carpet_press=Prop(4, 12),  # carpet-press — "Carpet Boost Switch"
    child_lock=Prop(4, 27),  # child-lock — "Child Lock Switch (0: Off, 1: On)"
)


DREAME_R2211O_CONSUMABLES = DreameConsumablesCapability(
    main_brush_life=Prop(9, 2),  # brush-life-level — "Cleaning Brush Remaining Life"
    main_brush_left_time=Prop(9, 1),  # brush-left-time — "Cleaning Brush Remaining Time"
    reset_main_brush=Action(9, 1),  # reset-brush-life — "Reset Cleaning Brush"
    side_brush_life=Prop(10, 2),  # brush-life-level — "Cleaning Brush Remaining Life"
    side_brush_left_time=Prop(10, 1),  # brush-left-time — "Cleaning Brush Remaining Time"
    reset_side_brush=Action(10, 1),  # reset-brush-life — "Reset Cleaning Brush"
    filter_life=Prop(11, 1),  # filter-life-level — "Filter Screen Remaining Life"
    filter_left_time=Prop(11, 2),  # filter-left-time — "Filter Screen Remaining Time"
    reset_filter=Action(11, 1),  # reset-filter-life — "Reset Filter Screen"
    mop_life=Prop(18, 1),  # mop-life-level — "Mop Remaining Life"
    mop_left_time=Prop(18, 2),  # mop-left-time — "Mop Remaining Time"
    reset_mop=Action(18, 1),  # reset-mop-life — "Reset Mop"
)


DREAME_R2211O_CLEAN_HISTORY = DreameCleanHistoryCapability(
    service=12,
    first_clean_time=Prop(12, 1),  # first-clean-time — "First Cleaning Start Time"
    total_clean_time=Prop(12, 2),  # total-clean-time — "Total Cleaning Time"
    total_clean_times=Prop(12, 3),  # total-clean-times — "Total Cleaning Count"
    total_clean_area=Prop(12, 4),  # total-clean-area — "Total Cleaning Area"
)


DREAME_R2211O_DND = DreameDndCapability(
    service=5,
    enable=Prop(5, 1),  # enable — "Enable"
    start_time=Prop(5, 2),  # start-time — "Do Not Disturb Start Time"
    end_time=Prop(5, 3),  # end-time — "Do Not Disturb End Time"
)


DREAME_R2211O_VOICE = DreameAudioCapability(
    service=7,
    voice_packet_id=Prop(7, 2),  # voice-packet-id — "Voice Pack ID"
    voice_change_state=Prop(7, 3),  # voice-change-state — "Voice Pack Switching Status"
    set_voice=Prop(7, 4),  # set-voice — "Set Personalized Voice"
    locate=Action(7, 1),  # position — "Locate My Robot"
    play_sound=Action(7, 2),  # play-sound — "Voice Preview"
)


DREAME_R2211O = ModelProfile(
    profile_id="dreame.r2211o",
    brand="dreame",
    core=DREAME_P2149O_CORE,
    map=DREAME_R2211O_MAP,
    room_clean=DREAME_R2211O_ROOM_CLEAN,
    schedule=DREAME_R2211O_SCHEDULE,
    settings=DREAME_R2211O_SETTINGS,
    consumables=DREAME_R2211O_CONSUMABLES,
    clean_history=DREAME_R2211O_CLEAN_HISTORY,
    dnd=DREAME_R2211O_DND,
    voice=DREAME_R2211O_VOICE,
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:dreame-r2211o:2",),
)


DREAME_R2215_CORE = CoreCapability(
    status=Prop(2, 1),  # status — "Working Status"
    fault=Prop(2, 2),  # fault — "Fault"
    mode=Prop(2, 3),  # mode — "Mode"
    battery=Prop(3, 1),  # battery-level — "Battery Level"
    charging_state=Prop(3, 2),  # charging-state — "Battery Charging Status"
    fan_speed=Prop(4, 4),  # cleaning-mode — "Cleaning Mode"
    water_level=Prop(4, 5),  # mop-mode — "Water Level Settings in Mopping Mode"
    volume=Prop(7, 1),  # volume — "Volume"
    start=Action(2, 1),  # start-sweep — "Start Cleaning"
    stop=Action(2, 2),  # stop-sweeping — "Pause"
    charge=Action(3, 1),  # start-charge — "Return to Charge"
    locate=Action(7, 1),  # position — "Locate My Robot"
    status_map={1: 'cleaning', 2: 'idle', 3: 'paused', 4: 'error', 5: 'returning', 6: 'docked'},
    modes={'silent': 0, 'basic': 1, 'strong': 2, 'full_speed': 3},
    fan_speeds={'quiet': 0, 'standard': 1, 'medium': 2, 'strong': 3},
    water_levels={'low': 1, 'middle': 2, 'height': 3},
)


DREAME_R2215_MAP = DreameMapCapability(
    service=6,
    map_data=Prop(6, 1),  # map-data — "Map Data"
    frame_info=Prop(6, 2),  # frame-info — "Frame Information"
    object_name=Prop(6, 3),  # object-name — "Intermediate Map Data File Name on FDS"
    map_extend_data=Prop(6, 4),  # map-extend-data — "Map Editing Parameters"
    robot_time=Prop(6, 5),  # robot-time — "Host Current Timestamp"
    result_code=Prop(6, 6),  # result-code — "Map Editing Response Code"
    mult_map_state=Prop(6, 7),  # mult-map-state — "Set Multi-layer Map Switch"
    mult_map_info=Prop(6, 8),  # mult-map-info — "Multi-layer Map Information"
    map_req=Action(6, 1, in_piid=2, out_piids=(1, 3, 5)),  # map-req — "Request Map Data"
    update_map=Action(6, 2, in_piid=4, out_piids=(6,)),  # update-map — "Update Map Information"
)


DREAME_R2215_ROOM_CLEAN = RoomCleanCapability(
    room_ids=Prop(2, 4),  # room-ids — "Mi Home Room ID Parameter"
    start=Action(2, 3, in_piid=4),  # start-room-sweep — "Clean Room"
)


DREAME_R2215_SCHEDULE = DreameScheduleCapability(
    service=8,
    time_zone=Prop(8, 1),  # time-zone — "Host Timezone Retrieval"
    timer_clean=Prop(8, 2),  # timer-clean — "Scheduled Reservation Cleaning"
    timer_id=Prop(8, 3),  # timer-id — "Reservation ID"
    delete_timer=Action(8, 1, in_piid=3),  # delete-timer — "Delete Scheduled Reservation"
)


DREAME_R2215_SETTINGS = DreameSettingsCapability(
    service=4,
    cleaning_mode=Prop(4, 4),  # cleaning-mode — "Cleaning Mode"
    mop_mode=Prop(4, 5),  # mop-mode — "Water Level Settings in Mopping Mode"
    waterbox_status=Prop(4, 6),  # waterbox-status — "Water Tank Status"
    task_status=Prop(4, 7),  # task-status — "Host Task Status"
    break_point_restart=Prop(4, 11),  # break-point-restart — "Resume Cleaning Switch"
    carpet_press=Prop(4, 12),  # carpet-press — "Carpet Boost Switch"
    child_lock=Prop(4, 27),  # child-lock — "Child Lock Switch"
)


DREAME_R2215_CONSUMABLES = DreameConsumablesCapability(
    main_brush_life=Prop(9, 2),  # brush-life-level — "Cleaning Brush Remaining Life"
    main_brush_left_time=Prop(9, 1),  # brush-left-time — "Cleaning Brush Remaining Time"
    reset_main_brush=Action(9, 1),  # reset-brush-life — "Reset Cleaning Brush"
    side_brush_life=Prop(10, 2),  # brush-life-level — "Cleaning Brush Remaining Life"
    side_brush_left_time=Prop(10, 1),  # brush-left-time — "Cleaning Brush Remaining Time"
    reset_side_brush=Action(10, 1),  # reset-brush-life — "Reset Cleaning Brush"
    filter_life=Prop(11, 1),  # filter-life-level — "Filter Remaining Life"
    filter_left_time=Prop(11, 2),  # filter-left-time — "Filter Remaining Time"
    reset_filter=Action(11, 1),  # reset-filter-life — "Reset Filter"
    mop_life=Prop(18, 1),  # mop-life-level — "Mop Remaining Life"
    mop_left_time=Prop(18, 2),  # mop-left-time — "Mop Remaining Time"
    reset_mop=Action(18, 1),  # reset-mop-life — "Reset Mop"
)


DREAME_R2215_CLEAN_HISTORY = DreameCleanHistoryCapability(
    service=12,
    first_clean_time=Prop(12, 1),  # first-clean-time — "First Cleaning Start Time"
    total_clean_time=Prop(12, 2),  # total-clean-time — "Total Cleaning Time"
    total_clean_times=Prop(12, 3),  # total-clean-times — "Total Cleaning Count"
    total_clean_area=Prop(12, 4),  # total-clean-area — "Total Cleaning Area"
)


DREAME_R2215_DND = DreameDndCapability(
    service=5,
    enable=Prop(5, 1),  # enable — "Enable"
    start_time=Prop(5, 2),  # start-time — "Do Not Disturb Start Time"
    end_time=Prop(5, 3),  # end-time — "Do Not Disturb End Time"
)


DREAME_R2215_VOICE = DreameAudioCapability(
    service=7,
    voice_packet_id=Prop(7, 2),  # voice-packet-id — "Voice Pack ID"
    voice_change_state=Prop(7, 3),  # voice-change-state — "Voice Pack Switching Status"
    set_voice=Prop(7, 4),  # set-voice — "Set Personalized Voice"
    locate=Action(7, 1),  # position — "Locate My Robot"
    play_sound=Action(7, 2),  # play-sound — "Voice Preview"
)


DREAME_R2215 = ModelProfile(
    profile_id="dreame.r2215",
    brand="dreame",
    core=DREAME_R2215_CORE,
    map=DREAME_R2215_MAP,
    room_clean=DREAME_R2215_ROOM_CLEAN,
    schedule=DREAME_R2215_SCHEDULE,
    settings=DREAME_R2215_SETTINGS,
    consumables=DREAME_R2215_CONSUMABLES,
    clean_history=DREAME_R2215_CLEAN_HISTORY,
    dnd=DREAME_R2215_DND,
    voice=DREAME_R2215_VOICE,
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:dreame-r2215:2",),
)


DREAME_R2216O_MAP = DreameMapCapability(
    service=6,
    map_data=Prop(6, 1),  # map-data — "Map Data"
    frame_info=Prop(6, 2),  # frame-info — "Frame Information"
    object_name=Prop(6, 3),  # object-name — "Intermediate Map Data File Name on FDS"
    map_extend_data=Prop(6, 4),  # map-extend-data — "Map Editing Parameters"
    robot_time=Prop(6, 5),  # robot-time — "Host Current Timestamp"
    result_code=Prop(6, 6),  # result-code — "Map Editing Response Code"
    mult_map_state=Prop(6, 7),  # mult-map-state — "Set Multi-layer Map Switch"
    mult_map_info=Prop(6, 8),  # mult-map-info — "Multi-layer Map Information"
    map_req=Action(6, 1, in_piid=2, out_piids=(1, 3, 5)),  # map-req — "Request Map Data"
    update_map=Action(6, 2, in_piid=4, out_piids=(6,)),  # update-map — "Update Map Information"
)


DREAME_R2216O_ROOM_CLEAN = RoomCleanCapability(
    room_ids=Prop(2, 4),  # room-ids — "Mi Home Room ID Parameter"
    start=Action(2, 3, in_piid=4),  # start-room-sweep — "Clean Room"
)


DREAME_R2216O_SCHEDULE = DreameScheduleCapability(
    service=8,
    time_zone=Prop(8, 1),  # time-zone — "Host Timezone Retrieval"
    timer_clean=Prop(8, 2),  # timer-clean — "Scheduled Reservation Cleaning"
    timer_id=Prop(8, 3),  # timer-id — "Reservation ID"
    delete_timer=Action(8, 1, in_piid=3),  # delete-timer — "Delete Scheduled Reservation"
)


DREAME_R2216O_SETTINGS = DreameSettingsCapability(
    service=4,
    cleaning_mode=Prop(4, 4),  # cleaning-mode — "Cleaning Mode"
    mop_mode=Prop(4, 5),  # mop-mode — "Water Level Settings in Mopping Mode"
    waterbox_status=Prop(4, 6),  # waterbox-status — "Mop Water Tank Installation Status"
    task_status=Prop(4, 7),  # task-status — "Host Task Status"
    break_point_restart=Prop(4, 11),  # break-point-restart — "Resume Cleaning Switch"
    carpet_press=Prop(4, 12),  # carpet-press — "Carpet Boost Switch"
    child_lock=Prop(4, 27),  # child-lock — "Child Lock Switch (0: Off, 1: On)"
)


DREAME_R2216O_CONSUMABLES = DreameConsumablesCapability(
    main_brush_life=Prop(9, 2),  # brush-life-level — "Cleaning Brush Remaining Life"
    main_brush_left_time=Prop(9, 1),  # brush-left-time — "Cleaning Brush Remaining Time"
    reset_main_brush=Action(9, 1),  # reset-brush-life — "Reset Cleaning Brush"
    side_brush_life=Prop(10, 2),  # brush-life-level — "Cleaning Brush Remaining Life"
    side_brush_left_time=Prop(10, 1),  # brush-left-time — "Cleaning Brush Remaining Time"
    reset_side_brush=Action(10, 1),  # reset-brush-life — "Reset Cleaning Brush"
    filter_life=Prop(11, 1),  # filter-life-level — "Filter Remaining Life"
    filter_left_time=Prop(11, 2),  # filter-left-time — "Filter Remaining Time"
    reset_filter=Action(11, 1),  # reset-filter-life — "Reset Filter"
)


DREAME_R2216O_CLEAN_HISTORY = DreameCleanHistoryCapability(
    service=12,
    first_clean_time=Prop(12, 1),  # first-clean-time — "First Cleaning Start Time"
    total_clean_time=Prop(12, 2),  # total-clean-time — "Total Cleaning Time"
    total_clean_times=Prop(12, 3),  # total-clean-times — "Total Cleaning Count"
    total_clean_area=Prop(12, 4),  # total-clean-area — "Total Cleaning Area"
)


DREAME_R2216O_DND = DreameDndCapability(
    service=5,
    enable=Prop(5, 1),  # enable — "Enable"
    start_time=Prop(5, 2),  # start-time — "Do Not Disturb Start Time"
    end_time=Prop(5, 3),  # end-time — "Do Not Disturb End Time"
)


DREAME_R2216O_VOICE = DreameAudioCapability(
    service=7,
    voice_packet_id=Prop(7, 2),  # voice-packet-id — "Voice Pack ID"
    voice_change_state=Prop(7, 3),  # voice-change-state — "Voice Pack Switching Status"
    set_voice=Prop(7, 4),  # set-voice — "Set Personalized Voice"
    locate=Action(7, 1),  # position — "Locate My Robot"
    play_sound=Action(7, 2),  # play-sound — "Voice Preview"
)


DREAME_R2216O = ModelProfile(
    profile_id="dreame.r2216o",
    brand="dreame",
    core=DREAME_P2114A_CORE,
    map=DREAME_R2216O_MAP,
    room_clean=DREAME_R2216O_ROOM_CLEAN,
    schedule=DREAME_R2216O_SCHEDULE,
    settings=DREAME_R2216O_SETTINGS,
    consumables=DREAME_R2216O_CONSUMABLES,
    clean_history=DREAME_R2216O_CLEAN_HISTORY,
    dnd=DREAME_R2216O_DND,
    voice=DREAME_R2216O_VOICE,
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:dreame-r2216o:1",),
)


DREAME_R2228_MAP = DreameMapCapability(
    service=6,
    map_data=Prop(6, 1),  # map-data — "Map Data"
    frame_info=Prop(6, 2),  # frame-info — "Frame Information"
    object_name=Prop(6, 3),  # object-name — "Intermediate Map Data File Name on FDS"
    map_extend_data=Prop(6, 4),  # map-extend-data — "Map Editing Parameters"
    robot_time=Prop(6, 5),  # robot-time — "Host Current Timestamp"
    result_code=Prop(6, 6),  # result-code — "Map Editing Response Code"
    mult_map_state=Prop(6, 7),  # mult-map-state — "Set Multi-layer Map Switch (1: Enable, 0: Disable)"
    mult_map_info=Prop(6, 8),  # mult-map-info — "Multi-layer Map Information"
    map_req=Action(6, 1, in_piid=2, out_piids=(1, 3, 5)),  # map-req — "Request Map Data"
    update_map=Action(6, 2, in_piid=4, out_piids=(6,)),  # update-map — "Update Map Information"
)


DREAME_R2228_ROOM_CLEAN = RoomCleanCapability(
    room_ids=Prop(2, 4),  # room-ids — "Mi Home Room ID Parameter"
    start=Action(2, 3, in_piid=4),  # start-room-sweep — "Clean Room"
)


DREAME_R2228_SCHEDULE = DreameScheduleCapability(
    service=8,
    time_zone=Prop(8, 1),  # time-zone — "Host Timezone Retrieval"
    timer_clean=Prop(8, 2),  # timer-clean — "Scheduled Reservation Cleaning"
    timer_id=Prop(8, 3),  # timer-id — "Reservation ID"
    delete_timer=Action(8, 1, in_piid=3),  # delete-timer — "Delete Scheduled Reservation"
)


DREAME_R2228_SETTINGS = DreameSettingsCapability(
    service=4,
    cleaning_mode=Prop(4, 4),  # cleaning-mode — "Cleaning Mode"
    mop_mode=Prop(4, 5),  # mop-mode — "Water Level Settings in Mopping Mode"
    waterbox_status=Prop(4, 6),  # waterbox-status — "Water Tank Status"
    task_status=Prop(4, 7),  # task-status — "Host Task Status"
    break_point_restart=Prop(4, 11),  # break-point-restart — "Resume Cleaning Switch"
    carpet_press=Prop(4, 12),  # carpet-press — "Carpet Boost Switch"
    child_lock=Prop(4, 27),  # child-lock — "Child Lock"
)


DREAME_R2228_CONSUMABLES = DreameConsumablesCapability(
    main_brush_life=Prop(9, 2),  # brush-life-level — "Cleaning Brush Remaining Life"
    main_brush_left_time=Prop(9, 1),  # brush-left-time — "Cleaning Brush Remaining Time"
    reset_main_brush=Action(9, 1),  # reset-brush-life — "Reset Cleaning Brush"
    side_brush_life=Prop(10, 2),  # brush-life-level — "Cleaning Brush Remaining Life"
    side_brush_left_time=Prop(10, 1),  # brush-left-time — "Cleaning Brush Remaining Time"
    reset_side_brush=Action(10, 1),  # reset-brush-life — "Reset Cleaning Brush"
    filter_life=Prop(11, 1),  # filter-life-level — "Filter Remaining Life"
    filter_left_time=Prop(11, 2),  # filter-left-time — "Filter Remaining Time"
    reset_filter=Action(11, 1),  # reset-filter-life — "Reset Filter"
    mop_life=Prop(18, 1),  # mop-life-level — "Mop Remaining Life"
    mop_left_time=Prop(18, 2),  # mop-left-time — "Mop Remaining Time"
    reset_mop=Action(18, 1),  # reset-mop-life — "Reset Mop"
    detergent_life=Prop(20, 1),  # life-level — "Cleaning Solution Remaining Life"
    reset_detergent=Action(20, 1),  # reset-life — "Reset"
)


DREAME_R2228_CLEAN_HISTORY = DreameCleanHistoryCapability(
    service=12,
    first_clean_time=Prop(12, 1),  # first-clean-time — "First Cleaning Start Time"
    total_clean_time=Prop(12, 2),  # total-clean-time — "Total Cleaning Time"
    total_clean_times=Prop(12, 3),  # total-clean-times — "Total Cleaning Count"
    total_clean_area=Prop(12, 4),  # total-clean-area — "Total Cleaning Area"
)


DREAME_R2228_DND = DreameDndCapability(
    service=5,
    enable=Prop(5, 1),  # enable — "Enable"
    start_time=Prop(5, 2),  # start-time — "Do Not Disturb Start Time"
    end_time=Prop(5, 3),  # end-time — "Do Not Disturb End Time"
)


DREAME_R2228_VOICE = DreameAudioCapability(
    service=7,
    voice_packet_id=Prop(7, 2),  # voice-packet-id — "Voice Pack ID"
    voice_change_state=Prop(7, 3),  # voice-change-state — "Voice Pack Switching Status"
    set_voice=Prop(7, 4),  # set-voice — "Set Personalized Voice"
    locate=Action(7, 1),  # position — "Locate My Robot"
    play_sound=Action(7, 2),  # play-sound — "Voice Preview"
)


DREAME_R2228 = ModelProfile(
    profile_id="dreame.r2228",
    brand="dreame",
    core=DREAME_P2114A_CORE,
    map=DREAME_R2228_MAP,
    room_clean=DREAME_R2228_ROOM_CLEAN,
    schedule=DREAME_R2228_SCHEDULE,
    settings=DREAME_R2228_SETTINGS,
    consumables=DREAME_R2228_CONSUMABLES,
    clean_history=DREAME_R2228_CLEAN_HISTORY,
    dnd=DREAME_R2228_DND,
    voice=DREAME_R2228_VOICE,
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:dreame-r2228:2",),
)


DREAME_R2235A_CORE = CoreCapability(
    status=Prop(2, 1),  # status — "Working Status"
    fault=Prop(2, 2),  # fault — "Fault"
    mode=Prop(2, 4),  # mode — "Mode"
    battery=Prop(3, 1),  # battery-level — "Battery Level"
    charging_state=Prop(3, 2),  # charging-state — "Battery Charging Status"
    start=Action(2, 1),  # start-sweep — "Start Sweeping"
    stop=Action(2, 2),  # stop-sweeping — "Stop Cleaning"
    charge=Action(3, 1),  # start-charge — "Start Charging"
    status_map={1: 'cleaning', 2: 'idle', 3: 'paused'},
    modes={'auto': 0},
)


DREAME_R2235A_ROOM_CLEAN = RoomCleanCapability(
    room_ids=Prop(2, 9),  # room-ids — "Mi Home Room ID Parameter"
    start=Action(2, 6, in_piid=9),  # start-room-sweep — "Clean Room"
)


DREAME_R2235A_CONSUMABLES = DreameConsumablesCapability(
    mop_life=Prop(9, 1),  # mop-life-level — "Mop Remaining Life"
    mop_left_time=Prop(9, 2),  # mop-left-time — "Mop Remaining Time"
    reset_mop=Action(9, 1),  # reset-mop-life — "Reset Mop Life"
)


DREAME_R2235A = ModelProfile(
    profile_id="dreame.r2235a",
    brand="dreame",
    core=DREAME_R2235A_CORE,
    room_clean=DREAME_R2235A_ROOM_CLEAN,
    consumables=DREAME_R2235A_CONSUMABLES,
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:dreame-r2235a:1",),
)


DREAME_R2254_MAP = DreameMapCapability(
    service=6,
    map_data=Prop(6, 1),  # map-data — "Map Data"
    frame_info=Prop(6, 2),  # frame-info — "Frame Information"
    object_name=Prop(6, 3),  # object-name — "Intermediate Map Data File Name on FDS"
    map_extend_data=Prop(6, 4),  # map-extend-data — "Map Editing Parameters"
    robot_time=Prop(6, 5),  # robot-time — "Host Current Timestamp"
    result_code=Prop(6, 6),  # result-code — "Map Editing Response Code"
    map_req=Action(6, 1, in_piid=2, out_piids=(1, 3, 5)),  # map-req — "Request Map Data"
    update_map=Action(6, 2, in_piid=4, out_piids=(6,)),  # update-map — "Update Map Information"
)


DREAME_R2254_ROOM_CLEAN = RoomCleanCapability(
    room_ids=Prop(2, 4),  # room-ids — "Mi Home Room ID Parameter"
    start=Action(2, 3, in_piid=4),  # start-room-sweep — "Clean Room"
)


DREAME_R2254_SCHEDULE = DreameScheduleCapability(
    service=8,
    time_zone=Prop(8, 1),  # time-zone — "Host Timezone Retrieval"
    timer_clean=Prop(8, 2),  # timer-clean — "Scheduled Reservation Cleaning"
    timer_id=Prop(8, 3),  # timer-id — "Reservation ID"
    delete_timer=Action(8, 1, in_piid=3),  # delete-timer — "Delete Scheduled Reservation"
)


DREAME_R2254_SETTINGS = DreameSettingsCapability(
    service=4,
    cleaning_mode=Prop(4, 4),  # cleaning-mode — "Cleaning Mode"
    mop_mode=Prop(4, 5),  # mop-mode — "Water Level Settings in Mopping Mode"
    waterbox_status=Prop(4, 6),  # waterbox-status — "Water Tank Status"
    task_status=Prop(4, 7),  # task-status — "Host Task Status"
    break_point_restart=Prop(4, 11),  # break-point-restart — "Resume Cleaning Switch"
    carpet_press=Prop(4, 12),  # carpet-press — "Carpet Boost Switch"
    child_lock=Prop(4, 27),  # child-lock — "Child Lock"
)


DREAME_R2254_CONSUMABLES = DreameConsumablesCapability(
    main_brush_life=Prop(9, 2),  # brush-life-level — "Cleaning Brush Remaining Life"
    main_brush_left_time=Prop(9, 1),  # brush-left-time — "Cleaning Brush Remaining Time"
    reset_main_brush=Action(9, 1),  # reset-brush-life — "Reset Cleaning Brush"
    side_brush_life=Prop(10, 2),  # brush-life-level — "Cleaning Brush Remaining Life"
    side_brush_left_time=Prop(10, 1),  # brush-left-time — "Cleaning Brush Remaining Time"
    reset_side_brush=Action(10, 1),  # reset-brush-life — "Reset Cleaning Brush"
    filter_life=Prop(11, 1),  # filter-life-level — "Filter Remaining Life"
    filter_left_time=Prop(11, 2),  # filter-left-time — "Filter Remaining Time"
    reset_filter=Action(11, 1),  # reset-filter-life — "Reset Filter"
    detergent_life=Prop(20, 1),  # life-level — "Cleaning Solution Remaining Life"
    reset_detergent=Action(20, 1),  # reset-life — "Reset"
)


DREAME_R2254_CLEAN_HISTORY = DreameCleanHistoryCapability(
    service=12,
    first_clean_time=Prop(12, 1),  # first-clean-time — "First Cleaning Start Time"
    total_clean_time=Prop(12, 2),  # total-clean-time — "Total Cleaning Time"
    total_clean_times=Prop(12, 3),  # total-clean-times — "Total Cleaning Count"
    total_clean_area=Prop(12, 4),  # total-clean-area — "Total Cleaning Area"
)


DREAME_R2254_DND = DreameDndCapability(
    service=5,
    enable=Prop(5, 1),  # enable — "Enable"
    start_time=Prop(5, 2),  # start-time — "Do Not Disturb Start Time"
    end_time=Prop(5, 3),  # end-time — "Do Not Disturb End Time"
)


DREAME_R2254_VOICE = DreameAudioCapability(
    service=7,
    voice_packet_id=Prop(7, 2),  # voice-packet-id — "Voice Pack ID"
    voice_change_state=Prop(7, 3),  # voice-change-state — "Voice Pack Switching Status"
    set_voice=Prop(7, 4),  # set-voice — "Set Personalized Voice"
    locate=Action(7, 1),  # position — "Locate My Robot"
    play_sound=Action(7, 2),  # play-sound — "Voice Preview"
)


DREAME_R2254 = ModelProfile(
    profile_id="dreame.r2254",
    brand="dreame",
    core=DREAME_P2114A_CORE,
    map=DREAME_R2254_MAP,
    room_clean=DREAME_R2254_ROOM_CLEAN,
    schedule=DREAME_R2254_SCHEDULE,
    settings=DREAME_R2254_SETTINGS,
    consumables=DREAME_R2254_CONSUMABLES,
    clean_history=DREAME_R2254_CLEAN_HISTORY,
    dnd=DREAME_R2254_DND,
    voice=DREAME_R2254_VOICE,
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:dreame-r2254:3",),
)


DREAME_R2257O_CORE = CoreCapability(
    status=Prop(2, 1),  # status — "Working Status"
    fault=Prop(2, 2),  # fault — "Fault"
    mode=Prop(2, 4),  # mode — "Mode"
    battery=Prop(3, 1),  # battery-level — "Battery Level"
    charging_state=Prop(3, 2),  # charging-state — "Battery Charging Status"
    start=Action(2, 1),  # start-sweep — "Start Sweeping"
    stop=Action(2, 2),  # stop-sweeping — "Stop Cleaning"
    charge=Action(3, 1),  # start-charge — "Start Charging"
    status_map={1: 'cleaning', 2: 'idle'},
    modes={'auto': 0},
)


DREAME_R2257O_ROOM_CLEAN = RoomCleanCapability(
    room_ids=Prop(2, 9),  # room-ids — "Mi Home Room ID Parameter"
    start=Action(2, 6, in_piid=9),  # start-room-sweep — "Clean Room"
)


DREAME_R2257O_CONSUMABLES = DreameConsumablesCapability(
    mop_life=Prop(9, 1),  # mop-life-level — "Mop Remaining Life"
    mop_left_time=Prop(9, 2),  # mop-left-time — "Mop Remaining Time"
    reset_mop=Action(9, 1),  # reset-mop-life — "Reset Mop Life"
)


DREAME_R2257O = ModelProfile(
    profile_id="dreame.r2257o",
    brand="dreame",
    core=DREAME_R2257O_CORE,
    room_clean=DREAME_R2257O_ROOM_CLEAN,
    consumables=DREAME_R2257O_CONSUMABLES,
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:dreame-r2257o:1",),
)
