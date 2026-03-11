from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class AlarmsScreen(QWidget):
    def __init__(self, alarm_service):
        super().__init__()
        self.alarm_service = alarm_service

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        title = QLabel("Alarm History")
        title.setObjectName("SectionTitle")
        root.addWidget(title)

        filter_row = QHBoxLayout()

        self.cmb_severity = QComboBox()
        self.cmb_severity.addItems(["all", "critical", "warning", "info"])

        self.cmb_state = QComboBox()
        self.cmb_state.addItems(["all", "ACTIVE", "CLEARED"])

        self.cmb_source = QComboBox()
        self.cmb_source.addItems(["all", "plc_alarm", "manual_interlock", "tag"])

        self.lbl_count = QLabel("0 records")

        filter_row.addWidget(QLabel("Severity"))
        filter_row.addWidget(self.cmb_severity)
        filter_row.addWidget(QLabel("State"))
        filter_row.addWidget(self.cmb_state)
        filter_row.addWidget(QLabel("Source"))
        filter_row.addWidget(self.cmb_source)
        filter_row.addStretch()
        filter_row.addWidget(self.lbl_count)

        root.addLayout(filter_row)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Timestamp", "Tag", "Text", "Severity", "Source", "Value", "State"]
        )
        root.addWidget(self.table)

        self.cmb_severity.currentTextChanged.connect(self.refresh_table)
        self.cmb_state.currentTextChanged.connect(self.refresh_table)
        self.cmb_source.currentTextChanged.connect(self.refresh_table)

        self.alarm_service.alarm_history_changed.connect(self.refresh_table)
        self.refresh_table()

    def refresh_table(self):
        history = self.alarm_service.get_filtered_history(
            severity=self.cmb_severity.currentText(),
            state=self.cmb_state.currentText(),
            source=self.cmb_source.currentText(),
        )

        self.table.setRowCount(len(history))
        for row, rec in enumerate(history):
            items = [
                QTableWidgetItem(rec.timestamp),
                QTableWidgetItem(rec.tag_name),
                QTableWidgetItem(rec.text),
                QTableWidgetItem(rec.severity),
                QTableWidgetItem(rec.source),
                QTableWidgetItem(str(rec.value)),
                QTableWidgetItem(rec.state),
            ]

            self._apply_row_color(items, rec.severity)

            for col, item in enumerate(items):
                self.table.setItem(row, col, item)

        self.lbl_count.setText(f"{len(history)} records")
        self.table.resizeColumnsToContents()

    def _apply_row_color(self, items, severity: str):
        sev = str(severity or "warning").lower()
        if sev == "critical":
            color = QColor("#7f1d1d")
        elif sev == "info":
            color = QColor("#0c4a6e")
        else:
            color = QColor("#78350f")

        for item in items:
            item.setBackground(color)