import json

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from hmi.services.plc_service import PlcService
from hmi.services.tag_manager import TagManager


class SettingsScreen(QWidget):
    config_saved = Signal(str)

    DRIVER_OPTIONS = ["simulator", "modbus", "siemens_s7", "opcua"]
    TAG_GROUP_OPTIONS = ["status", "manual", "command", "recipe", "io", "alarm", "system"]
    TAG_AREA_OPTIONS = ["", "coil", "holding_register", "input_register", "discrete_input", "dbw", "dbx", "opcua_node"]
    TAG_TYPE_OPTIONS = ["bool", "uint16", "int16", "uint32", "int32", "float", "string"]
    TAG_ACCESS_OPTIONS = ["r", "w", "rw"]
    ALARM_SEVERITY_OPTIONS = ["critical", "warning", "info"]

    def __init__(self, plc_service: PlcService, tag_manager: TagManager, current_user=None, app_config=None):
        super().__init__()
        self.plc = plc_service
        self.tag_manager = tag_manager
        self.current_user = current_user or {}
        self.app_config = app_config or {}

        self.is_admin = str(self.current_user.get("role", "")).lower() == "admin"
        self.engineering_mode = bool(self.app_config.get("engineering_mode", False))
        self.production_lock_mode = bool(self.app_config.get("production_lock_mode", False))

        role_permissions = self.app_config.get("role_permissions", {})
        self.user_role = str(self.current_user.get("role", "operator")).lower()
        self.permissions = role_permissions.get(self.user_role, {})

        self.engineering_edit_allowed = bool(self.permissions.get("engineering_edit", False)) and not self.production_lock_mode

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        title = QLabel("Settings")
        title.setObjectName("SectionTitle")
        root.addWidget(title)

        if self.production_lock_mode:
            warn = QLabel(
                "Production Lock Mode is ON. Engineering edits are disabled. Runtime profile selection is still available."
            )
            warn.setWordWrap(True)
            warn.setObjectName("SubtleText")
            root.addWidget(warn)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        self.runtime_tab = QWidget()
        self.tabs.addTab(self.runtime_tab, "Runtime")
        self._build_runtime_tab()

        if self.engineering_mode and self.is_admin:
            self.profiles_tab = QWidget()
            self.tag_catalog_tab = QWidget()
            self.tag_binding_tab = QWidget()
            self.alarms_tab = QWidget()
            self.manual_tab = QWidget()
            self.help_tab = QWidget()

            self.tabs.addTab(self.profiles_tab, "Profiles")
            self.tabs.addTab(self.tag_catalog_tab, "Tag Catalog")
            self.tabs.addTab(self.tag_binding_tab, "Tag Binding")
            self.tabs.addTab(self.alarms_tab, "Alarm Mapping")
            self.tabs.addTab(self.manual_tab, "Manual Devices")
            self.tabs.addTab(self.help_tab, "Help")

            self._build_profiles_tab()
            self._build_tag_catalog_tab()
            self._build_tag_binding_tab()
            self._build_alarms_tab()
            self._build_manual_tab()
            self._build_help_tab()
        else:
            note = QLabel("Engineering configuration is available only in admin login and engineering mode.")
            note.setWordWrap(True)
            root.addWidget(note)

    # ---------------- Runtime ----------------

    def _build_runtime_tab(self):
        layout = QVBoxLayout(self.runtime_tab)

        top_help = QLabel(
            "Use this tab for profile selection and basic runtime connection control. "
            "Engineering import/export is available below for admin users."
        )
        top_help.setWordWrap(True)
        top_help.setObjectName("SubtleText")
        layout.addWidget(top_help)

        self.cmb_profile = QComboBox()
        self.cmb_profile.addItems(self.plc.get_connection_names())
        self.cmb_profile.setCurrentText(self.plc.get_active_connection_name())

        self.chk_persist = QCheckBox("Save selected profile to config file")

        self.lbl_driver = QLabel("-")
        self.lbl_host = QLabel("-")
        self.lbl_port = QLabel("-")
        self.lbl_poll = QLabel("-")

        form = QFormLayout()
        form.addRow("Connection Profile", self.cmb_profile)
        form.addRow("", self.chk_persist)
        form.addRow("Driver", self.lbl_driver)
        form.addRow("Host / URL", self.lbl_host)
        form.addRow("Port", self.lbl_port)
        form.addRow("Poll Interval (ms)", self.lbl_poll)

        self.btn_apply = QPushButton("Apply Profile")
        self.btn_apply.setObjectName("PrimaryButton")
        self.btn_connect = QPushButton("Connect")
        self.btn_connect.setObjectName("PrimaryButton")
        self.btn_disconnect = QPushButton("Disconnect")

        layout.addLayout(form)
        layout.addWidget(self.btn_apply)
        layout.addWidget(self.btn_connect)
        layout.addWidget(self.btn_disconnect)

        if self.engineering_mode and self.is_admin:
            backup_row = QHBoxLayout()
            self.btn_export_config = QPushButton("Export Config Backup")
            self.btn_import_config = QPushButton("Import Config Backup")
            backup_row.addWidget(self.btn_export_config)
            backup_row.addWidget(self.btn_import_config)
            backup_row.addStretch()
            layout.addLayout(backup_row)

            self.btn_export_config.clicked.connect(self.export_config_backup)
            self.btn_import_config.clicked.connect(self.import_config_backup)

            if not self.engineering_edit_allowed:
                self.btn_import_config.setEnabled(False)

        layout.addStretch()

        self.btn_apply.clicked.connect(self.apply_profile)
        self.btn_connect.clicked.connect(self.plc.start)
        self.btn_disconnect.clicked.connect(self.plc.stop)
        self.cmb_profile.currentTextChanged.connect(self.preview_profile)

        self.plc.active_profile_changed.connect(self.on_profile_changed)
        self.preview_profile(self.cmb_profile.currentText())

    def export_config_backup(self):
        try:
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Config Backup",
                "hmi_config_backup.json",
                "JSON Files (*.json)"
            )
            if not path:
                return

            data = self.tag_manager.export_full_config()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            QMessageBox.information(self, "Export Successful", f"Backup exported to:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Error", str(exc))

    def import_config_backup(self):
        if not self.engineering_edit_allowed:
            QMessageBox.warning(self, "Locked", "Engineering edits are disabled.")
            return

        try:
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Import Config Backup",
                "",
                "JSON Files (*.json)"
            )
            if not path:
                return

            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.tag_manager.import_full_config(data)
            self.tag_manager.save()
            self.config_saved.emit("import_backup")
            QMessageBox.information(self, "Import Successful", "Configuration imported and reloaded.")
        except Exception as exc:
            QMessageBox.critical(self, "Import Error", str(exc))

    def preview_profile(self, profile_name: str):
        cfg = self.tag_manager.connections.get(profile_name, {})
        self.lbl_driver.setText(str(cfg.get("driver", "")))
        
        endpoint = str(cfg.get("endpoint", "")).strip()
        host_value = endpoint or str(cfg.get("host", ""))
        self.lbl_host.setText(host_value)

        port_value = cfg.get("port", "")
        if not port_value and endpoint.startswith("opc.tcp://"):
            try:
                host_port = endpoint.split("://", 1)[1].split("/", 1)[0]
                if ":" in host_port:
                    port_value = host_port.rsplit(":", 1)[1]
            except Exception:
                port_value = ""

        self.lbl_port.setText(str(port_value))
        self.lbl_poll.setText(str(cfg.get("poll_ms", "")))

    def apply_profile(self):
        profile_name = self.cmb_profile.currentText()
        persist = self.chk_persist.isChecked()
        try:
            self.plc.set_active_connection(profile_name, persist=persist)
            QMessageBox.information(self, "Profile Applied", f"Active connection profile changed to: {profile_name}")
            self.preview_profile(profile_name)
        except Exception as exc:
            QMessageBox.critical(self, "Profile Error", str(exc))

    def on_profile_changed(self, profile_name: str):
        self.cmb_profile.blockSignals(True)
        self.cmb_profile.setCurrentText(profile_name)
        self.cmb_profile.blockSignals(False)
        self.preview_profile(profile_name)

    # ---------------- Profiles ----------------

    def _build_profiles_tab(self):
        layout = QVBoxLayout(self.profiles_tab)

        hint = QLabel(
            "Profile fields:\n"
            "- Name: unique profile name.\n"
            "- Driver: simulator / modbus / siemens_s7 / opcua.\n"
            "- Host: PLC IP or endpoint.\n"
            "- Port: communication port.\n"
            "- Poll ms: scan interval in milliseconds."
        )
        hint.setWordWrap(True)
        hint.setObjectName("SubtleText")
        layout.addWidget(hint)

        self.tbl_profiles = QTableWidget(0, 5)
        self.tbl_profiles.setHorizontalHeaderLabels(["Name", "Driver", "Host", "Port", "Poll ms"])
        layout.addWidget(self.tbl_profiles)

        btn_row = QHBoxLayout()
        self.btn_profile_add = QPushButton("Add Profile")
        self.btn_profile_delete = QPushButton("Delete Selected")
        self.btn_profile_save = QPushButton("Save Profiles")
        self.btn_profile_save.setObjectName("PrimaryButton")
        btn_row.addWidget(self.btn_profile_add)
        btn_row.addWidget(self.btn_profile_delete)
        btn_row.addWidget(self.btn_profile_save)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.btn_profile_add.clicked.connect(self.add_profile_row)
        self.btn_profile_delete.clicked.connect(self.delete_selected_profile_row)
        self.btn_profile_save.clicked.connect(self.save_profiles_tab)

        self.load_profiles_table()
        self._apply_engineering_lock([self.btn_profile_add, self.btn_profile_delete, self.btn_profile_save, self.tbl_profiles])

    def load_profiles_table(self):
        data = self.tag_manager.connections
        self.tbl_profiles.setRowCount(0)
        for name, cfg in data.items():
            self._insert_profile_row(name, cfg)

    def _insert_profile_row(self, name="", cfg=None):
        cfg = cfg or {}
        row = self.tbl_profiles.rowCount()
        self.tbl_profiles.insertRow(row)

        self.tbl_profiles.setItem(row, 0, QTableWidgetItem(str(name)))

        driver = QComboBox()
        driver.addItems(self.DRIVER_OPTIONS)
        driver.setCurrentText(str(cfg.get("driver", "simulator")))
        self.tbl_profiles.setCellWidget(row, 1, driver)

        self.tbl_profiles.setItem(row, 2, QTableWidgetItem(str(cfg.get("host", ""))))
        self.tbl_profiles.setItem(row, 3, QTableWidgetItem(str(cfg.get("port", ""))))
        self.tbl_profiles.setItem(row, 4, QTableWidgetItem(str(cfg.get("poll_ms", 250))))

    def add_profile_row(self):
        self._insert_profile_row()

    def delete_selected_profile_row(self):
        row = self.tbl_profiles.currentRow()
        if row >= 0:
            self.tbl_profiles.removeRow(row)

    def save_profiles_tab(self):
        if not self.engineering_edit_allowed:
            QMessageBox.warning(self, "Locked", "Engineering edits are disabled.")
            return

        try:
            profiles = {}
            for row in range(self.tbl_profiles.rowCount()):
                name = self._table_text(self.tbl_profiles, row, 0)
                if not name:
                    continue
                if name in profiles:
                    raise ValueError(f"Duplicate profile name: {name}")

                driver = self._combo_value(self.tbl_profiles, row, 1, "simulator")
                previous_cfg = dict(self.tag_manager.connections.get(name, {}))
                host_text = self._table_text(self.tbl_profiles, row, 2)
                port_value = self._safe_int(self._table_text(self.tbl_profiles, row, 3), 0)
                poll_ms = self._safe_int(self._table_text(self.tbl_profiles, row, 4), 250)

                profile_cfg = dict(previous_cfg)
                profile_cfg.update({
                    "driver": driver,
                    "host": host_text,
                    "port": port_value,
                    "poll_ms": poll_ms,
                })

                if driver == "opcua":
                    endpoint = str(previous_cfg.get("endpoint", "")).strip()
                    if host_text.lower().startswith("opc.tcp://"):
                        endpoint = host_text
                    elif host_text:
                        effective_port = port_value or 4840
                        endpoint = f"opc.tcp://{host_text}:{effective_port}"
                    if endpoint:
                        profile_cfg["endpoint"] = endpoint

                profiles[name] = profile_cfg

            self.tag_manager.connections = profiles
            if self.tag_manager.active_connection_name not in profiles and profiles:
                self.tag_manager.active_connection_name = next(iter(profiles.keys()))
            self.tag_manager.ensure_binding_matrix()    
            self.tag_manager.save()
            self.refresh_runtime_profile_list()
            self.refresh_binding_profile_list()
            self.config_saved.emit("profiles")
            QMessageBox.information(self, "Saved", "Profiles saved successfully.")
        except Exception as exc:
            QMessageBox.critical(self, "Save Error", str(exc))

    def refresh_runtime_profile_list(self):
        names = self.tag_manager.get_connection_names()
        self.cmb_profile.blockSignals(True)
        self.cmb_profile.clear()
        self.cmb_profile.addItems(names)
        self.cmb_profile.setCurrentText(self.tag_manager.get_active_connection_name())
        self.cmb_profile.blockSignals(False)
        self.preview_profile(self.cmb_profile.currentText())

    def refresh_binding_profile_list(self):
        if not hasattr(self, "cmb_binding_profile"):
            return
        names = self.tag_manager.get_connection_names()
        current = self.tag_manager.get_active_connection_name()
        self.cmb_binding_profile.blockSignals(True)
        self.cmb_binding_profile.clear()
        self.cmb_binding_profile.addItems(names)
        self.cmb_binding_profile.setCurrentText(current)
        self.cmb_binding_profile.blockSignals(False)
        self.load_tag_binding_table(current)

    # ---------------- Tag Catalog ----------------

    def _build_tag_catalog_tab(self):
        layout = QVBoxLayout(self.tag_catalog_tab)

        hint = QLabel(
            "Tag Catalog fields:\n"
            "- Name: logical tag used by app screens.\n"
            "- Group: functional grouping like manual/status/alarm.\n"
            "- Data Type: bool, uint16, int16, float, etc.\n"
            "- Access: r / w / rw.\n"
            "- Default: fallback/startup value.\n"
            "- Scale: used for numeric scaling."
        )
        hint.setWordWrap(True)
        hint.setObjectName("SubtleText")
        layout.addWidget(hint)

        self.tbl_tags = QTableWidget(0, 6)
        self.tbl_tags.setHorizontalHeaderLabels(
            ["Name", "Group", "Data Type", "Access", "Default", "Scale"]
        )
        layout.addWidget(self.tbl_tags)

        btn_row = QHBoxLayout()
        self.btn_tag_add = QPushButton("Add Tag")
        self.btn_tag_delete = QPushButton("Delete Selected")
        self.btn_tag_save = QPushButton("Save Tag Catalog")
        self.btn_tag_save.setObjectName("PrimaryButton")
        btn_row.addWidget(self.btn_tag_add)
        btn_row.addWidget(self.btn_tag_delete)
        btn_row.addWidget(self.btn_tag_save)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.btn_tag_add.clicked.connect(self.add_tag_row)
        self.btn_tag_delete.clicked.connect(self.delete_selected_tag_row)
        self.btn_tag_save.clicked.connect(self.save_tag_catalog_tab)

        self.load_tag_catalog_table()
        self._apply_engineering_lock([self.btn_tag_add, self.btn_tag_delete, self.btn_tag_save, self.tbl_tags])

    def load_tag_catalog_table(self):
        self.tbl_tags.setRowCount(0)
        tags = self.tag_manager.get_all_tag_dicts()
        for tag in tags:
            self._insert_tag_catalog_row(tag)

    def _insert_tag_catalog_row(self, tag=None):
        tag = tag or {}
        row = self.tbl_tags.rowCount()
        self.tbl_tags.insertRow(row)

        self.tbl_tags.setItem(row, 0, QTableWidgetItem(str(tag.get("name", ""))))

        cmb_group = QComboBox()
        cmb_group.setEditable(True)
        cmb_group.addItems(self.TAG_GROUP_OPTIONS)
        cmb_group.setCurrentText(str(tag.get("group", "status")))
        self.tbl_tags.setCellWidget(row, 1, cmb_group)

        cmb_type = QComboBox()
        cmb_type.setEditable(True)
        cmb_type.addItems(self.TAG_TYPE_OPTIONS)
        cmb_type.setCurrentText(str(tag.get("data_type", "bool")))
        self.tbl_tags.setCellWidget(row, 2, cmb_type)

        cmb_access = QComboBox()
        cmb_access.addItems(self.TAG_ACCESS_OPTIONS)
        cmb_access.setCurrentText(str(tag.get("access", "r")))
        self.tbl_tags.setCellWidget(row, 3, cmb_access)

        self.tbl_tags.setItem(row, 4, QTableWidgetItem(str(tag.get("default", ""))))
        self.tbl_tags.setItem(row, 5, QTableWidgetItem(str(tag.get("scale", 1.0))))

    def add_tag_row(self):
        self._insert_tag_catalog_row()

    def delete_selected_tag_row(self):
        row = self.tbl_tags.currentRow()
        if row >= 0:
            self.tbl_tags.removeRow(row)

    def save_tag_catalog_tab(self):
        if not self.engineering_edit_allowed:
            QMessageBox.warning(self, "Locked", "Engineering edits are disabled.")
            return

        try:
            tag_dicts = []
            names = set()

            for row in range(self.tbl_tags.rowCount()):
                name = self._table_text(self.tbl_tags, row, 0)
                if not name:
                    continue
                if name in names:
                    raise ValueError(f"Duplicate tag name: {name}")
                names.add(name)

                tag_dicts.append({
                    "name": name,
                    "group": self._combo_value(self.tbl_tags, row, 1, "status"),
                    "data_type": self._combo_value(self.tbl_tags, row, 2, "bool"),
                    "access": self._combo_value(self.tbl_tags, row, 3, "r"),
                    "default": self._parse_default(self._table_text(self.tbl_tags, row, 4)),
                    "scale": self._safe_float(self._table_text(self.tbl_tags, row, 5), 1.0),
                })

            name_set = {t["name"] for t in tag_dicts}
            self._validate_alarm_mapping_against_tag_names(name_set)
            self._validate_manual_devices_against_tag_names(name_set)

            self.tag_manager.replace_all_tags_from_dicts(tag_dicts)
            self.tag_manager.save()
            self.load_tag_binding_table()
            self.config_saved.emit("tags")
            QMessageBox.information(self, "Saved", "Tag catalog saved successfully.")
        except Exception as exc:
            QMessageBox.critical(self, "Save Error", str(exc))

    # ---------------- Tag Binding ----------------

    def _build_tag_binding_tab(self):
        layout = QVBoxLayout(self.tag_binding_tab)

        hint = QLabel(
            "Tag Binding fields (for selected profile):\n"
            "- Tag: logical name from catalog.\n"
            "- Area: driver-specific memory area / node type.\n"
            "- Address: register/offset/node id for selected profile.\n"
            "- This table is user-definable and should match your PLC/OPC program map.\n"
            "- Modbus: coil/holding_register/input_register/discrete_input + numeric address.\n"
            "- Siemens S7: dbw byte-offset, dbx encoded as byte*100+bit (1203 => DBX12.3).\n"
            "- OPC UA: opcua_node + full NodeId string (ns=...;s=...)."
        )
        hint.setWordWrap(True)
        hint.setObjectName("SubtleText")
        layout.addWidget(hint)

        self.cmb_binding_profile = QComboBox()
        self.cmb_binding_profile.addItems(self.tag_manager.get_connection_names())
        self.cmb_binding_profile.setCurrentText(self.tag_manager.get_active_connection_name())
        layout.addWidget(self.cmb_binding_profile)

        self.tbl_bindings = QTableWidget(0, 3)
        self.tbl_bindings.setHorizontalHeaderLabels(["Tag", "Area", "Address"])
        layout.addWidget(self.tbl_bindings)

        btn_row = QHBoxLayout()
        self.btn_binding_save = QPushButton("Save Tag Bindings")
        self.btn_binding_save.setObjectName("PrimaryButton")
        btn_row.addWidget(self.btn_binding_save)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.cmb_binding_profile.currentTextChanged.connect(self.load_tag_binding_table)
        self.btn_binding_save.clicked.connect(self.save_tag_binding_tab)

        self.load_tag_binding_table()
        self._apply_engineering_lock([self.cmb_binding_profile, self.tbl_bindings, self.btn_binding_save])

    def load_tag_binding_table(self, profile_name: str = ""):
        profile = profile_name or self.cmb_binding_profile.currentText()
        bindings = self.tag_manager.get_bindings_for_profile(profile)
        catalog = self.tag_manager.get_all_tag_dicts()

        self.tbl_bindings.setRowCount(0)
        for tag in catalog:
            tag_name = str(tag.get("name", "")).strip()
            if not tag_name:
                continue

            binding = bindings.get(tag_name, {})
            row = self.tbl_bindings.rowCount()
            self.tbl_bindings.insertRow(row)
            self.tbl_bindings.setItem(row, 0, QTableWidgetItem(tag_name))

            cmb_area = QComboBox()
            cmb_area.setEditable(True)
            cmb_area.addItems(self.TAG_AREA_OPTIONS)
            cmb_area.setCurrentText(str(binding.get("area", "")))
            self.tbl_bindings.setCellWidget(row, 1, cmb_area)

            self.tbl_bindings.setItem(row, 2, QTableWidgetItem(str(binding.get("address", ""))))

    def save_tag_binding_tab(self):
        if not self.engineering_edit_allowed:
            QMessageBox.warning(self, "Locked", "Engineering edits are disabled.")
            return

        try:
            profile = self.cmb_binding_profile.currentText()
            bindings = {}
            for row in range(self.tbl_bindings.rowCount()):
                tag_name = self._table_text(self.tbl_bindings, row, 0)
                if not tag_name:
                    continue
                address_text = self._table_text(self.tbl_bindings, row, 2)
                bindings[tag_name] = {
                    "area": self._combo_value(self.tbl_bindings, row, 1, ""),
                    "address": self._parse_address(address_text),
                }

            self.tag_manager.set_bindings_for_profile(profile, bindings)
            self.tag_manager.save()
            self.config_saved.emit("tag_bindings")
            QMessageBox.information(self, "Saved", f"Tag bindings saved for profile: {profile}")
        except Exception as exc:
            QMessageBox.critical(self, "Save Error", str(exc))

    # ---------------- Alarm Mapping ----------------

    def _build_alarms_tab(self):
        layout = QVBoxLayout(self.alarms_tab)

        hint = QLabel(
            "Alarm Mapping fields:\n"
            "- Alarm Tag: word/register tag carrying alarm bits.\n"
            "- Bit No: bit position inside that word.\n"
            "- Alarm Text: message shown in banner/history.\n"
            "- Severity: critical / warning / info."
        )
        hint.setWordWrap(True)
        hint.setObjectName("SubtleText")
        layout.addWidget(hint)

        self.tbl_alarms = QTableWidget(0, 4)
        self.tbl_alarms.setHorizontalHeaderLabels(["Alarm Tag", "Bit No", "Alarm Text", "Severity"])
        layout.addWidget(self.tbl_alarms)

        btn_row = QHBoxLayout()
        self.btn_alarm_add = QPushButton("Add Alarm Bit")
        self.btn_alarm_delete = QPushButton("Delete Selected")
        self.btn_alarm_save = QPushButton("Save Alarm Mapping")
        self.btn_alarm_save.setObjectName("PrimaryButton")
        btn_row.addWidget(self.btn_alarm_add)
        btn_row.addWidget(self.btn_alarm_delete)
        btn_row.addWidget(self.btn_alarm_save)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.btn_alarm_add.clicked.connect(self.add_alarm_row)
        self.btn_alarm_delete.clicked.connect(self.delete_selected_alarm_row)
        self.btn_alarm_save.clicked.connect(self.save_alarms_tab)

        self.load_alarms_table()
        self._apply_engineering_lock([self.btn_alarm_add, self.btn_alarm_delete, self.btn_alarm_save, self.tbl_alarms])

    def load_alarms_table(self):
        self.tbl_alarms.setRowCount(0)
        for word in self.tag_manager.get_alarm_words():
            tag = word.get("tag", "")
            bits = word.get("bits", {})
            for bit_no, bit_def in bits.items():
                self._insert_alarm_row(tag, bit_no, bit_def)

    def _insert_alarm_row(self, tag_name="", bit_no="", bit_def=None):
        bit_def = bit_def if bit_def is not None else {}
        row = self.tbl_alarms.rowCount()
        self.tbl_alarms.insertRow(row)

        alarm_tag_names = [t.name for t in self.tag_manager.all_tags()]
        cmb_tag = QComboBox()
        cmb_tag.setEditable(True)
        cmb_tag.addItems(alarm_tag_names)
        cmb_tag.setCurrentText(str(tag_name))
        self.tbl_alarms.setCellWidget(row, 0, cmb_tag)

        self.tbl_alarms.setItem(row, 1, QTableWidgetItem(str(bit_no)))

        text = bit_def.get("text", "") if isinstance(bit_def, dict) else str(bit_def)
        severity = bit_def.get("severity", "warning") if isinstance(bit_def, dict) else "warning"

        self.tbl_alarms.setItem(row, 2, QTableWidgetItem(text))

        cmb_severity = QComboBox()
        cmb_severity.addItems(self.ALARM_SEVERITY_OPTIONS)
        cmb_severity.setCurrentText(str(severity))
        self.tbl_alarms.setCellWidget(row, 3, cmb_severity)

    def add_alarm_row(self):
        self._insert_alarm_row()

    def delete_selected_alarm_row(self):
        row = self.tbl_alarms.currentRow()
        if row >= 0:
            self.tbl_alarms.removeRow(row)

    def save_alarms_tab(self):
        if not self.engineering_edit_allowed:
            QMessageBox.warning(self, "Locked", "Engineering edits are disabled.")
            return

        try:
            grouped = {}
            tag_names = {td.name for td in self.tag_manager.all_tags()}

            for row in range(self.tbl_alarms.rowCount()):
                tag = self._combo_value(self.tbl_alarms, row, 0, "")
                bit_no = self._table_text(self.tbl_alarms, row, 1)
                text = self._table_text(self.tbl_alarms, row, 2)
                severity = self._combo_value(self.tbl_alarms, row, 3, "warning")

                if not tag and not bit_no and not text:
                    continue

                if tag not in tag_names:
                    raise ValueError(f"Alarm mapping references unknown tag: {tag}")

                bit_int = int(bit_no)
                if bit_int < 0 or bit_int > 31:
                    raise ValueError(f"Invalid bit number {bit_int} for tag {tag}")

                grouped.setdefault(tag, {})
                grouped[tag][str(bit_int)] = {
                    "text": text,
                    "severity": severity,
                }

            alarm_words = [{"tag": tag, "bits": bits} for tag, bits in grouped.items()]
            self.tag_manager.set_alarm_words(alarm_words)
            self.tag_manager.save()
            self.config_saved.emit("alarms")
            QMessageBox.information(self, "Saved", "Alarm mapping saved successfully.")
        except Exception as exc:
            QMessageBox.critical(self, "Save Error", str(exc))

    # ---------------- Manual Devices ----------------

    def _build_manual_tab(self):
        layout = QVBoxLayout(self.manual_tab)

        hint = QLabel(
            "Manual Device fields:\n"
            "- Key: unique internal id such as M1, M2, M3, SLIDE.\n"
            "- Title: text shown on manual screen.\n"
            "- Fwd/Rev Cmd: command tags written by the app.\n"
            "- Running/Fwd Done/Rev Done: feedback tags from PLC.\n"
            "- Interlock Word: PLC word/register containing interlock bits.\n"
            "- Interlock table: define each bit, text, and severity."
        )
        hint.setWordWrap(True)
        hint.setObjectName("SubtleText")
        layout.addWidget(hint)

        self.tbl_manual = QTableWidget(0, 8)
        self.tbl_manual.setHorizontalHeaderLabels([
            "Key", "Title", "Fwd Cmd", "Rev Cmd",
            "Running FB", "Fwd Done FB", "Rev Done FB", "Interlock Word"
        ])
        layout.addWidget(self.tbl_manual)

        self.tbl_interlocks = QTableWidget(0, 3)
        self.tbl_interlocks.setHorizontalHeaderLabels(["Bit No", "Interlock Text", "Severity"])
        layout.addWidget(self.tbl_interlocks)

        btn_interlock_row = QHBoxLayout()
        self.btn_interlock_add = QPushButton("Add Interlock Bit")
        self.btn_interlock_delete = QPushButton("Delete Interlock Bit")
        btn_interlock_row.addWidget(self.btn_interlock_add)
        btn_interlock_row.addWidget(self.btn_interlock_delete)
        btn_interlock_row.addStretch()
        layout.addLayout(btn_interlock_row)

        btn_row = QHBoxLayout()
        self.btn_manual_add = QPushButton("Add Device")
        self.btn_manual_delete = QPushButton("Delete Selected Device")
        self.btn_manual_save = QPushButton("Save Manual Devices")
        self.btn_manual_save.setObjectName("PrimaryButton")
        btn_row.addWidget(self.btn_manual_add)
        btn_row.addWidget(self.btn_manual_delete)
        btn_row.addWidget(self.btn_manual_save)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.btn_manual_add.clicked.connect(self.add_manual_row)
        self.btn_manual_delete.clicked.connect(self.delete_selected_manual_row)
        self.btn_manual_save.clicked.connect(self.save_manual_tab)
        self.tbl_manual.currentCellChanged.connect(self.on_manual_row_changed)
        self.btn_interlock_add.clicked.connect(self.add_interlock_row)
        self.btn_interlock_delete.clicked.connect(self.delete_selected_interlock_row)

        self.load_manual_table()
        self._apply_engineering_lock([
            self.btn_manual_add, self.btn_manual_delete, self.btn_manual_save,
            self.btn_interlock_add, self.btn_interlock_delete,
            self.tbl_manual, self.tbl_interlocks
        ])

    def load_manual_table(self):
        self.tbl_manual.setRowCount(0)
        devices = self.tag_manager.get_manual_devices()
        for dev in devices:
            self._insert_manual_row(dev)

        if self.tbl_manual.rowCount() > 0:
            self.tbl_manual.setCurrentCell(0, 0)
            self.load_selected_manual_interlocks()

    def _insert_manual_row(self, dev=None):
        dev = dev or {}
        row = self.tbl_manual.rowCount()
        self.tbl_manual.insertRow(row)

        tag_names = [t.name for t in self.tag_manager.all_tags()]

        self.tbl_manual.setItem(row, 0, QTableWidgetItem(str(dev.get("key", ""))))
        self.tbl_manual.setItem(row, 1, QTableWidgetItem(str(dev.get("title", ""))))

        for col, key in [
            (2, "fwd_cmd"),
            (3, "rev_cmd"),
            (4, "running_fb"),
            (5, "fwd_done_fb"),
            (6, "rev_done_fb"),
            (7, "interlock_word"),
        ]:
            cmb = QComboBox()
            cmb.setEditable(True)
            cmb.addItems(tag_names)
            cmb.setCurrentText(str(dev.get(key, "")))
            self.tbl_manual.setCellWidget(row, col, cmb)

    def add_manual_row(self):
        self._insert_manual_row()

    def delete_selected_manual_row(self):
        row = self.tbl_manual.currentRow()
        if row >= 0:
            self.tbl_manual.removeRow(row)
            self.tbl_interlocks.setRowCount(0)

    def add_interlock_row(self):
        row = self.tbl_interlocks.rowCount()
        self.tbl_interlocks.insertRow(row)

        cmb_sev = QComboBox()
        cmb_sev.addItems(self.ALARM_SEVERITY_OPTIONS)
        cmb_sev.setCurrentText("warning")
        self.tbl_interlocks.setCellWidget(row, 2, cmb_sev)

    def delete_selected_interlock_row(self):
        row = self.tbl_interlocks.currentRow()
        if row >= 0:
            self.tbl_interlocks.removeRow(row)

    def on_manual_row_changed(self, current_row, current_column, previous_row, previous_column):
        self.load_selected_manual_interlocks()

    def load_selected_manual_interlocks(self):
        self.tbl_interlocks.setRowCount(0)

        row = self.tbl_manual.currentRow()
        if row < 0:
            return

        key = self._table_text(self.tbl_manual, row, 0)
        devices = self.tag_manager.get_manual_devices()
        found = next((d for d in devices if d.get("key") == key), None)
        if not found:
            return

        interlocks = found.get("interlocks", {})
        for bit, bit_def in interlocks.items():
            self._insert_interlock_row(bit, bit_def)

    def _insert_interlock_row(self, bit_no="", bit_def=None):
        bit_def = bit_def if bit_def is not None else {}
        row = self.tbl_interlocks.rowCount()
        self.tbl_interlocks.insertRow(row)

        text = bit_def.get("text", "") if isinstance(bit_def, dict) else str(bit_def)
        severity = bit_def.get("severity", "warning") if isinstance(bit_def, dict) else "warning"

        self.tbl_interlocks.setItem(row, 0, QTableWidgetItem(str(bit_no)))
        self.tbl_interlocks.setItem(row, 1, QTableWidgetItem(text))

        cmb_sev = QComboBox()
        cmb_sev.addItems(self.ALARM_SEVERITY_OPTIONS)
        cmb_sev.setCurrentText(str(severity))
        self.tbl_interlocks.setCellWidget(row, 2, cmb_sev)

    def save_manual_tab(self):
        if not self.engineering_edit_allowed:
            QMessageBox.warning(self, "Locked", "Engineering edits are disabled.")
            return

        try:
            devices = []
            tag_names = {td.name for td in self.tag_manager.all_tags()}
            interlock_map_by_key = {}

            current_row = self.tbl_manual.currentRow()
            if current_row >= 0:
                current_key = self._table_text(self.tbl_manual, current_row, 0)
                if current_key:
                    interlock_map_by_key[current_key] = self._collect_interlock_rows()

            for dev in self.tag_manager.get_manual_devices():
                interlock_map_by_key.setdefault(dev.get("key", ""), dev.get("interlocks", {}))

            keys_seen = set()

            for row in range(self.tbl_manual.rowCount()):
                key = self._table_text(self.tbl_manual, row, 0)
                if not key:
                    continue
                if key in keys_seen:
                    raise ValueError(f"Duplicate manual device key: {key}")
                keys_seen.add(key)

                dev = {
                    "key": key,
                    "title": self._table_text(self.tbl_manual, row, 1),
                    "fwd_cmd": self._combo_value(self.tbl_manual, row, 2, ""),
                    "rev_cmd": self._combo_value(self.tbl_manual, row, 3, ""),
                    "running_fb": self._combo_value(self.tbl_manual, row, 4, ""),
                    "fwd_done_fb": self._combo_value(self.tbl_manual, row, 5, ""),
                    "rev_done_fb": self._combo_value(self.tbl_manual, row, 6, ""),
                    "interlock_word": self._combo_value(self.tbl_manual, row, 7, ""),
                    "interlocks": interlock_map_by_key.get(key, {}),
                }

                for ref in [
                    dev["fwd_cmd"], dev["rev_cmd"], dev["running_fb"],
                    dev["fwd_done_fb"], dev["rev_done_fb"], dev["interlock_word"]
                ]:
                    if ref and ref not in tag_names:
                        raise ValueError(f"Manual device {key} references unknown tag: {ref}")

                devices.append(dev)

            self.tag_manager.set_manual_devices(devices)
            self.tag_manager.save()
            self.config_saved.emit("manual_devices")
            QMessageBox.information(self, "Saved", "Manual device configuration saved successfully.")
        except Exception as exc:
            QMessageBox.critical(self, "Save Error", str(exc))

    def _collect_interlock_rows(self):
        result = {}
        for row in range(self.tbl_interlocks.rowCount()):
            bit_no = self._table_text(self.tbl_interlocks, row, 0)
            text = self._table_text(self.tbl_interlocks, row, 1)
            severity = self._combo_value(self.tbl_interlocks, row, 2, "warning")

            if bit_no == "":
                continue

            bit_int = int(bit_no)
            if bit_int < 0 or bit_int > 31:
                raise ValueError(f"Invalid interlock bit number: {bit_int}")

            result[str(bit_int)] = {
                "text": text,
                "severity": severity,
            }
        return result

    # ---------------- Help Tab ----------------

    def _build_help_tab(self):
        layout = QVBoxLayout(self.help_tab)

        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setPlainText(
            "ENGINEERING HELP\n\n"
            "1. Profiles\n"
            "   - Name: unique PLC connection profile name.\n"
            "   - Driver: simulator, modbus, siemens_s7, opcua.\n"
            "   - Host: PLC IP or OPC UA endpoint.\n"
            "   - Port: communication port.\n"
            "   - Poll ms: tag scan time.\n\n"
            "2. Tag Catalog\n"
            "   - Name: logical tag used by app screens.\n"
            "   - Group: use status/manual/command/alarm/io/recipe.\n"
            "   - Data Type: bool, uint16, int16, float, etc.\n"
            "   - Access: r / w / rw.\n"
            "   - Default: startup value.\n"
            "   - Scale: numeric scaling factor.\n\n"
            "3. Tag Binding\n"
            "   - Select connection profile first.\n"
            "   - Set Area and Address per tag for that profile.\n"
            "   - These are user-defined mappings; use them to match your PLC program.\n"
            "   - Modbus areas: coil, holding_register, input_register, discrete_input.\n"
            "   - Siemens S7 areas: dbw (word byte offset), dbx (byte*100+bit encoding).\n"
            "   - OPC UA area: opcua_node (full NodeId like ns=3;s=\"DB\".\"Tag\").\n"
            "   - New tags/profiles auto-create empty binding rows.\n\n"
            "4. Alarm Mapping\n"
            "   - Alarm Tag must be a valid word/register tag.\n"
            "   - Bit No is the bit index inside that word.\n"
            "   - Alarm Text is shown in banner/history.\n"
            "   - Severity supports critical, warning, info.\n\n"
            "5. Manual Devices\n"
            "   - Key: internal unique id such as M1, M2, M3, SLIDE.\n"
            "   - Title: text shown on manual screen.\n"
            "   - Fwd/Rev Cmd: command tags written by the app.\n"
            "   - Running/Fwd Done/Rev Done: feedback tags from PLC.\n"
            "   - Interlock Word: PLC word/register containing interlock bits.\n"
            "   - Interlock table: define each bit, text, and severity.\n\n"
            "6. Backup\n"
            "   - Export Config Backup saves the full engineering configuration.\n"
            "   - Import Config Backup loads a previously saved backup and reloads the app live.\n\n"
            "7. Production Lock Mode\n"
            "   - When ON, engineering edits are disabled.\n"
            "   - Runtime actions such as profile selection can still remain available.\n"
            "   - Simulator usage can also be disabled by role/lock settings.\n"
        )
        layout.addWidget(help_text)

    # ---------------- Validation ----------------

    def _validate_alarm_mapping_against_tag_names(self, tag_names: set):
        for word in self.tag_manager.get_alarm_words():
            tag = word.get("tag", "")
            if tag and tag not in tag_names:
                raise ValueError(f"Alarm mapping references unknown tag: {tag}")

    def _validate_manual_devices_against_tag_names(self, tag_names: set):
        for dev in self.tag_manager.get_manual_devices():
            for ref in [
                dev.get("fwd_cmd", ""),
                dev.get("rev_cmd", ""),
                dev.get("running_fb", ""),
                dev.get("fwd_done_fb", ""),
                dev.get("rev_done_fb", ""),
                dev.get("interlock_word", ""),
            ]:
                if ref and ref not in tag_names:
                    raise ValueError(f"Manual device {dev.get('key', '')} references unknown tag: {ref}")

    # ---------------- Helpers ----------------

    def _apply_engineering_lock(self, widgets):
        if self.engineering_edit_allowed:
            return
        for w in widgets:
            try:
                w.setEnabled(False)
            except Exception:
                pass

    def _combo_value(self, table, row, col, default=""):
        w = table.cellWidget(row, col)
        if isinstance(w, QComboBox):
            return w.currentText().strip()
        return default

    def _table_text(self, table, row, col):
        item = table.item(row, col)
        return item.text().strip() if item else ""

    def _safe_int(self, value, default=0):
        try:
            return int(value)
        except Exception:
            return default

    def _safe_float(self, value, default=0.0):
        try:
            return float(value)
        except Exception:
            return default

    def _parse_default(self, value: str):
        v = value.strip()
        if v.lower() == "true":
            return True
        if v.lower() == "false":
            return False
        try:
            if "." in v:
                return float(v)
            return int(v)
        except Exception:
            return v

    def _parse_address(self, value: str):
        v = value.strip()
        if v == "":
            return ""
        try:
            return int(v)
        except Exception:
            return v