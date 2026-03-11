import json
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from hmi.login_dialog import LoginDialog
from hmi.main_window import MainWindow
from hmi.services.auth_service import AuthService
from hmi.services.tag_manager import TagManager
from hmi.services.plc_service import PlcService
from hmi.services.alarm_service import AlarmService


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


BASE_DIR = get_base_dir()


def resource_path(*parts) -> str:
    return str(BASE_DIR.joinpath(*parts))


def load_json(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Required file not found: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def load_stylesheet(app: QApplication) -> None:
    qss_path = Path(resource_path("assets", "styles.qss"))
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("KV HMI V2")

    load_stylesheet(app)

    try:
        app_config = load_json(resource_path("config", "app_config.json"))
        auth_service = AuthService(resource_path("config", "users.json"))
        tag_manager = TagManager(resource_path("config", "tags.json"))
        plc_service = PlcService(tag_manager)
        alarm_service = AlarmService(tag_manager)
    except Exception as exc:
        QMessageBox.critical(None, "Startup Error", str(exc))
        raise

    current_user = None
    if app_config.get("login_required", True):
        dlg = LoginDialog(auth_service)
        if dlg.exec() != LoginDialog.Accepted:
            sys.exit(0)
        current_user = dlg.authenticated_user

    window = MainWindow(
        tag_manager=tag_manager,
        plc_service=plc_service,
        alarm_service=alarm_service,
        current_user=current_user,
        app_config=app_config,
    )
    window.show()

    plc_service.tag_changed.connect(alarm_service.process_tag_change)
    plc_service.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()