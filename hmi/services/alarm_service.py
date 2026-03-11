from datetime import datetime

from PySide6.QtCore import QObject, Signal

from hmi.models.tag_models import AlarmRecord


class AlarmService(QObject):
    active_alarm_count_changed = Signal(int)
    active_alarm_text_changed = Signal(str)
    alarm_history_changed = Signal()

    def __init__(self, tag_manager):
        super().__init__()
        self.tag_manager = tag_manager
        self.active = {}
        self.history = []

        self.tag_alarm_defs = {}
        self.alarm_word_defs = {}
        self.manual_interlock_defs = {}

        self.reload_from_tag_manager(clear_history=False)

    def reload_from_tag_manager(self, clear_history: bool = False):
        self.tag_alarm_defs = {}
        self.alarm_word_defs = {}
        self.manual_interlock_defs = {}

        for td in self.tag_manager.all_tags():
            if getattr(td, "alarm", False):
                self.tag_alarm_defs[td.name] = td

        for word in self.tag_manager.get_alarm_words():
            tag = word.get("tag", "")
            bits = word.get("bits", {})
            if tag:
                self.alarm_word_defs[tag] = bits

        for dev in self.tag_manager.get_manual_devices():
            interlock_tag = dev.get("interlock_word", "")
            if interlock_tag:
                self.manual_interlock_defs[interlock_tag] = {
                    "title": dev.get("title", dev.get("key", interlock_tag)),
                    "bits": dev.get("interlocks", {}),
                }

        self.active = {}
        if clear_history:
            self.history = []

        self._emit()

    def process_tag_change(self, tag_name: str, value):
        if tag_name in self.tag_alarm_defs:
            self._process_tag_alarm(tag_name, value)

        if tag_name in self.alarm_word_defs:
            self._process_word_alarm(
                tag_name=tag_name,
                value=value,
                bit_defs=self.alarm_word_defs[tag_name],
                prefix=f"alarm::{tag_name}",
                display_prefix="",
                source="plc_alarm",
                default_severity="warning",
            )

        if tag_name in self.manual_interlock_defs:
            dev = self.manual_interlock_defs[tag_name]
            self._process_word_alarm(
                tag_name=tag_name,
                value=value,
                bit_defs=dev.get("bits", {}),
                prefix=f"interlock::{tag_name}",
                display_prefix=f"{dev.get('title', tag_name)}: ",
                source="manual_interlock",
                default_severity="warning",
            )

    def _process_tag_alarm(self, tag_name: str, value):
        tag_def = self.tag_alarm_defs[tag_name]

        active_now = False
        if str(tag_def.data_type).lower() == "bool":
            if getattr(tag_def, "alarm_when", None) is None:
                active_now = bool(value)
            else:
                active_now = bool(value) == bool(tag_def.alarm_when)
        else:
            active_now = int(value or 0) != 0

        key = f"tag::{tag_name}"
        text = getattr(tag_def, "alarm_text", "") or tag_name
        severity = "warning"

        if active_now:
            self._activate_alarm(
                key=key,
                tag_name=tag_name,
                text=text,
                value=value,
                severity=severity,
                source="tag",
            )
        else:
            self._clear_alarm(key, value)

    def _process_word_alarm(
        self,
        tag_name: str,
        value,
        bit_defs: dict,
        prefix: str,
        display_prefix: str = "",
        source: str = "plc_alarm",
        default_severity: str = "warning",
    ):
        word_val = int(value or 0)
        active_keys_now = set()

        for bit_str, bit_def in bit_defs.items():
            bit = int(bit_str)
            text, severity = self._normalize_bit_def(bit_def, default_severity=default_severity)

            key = f"{prefix}.bit{bit}"
            if word_val & (1 << bit):
                active_keys_now.add(key)
                self._activate_alarm(
                    key=key,
                    tag_name=f"{tag_name}.bit{bit}",
                    text=f"{display_prefix}{text}",
                    value=word_val,
                    severity=severity,
                    source=source,
                )

        old_keys = [k for k in list(self.active.keys()) if k.startswith(prefix)]
        for key in old_keys:
            if key not in active_keys_now:
                self._clear_alarm(key, word_val)

    def _normalize_bit_def(self, bit_def, default_severity: str = "warning"):
        if isinstance(bit_def, dict):
            text = str(bit_def.get("text", "")).strip()
            severity = str(bit_def.get("severity", default_severity)).strip().lower() or default_severity
            return text, severity

        return str(bit_def), default_severity

    def _activate_alarm(self, key: str, tag_name: str, text: str, value, severity: str, source: str):
        if key in self.active:
            return

        rec = AlarmRecord(
            timestamp=self._ts(),
            tag_name=tag_name,
            text=text,
            value=value,
            state="ACTIVE",
            severity=severity,
            source=source,
        )
        self.active[key] = rec
        self.history.insert(0, rec)
        self._emit()

    def _clear_alarm(self, key: str, value):
        if key not in self.active:
            return

        old = self.active[key]
        rec = AlarmRecord(
            timestamp=self._ts(),
            tag_name=old.tag_name,
            text=old.text,
            value=value,
            state="CLEARED",
            severity=old.severity,
            source=old.source,
        )
        del self.active[key]
        self.history.insert(0, rec)
        self._emit()

    def _ts(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _emit(self):
        self.active_alarm_count_changed.emit(len(self.active))
        self.active_alarm_text_changed.emit(self.get_active_text())
        self.alarm_history_changed.emit()

    def get_active_count(self):
        return len(self.active)

    def get_active_text(self):
        if not self.active:
            return "No active alarms"
        first = next(iter(self.active.values()))
        return first.text

    def get_history(self):
        return self.history

    def get_filtered_history(self, severity: str = "all", state: str = "all", source: str = "all"):
        rows = self.history

        if severity != "all":
            rows = [r for r in rows if r.severity == severity]

        if state != "all":
            rows = [r for r in rows if r.state.lower() == state.lower()]

        if source != "all":
            rows = [r for r in rows if r.source == source]

        return rows