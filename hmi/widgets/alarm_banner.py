from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel


class AlarmBanner(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("Card")

        self.count_label = QLabel("Alarms: 0")
        self.count_label.setObjectName("CardTitle")

        self.text_label = QLabel("No active alarms")
        self.text_label.setObjectName("SubtleText")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.addWidget(self.count_label)
        layout.addSpacing(16)
        layout.addWidget(self.text_label, 1)

        self.set_normal()

    def set_alarm_state(self, count: int, text: str, severity: str = "warning"):
        self.count_label.setText(f"Alarms: {count}")
        self.text_label.setText(text)

        if count <= 0:
            self.set_normal()
            return

        sev = str(severity or "warning").lower()
        if sev == "critical":
            self.setStyleSheet(
                "QFrame { background:#7f1d1d; border:1px solid #ef4444; border-radius:12px; }"
            )
        elif sev == "info":
            self.setStyleSheet(
                "QFrame { background:#0c4a6e; border:1px solid #38bdf8; border-radius:12px; }"
            )
        else:
            self.setStyleSheet(
                "QFrame { background:#78350f; border:1px solid #f59e0b; border-radius:12px; }"
            )

    def set_normal(self):
        self.setStyleSheet(
            "QFrame { background:#172033; border:1px solid #2d3b55; border-radius:12px; }"
        )