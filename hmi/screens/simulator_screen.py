from PySide6.QtWidgets import QVBoxLayout, QLabel, QWidget

from hmi.drivers.simulator_driver import SimulatorDriver


class SimulatorScreen(QWidget):
    def __init__(self, plc_service):
        super().__init__()
        self.plc = plc_service

        root = QVBoxLayout(self)
        title = QLabel("Simulator")
        title.setObjectName("SectionTitle")
        root.addWidget(title)

        note = QLabel("Simulator is active when driver = simulator in config/tags.json")
        note.setWordWrap(True)
        root.addWidget(note)

        self.driver_note = QLabel("")
        root.addWidget(self.driver_note)
        root.addStretch()

        driver = self.plc.driver
        self.driver_note.setText(
            "Driver: SimulatorDriver" if isinstance(driver, SimulatorDriver) else "Driver: Non-simulator"
        )