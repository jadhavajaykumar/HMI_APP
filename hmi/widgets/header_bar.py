from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel


class HeaderBar(QFrame):
    def __init__(self, current_user=None):
        super().__init__()
        self.setObjectName("HeaderBar")

        self.title_label = QLabel("PC HMI V2")
        self.title_label.setObjectName("TitleLabel")

        user_text = "User: -"
        if current_user:
            user_text = f"User: {current_user.get('username')} ({current_user.get('role')})"
        self.user_label = QLabel(user_text)
        self.user_label.setObjectName("SubtleText")

        self.connection_label = QLabel("PLC: Disconnected")
        self.connection_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.addWidget(self.title_label)
        layout.addSpacing(18)
        layout.addWidget(self.user_label)
        layout.addStretch()
        layout.addWidget(self.connection_label)

    def set_connection_state(self, connected: bool):
        if connected:
            self.connection_label.setText("PLC: Connected")
            self.connection_label.setStyleSheet("color: #86efac; font-weight: 700;")
        else:
            self.connection_label.setText("PLC: Disconnected")
            self.connection_label.setStyleSheet("color: #fca5a5; font-weight: 700;")