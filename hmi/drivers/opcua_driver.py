import logging
from typing import Any, List

from asyncua.sync import Client

from hmi.drivers.base_driver import BasePlcDriver
from hmi.models.tag_models import TagDefinition


class OpcUaDriver(BasePlcDriver):
    def __init__(
        self,
        endpoint: str,
        username: str = "",
        password: str = "",
        security_string: str = "",
    ):
        self.logger = logging.getLogger(__name__)
        self.endpoint = endpoint
        self.username = username
        self.password = password
        self.security_string = security_string
        self.client = Client(self.endpoint)
        self._connected = False
        self._bad_nodes_logged: set[str] = set()
        
        if self.security_string:
            self.client.set_security_string(self.security_string)

        if self.username:
            self.client.set_user(self.username)
        if self.password:
            self.client.set_password(self.password)

    def connect(self) -> bool:
        self.logger.info(
            "OPC UA connect endpoint=%s username_set=%s security_set=%s",
            self.endpoint,
            bool(self.username),
            bool(self.security_string),
        )
        try:
            self.client.connect()
            self._connected = True
            self._bad_nodes_logged.clear()
            self.logger.info("OPC UA session established")
            return True
        except Exception:
            self.logger.exception(
                "OPC UA connection failed endpoint=%s security_set=%s",
                self.endpoint,
                bool(self.security_string),
            )
            raise

    def disconnect(self) -> None:
        if self._connected:
            self.client.disconnect()
        self._connected = False
        self._bad_nodes_logged.clear()

    def is_connected(self) -> bool:
        return self._connected

    def read_tags(self, tags: List[TagDefinition]) -> dict[str, Any]:
        out = {}
        for tag in tags:
            if str(tag.area).lower() != "opcua_node":
                out[tag.name] = None
                continue

            node_id = str(tag.address)
            try:
                node = self.client.get_node(node_id)
                out[tag.name] = node.read_value()
            except Exception:
                if node_id not in self._bad_nodes_logged:
                    self._bad_nodes_logged.add(node_id)
                    self.logger.exception(
                        "OPC UA read failed tag='%s' node='%s' (value set to None)",
                        tag.name,
                        node_id,
                    )
                out[tag.name] = None
        return out

    def write_tag(self, tag: TagDefinition, value: Any) -> bool:
        if str(tag.area).lower() != "opcua_node":
            raise ValueError(f"Unsupported OPC UA area: {tag.area}")

        node_id = str(tag.address)
        try:
            node = self.client.get_node(node_id)
            node.write_value(value)
        except Exception:
            self.logger.exception("OPC UA write failed tag='%s' node='%s'", tag.name, node_id)
            raise
        return True