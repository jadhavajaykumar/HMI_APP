import json
from pathlib import Path
from typing import Dict, List

from hmi.models.tag_models import TagDefinition, TagValue


class TagManager:
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)

        self.raw_data = {}
        self.active_connection_name = ""
        self.connections = {}
        self.connection_config = {}

        self.manual_devices = []
        self.alarm_words = []

        self.tag_catalog = []
        self.tag_bindings = {}

        self.tag_defs: Dict[str, TagDefinition] = {}
        self.tag_values: Dict[str, TagValue] = {}

        self._load()

    def _load(self) -> None:
        self.raw_data = json.loads(self.config_path.read_text(encoding="utf-8"))

        self.connections = self.raw_data.get("connections", {})
        self.active_connection_name = self.raw_data.get("active_connection", "")
        if not self.active_connection_name and self.connections:
            self.active_connection_name = next(iter(self.connections.keys()))

        self.connection_config = self.connections.get(self.active_connection_name, {})
        self.manual_devices = self.raw_data.get("manual_devices", [])
        self.alarm_words = self.raw_data.get("alarm_words", [])

        # Prefer split architecture (tag_catalog + tag_bindings) while staying
        # backward compatible with older flat-tag configs.
        self.tag_catalog = self.raw_data.get("tag_catalog")
        if self.tag_catalog is None:
            self.tag_catalog = self.raw_data.get("tags", [])
            
        self.tag_bindings = self.raw_data.get("tag_bindings", {})
        self.ensure_binding_matrix()

        active_binding = self.tag_bindings.get(self.active_connection_name, {})

        old_values = {
            name: tv.value for name, tv in self.tag_values.items()
        } if self.tag_values else {}

        self.tag_defs = {}
        self.tag_values = {}

        for base_tag in self.tag_catalog:
            name = base_tag["name"]
            binding = active_binding.get(name, {})

            tag_data = {
                **base_tag,
                "area": binding.get("area", ""),
                "address": binding.get("address", ""),
            }

            tag_def = TagDefinition(**tag_data)
            self.tag_defs[tag_def.name] = tag_def
            self.tag_values[tag_def.name] = TagValue(
                definition=tag_def,
                value=old_values.get(tag_def.name, tag_def.default),
                quality="init"
            )

    def reload(self) -> None:
        self._load()

    def save(self) -> None:
        self.ensure_binding_matrix()
        self.raw_data["active_connection"] = self.active_connection_name
        self.raw_data["connections"] = self.connections
        self.raw_data["manual_devices"] = self.manual_devices
        self.raw_data["alarm_words"] = self.alarm_words
        self.raw_data["tag_catalog"] = self.tag_catalog
        self.raw_data["tag_bindings"] = self.tag_bindings

        self.config_path.write_text(
            json.dumps(self.raw_data, indent=2),
            encoding="utf-8"
        )

    def export_full_config(self) -> dict:
        return {
            "active_connection": self.active_connection_name,
            "connections": self.connections,
            "manual_devices": self.manual_devices,
            "alarm_words": self.alarm_words,
            "tag_catalog": self.tag_catalog,
            "tag_bindings": self.tag_bindings,
        }

    def import_full_config(self, config_data: dict) -> None:
        if not isinstance(config_data, dict):
            raise ValueError("Imported config must be a JSON object.")
        if "connections" not in config_data:
            raise ValueError("Imported config is missing 'connections'.")
        if "tag_catalog" not in config_data:
            raise ValueError("Imported config is missing 'tag_catalog'.")
        if "tag_bindings" not in config_data and "tags" not in config_data:
            raise ValueError("Imported config is missing 'tag_bindings' (or legacy 'tags').")

        self.raw_data = {
            "active_connection": config_data.get("active_connection", ""),
            "connections": config_data.get("connections", {}),
            "manual_devices": config_data.get("manual_devices", []),
            "alarm_words": config_data.get("alarm_words", []),
            "tag_catalog": config_data.get("tag_catalog", config_data.get("tags", [])),
            "tag_bindings": config_data.get("tag_bindings", {}),
        }

        self._load()

    def generate_validation_report(self) -> list[str]:
        issues = []
        tag_names = set(self.tag_defs.keys())

        if not self.connections:
            issues.append("No connection profiles defined.")

        if self.active_connection_name and self.active_connection_name not in self.connections:
            issues.append(f"Active connection '{self.active_connection_name}' is not present in connections.")

        for tag in self.tag_defs.values():
            if not str(tag.name).strip():
                issues.append("Found tag with empty name.")
            if tag.area == "":
                issues.append(f"Tag '{tag.name}' has empty area for active profile '{self.active_connection_name}'.")
            if str(tag.access).lower() not in {"r", "w", "rw"}:
                issues.append(f"Tag '{tag.name}' has invalid access '{tag.access}'.")

        for word in self.alarm_words:
            tag = word.get("tag", "")
            if tag not in tag_names:
                issues.append(f"Alarm word mapping references missing tag '{tag}'.")
            bits = word.get("bits", {})
            for bit_no in bits.keys():
                try:
                    bit_int = int(bit_no)
                    if bit_int < 0 or bit_int > 31:
                        issues.append(f"Alarm word '{tag}' uses invalid bit '{bit_no}'.")
                except Exception:
                    issues.append(f"Alarm word '{tag}' has non-integer bit '{bit_no}'.")

        for dev in self.manual_devices:
            key = dev.get("key", "")
            if not key:
                issues.append("Manual device with empty key found.")
            for ref_name in [
                dev.get("fwd_cmd", ""),
                dev.get("rev_cmd", ""),
                dev.get("running_fb", ""),
                dev.get("fwd_done_fb", ""),
                dev.get("rev_done_fb", ""),
                dev.get("interlock_word", ""),
            ]:
                if ref_name and ref_name not in tag_names:
                    issues.append(f"Manual device '{key}' references missing tag '{ref_name}'.")

        if not issues:
            issues.append("Validation OK: no issues found.")

        return issues

    # ---------- compatibility helpers for existing screens ----------

    def get_all_tag_dicts(self) -> list:
        """
        Compatibility method for existing SettingsScreen.
        Returns current logical tag catalog (without profile-specific binding fields).
        """
        return [dict(tag) for tag in self.tag_catalog]

    def replace_all_tags_from_dicts(self, tag_dicts: list):
        """
        Compatibility method for existing SettingsScreen tag editor.
        Replaces only the logical tag catalog.
        Keeps current profile bindings for tags that still exist.
        """
        self.tag_catalog = [dict(tag) for tag in tag_dicts]
        valid_names = {tag["name"] for tag in self.tag_catalog if "name" in tag}

        # prune bindings for deleted tags
        for profile_name, bindings in self.tag_bindings.items():
            self.tag_bindings[profile_name] = {
                tag_name: binding
                for tag_name, binding in bindings.items()
                if tag_name in valid_names
            }

        self.ensure_binding_matrix()
        
        self.raw_data["tag_catalog"] = self.tag_catalog
        self.raw_data["tag_bindings"] = self.tag_bindings
        self._load()

    def get_connection_names(self) -> List[str]:
        return list(self.connections.keys())

    def set_active_connection(self, connection_name: str) -> None:
        if connection_name not in self.connections:
            raise KeyError(f"Connection profile not found: {connection_name}")
        self.active_connection_name = connection_name
        self.connection_config = self.connections[connection_name]
        self.raw_data["active_connection"] = connection_name
        self._load()

    def get_active_connection_name(self) -> str:
        return self.active_connection_name

    def get_manual_devices(self):
        return self.manual_devices

    def set_manual_devices(self, devices: list):
        self.manual_devices = devices

    def get_alarm_words(self):
        return self.alarm_words

    def set_alarm_words(self, alarm_words: list):
        self.alarm_words = alarm_words

    def get_definition(self, tag_name: str) -> TagDefinition:
        return self.tag_defs[tag_name]

    def get_value(self, tag_name: str):
        return self.tag_values[tag_name].value

    def set_value(self, tag_name: str, value, quality: str = "good") -> None:
        tag = self.tag_values[tag_name]
        tag.value = value
        tag.quality = quality

    def all_tags(self) -> List[TagDefinition]:
        return list(self.tag_defs.values())

    def get_tag_catalog(self):
        return self.tag_catalog

    def get_tag_bindings(self):
        return self.tag_bindings

    # ---------- binding helpers ----------

    def ensure_binding_matrix(self):
        if not isinstance(self.tag_bindings, dict):
            self.tag_bindings = {}

        tag_names = [
            str(tag.get("name", "")).strip()
            for tag in self.tag_catalog
            if isinstance(tag, dict) and str(tag.get("name", "")).strip()
        ]

        for profile_name in self.connections.keys():
            profile_bindings = self.tag_bindings.get(profile_name, {})
            if not isinstance(profile_bindings, dict):
                profile_bindings = {}

            # prune deleted tags
            profile_bindings = {
                tag_name: binding
                for tag_name, binding in profile_bindings.items()
                if tag_name in tag_names
            }

            # create missing binding rows
            for tag_name in tag_names:
                profile_bindings.setdefault(tag_name, {"area": "", "address": ""})

            self.tag_bindings[profile_name] = profile_bindings

        # drop bindings for profiles that no longer exist
        self.tag_bindings = {
            profile_name: bindings
            for profile_name, bindings in self.tag_bindings.items()
            if profile_name in self.connections
        }

    def get_bindings_for_profile(self, profile_name: str) -> dict:
        self.ensure_binding_matrix()
        return dict(self.tag_bindings.get(profile_name, {}))

    def set_bindings_for_profile(self, profile_name: str, bindings: dict):
        if profile_name not in self.connections:
            raise KeyError(f"Connection profile not found: {profile_name}")

        self.ensure_binding_matrix()
        clean = {}
        for tag in self.tag_catalog:
            tag_name = str(tag.get("name", "")).strip()
            if not tag_name:
                continue
            b = bindings.get(tag_name, {}) if isinstance(bindings, dict) else {}
            clean[tag_name] = {
                "area": str(b.get("area", "")).strip(),
                "address": b.get("address", ""),
            }
        self.tag_bindings[profile_name] = clean