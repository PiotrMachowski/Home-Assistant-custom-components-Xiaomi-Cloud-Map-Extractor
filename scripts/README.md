# Map processor

This script can:
 - download map from Xiaomi cloud and parse it
 - parse already downloaded raw map file

To use this script it have to be in the same folder as [integration files](../custom_components/xiaomi_cloud_map_extractor).

Config file (passed with argument `--config`) should contain configuration of `xiaomi_cloud_map_extractor` camera (cloud credentials are used only for `download` mode).

### Dependencies installation
```bash
pip3 install pillow pybase64 python requests pycryptodome pyyaml
```

### Downloading map from Xiaomi cloud
```bash
python3 map_processor.py download --config camera.yaml
```

### Parsing already downloaded raw map file
```bash
python3 map_processor.py parse --config camera.yaml --map-file map_data.gz --api xiaomi
```

### Testing multiple raw map files
```bash
python3 map_processor.py test --config camera.yaml --test-data test_data
```
Supported file structure:
```
|-- camera.yaml
`-- test_data
    |-- dreame
    |   |-- map_data_dreame.vacuum.mc1808.b64
    |   |-- map_data_dreame.vacuum.p2028.b64
    |   `-- map_data_dreame.vacuum.p2259.b64
    |-- roidmi
    |   |-- map_data_roidmi.vacuum.v60_1.gz
    |   `-- map_data_viomi.vacuum.v18_1.gz
    |-- viomi
    |   |-- map_data_viomi.vacuum.v6.zlib
    |   `-- map_data_viomi.vacuum.v7_1.zlib
    `-- xiaomi
        |-- map_data_roborock.vacuum.a08.gz
        |-- map_data_roborock.vacuum.s5.gz
        `-- map_data_rockrobo.vacuum.v1.gz
```