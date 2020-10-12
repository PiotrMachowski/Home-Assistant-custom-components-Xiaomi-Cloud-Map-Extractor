To use these scripts they have to be in the same folder as [integration files](../custom_components/xiaomi_cloud_map_extractor).
First step is configuration: you have to adjust lines marked with tags:
```
********* CONFIGURATION *********

(...)

********* CONFIGURATION END *********
```

Dependencies installation:
```bash
pip3 install pycryptodome python-miio pillow pybase64 python-secrets requests
```

Retrieving tokens
```bash
python3 get_tokens.py
```

Retrieving map
```bash
python3 get_map.py
```

To open binary map file (`map_data.gz`) you can use [RoboMapViever](https://github.com/marcelrv/XiaomiRobotVacuumProtocol/tree/master/RRMapFile).