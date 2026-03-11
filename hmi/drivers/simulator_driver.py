from typing import Any, List

from hmi.drivers.base_driver import BasePlcDriver
from hmi.models.tag_models import TagDefinition


class SimulatorDriver(BasePlcDriver):
    def __init__(self, tag_defs=None, manual_devices=None, alarm_words=None):
        self._connected = False
        self.tag_defs = tag_defs or []
        self.manual_devices = manual_devices or []
        self.alarm_words = alarm_words or []

        self._memory = {}
        self._tag_by_name = {}
        self._motion_state = {}

        for tag in self.tag_defs:
            self._tag_by_name[tag.name] = tag
            self._memory[(tag.area, tag.address)] = tag.default

        for dev in self.manual_devices:
            key = dev.get("key", dev.get("title", "device"))
            self._motion_state[key] = {"counter": 0, "direction": None}

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def read_tags(self, tags: List[TagDefinition]) -> dict[str, Any]:
        if not self._connected:
            raise ConnectionError("Simulator not connected")

        self._simulate_manual_devices()
        self._simulate_machine_status()

        out = {}
        for tag in tags:
            out[tag.name] = self._memory.get((tag.area, tag.address), tag.default)
        return out

    def write_tag(self, tag: TagDefinition, value: Any) -> bool:
        if not self._connected:
            raise ConnectionError("Simulator not connected")
        self._memory[(tag.area, tag.address)] = value
        return True

    # ---------------- Helpers ----------------

    def _set_tag_by_name(self, tag_name: str, value):
        tag = self._tag_by_name.get(tag_name)
        if not tag:
            return
        self._memory[(tag.area, tag.address)] = value

    def _get_tag_by_name(self, tag_name: str, default=None):
        tag = self._tag_by_name.get(tag_name)
        if not tag:
            return default
        return self._memory.get((tag.area, tag.address), default)

    def _simulate_manual_devices(self):
        any_running = False

        for dev in self.manual_devices:
            key = dev.get("key", dev.get("title", "device"))
            state = self._motion_state.setdefault(key, {"counter": 0, "direction": None})

            fwd_cmd = bool(self._get_tag_by_name(dev.get("fwd_cmd", ""), False))
            rev_cmd = bool(self._get_tag_by_name(dev.get("rev_cmd", ""), False))
            running_tag = dev.get("running_fb", "")
            fwd_done_tag = dev.get("fwd_done_fb", "")
            rev_done_tag = dev.get("rev_done_fb", "")
            interlock_word_tag = dev.get("interlock_word", "")

            interlock_word = int(self._get_tag_by_name(interlock_word_tag, 0) or 0)

            if state["counter"] > 0:
                state["counter"] -= 1
                self._set_tag_by_name(running_tag, True)
                any_running = True

                if state["counter"] == 0:
                    self._set_tag_by_name(running_tag, False)
                    if state["direction"] == "fwd":
                        self._set_tag_by_name(fwd_done_tag, True)
                    elif state["direction"] == "rev":
                        self._set_tag_by_name(rev_done_tag, True)
                    state["direction"] = None

            else:
                self._set_tag_by_name(running_tag, False)

                if fwd_cmd and interlock_word == 0:
                    self._set_tag_by_name(fwd_done_tag, False)
                    self._set_tag_by_name(rev_done_tag, False)
                    self._set_tag_by_name(running_tag, True)
                    state["counter"] = 5
                    state["direction"] = "fwd"
                    any_running = True

                elif rev_cmd and interlock_word == 0:
                    self._set_tag_by_name(fwd_done_tag, False)
                    self._set_tag_by_name(rev_done_tag, False)
                    self._set_tag_by_name(running_tag, True)
                    state["counter"] = 5
                    state["direction"] = "rev"
                    any_running = True

        self._set_if_exists("Machine.RunStatus", 1 if any_running else 0)

    def _simulate_machine_status(self):
        if self._tag_by_name.get("Machine.FaultCode") and self._tag_by_name.get("Alarm.Word0"):
            word0 = int(self._get_tag_by_name("Alarm.Word0", 0) or 0)
            self._set_tag_by_name("Machine.FaultCode", 1 if word0 else 0)

    def _set_if_exists(self, tag_name: str, value):
        if tag_name in self._tag_by_name:
            self._set_tag_by_name(tag_name, value)