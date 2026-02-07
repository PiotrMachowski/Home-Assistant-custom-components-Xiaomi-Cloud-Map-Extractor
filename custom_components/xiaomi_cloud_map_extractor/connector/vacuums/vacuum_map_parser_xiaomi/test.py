from time import time
from Crypto.Cipher import AES
from Crypto.Hash import MD5
from Crypto.Util.Padding import pad, unpad
import base64
import json
import zlib
import hashlib
from typing import Union

def inflate(data: Union[bytes, bytearray, memoryview, str]):
    if isinstance(data, str):
        # If we were accidentally passed a hex string, interpret it as such.
        # Otherwise, preserve raw byte values via latin1.
        stripped = data.strip()
        is_hex = len(stripped) % 2 == 0 and all(c in "0123456789abcdefABCDEF" for c in stripped)
        data = bytes.fromhex(stripped) if is_hex else stripped.encode("latin1")

    inflated_string = zlib.decompress(bytes(data)).decode("utf-8")
    return inflated_string

def loadMapFromFile(file_path: str):
    with open(file_path, 'rb') as f:
        rawMapContent = f.read()
        jsoMapContent = json.loads(rawMapContent)
        return base64_decode(jsoMapContent["data"].encode('latin1'))


def encrypt(source: bytes, key: bytes, iv: bytes):
    """
    Encrypts a string using AES encryption in CBC mode.
    """
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(pad(source, AES.block_size))
    return encrypted.hex().upper()

def decrypt(encrypted_bytes: bytes, key: bytes, iv: bytes) -> bytes:
    """
    Decrypts a string using AES decryption in CBC mode.
    """
    try:
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(encrypted_bytes)
        decrypted_unpadded = unpad(decrypted, AES.block_size, "pkcs7")
        return decrypted_unpadded
    except Exception as e:
        raise RuntimeError("AES decrypt failed (check modelKey/did/key derivation and input map data)") from e


def md5_hash(data: bytes):
    """
    Returns the MD5 hash of the given data.
    """
    return hashlib.md5(data).hexdigest()

def base64Encoding(input):
  dataBase64 = base64.b64encode(input)
  dataBase64P = dataBase64.decode("UTF-8")
  return dataBase64P

def base64_decode(input: bytes):
    """
    Decodes a Base64 string to hexadecimal.
    """
    decoded_bytes = base64.decodebytes(input)
    return decoded_bytes.hex()

def decryptMap(encryptedMapContent: bytes, modelKey: str, did: str):

    originalWork = modelKey + did

    iv = b"ABCDEF1234123412" # iv as a byte array

    encKey = encrypt(originalWork.encode('latin1'), modelKey.encode('latin1'), iv)
    encKey2 = bytes.fromhex(encKey)
    md5Key = md5_hash(encKey2)
    decryptKey = bytes.fromhex(md5Key)

    encryptedBytes = bytes.fromhex(encryptedMapContent)
    decrypted_base64_bytes = decrypt(encryptedBytes, decryptKey, iv)
    inflatedString = inflate(decrypted_base64_bytes)

    ## Write decrypted map to file
    #with open("0.decrypted.map.json", "w") as decryptedFile:
    #    # Writing data to a file
    #    decryptedFile.write(inflatedString)
    print ('MD5 Key:', md5Key)
    print ('AES Key:', decryptKey)
    return inflatedString, decrypted_base64_bytes

def transformMapData(map_data):
    if map_data is None:
        return None

    map_data = json.loads(map_data)

    map_id = map_data.get("map_id")
    map_rotate = map_data.get("rotate")
    map_name = map_data.get("map_name")
    map_version = map_data.get("map_type")
    map_temp = map_data.get("temp")
    map_height = map_data.get("height")
    map_width = map_data.get("width")
    task_id = map_data.get("task_id")
    origin_x = map_data.get("origin_x")
    origin_y = map_data.get("origin_y")
    have_charge_pile = map_data.get("have_pile")
    charge_pile_x = map_data.get("pile_x")
    charge_pile_y = map_data.get("pile_y")
    charge_pile_yaw = map_data.get("pile_yaw")
    map_resolution = map_data.get("resolution")

    # Inflate the base64-encoded map data
    byte_array = zlib.decompress(base64.b64decode(map_data.get("map_data")))

    # JSON can't serialize bytearray; store as list of uint8 values.
    data = list(byte_array)
    if map_data.get("dirty_map_data") is not None:
        dirty_byte_array = zlib.decompress(base64.b64decode(map_data.get("dirty_map_data")))
        data_dirty = list(dirty_byte_array)
    if map_data.get("additional_map_data") is not None:
        additional_byte_array = zlib.decompress(base64.b64decode(map_data.get("additional_map_data")))
        data_additional = list(additional_byte_array)
    fb_walls = map_data.get("fb_walls")
    fb_area = map_data.get("fb_regions")
    rooms = map_data.get("room_attrs")
    ai_obj = map_data.get("ai_region")
    ai_region = map_data.get("ai_region")
    furniture = map_data.get("furniture")
    carpet = map_data.get("carpets")
    threed_info = map_data.get("map_3d_info")
    cleaning = map_data.get("current_cleaning_config")
    room_colors = None

    if isinstance(map_data.get("map_room_info"), list):
        room_colors = {}
        for item in map_data["map_room_info"]:
            room_colors[item["grid_id"]] = item["color"]


    position = map_data.get("position")
    path = map_data.get("paths")
    dirty_path = map_data.get("dirty_paths")
    mop_fall_pos = map_data.get("mop_fall_pos")
    door = map_data.get("map_sills")
    dirty_clean_zone = map_data.get("dirty_clean_zones")
    hidden_zones = map_data.get("hidden_zones")

    # Charge details
    charge = {
        "haveChargePile": have_charge_pile,
        "chargePileX": charge_pile_x,
        "chargePileY": charge_pile_y,
        "chargePileYaw": charge_pile_yaw,
    }

    # Origin details
    origin = {
        "x": round(origin_x / 1000, 2) if origin_x is not None else None,
        "y": round(origin_y / 1000, 2) if origin_y is not None else None,
    }

    # Accuracy
    accuracy = round(map_resolution / 1000, 2) if map_resolution is not None else None

    # Header
    header = {
        "key": int(time() * 1000),
        "mapId": map_id,
        "rotate": map_rotate,
        "map_name": map_name,
        "mapVersion": map_version,
        "mapWidth": map_width,
        "mapHeight": map_height,
        "mapTemp": map_temp,
        "resolution": map_resolution,
        "taskID": task_id,
        "charge": charge,
        "origin": origin,
        "accuracy": accuracy,
        "roomColors": room_colors,
        "position": position,
    }

    # Extra
    extra = {
        "fbWalls": fb_walls,
        "fbArea": fb_area,
        "AI_obj": ai_obj,
        "AI_region": ai_region,
        "furniture": furniture,
        "carpet": carpet,
        "3d_info": threed_info,
        "rooms": rooms,
        "cleaning": cleaning,
        "path": path,
    }

    # Final map structure
    map_result = {
        "header": header,
        "data": data,
        "extra": extra,
    }

    return map_result


def main():
    # _miot.Device.model.slice(-16)
    modelKey = "mi.vacuum.e101gb"
    # _miot.Device.deviceID
    did = "1154453654"

    mapContent = loadMapFromFile(r"D:\Projects\xiaomi vacuum\raw_map_data.txt")
    decryptedMapContent, decrypted_base64_bytes = decryptMap(mapContent, modelKey, did)

    transformedMapData = transformMapData(decryptedMapContent)

    with open(r"D:\Projects\xiaomi vacuum\data_raw.txt", "wb") as f:
        f.write(decrypted_base64_bytes)
        f.close()


    with open(r"D:\Projects\xiaomi vacuum\data_final_raw.json", "w", encoding="utf-8") as f:
        f.write(decryptedMapContent)
        f.close()

    with open(r"D:\Projects\xiaomi vacuum\data_final.json", "w", encoding="utf-8") as f:
        json.dump(transformedMapData, f, ensure_ascii=False)
        f.close()

    #print ('Map content:', transformedMapData)

if __name__ == "__main__":
    main()