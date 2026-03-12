from PySide6.QtWidgets import QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from hmi.services.plc_service import PlcService
from hmi.services.tag_manager import TagManager


class IoScreen(QWidget):
    def __init__(self, plc_service: PlcService, tag_manager: TagManager):
        super().__init__()
        self.plc = plc_service
        self.tag_manager = tag_manager

        layout = QVBoxLayout(self)

        self.profile_label = QLabel()
        self.profile_label.setWordWrap(True)
        layout.addWidget(self.profile_label)

        self.protocol_help_label = QLabel()
        self.protocol_help_label.setWordWrap(True)
        self.protocol_help_label.setObjectName("SubtleText")
        layout.addWidget(self.protocol_help_label)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Tag", "Group", "Area", "Address", "PLC Address", "Access", "Value"])
        layout.addWidget(self.table)

        self.refresh_table()
        self.plc.tag_changed.connect(self.on_tag_changed)
        self.plc.active_profile_changed.connect(self.on_profile_changed)

    def _format_plc_address(self, area: str, address, cfg: dict) -> str:
        driver = str(cfg.get("driver", "simulator")).lower()

        if driver == "modbus":
            if area == "coil":
                return f"Coil {address}"
            if area == "holding_register":
                return f"Holding Register {address}"
            if area == "input_register":
                return f"Input Register {address}"
            if area == "discrete_input":
                return f"Discrete Input {address}"
            return "-"

        if driver == "siemens_s7":
            db_number = cfg.get("siemens", {}).get("db_number", 1)
            if area == "dbw":
                return f"DB{db_number}.DBW{address}"
            if area == "dbx":
                try:
                    byte_index = int(address) // 100
                    bit_index = int(address) % 100
                    return f"DB{db_number}.DBX{byte_index}.{bit_index}"
                except Exception:
                    return f"DB{db_number}.DBX?<invalid:{address}>"
            return "-"

        if driver == "opcua" and area == "opcua_node":
            return str(address)

        return "Simulator / Not mapped"

    def _build_protocol_help(self, cfg: dict) -> str:
        driver = str(cfg.get("driver", "simulator")).lower()
        if driver == "modbus":
            return (
                "Modbus mapping: use Area + Address shown below as your PLC map. "
                "Example: area=holding_register, address=100 means register 100. "
                "You can edit these in Settings → Tag Binding."
            )
        if driver == "siemens_s7":
            db_number = cfg.get("siemens", {}).get("db_number", 1)
            return (
                f"Siemens S7 mapping: this profile writes to DB{db_number}. "
                "dbw uses byte offsets (DBW), dbx uses encoded byte*100+bit "
                "(example address 1203 = DBX12.3). Edit in Settings → Tag Binding."
            )
        if driver == "opcua":
            return (
                "OPC UA mapping: Address column stores full NodeId strings (for example ns=3;s=\"HMI_DB\".\"StartCmd\"). "
                "Use exactly these NodeIds on the server side. Edit in Settings → Tag Binding."
            )
        return "Simulator mapping: no PLC address is required."

    def refresh_table(self):
        active_profile = self.tag_manager.get_active_connection_name()
        cfg = self.tag_manager.connection_config
        driver = str(cfg.get("driver", "simulator"))
        self.profile_label.setText(f"Active profile: {active_profile} (driver: {driver})")
        self.protocol_help_label.setText(self._build_protocol_help(cfg))
        
        tags = self.tag_manager.all_tags()
        self.table.setRowCount(len(tags))
        for row, tag in enumerate(tags):
            self.table.setItem(row, 0, QTableWidgetItem(tag.name))
            self.table.setItem(row, 1, QTableWidgetItem(tag.group))
            self.table.setItem(row, 2, QTableWidgetItem(tag.area))
            self.table.setItem(row, 3, QTableWidgetItem(str(tag.address)))
            self.table.setItem(row, 4, QTableWidgetItem(self._format_plc_address(tag.area, tag.address, cfg)))
            self.table.setItem(row, 5, QTableWidgetItem(str(tag.access)))
            self.table.setItem(row, 6, QTableWidgetItem(str(self.tag_manager.get_value(tag.name))))
        self.table.resizeColumnsToContents()

    def on_tag_changed(self, tag_name: str, value):
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).text() == tag_name:
                self.table.setItem(row, 6, QTableWidgetItem(str(value)))
                break

    def on_profile_changed(self, _: str):
        self.refresh_table()