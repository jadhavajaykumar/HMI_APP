from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from hmi.services.plc_service import PlcService
from hmi.services.tag_manager import TagManager


class IoScreen(QWidget):
    def __init__(self, plc_service: PlcService, tag_manager: TagManager):
        super().__init__()
        self.plc = plc_service
        self.tag_manager = tag_manager

        layout = QVBoxLayout(self)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Tag", "Group", "Area", "Address", "Access", "Value"])
        layout.addWidget(self.table)

        self.refresh_table()
        self.plc.tag_changed.connect(self.on_tag_changed)

    def refresh_table(self):
        tags = self.tag_manager.all_tags()
        self.table.setRowCount(len(tags))
        for row, tag in enumerate(tags):
            self.table.setItem(row, 0, QTableWidgetItem(tag.name))
            self.table.setItem(row, 1, QTableWidgetItem(tag.group))
            self.table.setItem(row, 2, QTableWidgetItem(tag.area))
            self.table.setItem(row, 3, QTableWidgetItem(str(tag.address)))
            self.table.setItem(row, 4, QTableWidgetItem(str(tag.access)))
            self.table.setItem(row, 5, QTableWidgetItem(str(self.tag_manager.get_value(tag.name))))
        self.table.resizeColumnsToContents()

    def on_tag_changed(self, tag_name: str, value):
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).text() == tag_name:
                self.table.setItem(row, 5, QTableWidgetItem(str(value)))
                break