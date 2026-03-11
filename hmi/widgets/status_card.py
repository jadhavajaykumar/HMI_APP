from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class StatusCard(QFrame):
    def __init__(self, title: str, value: str = "-", subtitle: str = ""):
        super().__init__()
        self.setObjectName("Card")
        self.title_label = QLabel(title)
        self.title_label.setObjectName("CardTitle")
        self.value_label = QLabel(value)
        self.value_label.setObjectName("CardValue")
        self.value_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("SubtleText")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.subtitle_label)
        layout.addStretch()

    def set_value(self, value: str):
        self.value_label.setText(str(value))

    def set_subtitle(self, text: str):
        self.subtitle_label.setText(text)