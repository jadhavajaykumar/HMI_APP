from PySide6.QtWidgets import (
    QGridLayout, QGroupBox, QVBoxLayout, QLabel, QWidget
)

from hmi.widgets.status_card import StatusCard
from hmi.widgets.tag_widgets import (
    BoundIndicator, BoundLabel, BoundPulseButton, BoundSpinWrite
)


class HomeScreen(QWidget):
    def __init__(self, plc_service, manual_actions_enabled: bool = True):
        super().__init__()
        self.plc = plc_service
        self.manual_actions_enabled = manual_actions_enabled

        root = QVBoxLayout(self)
        title = QLabel("Home Dashboard")
        title.setObjectName("SectionTitle")
        root.addWidget(title)

        cards = QGridLayout()
        self.card_status = StatusCard("Machine Status", "Stopped")
        self.card_fault = StatusCard("Fault Code", "0")
        self.card_good = StatusCard("Good Count", "0")
        self.card_recipe = StatusCard("Target Qty", "50")

        cards.addWidget(self.card_status, 0, 0)
        cards.addWidget(self.card_fault, 0, 1)
        cards.addWidget(self.card_good, 1, 0)
        cards.addWidget(self.card_recipe, 1, 1)
        root.addLayout(cards)

        live_box = QGroupBox("Live Tags")
        live_layout = QVBoxLayout(live_box)
        live_layout.addWidget(BoundLabel(self.plc, "Machine.RunStatus", "Run Status"))
        live_layout.addWidget(BoundLabel(self.plc, "Machine.FaultCode", "Fault Code"))
        live_layout.addWidget(BoundLabel(self.plc, "Counters.GoodCount", "Good Count"))
        live_layout.addWidget(BoundIndicator(self.plc, "Input.DoorClosed", "Door Closed"))
        root.addWidget(live_box)

        cmd_box = QGroupBox("Commands")
        cmd_layout = QVBoxLayout(cmd_box)

        self.btn_start = BoundPulseButton(self.plc, "Command.Start", "START")
        self.btn_stop = BoundPulseButton(self.plc, "Command.Stop", "STOP")
        self.btn_reset = BoundPulseButton(self.plc, "Command.Reset", "RESET")
        self.recipe_editor = BoundSpinWrite(self.plc, "Recipe.TargetQty", "Target Qty")

        self.btn_start.setEnabled(self.manual_actions_enabled)
        self.btn_stop.setEnabled(self.manual_actions_enabled)
        self.btn_reset.setEnabled(self.manual_actions_enabled)
        self.recipe_editor.setEnabled(self.manual_actions_enabled)

        cmd_layout.addWidget(self.btn_start)
        cmd_layout.addWidget(self.btn_stop)
        cmd_layout.addWidget(self.btn_reset)
        cmd_layout.addWidget(self.recipe_editor)
        root.addWidget(cmd_box)
        root.addStretch()

        self.plc.tag_changed.connect(self.on_tag_changed)
        self.on_tag_changed("Machine.RunStatus", self.plc.read_tag("Machine.RunStatus"))
        self.on_tag_changed("Machine.FaultCode", self.plc.read_tag("Machine.FaultCode"))
        self.on_tag_changed("Counters.GoodCount", self.plc.read_tag("Counters.GoodCount"))
        self.on_tag_changed("Recipe.TargetQty", self.plc.read_tag("Recipe.TargetQty"))

    def on_tag_changed(self, tag_name: str, value):
        if tag_name == "Machine.RunStatus":
            self.card_status.set_value("Running" if int(value or 0) == 1 else "Stopped")
        elif tag_name == "Machine.FaultCode":
            self.card_fault.set_value(str(value))
        elif tag_name == "Counters.GoodCount":
            self.card_good.set_value(str(value))
        elif tag_name == "Recipe.TargetQty":
            self.card_recipe.set_value(str(value))