from PySide6.QtWidgets import (
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from hmi.widgets.manual_axis_card import ManualAxisCard


class ManualScreen(QWidget):
    def __init__(self, plc_service, tag_manager, manual_actions_enabled: bool = True):
        super().__init__()
        self.plc = plc_service
        self.tag_manager = tag_manager
        self.manual_actions_enabled = manual_actions_enabled

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        title = QLabel("Manual Operation")
        title.setObjectName("SectionTitle")
        root.addWidget(title)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(4, 4, 4, 4)
        self.content_layout.setSpacing(12)

        self.scroll.setWidget(self.content)
        root.addWidget(self.scroll, 1)

        self.build_from_config()

    def build_from_config(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        devices = self.tag_manager.get_manual_devices()
        if not devices:
            note = QLabel("No manual devices configured.")
            note.setWordWrap(True)
            self.content_layout.addWidget(note)
            self.content_layout.addStretch()
            return

        for dev in devices:
            card = ManualAxisCard(
                self.plc,
                dev,
                manual_actions_enabled=self.manual_actions_enabled,
            )
            self.content_layout.addWidget(card)

        self.content_layout.addStretch()