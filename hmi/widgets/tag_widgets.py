from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QSpinBox
)

from hmi.widgets.indicator import IndicatorLamp


class BoundLabel(QWidget):
    def __init__(self, plc_service, tag_name: str, title: str):
        super().__init__()
        self.plc = plc_service
        self.tag_name = tag_name

        self.title = QLabel(title)
        self.value = QLabel("-")
        self.value.setObjectName("CardValue")

        layout = QHBoxLayout(self)
        layout.addWidget(self.title)
        layout.addStretch()
        layout.addWidget(self.value)

        self.plc.tag_changed.connect(self.on_tag_changed)
        self.on_tag_changed(tag_name, self.plc.read_tag(tag_name))

    def on_tag_changed(self, tag_name, value):
        if tag_name == self.tag_name:
            self.value.setText(str(value))


class BoundIndicator(QWidget):
    def __init__(self, plc_service, tag_name: str, text: str):
        super().__init__()
        self.plc = plc_service
        self.tag_name = tag_name
        self.lamp = IndicatorLamp(text)

        layout = QHBoxLayout(self)
        layout.addWidget(self.lamp)

        self.plc.tag_changed.connect(self.on_tag_changed)
        self.on_tag_changed(tag_name, self.plc.read_tag(tag_name))

    def on_tag_changed(self, tag_name, value):
        if tag_name == self.tag_name:
            self.lamp.set_state(bool(value))


class BoundSpinWrite(QWidget):
    def __init__(self, plc_service, tag_name: str, title: str, minimum=0, maximum=999999):
        super().__init__()
        self.plc = plc_service
        self.tag_name = tag_name

        self.label = QLabel(title)
        self.spin = QSpinBox()
        self.spin.setRange(minimum, maximum)
        self.btn = QPushButton("Write")
        self.btn.setObjectName("PrimaryButton")

        layout = QHBoxLayout(self)
        layout.addWidget(self.label)
        layout.addWidget(self.spin)
        layout.addWidget(self.btn)
        layout.addStretch()

        self.btn.clicked.connect(self.write_value)
        self.plc.tag_changed.connect(self.on_tag_changed)
        self.on_tag_changed(tag_name, self.plc.read_tag(tag_name))

    def write_value(self):
        self.plc.write_tag(self.tag_name, self.spin.value())

    def on_tag_changed(self, tag_name, value):
        if tag_name == self.tag_name:
            self.spin.blockSignals(True)
            self.spin.setValue(int(value or 0))
            self.spin.blockSignals(False)


class BoundPulseButton(QPushButton):
    def __init__(self, plc_service, tag_name: str, text: str):
        super().__init__(text)
        self.plc = plc_service
        self.tag_name = tag_name
        self.clicked.connect(self._pulse)

    def _pulse(self):
        self.plc.pulse_coil(self.tag_name)