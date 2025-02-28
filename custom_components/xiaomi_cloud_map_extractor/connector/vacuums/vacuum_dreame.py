from typing import Self

from vacuum_map_parser_base.map_data import MapData

from vacuum_map_parser_dreame.map_data_parser import DreameMapDataParser
from .base.model import VacuumConfig, VacuumApi
from .base.vacuum_v2 import BaseXiaomiCloudVacuumV2


class DreameCloudVacuum(BaseXiaomiCloudVacuumV2):
    _dreame_map_data_parser: DreameMapDataParser
    _robot_stamp: int
    _enc_key: str | None

    def __init__(self: Self, vacuum_config: VacuumConfig) -> None:
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

    @staticmethod
    def vacuum_platform() -> VacuumApi:
        return VacuumApi.DREAME

    @property
    def map_archive_extension(self: Self) -> str:
        if self.model in DreameMapDataParser.IVs:
            return "enc.b64"
        return "b64"

    @property
    def map_data_parser(self: Self) -> DreameMapDataParser:
        return self._dreame_map_data_parser

    def decode_and_parse(self: Self, raw_map: bytes) -> MapData:
        decoded_map = self.map_data_parser.unpack_map(raw_map, enckey=self._enc_key)
        return self.map_data_parser.parse(decoded_map)

    async def get_map_name(self: Self) -> str | None:
        if self.model in DreameMapDataParser.IVs:
            if self._robot_stamp != 0:
                parameters = [{'piid': 2, 'value': f'{{"req_type":1,"frame_type":"I","time":{self._robot_stamp}}}'}]
            else:
                parameters = [{'piid': 2, 'value': '{"req_type":1,"frame_type":"I"}'}]

            response = await self._connector.get_other_info(self._device_id, "action", parameters={
                "did": self._device_id,
                "siid": 6,
                "aiid": 1,
                "in": parameters,
            })

            if response is None:
                return None

            _key = response["result"]["out"][1]["value"]

            if len(_key) == 0:
                self._robot_stamp = response["result"]["out"][2]["value"]
                return None

            _map_name = _key.split(",")
            map_name = _map_name[0].split("/")[2]
            self._enc_key = _map_name[1]
            self._robot_stamp = 0
            return map_name
        else:
            await self._connector.get_other_info(self._device_id, "action", parameters={
                "did": self._device_id,
                "siid": 6,
                "aiid": 1,
                "in": [{'piid': 2, 'value': '{"req_type":1,"frame_type":"I","force_type":1}'}],
            })
            return await super().get_map_name()

    def store_map(self: Self, raw_map_data):
        super().store_map(raw_map_data)
        with open(f"{self._store_map_path}/map_data_{self.model}.enc.key", "w") as enc_key_file:
            enc_key_file.write(self._enc_key)
