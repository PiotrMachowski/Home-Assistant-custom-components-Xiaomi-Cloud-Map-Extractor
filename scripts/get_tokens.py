from .xiaomi_cloud_connector import XiaomiCloudConnector
from .const import *

# ********* CONFIGURATION *********

username = ""
password = ""
country = ""

# ********* CONFIGURATION END *********

connector = XiaomiCloudConnector(username, password)
logged = connector.login()
if logged:
    devices = connector.get_devices(country)
    print("Found devices:")
    for device in devices["result"]["list"]:
        print("-----")
        if "name" in device:
            print("NAME:  " + device["name"])
        if "did" in device:
            print("ID:    " + device["did"])
        if "localip" in device:
            print("IP:    " + device["localip"])
        if "token" in device:
            print("TOKEN: " + device["token"])
else:
    print("Unable to log in")
