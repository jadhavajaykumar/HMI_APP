from typing import Any, List

import snap7
from snap7.util import get_bool, get_int, get_uint, set_bool, set_int, set_uint

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
        
    @staticmethod
    def _is_uint16(tag: TagDefinition) -> bool:
        return str(tag.data_type).lower() in {"uint16", "word"}

    @staticmethod
    def _parse_dbx_address(address: int) -> tuple[int, int]:
        byte_index = int(address) // 100
        bit_index = int(address) % 100
        if bit_index < 0 or bit_index > 7:
            raise ValueError(
                f"Invalid Siemens DBX bit index {bit_index} for address {address}. "
                "Expected encoded form byte*100+bit where bit is 0..7."
            )
        return byte_index, bit_index

    def read_tags(self, tags: List[TagDefinition]) -> dict[str, Any]:
        if not self._connected:
            raise ConnectionError("Siemens S7 driver is not connected")
            
        out = {}
        for tag in tags:
            if tag.area == "dbw":
                raw = self.client.db_read(self.db_number, tag.address, 2)
                out[tag.name] = get_uint(raw, 0) if self._is_uint16(tag) else get_int(raw, 0)
            elif tag.area == "dbx":
                byte_index, bit_index = self._parse_dbx_address(tag.address)
                raw = self.client.db_read(self.db_number, byte_index, 1)
                out[tag.name] = get_bool(raw, 0, bit_index)
            else:
                out[tag.name] = None
        return out

    def write_tag(self, tag: TagDefinition, value: Any) -> bool:
        if not self._connected:
            raise ConnectionError("Siemens S7 driver is not connected")

        if tag.area == "dbw":
            data = bytearray(2)
            if self._is_uint16(tag):
                set_uint(data, 0, int(value))
            else:
                set_int(data, 0, int(value))
            self.client.db_write(self.db_number, tag.address, data)
            return True

        if tag.area == "dbx":
            byte_index, bit_index = self._parse_dbx_address(tag.address)
            data = self.client.db_read(self.db_number, byte_index, 1)
            set_bool(data, 0, bit_index, bool(value))
            self.client.db_write(self.db_number, byte_index, data)
            return True

        raise ValueError(f"Unsupported Siemens area: {tag.area}")