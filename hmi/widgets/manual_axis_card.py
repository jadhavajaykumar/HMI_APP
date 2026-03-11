from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
)

from hmi.widgets.indicator import IndicatorLamp


class ManualAxisCard(QFrame):
    def __init__(self, plc_service, device_cfg: dict, manual_actions_enabled: bool = True):
        super().__init__()
        self.plc = plc_service
        self.cfg = device_cfg
        self.manual_actions_enabled = manual_actions_enabled

        self.setObjectName("Card")

        self.title = QLabel(device_cfg.get("title", device_cfg.get("key", "Device")))
        self.title.setObjectName("SectionTitle")

        self.btn_fwd = QPushButton("Forward")
        self.btn_rev = QPushButton("Reverse")
        self.btn_fwd.setObjectName("PrimaryButton")
        self.btn_rev.setObjectName("PrimaryButton")

        self.ind_running = IndicatorLamp("Running")
        self.ind_fwd_done = IndicatorLamp("Forward Reached")
        self.ind_rev_done = IndicatorLamp("Reverse Reached")

        self.lbl_interlock_title = QLabel("Interlock")
        self.lbl_interlock_text = QLabel("-")
        self.lbl_interlock_text.setWordWrap(True)
        self.lbl_interlock_text.setObjectName("SubtleText")

        layout = QGridLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(10)

        layout.addWidget(self.title, 0, 0, 1, 3)
        layout.addWidget(self.btn_fwd, 1, 0)
        layout.addWidget(self.btn_rev, 1, 1)

        layout.addWidget(self.ind_running, 2, 0, 1, 2)
        layout.addWidget(self.ind_fwd_done, 3, 0, 1, 2)
        layout.addWidget(self.ind_rev_done, 4, 0, 1, 2)

        layout.addWidget(self.lbl_interlock_title, 5, 0)
        layout.addWidget(self.lbl_interlock_text, 5, 1, 1, 2)

        self.btn_fwd.clicked.connect(self.on_fwd)
        self.btn_rev.clicked.connect(self.on_rev)
        self.plc.tag_changed.connect(self.on_tag_changed)

        self.btn_fwd.setEnabled(self.manual_actions_enabled)
        self.btn_rev.setEnabled(self.manual_actions_enabled)

        self.refresh_from_cache()

    def on_fwd(self):
        tag = self.cfg.get("fwd_cmd", "")
        if tag and self.manual_actions_enabled:
            self.plc.pulse_coil(tag)

    def on_rev(self):
        tag = self.cfg.get("rev_cmd", "")
        if tag and self.manual_actions_enabled:
            self.plc.pulse_coil(tag)

    def refresh_from_cache(self):
        for tag in [
            self.cfg.get("running_fb", ""),
            self.cfg.get("fwd_done_fb", ""),
            self.cfg.get("rev_done_fb", ""),
            self.cfg.get("interlock_word", ""),
        ]:
            if tag:
                self.on_tag_changed(tag, self.plc.read_tag(tag))

    def on_tag_changed(self, tag_name: str, value):
        if tag_name == self.cfg.get("running_fb", ""):
            self.ind_running.set_state(bool(value))

        elif tag_name == self.cfg.get("fwd_done_fb", ""):
            self.ind_fwd_done.set_state(bool(value))

        elif tag_name == self.cfg.get("rev_done_fb", ""):
            self.ind_rev_done.set_state(bool(value))

        elif tag_name == self.cfg.get("interlock_word", ""):
            self.lbl_interlock_text.setText(self._decode_interlocks(value))

    def _decode_interlocks(self, value):
        word_val = int(value or 0)
        if word_val == 0:
            return "No active interlock"

        texts = []
        bit_texts = self.cfg.get("interlocks", {})
        for bit_str, bit_def in bit_texts.items():
            bit = int(bit_str)
            if word_val & (1 << bit):
                if isinstance(bit_def, dict):
                    texts.append(bit_def.get("text", f"Bit {bit}"))
                else:
                    texts.append(str(bit_def))

        if not texts:
            return f"Interlock word active: {word_val}"
        return " | ".join(texts)