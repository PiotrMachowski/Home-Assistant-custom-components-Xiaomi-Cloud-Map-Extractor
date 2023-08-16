from vacuum_map_parser_base.map_data import MapData
from vacuum_map_parser_dreame.map_data_parser import DreameMapDataParser

from .vacuum_base import VacuumConfig
from .vacuum_v2 import XiaomiCloudVacuumV2


class DreameCloudVacuum(XiaomiCloudVacuumV2):

    def __init__(self, vacuum_config: VacuumConfig):
        super().__init__(vacuum_config)
        self._dreame_map_data_parser = DreameMapDataParser(
            vacuum_config.palette,
            vacuum_config.sizes,
            vacuum_config.drawables,
            vacuum_config.image_config,
            vacuum_config.texts,
            vacuum_config.model,
        )
        self._robot_stamp = 0
        self._enc_key = None

    @property
    def map_archive_extension(self) -> str:
        if self.model in DreameMapDataParser.IVs:
            return "enc.b64"
        return "b64"

    @property
    def map_data_parser(self) -> DreameMapDataParser:
        return self._dreame_map_data_parser

    def decode_and_parse(self, raw_map: bytes) -> MapData:
        decoded_map = self.map_data_parser.unpack_map(raw_map, enckey=self._enc_key)
        return self.map_data_parser.parse(decoded_map)

    def get_map_name(self) -> str | None:
        if self.model in DreameMapDataParser.IVs:
            if self._robot_stamp != 0:
                parameters = [{'piid': 2, 'value': '{"req_type":1,"frame_type":"I","time":%d}' % self._robot_stamp}]
            else:
                parameters = [{'piid': 2, 'value': '{"req_type":1,"frame_type":"I"}'}]

            response = self._connector.get_other_info(self._device_id, "action", parameters={
                "did": self._device_id,
                "siid": 6,
                "aiid": 1,
                "in": parameters,
            })

            if response is None:
                return None

            _key = response["result"]["out"][1]["value"]

            if len(_key) == 0:
                robotstamp = response["result"]["out"][2]["value"]
                self._robot_stamp = robotstamp
                return None

            _map_name = _key.split(",")
            map_name = _map_name[0].split("/")[2]
            self._enc_key = _map_name[1]
            self._robot_stamp = 0
            return map_name
        else:
            return super().get_map_name()

    def store_map(self, raw_map_data):
        super().store_map(raw_map_data)
        with open(f"{self._store_map_path}/map_data_{self.model}.enc.key", "w") as enc_key_file:
            enc_key_file.write(self._enc_key)
