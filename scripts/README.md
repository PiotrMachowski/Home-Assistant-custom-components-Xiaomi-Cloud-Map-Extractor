# Map processor

This script can:
 - download map from Xiaomi cloud and parse it
 - parse already downloaded raw map file

To use this script it have to be in the same folder as [integration files](../custom_components/xiaomi_cloud_map_extractor).

Dependencies installation:
```bash
pip3 install pillow pybase64 python requests pycryptodome pyyaml
```

Downloading map from Xiaomi cloud:
```bash
python3 download --config camera.yaml
```

Parsing already downloaded raw map file:
```bash
python3 parse --config camera.yaml --map-file map_data.gz --api xiaomi
```

Config file (passed with argument `--config`) should contain configuration of `xiaomi_cloud_map_extractor` camera.