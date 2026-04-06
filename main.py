import os
import json

os.environ['KIVY_NO_CONSOLELOG'] = '1'
os.environ['KIVY_NO_FILELOG'] = '1'

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.clock import Clock
from kivy.properties import ObjectProperty
from kivy.config import Config

Config.set('kivy', 'log_level', 'error')
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')


def get_default_download_dir():
    return os.path.join(os.path.expanduser("~"), "Senpcli")


class SenpcliConfig:
    def __init__(self):
        self.config_dir = os.path.join(os.path.expanduser("~"), ".senpcli")
        self.config_path = os.path.join(self.config_dir, "app_config.json")
        self.quality = "1080p"
        self.sub_or_dub = "sub"
        self.site = "pahe"
        self.download_folder = get_default_download_dir()
        self.max_simultaneous_downloads = 2
        self.ignore_fillers = False
        self._load()

    def _load(self):
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            if os.path.exists(self.config_path):
                with open(self.config_path, "r") as f:
                    data = json.load(f)
                    self.quality = data.get("quality", "1080p")
                    self.sub_or_dub = data.get("sub_or_dub", "sub")
                    self.site = data.get("site", "pahe")
                    self.download_folder = data.get("download_folder", get_default_download_dir())
                    self.max_simultaneous_downloads = data.get("max_simultaneous_downloads", 2)
                    self.ignore_fillers = data.get("ignore_fillers", False)
                    return
        except Exception:
            pass
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
    storage = None
    download_manager = None

    def build(self):
        from constants import BG_PRIMARY
        Window.clearcolor = BG_PRIMARY
        
        sm = ScreenManager(transition=FadeTransition(duration=0.2))
        
        try:
            from screens.home_screen import HomeScreen
            sm.add_widget(HomeScreen(name="home"))
        except Exception as e:
            print(f"Error loading HomeScreen: {e}")

        try:
            from screens.download_screen import DownloadScreen
            sm.add_widget(DownloadScreen(name="downloads"))
        except Exception as e:
            print(f"Error loading DownloadScreen: {e}")

        try:
            from screens.library_screen import LibraryScreen
            sm.add_widget(LibraryScreen(name="library"))
        except Exception as e:
            print(f"Error loading LibraryScreen: {e}")

        try:
            from screens.settings_screen import SettingsScreen
            sm.add_widget(SettingsScreen(name="settings"))
        except Exception as e:
            print(f"Error loading SettingsScreen: {e}")

        try:
            from screens.player_screen import PlayerScreen
            sm.add_widget(PlayerScreen(name="player"))
        except Exception as e:
            print(f"Error loading PlayerScreen: {e}")

        from constants import APP_NAME
        self.title = APP_NAME
        self.icon = "icon.png"

        Clock.schedule_once(self._on_ready, 0.5)
        return sm

    def _on_ready(self, *args):
        try:
            from services.storage import StorageManager
            from services.downloader import DownloadManager
            
            self.config = SenpcliConfig()
            self.storage = StorageManager(self.config.download_folder)
            self.download_manager = DownloadManager(self)
            
            self.storage.ensure_download_dir()
            self.download_manager.scan_and_resume()
            self.root.current = "home"
        except Exception as e:
            print(f"Error in _on_ready: {e}")
            try:
                self.root.current = "home"
            except Exception:
                pass

    def switch_screen(self, screen_name):
        if self.root:
            try:
                self.root.current = screen_name
            except Exception:
                pass

    def on_config_change(self, key, value):
        if self.config:
            try:
                setattr(self.config, key, value)
                self.config.save()
            except Exception:
                pass

    def show_notification(self, title, message):
        try:
            from plyer import notification
            from constants import APP_NAME
            notification.notify(title=title, message=message, app_name=APP_NAME, timeout=5)
        except Exception:
            pass

    def on_stop(self):
        if self.download_manager:
            try:
                self.download_manager.shutdown()
            except Exception:
                pass
        if self.config:
            try:
                self.config.save()
            except Exception:
                pass


if __name__ == "__main__":
    SenpcliApp().run()