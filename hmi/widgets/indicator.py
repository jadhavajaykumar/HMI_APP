from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget


class IndicatorLamp(QWidget):
    def __init__(self, text: str, initial_state: bool = False, diameter: int = 18):
        super().__init__()
        self._state = initial_state
        self._diameter = diameter
        self.label = QLabel(text)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addSpacing(diameter + 4)
        layout.addWidget(self.label)
        layout.addStretch()

        self.setMinimumHeight(28)

    def set_state(self, state: bool):
        self._state = bool(state)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        color = QColor("#22c55e") if self._state else QColor("#475569")
        border = QColor("#d1d5db")
        x = 4
        y = (self.height() - self._diameter) // 2
        painter.setPen(border)
        painter.setBrush(color)
        painter.drawEllipse(x, y, self._diameter, self._diameter)