from typing import Any, List

import snap7
from snap7.util import get_bool, get_int, set_bool, set_int
from snap7.type import Areas

from hmi.drivers.base_driver import BasePlcDriver
from hmi.models.tag_models import TagDefinition


class SiemensS7Driver(BasePlcDriver):
    """
    Assumes tags map into DB bytes/bits for simplicity.
    Use area="dbx" for bool bit access and area="dbw" for int word access.
    address means:
      - dbx: byte.bit encoded as "byte*100 + bit", e.g. 1203 => byte 12 bit 3
      - dbw: byte offset of word
    """

    def __init__(self, host: str, rack: int = 0, slot: int = 1, db_number: int = 1):
        self.host = host
        self.rack = rack
        self.slot = slot
        self.db_number = db_number
        self.client = snap7.client.Client()
        self._connected = False

    def connect(self) -> bool:
        self.client.connect(self.host, self.rack, self.slot)
        self._connected = self.client.get_connected()
        return self._connected

    def disconnect(self) -> None:
        if self._connected:
            self.client.disconnect()
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def read_tags(self, tags: List[TagDefinition]) -> dict[str, Any]:
        out = {}
        for tag in tags:
            if tag.area == "dbw":
                raw = self.client.db_read(self.db_number, tag.address, 2)
                out[tag.name] = get_int(raw, 0)
            elif tag.area == "dbx":
                byte_index = tag.address // 100
                bit_index = tag.address % 100
                raw = self.client.db_read(self.db_number, byte_index, 1)
                out[tag.name] = get_bool(raw, 0, bit_index)
            else:
                out[tag.name] = None
        return out

    def write_tag(self, tag: TagDefinition, value: Any) -> bool:
        if tag.area == "dbw":
            data = bytearray(2)
            set_int(data, 0, int(value))
            self.client.db_write(self.db_number, tag.address, data)
            return True

        if tag.area == "dbx":
            byte_index = tag.address // 100
            bit_index = tag.address % 100
            data = self.client.db_read(self.db_number, byte_index, 1)
            set_bool(data, 0, bit_index, bool(value))
            self.client.db_write(self.db_number, byte_index, data)
            return True

        raise ValueError(f"Unsupported Siemens area: {tag.area}")