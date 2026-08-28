"""Viomi runtime profiles.

See docs/dev/module-notes.md for design rationale and verification status.
"""

from __future__ import annotations

from ..types import (
    Action,
    CleanHistoryCapability,
    ConsumablesCapability,
    CoreCapability,
    DndCapability,
    MapCapability,
    ModelProfile,
    PointZoneCapability,
    Prop,
    RoomCleanCapability,
    ScheduleCapability,
    SettingsCapability,
    VoiceCapability,
)


VIOMI_V12_CORE = CoreCapability(
    status=Prop(2, 1),  # status — "Working Status"
    fault=Prop(2, 2),  # fault — "Fault"
    mode=Prop(2, 19),  # mode — "Suction Power"
    sweep_type=Prop(2, 4),  # sweep-type — "Cleaning Method"
    battery=Prop(3, 1),  # battery-level — "Battery Level"
    fan_speed=Prop(4, 17),  # suction-grade — "Suction Power"
    water_level=Prop(4, 18),  # water-grade — "Water Output Level"
    start=Action(2, 1),  # start-sweep — "Start Cleaning"
    stop=Action(2, 2),  # stop-sweeping — "Stop Cleaning"
    pause=Action(2, 3),  # pause — "Pause Work"
    charge=Action(2, 4),  # start-charge — "Start Return to Charge"
    locate=Action(8, 2),  # find-device — "Find Robot Vacuum"
    status_map={0: 'idle', 1: 'idle', 2: 'paused', 3: 'returning', 4: 'docked', 5: 'cleaning', 6: 'cleaning', 7: 'cleaning'},
    modes={'silent': 0, 'basic': 1, 'medium': 2, 'strong': 3},
    sweep_types={'global': 0, 'mop': 1, 'edge': 2, 'area': 3, 'point': 4, 'control': 5},
    fan_speeds={'quiet': 0, 'standard': 1, 'medium_gear': 2, 'strong': 3},
    water_levels={'1': 0, '2': 1, '3': 2},
)


VIOMI_V12_MAP = MapCapability(
    service=7,
    map_list=Prop(7, 11),  # map-list — "Map List Data [{name : 'Map 1',id:1585849584,cur : true},{name : 'Map 2',id : 1585849784,cur : false}]"
    current_path=Prop(7, 10),  # cur-cleaning-path — "Robot Current Cleaning Trajectory Coordinates : [3.456,4.555,0.2,1,5.456,4.555,0.233,0,......]"
    split_points=Prop(7, 8),  # split-points — "Two Endpoint Coordinates of Split Line Segment, e.g.: '3.45,6.78|4.56,-3.45'"
    arrange_room_ids=Prop(7, 6),  # arrange-room-ids — "Room ID parameters to merge, comma separated, e.g.: '10,11,12' means merge rooms with IDs 10,11,12;"
    get_map_list=Action(7, 11, out_piids=(11,)),  # get-map-list — "Get Map List Data"
    upload_by_mapid=Action(7, 2, in_piid=2),  # upload-by-mapid — "Upload Specified ID Map"
    set_current_map=Action(7, 3, in_piid=2),  # set-cur-map — "Set Current Map"
    del_map=Action(7, 5, in_piid=2),  # del-map — "Delete Specified ID Map"
    rename_map=Action(7, 7, in_piids=(2, 4)),  # rename-map — "Rename Map"
    rename_room=Action(7, 10, in_piids=(2, 7, 9)),  # rename-room — "Room Rename"
    arrange_room=Action(7, 8, in_piids=(2, 5, 6)),  # arrange-room — "Merge Room"
    split_room=Action(7, 9, in_piids=(2, 5, 7, 8)),  # split-room — "Split Room"
)


VIOMI_V12_ROOM_CLEAN = RoomCleanCapability(
    clean_room_ids=Prop(4, 20),  # clean-room-ids — "When selecting room cleaning, pass room ID string parameter, comma separated, e.g.: '10,11,12,13', if empty then global cleaning"
    clean_room_mode=Prop(4, 21),  # clean-room-mode — "Select Room Cleaning Mode"
    clean_room_oper=Prop(4, 22),  # clean-room-oper — "Select Room Cleaning Operation"
    set_room_clean=Action(4, 13, in_piids=(21, 22, 20)),  # set-room-clean — "Select Room Cleaning"
)


VIOMI_V12_SCHEDULE = ScheduleCapability(
    service=5,
    delete=Action(5, 2, in_piid=1),  # del — "Delete One Group of Reservation"
    get=Action(5, 3, out_piids=(22,)),  # get — "Get Reservation Data"
    order_id=Prop(5, 1),  # order-id — "Reservation ID"
    enable=Prop(5, 2),  # enable — "Whether to Enable This Reservation"
    day=Prop(5, 3),  # day — "After converting to binary, each bit represents a day, 1 - reserved 0 - not reserved, bit0-bit6 Sunday-Saturday"
    hour=Prop(5, 4),  # hour — "Reservation Hour (24-hour format)"
    minute=Prop(5, 5),  # minute — "Reservation Minute"
    repeat=Prop(5, 6),  # repeat — "Whether Repeat"
    clean_way=Prop(5, 8),  # clean-way — "Reservation Cleaning Method"
    suction=Prop(5, 9),  # suction — "Reservation Suction Power"
    water=Prop(5, 10),  # water — "Reservation Water Output Level"
    twice_clean=Prop(5, 11),  # twice-clean — "Whether Second Cleaning"
    mapid=Prop(5, 12),  # mapid — "Reservation Map ID, if no map then pass 0"
    room_count=Prop(5, 13),  # room-count — "Number of Reserved Rooms"
    room_data=Prop(5, 14),  # room-data — "Reservation Room Data JSON String [{name:'Room 1',id:10},{name:'Room 2',id:11},{...},{...}...]"
    orderdata=Prop(5, 22),  # orderdata — "N groups of reservation data separated by commas, specific data within each group separated by underscores {order_id}_{order_enable}_{week}_{hour}_{minute}_{repeat}_{mode}_{suction}_{water}_{twice}_{mapid}_{room_size}_{roomid}_{roomname}"
)


VIOMI_V12_SETTINGS = SettingsCapability(
    mop_route=Prop(4, 6),  # mop-route — "Mopping/Sweep-Mop Route"
    direction=Prop(4, 16),  # direction — "Remote Control Method Parameters"
)


VIOMI_V12_CONSUMABLES = ConsumablesCapability(
    side_brush_hours=Prop(4, 9),  # side-brush-hours — "Side Brush Remaining Life Hours"
    main_brush_hours=Prop(4, 11),  # main-brush-hours — "Main Brush Remaining Life Hours"
    hypa_hours=Prop(4, 13),  # hypa-hours — "HEPA Filter Remaining Life Hours"
    mop_hours=Prop(4, 15),  # mop-hours — "Mop Remaining Life Hours"
    door_state=Prop(2, 12),  # door-state — "Box Status"
    reset_consumable=Action(4, 11, in_piid=19),  # reset-consumable — "Reset Specified Consumable Usage Time"
)


VIOMI_V12_CLEAN_HISTORY = CleanHistoryCapability(
    start_time=Prop(4, 25),  # clean-start-time — "Cleaning Start Time, timestamp, unit seconds"
    use_time=Prop(4, 26),  # clean-use-time — "Cleaning Usage Time, unit seconds"
    clean_area=Prop(4, 27),  # clean-area — "Total Cleaning Area, unit m2"
    map_url=Prop(4, 28),  # clean-map-url — "Cleaning Map URL"
    clean_mode=Prop(4, 29),  # clean-mode — "Cleaning Mode"
    clean_way=Prop(4, 30),  # clean-way — "Cleaning Method"
    current_map=Prop(4, 32),  # cur-map-id — "Current Map ID"
)


VIOMI_V12_DND = DndCapability(
    service=5,
    enable=Prop(5, 15),  # dnd-enable — "Do Not Disturb Whether Enabled"
    start_hour=Prop(5, 16),  # dnd-start-hour — "Do Not Disturb Start Hour"
    start_minute=Prop(5, 17),  # dnd-start-minute — "Do Not Disturb Start Minute"
    end_hour=Prop(5, 18),  # dnd-end-hour — "Do Not Disturb End Hour"
    end_minute=Prop(5, 19),  # dnd-end-minute — "Do Not Disturb End Minute"
    timezone=Prop(5, 20),  # dnd-timezone — "Timezone Parameter"
)


VIOMI_V12_VOICE = VoiceCapability(
    service=8,
    download_voice=Action(8, 3, in_piids=(3, 7, 8)),  # download-voice — "Start Download Voice Pack"
    get_download_status=Action(8, 4, out_piids=(6, 3, 4, 5)),  # get-downloadstatus — "Get Voice Pack File Download Status"
    target_voice=Prop(8, 3),  # target-voice — "Currently Downloading Voice Pack Name"
    cur_voice=Prop(8, 4),  # cur-voice — "Currently Used Voice Pack Name"
    download_status=Prop(8, 5),  # download-status — "Download Status"
    download_progress=Prop(8, 6),  # download-progress — "Download Progress"
    voice_url=Prop(8, 7),  # voice-url — "Voice Pack Link to Download"
)


VIOMI_V12 = ModelProfile(
    profile_id="viomi.v12",
    brand="viomi",
    core=VIOMI_V12_CORE,
    map=VIOMI_V12_MAP,
    room_clean=VIOMI_V12_ROOM_CLEAN,
    schedule=VIOMI_V12_SCHEDULE,
    settings=VIOMI_V12_SETTINGS,
    consumables=VIOMI_V12_CONSUMABLES,
    clean_history=VIOMI_V12_CLEAN_HISTORY,
    dnd=VIOMI_V12_DND,
    voice=VIOMI_V12_VOICE,
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:viomi-v12:1",),
)


VIOMI_V13_CORE = CoreCapability(
    status=Prop(2, 1),  # status — "Working Status"
    fault=Prop(2, 2),  # fault — "Fault"
    mode=Prop(2, 19),  # mode — "Suction Power"
    sweep_type=Prop(2, 4),  # sweep-type
    battery=Prop(3, 1),  # battery-level — "Battery Level"
    fan_speed=Prop(4, 17),  # suction-grade — "Suction Power"
    water_level=Prop(4, 18),  # water-grade — "Water Output Level"
    start=Action(2, 1),  # start-sweep — "Start Work"
    stop=Action(2, 2),  # stop-sweeping — "Stop Work"
    pause=Action(2, 3),  # pause — "Pause Work"
    charge=Action(2, 4),  # start-charge — "Start Return to Charge"
    locate=Action(8, 2),  # find-device — "Find Robot Vacuum"
    status_map={0: 'idle', 1: 'idle', 2: 'paused', 3: 'returning', 4: 'docked', 5: 'cleaning', 6: 'cleaning', 7: 'cleaning'},
    modes={'silent': 0, 'basic': 1, 'medium': 2, 'strong': 3},
    sweep_types={'global': 0, 'mop': 1, 'edge': 2, 'area': 3, 'point': 4, 'control': 5},
    fan_speeds={'0': 0, '1': 1, '2': 2, '3': 3},
    water_levels={'gear_1': 0, 'gear_2': 1, 'gear_3': 2},
)


VIOMI_V13_MAP = MapCapability(
    service=7,
    map_list=Prop(7, 11),  # map-list — "Map List Data [{name : 'Map 1',id:1585849584,cur : true},{name : 'Map 2',id : 1585849784,cur : false}]"
    current_path=Prop(7, 10),  # cur-cleaning-path — "Robot Current Cleaning Trajectory Coordinates : [3.456,4.555,0.2,1,5.456,4.555,0.233,0,......]"
    split_points=Prop(7, 8),  # split-points — "Two Endpoint Coordinates of Split Line Segment, e.g.: '3.45,6.78|4.56,-3.45'"
    arrange_room_ids=Prop(7, 6),  # arrange-room-ids — "Room ID parameters to merge, comma separated, e.g.: '10,11,12' means merge rooms with IDs 10,11,12;"
    get_map_list=Action(7, 11, out_piids=(11,)),  # get-map-list — "Get Map List Data"
    upload_by_mapid=Action(7, 2, in_piid=2),  # upload-by-mapid — "Upload Specified ID Map"
    set_current_map=Action(7, 3, in_piid=2),  # set-cur-map — "Set Current Map"
    del_map=Action(7, 5, in_piid=2),  # del-map — "Delete Specified ID Map"
    rename_map=Action(7, 7, in_piids=(2, 4)),  # rename-map — "Rename Map"
    rename_room=Action(7, 10, in_piids=(2, 7, 9)),  # rename-room — "Room Rename"
    arrange_room=Action(7, 8, in_piids=(2, 5, 6)),  # arrange-room — "Merge Room"
    split_room=Action(7, 9, in_piids=(2, 5, 7, 8)),  # split-room — "Split Room"
)


VIOMI_V13_ROOM_CLEAN = RoomCleanCapability(
    clean_room_ids=Prop(4, 20),  # clean-room-ids — "When selecting room cleaning, pass room ID string parameter, comma separated, e.g.: '10,11,12,13', if empty then global cleaning"
    clean_room_mode=Prop(4, 21),  # clean-room-mode — "Select Room Cleaning Mode"
    clean_room_oper=Prop(4, 22),  # clean-room-oper — "Select Room Cleaning Operation"
    set_room_clean=Action(4, 13, in_piids=(21, 22, 20)),  # set-room-clean — "Select Room Cleaning"
)


VIOMI_V13_SCHEDULE = ScheduleCapability(
    service=5,
    delete=Action(5, 2, in_piid=1),  # del — "Delete One Group of Reservation"
    get=Action(5, 3, out_piids=(22,)),  # get — "Get Reservation Data"
    order_id=Prop(5, 1),  # order-id — "Reservation ID"
    enable=Prop(5, 2),  # enable — "Whether to Enable This Reservation"
    day=Prop(5, 3),  # day — "After converting to binary, each bit represents a day, 1 - reserved 0 - not reserved, bit0-bit6 Sunday-Saturday"
    hour=Prop(5, 4),  # hour — "Reservation Hour (24-hour format)"
    minute=Prop(5, 5),  # minute — "Reservation Minute"
    repeat=Prop(5, 6),  # repeat — "Whether Repeat"
    clean_way=Prop(5, 8),  # clean-way — "Reservation Cleaning Method"
    suction=Prop(5, 9),  # suction — "Reservation Suction Power"
    water=Prop(5, 10),  # water — "Reservation Water Output Level"
    twice_clean=Prop(5, 11),  # twice-clean — "Whether Second Cleaning"
    mapid=Prop(5, 12),  # mapid — "Reservation Map ID, if no map then pass 0"
    room_count=Prop(5, 13),  # room-count — "Number of Reserved Rooms"
    room_data=Prop(5, 14),  # room-data — "Reservation Room Data JSON String [{name:'Room 1',id:10},{name:'Room 2',id:11},{...},{...}...]"
    orderdata=Prop(5, 22),  # orderdata — "N groups of reservation data separated by commas, specific data within each group separated by underscores {order_id}_{order_enable}_{week}_{hour}_{minute}_{repeat}_{mode}_{suction}_{water}_{twice}_{mapid}_{room_size}_{roomid}_{roomname}"
)


VIOMI_V13_SETTINGS = SettingsCapability(
    mop_route=Prop(4, 6),  # mop-route — "Mopping/Sweep-Mop Route"
    direction=Prop(4, 16),  # direction — "Remote Control Method Parameters"
)


VIOMI_V13_CONSUMABLES = ConsumablesCapability(
    side_brush_hours=Prop(4, 9),  # side-brush-hours — "Side Brush Remaining Life Hours"
    main_brush_hours=Prop(4, 11),  # main-brush-hours — "Main Brush Remaining Life Hours"
    hypa_hours=Prop(4, 13),  # hypa-hours — "HEPA Filter Remaining Life Hours"
    mop_hours=Prop(4, 15),  # mop-hours — "Mop Remaining Life Hours"
    door_state=Prop(2, 12),  # door-state — "Box Status"
    reset_consumable=Action(4, 11, in_piid=19),  # reset-consumable — "Reset Specified Consumable Usage Time"
)


VIOMI_V13_CLEAN_HISTORY = CleanHistoryCapability(
    start_time=Prop(4, 25),  # clean-start-time — "Cleaning Start Time, timestamp, unit seconds"
    use_time=Prop(4, 26),  # clean-use-time — "Cleaning Usage Time, unit seconds"
    clean_area=Prop(4, 27),  # clean-area — "Total Cleaning Area, unit m2"
    map_url=Prop(4, 28),  # clean-map-url — "Cleaning Map URL"
    clean_mode=Prop(4, 29),  # clean-mode — "Cleaning Mode"
    clean_way=Prop(4, 30),  # clean-way — "Cleaning Method"
    current_map=Prop(4, 32),  # cur-map-id — "Current Map ID"
)


VIOMI_V13_DND = DndCapability(
    service=5,
    enable=Prop(5, 15),  # dnd-enable — "Do Not Disturb Whether Enabled"
    start_hour=Prop(5, 16),  # dnd-start-hour — "Do Not Disturb Start Hour"
    start_minute=Prop(5, 17),  # dnd-start-minute — "Do Not Disturb Start Minute"
    end_hour=Prop(5, 18),  # dnd-end-hour — "Do Not Disturb End Hour"
    end_minute=Prop(5, 19),  # dnd-end-minute — "Do Not Disturb End Minute"
    timezone=Prop(5, 20),  # dnd-timezone — "Timezone Parameter"
)


VIOMI_V13_VOICE = VoiceCapability(
    service=8,
    download_voice=Action(8, 3, in_piids=(3, 7, 8)),  # download-voice — "Start Download Voice Pack"
    get_download_status=Action(8, 4, out_piids=(6, 3, 4, 5)),  # get-downloadstatus — "Get Voice Pack File Download Status"
    target_voice=Prop(8, 3),  # target-voice — "Currently Downloading Voice Pack Name"
    cur_voice=Prop(8, 4),  # cur-voice — "Currently Used Voice Pack Name"
    download_status=Prop(8, 5),  # download-status — "Download Status"
    download_progress=Prop(8, 6),  # download-progress — "Download Progress"
    voice_url=Prop(8, 7),  # voice-url — "Voice Pack Link to Download"
)


VIOMI_V13 = ModelProfile(
    profile_id="viomi.v13",
    brand="viomi",
    core=VIOMI_V13_CORE,
    map=VIOMI_V13_MAP,
    room_clean=VIOMI_V13_ROOM_CLEAN,
    schedule=VIOMI_V13_SCHEDULE,
    settings=VIOMI_V13_SETTINGS,
    consumables=VIOMI_V13_CONSUMABLES,
    clean_history=VIOMI_V13_CLEAN_HISTORY,
    dnd=VIOMI_V13_DND,
    voice=VIOMI_V13_VOICE,
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:viomi-v13:2",),
)


VIOMI_V15_CORE = CoreCapability(
    status=Prop(2, 1),  # status — "Working Status"
    fault=Prop(2, 2),  # fault — "Fault"
    mode=Prop(2, 19),  # mode — "Suction Power"
    sweep_type=Prop(2, 4),  # sweep-type — "Cleaning Mode"
    battery=Prop(3, 1),  # battery-level — "Battery Level"
    fan_speed=Prop(4, 17),  # suction-grade — "Suction Power"
    water_level=Prop(4, 18),  # water-grade — "Water Output Level"
    start=Action(2, 1),  # start-sweep — "Start Work"
    stop=Action(2, 2),  # stop-sweeping — "Stop Work"
    pause=Action(2, 3),  # pause — "Pause Work"
    charge=Action(2, 4),  # start-charge — "Start Return to Charge"
    locate=Action(8, 2),  # find-device — "Find Robot Vacuum"
    status_map={0: 'idle', 1: 'idle', 2: 'paused', 3: 'returning', 4: 'docked', 5: 'cleaning', 6: 'cleaning', 7: 'cleaning'},
    modes={'silent': 0, 'basic': 1, 'medium': 2, 'strong': 3},
    sweep_types={'total': 0, 'wall': 2, 'zone': 3, 'point': 4, 'control': 5},
    fan_speeds={'quiet': 0, 'standard': 1, 'medium_gear': 2, 'strong': 3},
    water_levels={'gear_1': 0, 'gear_2': 1, 'gear_3': 2},
)


VIOMI_V15_MAP = MapCapability(
    service=7,
    map_list=Prop(7, 11),  # map-list — "Map list data Map-list:'[[...bkmap,...record,1620954322,...map name,1]]'. The array holds two maps. Per group: the 1st unique value is the URL the plugin redeems from Mijia, sent to the device when switching maps; the 2nd is used by the plugin to fetch map data (only needed for display in the map-management list and cleaning records); the 3rd is presumably the id; the 4th is the map name; the last value 1 = curmap (the currently displayed map)."
    current_path=Prop(7, 10),  # cur-cleaning-path — "Robot Current Cleaning Trajectory Coordinates : {deg:0.02,posArray:[[14,23],[23,22],[23,21]......]}"
    split_points=Prop(7, 8),  # split-points — "Two Endpoint Coordinates of Split Line Segment, e.g.: '3.45,6.78|4.56,-3.45'"
    arrange_room_ids=Prop(7, 6),  # arrange-room-ids — "Room ID parameters to merge, comma separated, e.g.: '10,11,12' means merge rooms with IDs 10,11,12;"
    get_map_list=Action(7, 11, out_piids=(11,)),  # get-map-list — "Get Map List Data"
    upload_by_mapid=Action(7, 2),  # upload-by-mapid — "Set Machine Actively Upload Specified ID Map to Specified URL"
    set_current_map=Action(7, 3, in_piids=(2, 15)),  # set-cur-map — "Set Current Map"
    del_map=Action(7, 5, in_piid=2),  # del-map — "Delete Specified ID Map"
    rename_map=Action(7, 7, in_piids=(2, 4)),  # rename-map — "Rename Map"
    rename_room=Action(7, 10, in_piids=(2, 7, 9, 14)),  # rename-room — "Room Rename"
    arrange_room=Action(7, 8, in_piids=(2, 5, 6, 14), out_piids=(13,)),  # arrange-room — "Merge Room"
    split_room=Action(7, 9, in_piids=(2, 5, 7, 8, 14)),  # split-room — "Split Room"
)


VIOMI_V15_ROOM_CLEAN = RoomCleanCapability(
    clean_room_ids=Prop(4, 38),  # clean-room-ids — "When selecting room cleaning, pass room ID string parameter, comma separated, e.g.: '10,11,12,13', if empty then global cleaning"
    clean_room_mode=Prop(4, 36),  # clean-room-mode — "Select Room Cleaning Mode"
    clean_room_oper=Prop(4, 37),  # clean-room-oper — "Select Room Cleaning Operation"
    set_room_clean=Action(4, 13, in_piids=(36, 37, 38)),  # set-room-clean — "Select Room Cleaning"
)


VIOMI_V15_SCHEDULE = ScheduleCapability(
    service=5,
    delete=Action(5, 2, in_piid=1),  # del — "Delete One Group of Reservation"
    get=Action(5, 3, out_piids=(22,)),  # get — "Get Reservation Data"
    order_id=Prop(5, 1),  # order-id — "Reservation ID"
    enable=Prop(5, 2),  # enable — "Whether to Enable This Reservation"
    day=Prop(5, 3),  # day — "After converting to binary, each bit represents a day, 1 - reserved 0 - not reserved, bit0-bit6 Sunday-Saturday"
    hour=Prop(5, 4),  # hour — "Reservation Hour (24-hour format)"
    minute=Prop(5, 5),  # minute — "Reservation Minute"
    repeat=Prop(5, 6),  # repeat — "Whether Repeat"
    clean_way=Prop(5, 8),  # clean-way — "Reservation Cleaning Method"
    suction=Prop(5, 9),  # suction — "Reservation Suction Power"
    water=Prop(5, 10),  # water — "Reservation Water Output Level"
    twice_clean=Prop(5, 11),  # twice-clean — "Whether Second Cleaning"
    mapid=Prop(5, 12),  # mapid — "Reservation Map ID, if no map then pass 0"
    room_count=Prop(5, 13),  # room-count — "Number of Reserved Rooms"
    room_data=Prop(5, 14),  # room-data — "Reservation Room Data JSON String [{name:'Room 1',id:10},{name:'Room 2',id:11},{...},{...}...]"
    orderdata=Prop(5, 22),  # orderdata — "N groups of reservation data separated by commas, specific data within each group separated by underscores {order_id}_{order_enable}_{week}_{hour}_{minute}_{repeat}_{mode}_{suction}_{water}_{twice}_{mapid}_{room_size}_{roomid}_{roomname}"
)


VIOMI_V15_SETTINGS = SettingsCapability(
    mop_route=Prop(4, 6),  # mop-route — "Mopping/Sweep-Mop Route"
    direction=Prop(4, 16),  # direction — "Remote Control Method Parameters"
)


VIOMI_V15_CONSUMABLES = ConsumablesCapability(
    side_brush_hours=Prop(4, 9),  # side-brush-hours — "Side Brush Remaining Life Hours"
    main_brush_hours=Prop(4, 11),  # main-brush-hours — "Main Brush Remaining Life Hours"
    hypa_hours=Prop(4, 13),  # hypa-hours — "Dust Bin Remaining Life Hours"
    mop_hours=Prop(4, 15),  # mop-hours — "Mop Remaining Life Hours"
    door_state=Prop(2, 12),  # door-state — "Box Status"
    reset_consumable=Action(4, 11, in_piid=35),  # reset-consumable — "Reset Specified Consumable Usage Time"
)


VIOMI_V15_CLEAN_HISTORY = CleanHistoryCapability(
    start_time=Prop(4, 25),  # clean-start-time — "Cleaning Start Time, timestamp, unit seconds"
    use_time=Prop(4, 26),  # clean-use-time — "Cleaning Usage Time, unit seconds"
    clean_area=Prop(4, 27),  # clean-area — "Total Cleaning Area, unit m2"
    map_url=Prop(4, 28),  # clean-map-url — "Cleaning Map URL"
    clean_mode=Prop(4, 29),  # clean-mode — "Cleaning Mode"
    clean_way=Prop(4, 30),  # clean-way — "Cleaning Method"
    current_map=Prop(4, 32),  # cur-map-id — "Current Map ID"
)


VIOMI_V15_DND = DndCapability(
    service=5,
    enable=Prop(5, 15),  # dnd-enable — "Do Not Disturb Whether Enabled"
    start_hour=Prop(5, 16),  # dnd-start-hour — "Do Not Disturb Start Hour"
    start_minute=Prop(5, 17),  # dnd-start-minute — "Do Not Disturb Start Minute"
    end_hour=Prop(5, 18),  # dnd-end-hour — "Do Not Disturb End Hour"
    end_minute=Prop(5, 19),  # dnd-end-minute — "Do Not Disturb End Minute"
    timezone=Prop(5, 20),  # dnd-timezone — "Timezone Parameter"
)


VIOMI_V15_VOICE = VoiceCapability(
    service=8,
    download_voice=Action(8, 3, in_piids=(3, 7, 8)),  # download-voice — "Start Download Voice Pack"
    get_download_status=Action(8, 4, out_piids=(6, 3, 4, 5)),  # get-downloadstatus — "Get Voice Pack File Download Status"
    target_voice=Prop(8, 3),  # target-voice — "Currently Downloading Voice Pack Name"
    cur_voice=Prop(8, 4),  # cur-voice — "Currently Used Voice Pack Name"
    download_status=Prop(8, 5),  # download-status — "Download Status"
    download_progress=Prop(8, 6),  # download-progress — "Download Progress"
    voice_url=Prop(8, 7),  # voice-url — "Voice Pack Link to Download"
)


VIOMI_V15 = ModelProfile(
    profile_id="viomi.v15",
    brand="viomi",
    core=VIOMI_V15_CORE,
    map=VIOMI_V15_MAP,
    room_clean=VIOMI_V15_ROOM_CLEAN,
    schedule=VIOMI_V15_SCHEDULE,
    settings=VIOMI_V15_SETTINGS,
    consumables=VIOMI_V15_CONSUMABLES,
    clean_history=VIOMI_V15_CLEAN_HISTORY,
    dnd=VIOMI_V15_DND,
    voice=VIOMI_V15_VOICE,
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:viomi-v15:1",),
)


VIOMI_V45_CORE = CoreCapability(
    status=Prop(2, 1),  # status — "Status"
    fault=Prop(2, 2),  # fault — "Fault"
    mode=Prop(2, 4),  # mode — "Mode"
    battery=Prop(3, 1),  # battery-level — "Battery Level"
    fan_speed=Prop(7, 5),  # suction-state — "Suction Power"
    water_level=Prop(7, 6),  # water-state — "Water Level"
    sweep_type=Prop(2, 8),  # sweep-type — "Cleaning Method"
    repeat=Prop(7, 1),  # repeat-state — "Second Cleaning Switch"
    alarm=Prop(4, 1),  # alarm — "Alert Sound"
    volume=Prop(4, 2),  # volume — "Volume"
    start=Action(2, 1),  # start-sweep — "Start Cleaning"
    stop=Action(2, 2),  # stop-sweeping — "Stop"
    charge=Action(3, 1),  # start-charge — "Start Return to Charge"
    status_map={0: 'idle', 1: 'idle', 2: 'paused', 3: 'returning', 4: 'docked', 5: 'cleaning', 6: 'cleaning', 7: 'cleaning', 8: 'idle'},
    fan_speeds={'slient': 0, 'standard': 1, 'medium': 2, 'turbo': 3},
    water_levels={'low': 0, 'mid': 1, 'high': 2},
    modes={'sweep': 0, 'sweep_and_mop': 1, 'mop': 2},
    sweep_types={'global': 0, 'mop': 1, 'edge': 2, 'area': 3, 'point': 4, 'remote': 5, 'explore': 6, 'room': 7, 'floor': 8},
)


VIOMI_V45_POINT_ZONE = PointZoneCapability(
    service=9,
    zone_points=Prop(9, 2),  # zone-points — "Four Vertex Coordinates of Zone 'x1,y1,x2,y2,x3,y3,x4,y4'"
    target_point=Prop(9, 5),  # target-point — "Target Point for Spot Cleaning, XY comma separated, e.g. '3.23,6.89'"
    restrict_points=Prop(9, 3),  # restrict-points — "Set Virtual Wall Coordinates"
    beauty_point=Prop(9, 6),  # beauty-point — "Wall Editing Coordinates, two or three points, comma separated, 'x1,y1,x2,y2,x3,y3'"
    map_type=Prop(9, 8),  # map-type — "Map Type 0: Real-time Map 1: Spot Map 2: Zone Map 3: Memory Map"
    set_zone_point=Action(9, 8, in_piid=2, out_piids=(7, 8, 9)),  # set-zone-point — "Set Zone Points Four Vertex Coordinates of Zone 'x1,y1,x2,y2,x3,y3,x4,y4'"
    start_zone_clean=Action(9, 3),  # start-zone-clean — "Start Zone Cleaning"
    start_point_clean=Action(9, 9, in_piid=5, out_piids=(7, 8, 9)),  # start-point-clean-ii — "Start Spot Cleaning With Point Start"
    legacy_start_point_clean=Action(9, 1),  # start-point-clean — "Start Spot Cleaning"
    pause_point_clean=Action(9, 2, in_piid=4),  # pause-point-clean — "Pause Spot Cleaning"
    pause_zone_clean=Action(9, 4, in_piid=4),  # pause-zone-clean — "Pause Zone Cleaning"
    set_virtual_wall=Action(9, 6, in_piid=3, out_piids=(7, 8, 9)),  # set-virtual-wall — "Set Virtual Wall Coordinates"
    set_beauty_wall=Action(9, 5, in_piid=6, out_piids=(7, 8, 9)),  # set-beauty-wall — "Map Beautification, Wall Editing"
)


VIOMI_V45_MAP = MapCapability(
    service=10,
    current_map_id=Prop(10, 2),  # cur-map-id — "Current Map ID"
    map_num=Prop(10, 3),  # map-num — "Current Stored Map Count"
    map_list=Prop(10, 4),  # map-list — "Map List Data, Map Name + Map ID + Whether Current Map [{name : 'Map 1',id:1585849584,cur : true},{name : 'Map 2',id : 1585849784,cur : false}]"
    remember_state=Prop(10, 1),  # remember-state — "Memory Map Switch"
    has_new_map=Prop(10, 19),  # has-new-map — "Device Finished Cleaning Saved a New Map Awaiting Save or Rename"
    current_path=Prop(10, 5),  # cur-cleaning-path — "Robot Cleaning Trajectory Coordinates : [123,3.456,4.555,0.2,1, ...] [first_poseid, x, y, phi, update, ...]"
    start_cleaning_point=Prop(10, 15),  # start-cleaning-point — "Start Position Point to be Retrieved"
    end_cleaning_point=Prop(10, 16),  # end-cleaning-point — "End Position Point to be Retrieved"
    room_id_name_list=Prop(10, 17),  # room-id-name-list — "Room ID and Name Collection [{id:10,name:'Room 1'},{id:11,name:'Room 2'}]"
    split_points=Prop(10, 12),  # split-points — "Two Endpoint Coordinates of Split Line Segment e.g.: '3.45,6.78|4.56,-3.45'"
    arrange_room_ids=Prop(10, 11),  # arrange-room-ids — "Room ID parameters to merge, comma separated e.g.: '10,11,12' means merge rooms with IDs 10,11,12;"
    mijia_room_list=Prop(10, 22),  # mijia-room-list — "Mi Home Room ID and Device Room ID Correspondence Table [ [mijia_room_id1, device_room_id1_1, device_room_id1_2], [mijia_room_id2, device_room_id2_1, device_room_id2_2], [mijia_room_id3, device_room_id3], ...} Example: [ [340001249787,10,12], [340001249487,11,17], [340001248861,13] ] --- 20210222 Added"
    get_map_list=Action(10, 1, out_piids=(4,)),  # get-map-list — "Get Map List Data"
    upload_by_mapid=Action(10, 2, in_piid=6, out_piids=(6, 7, 18)),  # upload-by-mapid — "Get Specified ID Map"
    upload_by_mapid_ii=Action(10, 14, in_piid=6, out_piids=(6, 7, 18, 21)),  # upload-by-mapid-ii — "Upload Specified ID Map Difference from a2: Response contains whether new map upload needed parameter 20201110"
    set_current_map=Action(10, 3, in_piid=6),  # set-cur-map — "Set as Current Map"
    del_map=Action(10, 4, in_piid=6),  # del-map — "Delete Specified ID Map"
    rename_map=Action(10, 5, in_piids=(6, 8)),  # rename-map — "Rename Map"
    build_new_map=Action(10, 11, in_piid=14),  # build-new-map — "Create New Map, Next Completed Cleaning Map as New Map"
    reset_map=Action(10, 10),  # reset-map — "Clear All Existing Maps"
    get_current_path=Action(10, 12, in_piids=(15, 16), out_piids=(5,)),  # get-cur-path — "Get Cleaning Trajectory"
    get_map_room_list=Action(10, 13, in_piid=2, out_piids=(17,)),  # get-map-room-list — "Get All Room Information for Specified Map: ID and Room Name"
    rename_room=Action(10, 7, in_piids=(6, 9, 10), out_piids=(6, 7, 18)),  # rename-room — "Room Rename"
    arrange_room=Action(10, 8, in_piids=(6, 11, 13), out_piids=(6, 7, 18)),  # arrange-room — "Merge Room"
    split_room=Action(10, 9, in_piids=(6, 9, 12, 13), out_piids=(6, 7, 18)),  # split-room — "Split Room"
    set_mijia_room_list=Action(10, 18, in_piids=(6, 22)),  # set-mijia-room-list — "Send Matched Mi Home Room - Device Room List to Device End, for XiaoAi Voice Control --- 20210222 Added"
    point_zone=VIOMI_V45_POINT_ZONE,
)


VIOMI_V45_ROOM_CLEAN = RoomCleanCapability(
    room_ids=Prop(2, 10),  # room-ids — "Mi Home Room ID Parameter"
    start=Action(2, 7, in_piid=10),  # start-room-sweep — "Clean Room"
    clean_room_ids=Prop(7, 24),  # clean-room-ids — "When selecting room cleaning, pass room ID string parameter, comma separated, e.g.: '10,11,12,13', if empty then global cleaning"
    clean_room_mode=Prop(7, 25),  # clean-room-mode — "Select Room Cleaning Mode"
    clean_room_oper=Prop(7, 26),  # clean-room-oper — "Select Room Cleaning Operation"
    set_room_clean=Action(7, 3, in_piids=(24, 25, 26)),  # set-room-clean — "Select Room Cleaning, if no room ID passed then global cleaning"
)


VIOMI_V45_SCHEDULE = ScheduleCapability(
    service=8,
    add=Action(8, 1, in_piids=(1, 2, 3, 4, 5, 6, 11, 14, 12, 16)),  # add — "Create a New Reservation, Select All Rooms for Global Reservation, Set Preferences Too"
    delete=Action(8, 2, in_piid=1),  # del — "Delete Specified Reservation"
    get=Action(8, 3, out_piids=(15,)),  # get — "Get All Reservations"
    order_id=Prop(8, 1),  # order-id — "Reservation ID"
    enable=Prop(8, 2),  # enable — "Whether to Enable This Reservation"
    day=Prop(8, 3),  # day — "After converting to binary, each bit represents a day, 1 - reserved 0 - not reserved, bit0-bit6 Sunday-Saturday"
    hour=Prop(8, 4),  # hour — "Reservation Hour (24-hour format)"
    minute=Prop(8, 5),  # minute — "Reservation Minute"
    repeat=Prop(8, 6),  # repeat — "Repeat Task"
    clean_way=Prop(8, 7),  # clean-way — "Cleaning Method"
    suction=Prop(8, 8),  # suction — "Suction Power"
    water=Prop(8, 9),  # water — "Water Level"
    twice_clean=Prop(8, 10),  # twice-clean — "Second Cleaning"
    mapid=Prop(8, 11),  # mapid — "Selected Map ID, if no map then pass 0"
    room_count=Prop(8, 12),  # room-count — "Number of Reserved Rooms"
    room_data=Prop(8, 13),  # room-data — "Not needed when room-count is 0; Reservation Room Data JSON String [{name:'Room 1',id:10},{name:'Room 2',id:11},{...},{...}]"
    orderdata=Prop(8, 15),  # orderdata — "N Groups of Reservation Data Separated by Commas"
)


VIOMI_V45_SETTINGS = SettingsCapability(
    mop_route=Prop(7, 7),  # mop-route — "Mopping/Sweep-Mop Route"
    shake_shift=Prop(7, 50),  # shake-shift — "Vibration Water Tank Gear"
    tank_shake=Prop(7, 48),  # tank-shake — "Vibration Water Tank Switch"
    direction=Prop(7, 16),  # direction — "Remote Control Method Parameters"
    dirt_recognize=Prop(7, 35),  # dirt-recognize — "Dirt Recognition Switch"
    pet_recognize=Prop(7, 36),  # pet-recognize — "Pet Recognition Switch"
    ai_recognize=Prop(7, 42),  # ai-recognize — "AI Recognition Switch AI Recognition Switch Off: Dirt Recognition Switch, Pet Recognition Switch Auto Off AI Recognition Switch On: Dirt Recognition Switch, Pet Recognition Switch Read Last Startup Value"
    carpet_booster=Prop(7, 44),  # carpet-booster — "Global Carpet Boost Switch"
    carpet_avoid=Prop(7, 47),  # carpet-avoid — "Carpet Avoidance Switch"
    multi_prop_vacuum=Prop(7, 45),  # multi-prop-vacuum — "siid7 Multi-parameter Array"
)


VIOMI_V45_CONSUMABLES = ConsumablesCapability(
    side_brush_hours=Prop(7, 9),  # side-brush-hours — "Side Brush Remaining Life Hours"
    main_brush_hours=Prop(7, 11),  # main-brush-hours — "Main Brush Remaining Life Hours"
    hypa_hours=Prop(7, 13),  # hypa-hours — "HEPA Filter Remaining Life Hours"
    mop_hours=Prop(7, 15),  # mop-hours — "Mop Remaining Life Hours"
    door_state=Prop(7, 3),  # door-state — "Box Status"
    cloth_state=Prop(7, 4),  # cloth-state — "Cloth Status"
    reset_consumable=Action(7, 1, in_piid=17),  # reset-consumable — "Reset Specified Consumable Usage Time"
)


VIOMI_V45_CLEAN_HISTORY = CleanHistoryCapability(
    start_time=Prop(7, 27),  # record-start-time — "Cleaning Start Time, timestamp, unit seconds"
    use_time=Prop(7, 28),  # record-use-time — "Cleaning Usage Time, unit seconds"
    clean_area=Prop(7, 29),  # record-clean-area — "Total Cleaning Area ㎡"
    map_url=Prop(7, 30),  # record-map-url — "Cleaning Map URL"
    clean_mode=Prop(7, 31),  # record-clean-mode — "Cleaning Mode 20201121 Confirmed"
    clean_way=Prop(7, 32),  # record-clean-way — "Cleaning Method"
    current_map=Prop(7, 33),  # clean-current-map — "Clean Specified Map ID"
    task_status=Prop(7, 37),  # record-task-status — "Cleaning Record Device Status"
)


VIOMI_V45_DND = DndCapability(
    service=12,
    set_notdisturb=Action(12, 1, in_piids=(1, 2, 3, 4, 5, 6)),  # set-notdisturb — "Set Do Not Disturb Time"
    enable=Prop(12, 1),  # dnd-enable — "Do Not Disturb Whether Enabled"
    start_hour=Prop(12, 2),  # dnd-start-hour — "Do Not Disturb Start Hour"
    start_minute=Prop(12, 3),  # dnd-start-minute — "Do Not Disturb Start Minute"
    end_hour=Prop(12, 4),  # dnd-end-hour — "Do Not Disturb End Hour"
    end_minute=Prop(12, 5),  # dnd-end-minute — "Do Not Disturb End Minute"
    timezone=Prop(12, 6),  # dnd-timezone — "Timezone Parameter"
)


VIOMI_V45_VOICE = VoiceCapability(
    service=14,
    download_voice=Action(14, 1, in_piids=(1, 5, 6)),  # download-voice — "Download Voice Pack"
    get_download_status=Action(14, 2, out_piids=(1, 2, 3, 4)),  # get-download-status — "Get Download Status"
    target_voice=Prop(14, 1),  # target-voice — "Target Language to Modify"
    cur_voice=Prop(14, 2),  # cur-voice — "Current Voice"
    download_status=Prop(14, 3),  # download-status — "Voice Pack Download Status"
    download_progress=Prop(14, 4),  # download-progress — "Download Progress"
    voice_url=Prop(14, 5),  # voice-url — "Voice Pack Download URL, Exists in FDS"
)


VIOMI_V45 = ModelProfile(
    profile_id="viomi.v45",
    brand="viomi",
    core=VIOMI_V45_CORE,
    map=VIOMI_V45_MAP,
    room_clean=VIOMI_V45_ROOM_CLEAN,
    schedule=VIOMI_V45_SCHEDULE,
    settings=VIOMI_V45_SETTINGS,
    consumables=VIOMI_V45_CONSUMABLES,
    clean_history=VIOMI_V45_CLEAN_HISTORY,
    dnd=VIOMI_V45_DND,
    voice=VIOMI_V45_VOICE,
    notes=("urn:miot-spec-v2:device:vacuum:0000A006:viomi-v45:2",),
)
