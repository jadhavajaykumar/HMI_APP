from enum import Enum


class ScreenName(str, Enum):
    HOME = "home"
    MANUAL = "manual"
    IO = "io"
    ALARMS = "alarms"
    SIMULATOR = "simulator"
    SETTINGS = "settings"