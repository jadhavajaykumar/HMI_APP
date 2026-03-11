import logging

from PySide6.QtCore import QObject, QTimer, Signal

from hmi.drivers.modbus_driver import ModbusDriver
from hmi.drivers.simulator_driver import SimulatorDriver
from hmi.services.tag_manager import TagManager


class PlcService(QObject):
    tag_changed = Signal(str, object)
    connection_changed = Signal(bool)
    error_occurred = Signal(str)
    active_profile_changed = Signal(str)

    def __init__(self, tag_manager: TagManager):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.tag_manager = tag_manager
        self.driver = self._build_driver()
        self.timer = QTimer()
        self.timer.timeout.connect(self.poll_all)
        self.poll_ms = self.tag_manager.connection_config.get("poll_ms", 250)

    def _build_driver(self):
        cfg = self.tag_manager.connection_config
        driver_name = str(cfg.get("driver", "simulator")).lower()
        self.logger.info(
            "Building PLC driver for profile='%s' driver='%s'",
            self.tag_manager.get_active_connection_name(),
            driver_name,
        )

        if driver_name == "modbus":
            return ModbusDriver(
                host=cfg.get("host", "127.0.0.1"),
                port=cfg.get("port", 502),
                slave_id=cfg.get("slave_id", 1),
            )

        if driver_name == "siemens_s7":
            try:
                from hmi.drivers.siemens_s7_driver import SiemensS7Driver
            except ImportError as exc:
                raise ImportError(
                    "Siemens S7 driver selected, but python-snap7 is not installed. "
                    "Install it with: python -m pip install python-snap7"
                ) from exc

            s7cfg = cfg.get("siemens", {})
            return SiemensS7Driver(
                host=cfg.get("host", "127.0.0.1"),
                rack=s7cfg.get("rack", 0),
                slot=s7cfg.get("slot", 1),
                db_number=s7cfg.get("db_number", 1),
            )

        if driver_name == "opcua":
            try:
                from hmi.drivers.opcua_driver import OpcUaDriver
            except ImportError as exc:
                raise ImportError(
                    "OPC UA driver selected, but required package is not installed. "
                    "Install it with: python -m pip install asyncua"
                ) from exc

            endpoint = cfg.get("endpoint", "")
            if not endpoint:
                # backward-friendly fallback if user filled host/port instead of endpoint
                host = str(cfg.get("host", "")).strip()
                port = cfg.get("port", 4840)
                if host:
                    endpoint = host if host.lower().startswith("opc.tcp://") else f"opc.tcp://{host}:{port}"

            if not endpoint:
                raise ValueError(
                    "OPC UA profile is missing endpoint. "
                    "Set connection profile field 'endpoint', e.g. opc.tcp://192.168.0.20:4840"
                )

            return OpcUaDriver(
                endpoint=endpoint,
                username=cfg.get("username", ""),
                password=cfg.get("password", ""),
            )

        return SimulatorDriver(
            tag_defs=self.tag_manager.all_tags(),
            manual_devices=self.tag_manager.get_manual_devices(),
            alarm_words=self.tag_manager.get_alarm_words(),
        )

    def start(self):
        try:
            self.poll_ms = self.tag_manager.connection_config.get("poll_ms", 250)
            ok = self.driver.connect()
            self.connection_changed.emit(ok)
            if ok:
                self.logger.info(
                    "PLC connected profile='%s' poll_ms=%s",
                    self.tag_manager.get_active_connection_name(),
                    self.poll_ms,
                )
                self.timer.start(self.poll_ms)
        except Exception as exc:
            self.logger.exception("PLC start/connect failed")
            self.error_occurred.emit(str(exc))
            self.connection_changed.emit(False)

    def stop(self):
        self.timer.stop()
        try:
            self.driver.disconnect()
        except Exception:
            pass
        self.connection_changed.emit(False)

    def rebuild_driver(self):
        was_running = self.timer.isActive()
        self.stop()
        self.driver = self._build_driver()
        self.poll_ms = self.tag_manager.connection_config.get("poll_ms", 250)
        if was_running:
            self.start()

    def set_active_connection(self, connection_name: str, persist: bool = False):
        self.tag_manager.set_active_connection(connection_name)
        if persist:
            self.tag_manager.save()
        self.rebuild_driver()
        self.active_profile_changed.emit(connection_name)

    def get_active_connection_name(self) -> str:
        return self.tag_manager.get_active_connection_name()

    def get_connection_names(self):
        return self.tag_manager.get_connection_names()

    def poll_all(self):
        try:
            tags = self.tag_manager.all_tags()
            values = self.driver.read_tags(tags)

            for tag_name, value in values.items():
                old = self.tag_manager.get_value(tag_name)
                self.tag_manager.set_value(tag_name, value, quality="good")
                if old != value:
                    self.tag_changed.emit(tag_name, value)

        except Exception as exc:
            self.logger.exception("PLC poll failed")
            self.error_occurred.emit(str(exc))
            self.connection_changed.emit(False)

    def read_tag(self, tag_name: str):
        return self.tag_manager.get_value(tag_name)

    def write_tag(self, tag_name: str, value):
        tag_def = self.tag_manager.get_definition(tag_name)
        try:
            ok = self.driver.write_tag(tag_def, value)
            if ok:
                self.tag_manager.set_value(tag_name, value, quality="good")
                self.tag_changed.emit(tag_name, value)
            return ok
        except Exception as exc:
            self.logger.exception("PLC write failed for tag='%s'", tag_name)
            self.error_occurred.emit(str(exc))
            return False

    def pulse_coil(self, tag_name: str, duration_ms: int = 200):
        ok = self.write_tag(tag_name, True)
        if not ok:
            return
        QTimer.singleShot(duration_ms, lambda: self.write_tag(tag_name, False))