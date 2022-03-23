[![HACS Default][hacs_shield]][hacs]
[![GitHub Latest Release][releases_shield]][latest_release]
[![GitHub All Releases][downloads_total_shield]][releases]
[![Community Forum][community_forum_shield]][community_forum]
[![Buy me a coffee][buy_me_a_coffee_shield]][buy_me_a_coffee]
[![PayPal.Me][paypal_me_shield]][paypal_me]


[hacs_shield]: https://img.shields.io/static/v1.svg?label=HACS&message=Default&style=popout&color=green&labelColor=41bdf5&logo=HomeAssistantCommunityStore&logoColor=white
[hacs]: https://hacs.xyz/docs/default_repositories

[latest_release]: https://github.com/PiotrMachowski/Home-Assistant-custom-components-Xiaomi-Cloud-Map-Extractor/releases/latest
[releases_shield]: https://img.shields.io/github/release/PiotrMachowski/Home-Assistant-custom-components-Xiaomi-Cloud-Map-Extractor.svg?style=popout

[releases]: https://github.com/PiotrMachowski/Home-Assistant-custom-components-Xiaomi-Cloud-Map-Extractor/releases
[downloads_total_shield]: https://img.shields.io/github/downloads/PiotrMachowski/Home-Assistant-custom-components-Xiaomi-Cloud-Map-Extractor/total

[community_forum_shield]: https://img.shields.io/static/v1.svg?label=%20&message=Forum&style=popout&color=41bdf5&logo=HomeAssistant&logoColor=white
[community_forum]: https://community.home-assistant.io/t/xiaomi-cloud-vacuum-map-extractor/231292

[buy_me_a_coffee_shield]: https://img.shields.io/static/v1.svg?label=%20&message=Buy%20me%20a%20coffee&color=6f4e37&logo=buy%20me%20a%20coffee&logoColor=white
[buy_me_a_coffee]: https://www.buymeacoffee.com/PiotrMachowski

[paypal_me_shield]: https://img.shields.io/static/v1.svg?label=%20&message=PayPal.Me&logo=paypal
[paypal_me]: https://paypal.me/PiMachowski


# Xiaomi Cloud Map Extractor

This custom integration provides a way to present a live view of a map for Xiaomi, Roborock, Viomi and Roidmi vacuums.
([Supported devices](#supported-devices))

<img src="https://raw.githubusercontent.com/PiotrMachowski/Home-Assistant-custom-components-Xiaomi-Cloud-Map-Extractor/master/images/map_no_rooms.png" width=48%>  <img src="https://raw.githubusercontent.com/PiotrMachowski/Home-Assistant-custom-components-Xiaomi-Cloud-Map-Extractor/master/images/map_rooms.png" width=48%>

## Installation

### Using [HACS](https://hacs.xyz/) (recommended)

This integration can be installed using HACS.
To do it search for `Xiaomi Cloud Map Extractor` in *Integrations* section.

### Manual

To install this integration manually you have to download [*xiaomi_cloud_map_extractor.zip*](https://github.com/PiotrMachowski/Home-Assistant-custom-components-Xiaomi-Cloud-Map-Extractor/releases/latest/download/xiaomi_cloud_map_extractor.zip) and extract its contents to `config/custom_components/xiaomi_cloud_map_extractor` directory:
```bash
mkdir -p custom_components/xiaomi_cloud_map_extractor
cd custom_components/xiaomi_cloud_map_extractor
wget https://github.com/PiotrMachowski/Home-Assistant-custom-components-Xiaomi-Cloud-Map-Extractor/releases/latest/download/xiaomi_cloud_map_extractor.zip
unzip xiaomi_cloud_map_extractor.zip
rm xiaomi_cloud_map_extractor.zip
```

## Configuration

After installation of the custom component, it needs to be configured in `configuration.yaml` file.
To do so, add a camera entry to your configuration with at least a [basic](#basic) or [recommended](#recommended) configuration.
Vacuum token can be extracted by following [this guide](https://www.home-assistant.io/integrations/xiaomi_miio/#retrieving-the-access-token) (ignore "not recommended" message, as it applies only to built-in Xiaomi Miio integration).
You also need to enter your Xiaomi Cloud username and password.
These are the credentials used for the Xiaomi Home app (_not ones from Roborock app_).

After installation and a reboot of your Home Assistant instance, you should get a camera entity which shows the vacuum map.
This might take a few minutes after a first restart.
If you have a problem with configuration validation you have to remove camera from `configuration.yaml`, restart Home Assistant, add camera config and restart HA again.

After modification of camera's configuration you can reload its settings in [Configuration](https://my.home-assistant.io/redirect/config/) or using `xiaomi_cloud_map_extractor.reload` service.

### Examples

#### Basic

```yaml
camera:
  - platform: xiaomi_cloud_map_extractor
    host: !secret xiaomi_vacuum_host
    token: !secret xiaomi_vacuum_token
    username: !secret xiaomi_cloud_username
    password: !secret xiaomi_cloud_password
```

#### Recommended

```yaml
camera:
  - platform: xiaomi_cloud_map_extractor
    host: !secret xiaomi_vacuum_host
    token: !secret xiaomi_vacuum_token
    username: !secret xiaomi_cloud_username
    password: !secret xiaomi_cloud_password
    draw: ['all']
    attributes:
      - calibration_points
```


#### Full

| This configuration's purpose is to show all available options, do not use it unless you know what you are doing. |
| --- |

<details>
<summary>I know what I'm doing and I will not recklessly copy this config to my setup</summary>

```yaml
camera:
  - platform: xiaomi_cloud_map_extractor
    host: !secret xiaomi_vacuum_host
    token: !secret xiaomi_vacuum_token
    username: !secret xiaomi_cloud_username
    password: !secret xiaomi_cloud_password
    country: "de"
    name: "My Vacuum Camera"
    colors:
      color_map_inside: [32, 115, 185]
      color_map_outside: [19, 87, 148]
      color_map_wall: [100, 196, 254]
      color_map_wall_v2: [93, 109, 126]
      color_grey_wall: [93, 109, 126]
      color_ignored_obstacle: [0, 0, 0, 127]
      color_ignored_obstacle_with_photo: [0, 0, 0, 127]
      color_obstacle: [0, 0, 0, 127]
      color_obstacle_with_photo: [0, 0, 0, 127]
      color_path: [147, 194, 238]
      color_goto_path: [0, 255, 0]
      color_predicted_path: [255, 255, 0, 0]
      color_cleaned_area: [127, 127, 127, 127]
      color_zones: [0xAD, 0xD8, 0xFF, 0x8F]
      color_zones_outline: [0xAD, 0xD8, 0xFF]
      color_virtual_walls: [255, 0, 0]
      color_new_discovered_area: [64, 64, 64]
      color_no_go_zones: [255, 33, 55, 127]
      color_no_go_zones_outline: [255, 0, 0]
      color_no_mop_zones: [163, 130, 211, 127]
      color_no_mop_zones_outline: [163, 130, 211]
      color_charger: [0x66, 0xfe, 0xda, 0x7f]
      color_robo: [75, 235, 149]
      color_room_names: [0, 0, 0]
      color_unknown: [0, 0, 0]
      color_scan: [0xDF, 0xDF, 0xDF]
    room_colors:
      1: [240, 178, 122]
      2: [133, 193, 233]
      3: [217, 136, 128]
      4: [52, 152, 219]
      5: [205, 97, 85]
      6: [243, 156, 18]
      7: [88, 214, 141]
      8: [245, 176, 65]
      9: [252, 212, 81]
      10: [72, 201, 176]
      11: [84, 153, 199]
      12: [133, 193, 233]
      13: [245, 176, 65]
      14: [82, 190, 128]
      15: [72, 201, 176]
      16: [165, 105, 18]
    draw:
      - charger
      - cleaned_area
      - goto_path
      - ignored_obstacles
      - ignored_obstacles_with_photo
      - no_go_zones
      - no_mopping_zones
      - obstacles
      - obstacles_with_photo
      - path
      - predicted_path
      - room_names
      - vacuum_position
      - virtual_walls
      - zones
    texts:
      - text: "Room 1"
        x: 25
        y: 25
        color: [125, 20, 213]
      - text: "Room 2"
        x: 25
        y: 75
        color: [125, 20, 213, 127]
        font: "FreeSans.ttf"
        font_size: 25
    map_transformation:
      scale: 2
      rotate: 180
      trim:
        top: 10
        bottom: 20
        left: 30
        right: 40
    sizes:
      charger_radius: 4
      vacuum_radius: 6.5
      path_width: 1
      obstacle_radius: 3
      ignored_obstacle_radius: 3
      obstacle_with_photo_radius: 3
      ignored_obstacle_with_photo_radius: 3
    attributes:
      - calibration_points
      - charger
      - cleaned_rooms
      - country
      - goto
      - goto_path
      - goto_predicted_path
      - image
      - is_empty
      - map_name
      - no_go_areas
      - no_mopping_areas
      - obstacles
      - ignored_obstacles
      - obstacles_with_photo
      - ignored_obstacles_with_photo
      - path
      - room_numbers
      - rooms
      - vacuum_position
      - vacuum_room
      - vacuum_room_name
      - walls
      - zones
    scan_interval:
      seconds: 10
    auto_update: true
    store_map_raw: false
    store_map_image: true
    store_map_path: "/tmp"
    force_api: xiaomi
```
</details>

### Available configuration parameters

| Key | Type | Required | Value | Description |
|---|---|---|---|---|
| `platform` | string | true | `xiaomi_cloud_map_extractor` | Name of a platform |
| `host` | string | true | `192.168.0.123` | IP address of a vacuum |
| `token` | string | true | `ghjhca3ykg8o2zyyj7xb5adamhgsypel` | Token of a vacuum |
| `username` | string | true | `xiaomi.account@gmail.com` | Username (email or user ID) used to connect to Xiaomi cloud (the account used in the Xiaomi Home app) |
| `password` | string | true | `aVerySecretPassword` | Password used to connect to Xiaomi cloud (the account used in the Xiaomi Home app) |
| `name` | string | false |   | Desired name of camera entity |
| `country` | string | false | One of: `cn`, `de`, `us`, `ru`, `tw`, `sg`, `in`, `i2` | Server used in Xiaomi cloud. Leave empty if you are not sure. |
| `colors` | map | false |  | Colors configuration ([see below](#colors-configuration)) |
| `room_colors` | map | false |  | Room colors configuration ([see below](#room-colors-configuration)) |
| `draw` | list | false |  | List of elements to draw on a map ([see below](#draw-configuration)) |
| `texts` | list | false |  | List of texts to draw on a map ([see below](#texts-configuration)) |
| `map_transformation` | map | false |  | Parameters of map transformation ([see below](#map-transformation-configuration)) |
| `sizes` | map | false |  | Sizes of map's elements ([see below](#sizes-configuration)) |
| `attributes` | list | false |  | List of desired entity attributes ([see below](#attributes-configuration)) |
| `scan_interval` | interval | false | default: `5` seconds | Interval between map updates ([documentation](https://www.home-assistant.io/docs/configuration/platform_options/#scan-interval)) |
| `auto_update` | boolean | false | default: `true` | Activation/deactivation of automatic map updates. ([see below](#updates)) |
| `store_map_raw` | boolean | false | default: `false` | Enables storing raw map data in `store_map_path` directory ([more info](#retrieving-map)). Xiaomi map can be opened with [RoboMapViewer](https://github.com/marcelrv/XiaomiRobotVacuumProtocol/tree/master/RRMapFile). |
| `store_map_image` | boolean | false | default: `false` | Enables storing map image in `store_map_path` path with name `map_image_<device_model>.png` |
| `store_map_path` | string | false | default: `/tmp` | Storing map data directory |
| `force_api` | string | false | One of: `xiaomi`, `viomi`, `roidmi` | Forces usage of specific API. |

#### Colors configuration

  Each color is represented by a list of 3 or 4 parameters: `[red, green, blue]` or `[red, green, blue, alpha]`.
  Each parameter is a number from a range 0-255 and can be also provided as a HEX value: [0x12, 0xAF, 0xC5] matches #12AFC5.

  <img src="https://raw.githubusercontent.com/PiotrMachowski/Home-Assistant-custom-components-Xiaomi-Cloud-Map-Extractor/master/images/map_no_rooms_custom_colors.png" width=50%>

  | Color name | Description |
  | --- | --- |
  | `color_charger` | Charger fill |
  | `color_charger_outline` | Charger outline |
  | `color_cleaned_area` | Fill of area that already has been cleaned (Viomi) |
  | `color_goto_path` | Path for goto mode |
  | `color_grey_wall` | Obstacles (e.g. chairs, table legs) |
  | `color_ignored_obstacle_with_photo` | Ignored obstacle with photo mark on a map |
  | `color_ignored_obstacle` | Ignored obstacle mark on a map |
  | `color_map_inside` | Map inside (for software without rooms support) |
  | `color_map_outside` | Map outside |
  | `color_map_wall_v2` | Walls (for software with rooms support) |
  | `color_map_wall` | Walls (for software without rooms support) |
  | `color_new_discovered_area` | Newly discovered areas (Viomi) |
  | `color_no_go_zones_outline` | Outline of no-go zones |
  | `color_no_go_zones` | Fill of no-go zones |
  | `color_no_mop_zones_outline` | Outline of no-mopping zones |
  | `color_no_mop_zones` | Fill of no-mopping zones |
  | `color_obstacle_with_photo` | Obstacle with photo mark on a map |
  | `color_obstacle` | Obstacle mark on a map |
  | `color_path` | Path of a vacuum |
  | `color_predicted_path` | Predicted path to a point in goto mode |
  | `color_robo` | Vacuum fill |
  | `color_robo_outline` | Vacuum outline |
  | `color_room_names` | Room names (if available) |
  | `color_scan` | Areas not assigned to any room (for software with rooms support) |
  | `color_unknown` | Other areas |
  | `color_virtual_walls` | Virtual walls |
  | `color_zones_outline` | Outline of areas selected for zoned cleaning |
  | `color_zones` | Fill of areas selected for zoned cleaning |

#### Room colors configuration

  This section contains mapping between room numbers and colors.
  Each color is represented by a list of 3 or 4 parameters: `[red, green, blue]` or `[red, green, blue, alpha]`.
  Each parameter is a number from a range 0-255 and can be also provided as a HEX value: [0x12, 0xAF, 0xC5] matches #12AFC5.

#### Draw configuration

  A list of features to be drawn on a map. If all features should be drawn it can be replaced with:
  ```yaml
    draw: ["all"]
  ```
  Available values:
  - `charger`
  - `cleaned_area`
  - `goto_path`
  - `ignored_obstacles_with_photo`
  - `ignored_obstacles`
  - `no_go_zones`
  - `no_mopping_zones`
  - `obstacles_with_photo`
  - `obstacles`
  - `path`
  - `predicted_path`
  - `room_names`
  - `vacuum_position`
  - `virtual_walls`
  - `zones`

#### Texts configuration

Each list entry must obey a following schema.
You can get a list of available fonts by executing this command:
```bash
fc-list | grep ttf | sed "s/.*\///"| sed "s/ttf.*/ttf/"
```

  | Parameter | Type | Required | Default value | Description |
  |---|---|---|---|---|
  | `text` | string | true |   | Text to draw on a map |
  | `x` | float | true |   | X position of a text (in percents) |
  | `y` | float | true |   | Y position of a text (in percents) |
  | `color` | list | false | black | Desired color of a text, formatted like [here](#colors-configuration) |
  | `font` | string | false |   | Name of a font to use |
  | `font_size` | int | false |   | Size of a font |

#### Map transformation configuration

  | Parameter | Type | Required | Default value | Description |
  |---|---|---|---|---|
  | `scale` | float | false | 1 | Scaling factor for a map. |
  | `rotate` | integer | false | 0 | Angle of map rotation. Available values: [`0`, `90`, `180`, `270`] |
  | `trim` | map | false | 0 | Map trimming configuration. Each trimming direction is in percents: value `25` means trimming of quarter of image size in a given dimension. Available keys: [`left`, `right`, `top`, `bottom`] |

#### Sizes configuration

  | Parameter | Type | Required | Default value | Description |
  |---|---|---|---|---|
  | `charger_radius` | float | false | 6 | Radius of a charger circle. |
  | `vacuum_radius` | float | false | 6 | Radius of a vacuum semi-circle. |
  | `obstacle_radius` | float | false | 3 | Radius of an obstacle circle. |
  | `ignored_obstacle_radius` | float | false | 3 | Radius of an ignored obstacle circle circle. |
  | `obstacle_with_photo_radius` | float | false | 3 | Radius of an obstacle with photo circle. |
  | `ignored_obstacle_with_photo_radius` | float | false | 3 | Radius of an ignored obstacle with photo circle. |
  | `path_width` | float | false | 1 | Width of path line. |

#### Attributes configuration

  A list of attributes that an entity should have.
  Available values:
  - `calibration_points` - Calculated calibration points for [Lovelace Xiaomi Vacuum Map card](https://github.com/PiotrMachowski/lovelace-xiaomi-vacuum-map-card).
     <img src="https://raw.githubusercontent.com/PiotrMachowski/Home-Assistant-custom-components-Xiaomi-Cloud-Map-Extractor/master/images/map_card.gif" width=50%>
  - `charger`
  - `cleaned_rooms`
  - `country`
  - `goto_path`
  - `goto_predicted_path`
  - `goto`
  - `ignored_obstacles_with_photo`
  - `ignored_obstacles`
  - `image`
  - `is_empty`
  - `map_name`
  - `no_go_areas`
  - `no_mopping_areas`
  - `obstacles_with_photo`
  - `obstacles`
  - `path`
  - `room_numbers`
  - `rooms`
  - `vacuum_position`
  - `vacuum_room_name`
  - `vacuum_room`
  - `walls`
  - `zones`

## Updates

Camera image is updated every 5s by default.
It can be disabled in config using `auto_update` property.

You can also disable and enable automatic updates using services `camera.turn_off`, `camera.turn_on`.

If automatic updates are disabled you can manually trigger update using `homeassistant.update_entity` service.

You can change interval of automatic updates using `scan_interval` setting ([documentation](https://www.home-assistant.io/docs/configuration/platform_options/#scan-interval))

If you want to disable map updates when a vacuum is not running you can use [this blueprint](https://github.com/PiotrMachowski/Home-Assistant-custom-components-Xiaomi-Cloud-Map-Extractor/blob/master/blueprints/automation/disable_vacuum_camera_update_when_docked.yaml).

[![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FPiotrMachowski%2FHome-Assistant-custom-components-Xiaomi-Cloud-Map-Extractor%2Fblob%2Fmaster%2Fblueprints%2Fautomation%2Fdisable_vacuum_camera_update_when_docked.yaml)

## Supported devices

This integration was tested on following vacuums:
 - Xiaomi map format:
   - `rockrobo.vacuum.v1` (Xiaomi Vacuum Gen 1, Mi Robot Vacuum, SDJQR01RR, SDJQR02RR)
   - `roborock.vacuum.m1s` (Xiaomi Mi Robot 1S)
   - `roborock.vacuum.s4` (Roborock S4)
   - `roborock.vacuum.s5` (Roborock S5)
   - `roborock.vacuum.s5e` (Roborock S5 Max)
   - `rockrobo.vacuum.s6` (Roborock S6)
   - `roborock.vacuum.a08` (Roborock S6 Pure)
   - `roborock.vacuum.a10` (Roborock S6 MaxV)
   - `roborock.vacuum.a15` (Roborock S7)
 - Viomi map format:
   - `viomi.vacuum.v6` (Viomi Vacuum V2 Pro, Xiaomi Mijia STYJ02YM, Mi Robot Vacuum Mop Pro)
   - `viomi.vacuum.v7` (Mi Robot Vacuum-Mop Pro)
   - `viomi.vacuum.v8` (Mi Robot Vacuum-Mop Pro)
   - `viomi.vacuum.v13` (Viomi V3)
 - Roidmi map format:
   - `roidmi.vacuum.v60` (Roidmi EVE Plus)
   - `viomi.vacuum.v18` (Viomi S9)

## Unsupported devices

At this moment this integration is known to not work with following vacuums:
 - Dreame ([#126](https://github.com/PiotrMachowski/Home-Assistant-custom-components-Xiaomi-Cloud-Map-Extractor/issues/126)):

## Retrieving map

When `store_map_raw: true` is added to your config this integration will store a raw map file in `/tmp` directory.
If you don't use Core installation ([installation types](https://www.home-assistant.io/installation/#compare-installation-methods)) you can retrieve this file in the following way:
- In [SSH & Terminal add-on](https://github.com/hassio-addons/addon-ssh) enable protected access
- Open terminal and use the following command to copy file:
  ```
  docker exec homeassistant bash -c "mkdir -p /config/tmp/ && cp /tmp/map_* /config/tmp/"
  ```
- Map file will appear in `tmp` folder in your `config` folder

## Enabling debug logging

To enable debug logging add following section to your `configuration.yaml`

```yaml
logger:
  default: info
  logs:
    custom_components.xiaomi_cloud_map_extractor: debug
```

## Special thanks

This integration wouldn't exist without following projects:
 - [openHAB miIO add-on](https://github.com/openhab/openhab-addons/tree/main/bundles/org.openhab.binding.miio/src/main/java/org/openhab/binding/miio) by [@marcelrv](https://github.com/marcelrv)
 - [valeCLOUDo](https://github.com/Xento/valeCLOUDo) by [@Xento](https://github.com/Xento)
 - [Xiaomi Robot Vacuum Protocol](https://github.com/marcelrv/XiaomiRobotVacuumProtocol) by [@marcelrv](https://github.com/marcelrv)
 - [Valetudo](https://github.com/Hypfer/Valetudo) by [@Hypfer](https://github.com/Hypfer)


<a href="https://www.buymeacoffee.com/PiotrMachowski" target="_blank"><img src="https://bmc-cdn.nyc3.digitaloceanspaces.com/BMC-button-images/custom_images/orange_img.png" alt="Buy Me A Coffee" style="height: auto !important;width: auto !important;" ></a>
<a href="https://paypal.me/PiMachowski" target="_blank"><img src="https://www.paypalobjects.com/webstatic/mktg/logo/pp_cc_mark_37x23.jpg" border="0" alt="PayPal Logo" style="height: auto !important;width: auto !important;"></a>
