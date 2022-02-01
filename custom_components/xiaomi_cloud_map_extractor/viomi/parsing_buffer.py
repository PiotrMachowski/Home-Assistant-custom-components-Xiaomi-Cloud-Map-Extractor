import logging

from struct import unpack_from

_LOGGER = logging.getLogger(__name__)


class ParsingBuffer:
    def __init__(self, name: str, data: bytes, start_offs: int, length: int):
        self._name = name
        self._data = data
        self._offs = start_offs
        self._length = length
        self._image_beginning = None

    def set_name(self, name: str):
        self._name = name
        _LOGGER.debug('SECTION %s: offset 0x%x', self._name, self._offs)

    def mark_as_image_beginning(self):
        self._image_beginning = self._offs

    def get_at_image(self, offset) -> int:
        return self._data[self._image_beginning + offset - 1]

    def skip(self, field: str, n: int):
        if self._length < n:
            raise ValueError(f"error parsing {self._name}.{field} at offset {self._offs:#x}: buffer underrun")
        self._offs += n
        self._length -= n

    def get_uint8(self, field: str) -> int:
        if self._length < 1:
            raise ValueError(f"error parsing {self._name}.{field} at offset {self._offs:#x}: buffer underrun")
        self._offs += 1
        self._length -= 1
        return self._data[self._offs - 1]

    def get_uint16(self, field: str) -> int:
        if self._length < 2:
            raise ValueError(f"error parsing {self._name}.{field} at offset {self._offs:#x}: buffer underrun")
        self._offs += 2
        self._length -= 2
        return unpack_from('<H', self._data, self._offs - 2)[0]

    def get_uint32(self, field: str) -> int:
        if self._length < 4:
            raise ValueError(f"error parsing {self._name}.{field} at offset {self._offs:#x}: buffer underrun")
        self._offs += 4
        self._length -= 4
        return unpack_from('<L', self._data, self._offs - 4)[0]

    def get_float32(self, field: str) -> float:
        if self._length < 4:
            raise ValueError(f"error parsing {self._name}.{field} at offset {self._offs:#x}: buffer underrun")
        self._offs += 4
        self._length -= 4
        return unpack_from('<f', self._data, self._offs - 4)[0]

    def get_string_len8(self, field: str) -> str:
        n = self.get_uint8(field + '.len')
        if self._length < n:
            raise ValueError(f"error parsing {self._name}.{field} at offset {self._offs:#x}: buffer underrun")
        self._offs += n
        self._length -= n
        return self._data[self._offs - n:self._offs].decode('UTF-8')

    def peek_uint32(self, field: str) -> int:
        if self._length < 4:
            raise ValueError(f"error parsing {self._name}.{field} at offset {self._offs:#x}: buffer underrun")
        return unpack_from('<L', self._data, self._offs)[0]

    def check_empty(self):
        if self._length == 0:
            _LOGGER.debug('all of the data has been processed')
        else:
            _LOGGER.warning('%d bytes remained in the buffer', self._length)
