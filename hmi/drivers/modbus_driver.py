from typing import Any, List

from pymodbus.client import ModbusTcpClient

from hmi.drivers.base_driver import BasePlcDriver
from hmi.models.tag_models import TagDefinition


class ModbusDriver(BasePlcDriver):
    def __init__(self, host: str, port: int = 502, slave_id: int = 1):
        self.host = host
        self.port = port
        self.slave_id = slave_id
        self.client = ModbusTcpClient(host=self.host, port=self.port)

    def connect(self) -> bool:
        return self.client.connect()

    def disconnect(self) -> None:
        self.client.close()

    def is_connected(self) -> bool:
        return bool(self.client.connected)

    def read_tags(self, tags: List[TagDefinition]) -> dict[str, Any]:
        result = {}
        for tag in tags:
            if tag.area == "holding_register":
                rr = self.client.read_holding_registers(tag.address, count=1, slave=self.slave_id)
                result[tag.name] = None if rr.isError() else rr.registers[0]
            elif tag.area == "coil":
                rr = self.client.read_coils(tag.address, count=1, slave=self.slave_id)
                result[tag.name] = None if rr.isError() else rr.bits[0]
            else:
                result[tag.name] = None
        return result

    def write_tag(self, tag: TagDefinition, value: Any) -> bool:
        if tag.area == "coil":
            rr = self.client.write_coil(tag.address, bool(value), slave=self.slave_id)
            return not rr.isError()
        if tag.area == "holding_register":
            rr = self.client.write_register(tag.address, int(value), slave=self.slave_id)
            return not rr.isError()
        raise ValueError(f"Unsupported write area: {tag.area}")