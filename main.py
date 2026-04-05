import re
import os
import sys
import json
import time
import random
import threading
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.clock import Clock
from kivy.properties import ObjectProperty, ListProperty, StringProperty
from kivy.metrics import dp
from kivy.utils import platform
from kivy.config import Config

Config.set('kivy', 'log_level', 'warning')
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

from screens.home_screen import HomeScreen
from screens.download_screen import DownloadScreen
from screens.library_screen import LibraryScreen
from screens.settings_screen import SettingsScreen
from screens.player_screen import PlayerScreen
from services.storage import StorageManager
from services.downloader import DownloadManager

APP_NAME = "Senpcli"
APP_VERSION = "1.0.0"

BG_PRIMARY = [0.10, 0.10, 0.14, 1]
BG_SECONDARY = [0.15, 0.15, 0.20, 1]
BG_CARD = [0.20, 0.20, 0.26, 1]
BG_CARD_HOVER = [0.25, 0.25, 0.32, 1]
BG_INPUT = [0.13, 0.13, 0.18, 1]
ACCENT = [0.50, 0.38, 0.90, 1]
ACCENT_LIGHT = [0.65, 0.55, 1.0, 1]
ACCENT_DARK = [0.35, 0.25, 0.70, 1]
TEXT_PRIMARY = [0.96, 0.96, 0.98, 1]
TEXT_SECONDARY = [0.65, 0.65, 0.72, 1]
TEXT_HINT = [0.42, 0.42, 0.50, 1]
SUCCESS = [0.28, 0.78, 0.42, 1]
ERROR = [0.88, 0.28, 0.28, 1]
WARNING = [0.92, 0.72, 0.22, 1]
DIVIDER = [0.25, 0.25, 0.32, 1]


def get_default_download_dir():
    if platform == "android":
        return "/storage/emulated/0/Download/Senpcli"
    return os.path.join(os.path.expanduser("~"), "Senpcli")


class SenpcliConfig:
    def __init__(self):
        self.config_dir = self._get_config_dir()
        self.config_path = os.path.join(self.config_dir, "app_config.json")
        self.quality = "1080p"
        self.sub_or_dub = "sub"
        self.site = "pahe"
        self.download_folder = get_default_download_dir()
        self.max_simultaneous_downloads = 2
        self.ignore_fillers = False
        self._load()

    def _get_config_dir(self):
        if platform == "android":
            try:
                from android.storage import app_storage_path
                return app_storage_path()
            except ImportError:
                pass
        base = os.path.expanduser("~")
        d = os.path.join(base, ".senpwai-mobile")
        try:
            os.makedirs(d, exist_ok=True)
        except Exception:
            d = base
        return d

    def _load(self):
        if not os.path.exists(self.config_path):
            self._save()
            return
        try:
            with open(self.config_path, "r") as f:
                data = json.load(f)
            self.quality = data.get("quality", "1080p")
            self.sub_or_dub = data.get("sub_or_dub", "sub")
            self.site = data.get("site", "pahe")
            self.download_folder = data.get("download_folder", get_default_download_dir())
            self.max_simultaneous_downloads = data.get("max_simultaneous_downloads", 2)
            self.ignore_fillers = data.get("ignore_fillers", False)
        except Exception:
            self._save()

    def _save(self):
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.config_path, "w") as f:
                json.dump({
                    "quality": self.quality,
                    "sub_or_dub": self.sub_or_dub,
                    "site": self.site,
                    "download_folder": self.download_folder,
                    "max_simultaneous_downloads": self.max_simultaneous_downloads,
                    "ignore_fillers": self.ignore_fillers,
                }, f, indent=2)
        except Exception:
            pass

    def save(self):
        self._save()


class SenpcliApp(App):
    config = ObjectProperty(None)
    storage = ObjectProperty(None)
    download_manager = ObjectProperty(None)

    def build(self):
        self.title = APP_NAME
        self.icon = "icon.png"
        Window.clearcolor = BG_PRIMARY
        if platform != "android":
            Window.size = (dp(375), dp(740))

        self.config = SenpcliConfig()
        self.storage = StorageManager(self.config.download_folder)
        self.download_manager = DownloadManager(self)

        sm = ScreenManager(transition=FadeTransition(duration=0.2))
        sm.add_widget(HomeScreen(name="home"))
        sm.add_widget(DownloadScreen(name="downloads"))
        sm.add_widget(LibraryScreen(name="library"))
        sm.add_widget(SettingsScreen(name="settings"))
        sm.add_widget(PlayerScreen(name="player"))

        Clock.schedule_once(lambda dt: self._on_ready(), 0.2)
        return sm

    def _on_ready(self):
        self.storage.ensure_download_dir()
        self.download_manager.scan_and_resume()
        self.root.current = "home"

    def switch_screen(self, screen_name):
        if self.root and self.root.current != screen_name:
            try:
                self.root.current = screen_name
            except Exception:
                pass

    def on_config_change(self, key, value):
        setattr(self.config, key, value)
        self.config.save()
        if key == "download_folder":
            self.storage = StorageManager(value)
            self.download_manager.storage = self.storage

    def show_notification(self, title, message):
        try:
            from plyer import notification
            notification.notify(title=title, message=message, app_name=APP_NAME, timeout=5)
        except Exception:
            pass

    def on_stop(self):
        self.download_manager.shutdown()
        self.config.save()


if __name__ == "__main__":
    SenpcliApp().run()
