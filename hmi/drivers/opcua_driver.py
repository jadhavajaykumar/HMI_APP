import logging
from typing import Any, List

from asyncua.sync import Client

from hmi.drivers.base_driver import BasePlcDriver
from hmi.models.tag_models import TagDefinition


class OpcUaDriver(BasePlcDriver):
    def __init__(self, endpoint: str, username: str = "", password: str = ""):
        self.logger = logging.getLogger(__name__)
        self.endpoint = endpoint
        self.username = username
        self.password = password
        self.client = Client(self.endpoint)
        self._connected = False

        if self.username:
            self.client.set_user(self.username)
        if self.password:
            self.client.set_password(self.password)

    def connect(self) -> bool:
        self.logger.info(
            "OPC UA connect endpoint=%s username_set=%s",
            self.endpoint,
            bool(self.username),
        )
        self.client.connect()
        self._connected = True
        self.logger.info("OPC UA session established")
        return True

    def disconnect(self) -> None:
        if self._connected:
            self.client.disconnect()
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def read_tags(self, tags: List[TagDefinition]) -> dict[str, Any]:
        out = {}
        for tag in tags:
            if str(tag.area).lower() != "opcua_node":
                out[tag.name] = None
                continue

            node_id = str(tag.address)
            node = self.client.get_node(node_id)
            out[tag.name] = node.read_value()
        return out

    def write_tag(self, tag: TagDefinition, value: Any) -> bool:
        if str(tag.area).lower() != "opcua_node":
            raise ValueError(f"Unsupported OPC UA area: {tag.area}")

        node_id = str(tag.address)
        node = self.client.get_node(node_id)
        node.write_value(value)
        return True