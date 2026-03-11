from PySide6.QtWidgets import (
    QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QMessageBox
)


class LoginDialog(QDialog):
    def __init__(self, auth_service):
        super().__init__()
        self.auth_service = auth_service
        self.authenticated_user = None

        self.setWindowTitle("Login")
        self.setMinimumWidth(360)

        title = QLabel("Sign in to HMI")
        title.setObjectName("TitleLabel")

        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)

        form = QFormLayout()
        form.addRow("Username", self.username)
        form.addRow("Password", self.password)

        self.btn_login = QPushButton("Login")
        self.btn_login.setObjectName("PrimaryButton")
        self.btn_cancel = QPushButton("Cancel")

        btns = QHBoxLayout()
        btns.addWidget(self.btn_login)
        btns.addWidget(self.btn_cancel)

        root = QVBoxLayout(self)
        root.addWidget(title)
        root.addLayout(form)
        root.addLayout(btns)

        self.btn_login.clicked.connect(self.try_login)
        self.btn_cancel.clicked.connect(self.reject)

    def try_login(self):
        user = self.auth_service.authenticate(
            self.username.text().strip(),
            self.password.text()
        )
        if not user:
            QMessageBox.warning(self, "Login Failed", "Invalid username or password.")
            return
        self.authenticated_user = user
        self.accept()