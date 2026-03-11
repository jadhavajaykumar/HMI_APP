from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from hmi.navigation import ScreenName
from hmi.screens.home_screen import HomeScreen
from hmi.screens.manual_screen import ManualScreen
from hmi.screens.io_screen import IoScreen
from hmi.screens.alarms_screen import AlarmsScreen
from hmi.screens.simulator_screen import SimulatorScreen
from hmi.screens.settings_screen import SettingsScreen
from hmi.widgets.header_bar import HeaderBar
from hmi.widgets.alarm_banner import AlarmBanner
from hmi.services.audit_service import AuditService


class MainWindow(QMainWindow):
    def __init__(self, tag_manager, plc_service, alarm_service, current_user=None, app_config=None):
        super().__init__()
        self.tag_manager = tag_manager
        self.plc_service = plc_service
        self.alarm_service = alarm_service
        self.current_user = current_user or {}
        self.app_config = app_config or {}

        self.production_lock_mode = bool(self.app_config.get("production_lock_mode", False))
        self.role_permissions = self.app_config.get("role_permissions", {})
        self.user_role = str(self.current_user.get("role", "operator")).lower()

        self.audit_service = AuditService(
            enabled=bool(self.app_config.get("audit_log_enabled", True))
        )

        self.permissions = self._resolve_permissions()

        self.setWindowTitle("PC HMI V2")
        self.resize(1366, 840)

        root = QWidget()
        self.setCentralWidget(root)

        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        self.header = HeaderBar(current_user=current_user)
        self.alarm_banner = AlarmBanner()

        main_layout.addWidget(self.header)
        main_layout.addWidget(self.alarm_banner)

        body = QHBoxLayout()
        main_layout.addLayout(body, 1)

        nav_frame = QFrame()
        nav_frame.setObjectName("NavPanel")
        nav_layout = QVBoxLayout(nav_frame)
        nav_layout.setContentsMargins(8, 8, 8, 8)

        self.nav = QListWidget()
        nav_layout.addWidget(self.nav)

        self.screen_order = [
            ScreenName.HOME,
            ScreenName.MANUAL,
            ScreenName.IO,
            ScreenName.ALARMS,
            ScreenName.SIMULATOR,
            ScreenName.SETTINGS,
        ]

        self.screen_titles = {
            ScreenName.HOME: "Home",
            ScreenName.MANUAL: "Manual",
            ScreenName.IO: "I/O",
            ScreenName.ALARMS: "Alarms",
            ScreenName.SIMULATOR: "Simulator",
            ScreenName.SETTINGS: "Settings",
        }

        self.allowed_screens = set(self.permissions.get("screens", []))

        content_frame = QFrame()
        content_frame.setObjectName("ContentPanel")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(10, 10, 10, 10)

        self.stack = QStackedWidget()
        self.screens = {}
        self.visible_screen_order = []
        self._build_all_screens()

        content_layout.addWidget(self.stack)
        body.addWidget(nav_frame, 0)
        body.addWidget(content_frame, 1)
        nav_frame.setFixedWidth(220)

        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        if self.nav.count() > 0:
            self.nav.setCurrentRow(0)

        self.plc_service.connection_changed.connect(self.on_connection_changed)
        self.plc_service.error_occurred.connect(self.on_error)
        self.alarm_service.active_alarm_count_changed.connect(self.on_alarm_count_changed)
        self.alarm_service.active_alarm_text_changed.connect(self.on_alarm_text_changed)

        self.alarm_banner.set_alarm_state(
            self.alarm_service.get_active_count(),
            self.alarm_service.get_active_text(),
            self._get_active_alarm_severity(),
        )

    def _resolve_permissions(self):
        permissions = dict(self.role_permissions.get(self.user_role, {}))

        if self.production_lock_mode:
            permissions["engineering_edit"] = False
            permissions["simulator_use"] = False
            if "Simulator" in permissions.get("screens", []):
                permissions["screens"] = [s for s in permissions["screens"] if s != "Simulator"]

        return permissions

    def _build_navigation(self):
        self.nav.clear()
        self.visible_screen_order = []

        for screen_name in self.screen_order:
            title = self.screen_titles[screen_name]
            if title not in self.allowed_screens:
                continue
            self.visible_screen_order.append(screen_name)
            QListWidgetItem(title, self.nav)

    def _create_screen(self, name):
        if name == ScreenName.HOME:
            return HomeScreen(
                self.plc_service,
                manual_actions_enabled=bool(self.permissions.get("manual_actions", False)),
            )
        if name == ScreenName.MANUAL:
            return ManualScreen(
                self.plc_service,
                self.tag_manager,
                manual_actions_enabled=bool(self.permissions.get("manual_actions", False)),
            )
        if name == ScreenName.IO:
            return IoScreen(self.plc_service, self.tag_manager)
        if name == ScreenName.ALARMS:
            return AlarmsScreen(self.alarm_service)
        if name == ScreenName.SIMULATOR:
            return SimulatorScreen(self.plc_service)
        if name == ScreenName.SETTINGS:
            screen = SettingsScreen(
                self.plc_service,
                self.tag_manager,
                current_user=self.current_user,
                app_config=self.app_config,
            )
            screen.config_saved.connect(self.on_config_saved)
            return screen
        raise ValueError(f"Unknown screen: {name}")

    def _build_all_screens(self):
        self.screens = {}
        while self.stack.count():
            widget = self.stack.widget(0)
            self.stack.removeWidget(widget)
            widget.deleteLater()

        self._build_navigation()

        for name in self.visible_screen_order:
            if name == ScreenName.SIMULATOR and not self.permissions.get("simulator_use", False):
                continue
            screen = self._create_screen(name)
            self.screens[name] = screen
            self.stack.addWidget(screen)

    def on_config_saved(self, section: str):
        current_index = self.stack.currentIndex()
        try:
            self.tag_manager.reload()
            self.plc_service.rebuild_driver()
            self.alarm_service.reload_from_tag_manager(clear_history=False)
            self._build_all_screens()
            if self.stack.count() > 0:
                self.stack.setCurrentIndex(min(current_index, self.stack.count() - 1))

            report = self.tag_manager.generate_validation_report()
            report_text = "\n".join(report)

            self.audit_service.log(
                action=f"config_saved:{section}",
                user=self.current_user,
                details={"validation_report": report},
            )

            QMessageBox.information(
                self,
                "Reloaded",
                f"Configuration saved and reloaded live ({section}).\n\nValidation Report:\n{report_text}"
            )
        except Exception as exc:
            QMessageBox.critical(self, "Reload Error", str(exc))

    def _get_active_alarm_severity(self):
        if not self.alarm_service.active:
            return "warning"
        first = next(iter(self.alarm_service.active.values()))
        return getattr(first, "severity", "warning")

    def on_connection_changed(self, connected: bool):
        self.header.set_connection_state(connected)

    def on_error(self, message: str):
        QMessageBox.warning(self, "PLC Communication Error", message)

    def on_alarm_count_changed(self, count: int):
        self.alarm_banner.set_alarm_state(
            count,
            self.alarm_service.get_active_text(),
            self._get_active_alarm_severity(),
        )

    def on_alarm_text_changed(self, text: str):
        self.alarm_banner.set_alarm_state(
            self.alarm_service.get_active_count(),
            text,
            self._get_active_alarm_severity(),
        )