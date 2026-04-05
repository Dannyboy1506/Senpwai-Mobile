from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.properties import StringProperty, NumericProperty
from kivy.clock import Clock
from kivy.metrics import dp

from main import BG_CARD, ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, SUCCESS, ERROR, WARNING


class ActionButton(ButtonBehavior, Label):
    def __init__(self, text="", on_action=None, **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.halign = "center"
        self.valign = "middle"
        self.bind(size=self.setter("text_size"))
        self.font_size = dp(11)
        self._on_action = on_action
        self.bind(on_touch_down=self._on_touch)

    def _on_touch(self, widget, touch):
        if self.collide_point(*touch.pos) and self._on_action:
            self._on_action()


class DownloadItemWidget(RecycleDataViewBehavior, BoxLayout):
    title = StringProperty("")
    progress = NumericProperty(0)
    status = StringProperty("pending")
    speed = StringProperty("")
    downloaded = StringProperty("")
    error = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.size_hint_y = None
        self.height = dp(75)
        self.padding = [dp(12), dp(6)]
        self.spacing = dp(4)

        title_row = BoxLayout(size_hint_y=None, height=dp(22))
        self.title_label = Label(text="", halign="left", valign="middle",
                                color=TEXT_PRIMARY, font_size=dp(13))
        self.title_label.bind(size=self.title_label.setter("text_size"))
        title_row.add_widget(self.title_label)
        self.status_label = Label(text="", halign="right", valign="middle",
                                 color=TEXT_SECONDARY, font_size=dp(10), size_hint_x=None, width=dp(70))
        title_row.add_widget(self.status_label)
        self.add_widget(title_row)

        progress_row = BoxLayout(size_hint_y=None, height=dp(16), spacing=dp(5))
        self.progress_bg = Label(text="", color=TEXT_PRIMARY, font_size=dp(10))
        progress_row.add_widget(self.progress_bg)
        self.add_widget(progress_row)

        info_row = BoxLayout(size_hint_y=None, height=dp(22), spacing=dp(5))
        self.info_label = Label(text="", halign="left", valign="middle",
                               color=TEXT_SECONDARY, font_size=dp(10))
        info_row.add_widget(self.info_label)
        self.action_btn = ActionButton(text="", on_action=None,
                                       color=TEXT_PRIMARY, size_hint_x=None, width=dp(60))
        info_row.add_widget(self.action_btn)
        self.add_widget(info_row)

    def refresh_view_attrs(self, rv, index, data):
        self.title = data.get("title", "")
        self.progress = data.get("progress", 0)
        self.status = data.get("status", "pending")
        self.speed = data.get("speed", "")
        self.downloaded = data.get("downloaded", "")
        self.error = data.get("error", "")
        self._on_action = data.get("on_action", None)

        self.title_label.text = self.title
        self.status_label.text = self.status.upper()
        filled = int(self.progress / 5)
        self.progress_bg.text = f"[{'█' * filled}{'░' * (20 - filled)}] {self.progress:.0f}%"
        self.info_label.text = f"{self.downloaded}  {self.speed}"

        if self.status == "completed":
            self.status_label.color = SUCCESS
            self.action_btn.text = "Done"
            self.action_btn.color = TEXT_SECONDARY
            self.action_btn._on_action = None
        elif self.status == "failed":
            self.status_label.color = ERROR
            self.action_btn.text = "Retry"
            self.action_btn.color = WARNING
            self.action_btn._on_action = self._on_action
        elif self.status == "paused":
            self.status_label.color = WARNING
            self.action_btn.text = "Resume"
            self.action_btn.color = ACCENT
            self.action_btn._on_action = self._on_action
        elif self.status == "downloading":
            self.status_label.color = ACCENT
            self.action_btn.text = "Pause"
            self.action_btn.color = TEXT_PRIMARY
            self.action_btn._on_action = self._on_action
        else:
            self.status_label.color = TEXT_SECONDARY
            self.action_btn.text = "Cancel"
            self.action_btn.color = ERROR
            self.action_btn._on_action = self._on_action


class DownloadScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))

        self.panel = TabbedPanel(do_default_tab=False)
        self.panel.tab_width = dp(100)
        self.panel.background_color = [0.12, 0.12, 0.16, 1]

        self.active_tab = TabbedPanelItem(text="Active")
        self.active_rv = self._make_rv()
        self.active_tab.add_widget(self.active_rv)

        self.completed_tab = TabbedPanelItem(text="Done")
        self.completed_rv = self._make_rv()
        self.completed_tab.add_widget(self.completed_rv)

        self.failed_tab = TabbedPanelItem(text="Failed")
        self.failed_rv = self._make_rv()
        self.failed_tab.add_widget(self.failed_rv)

        self.panel.add_widget(self.active_tab)
        self.panel.add_widget(self.completed_tab)
        self.panel.add_widget(self.failed_tab)
        self.layout.add_widget(self.panel)
        self.add_widget(self.layout)

    def _make_rv(self):
        rv = RecycleView()
        rv.add_widget(RecycleBoxLayout(
            default_size=(None, dp(75)), default_size_hint=(1, None),
            size_hint_y=None, orientation="vertical",
        ))
        rv.bind(minimum_height=rv.setter("height"))
        return rv

    def on_enter(self):
        self._refresh()
        app = self.manager.parent
        app.download_manager.register_callback(lambda e, t: Clock.schedule_once(lambda dt: self._refresh()))

    def _refresh(self):
        app = self.manager.parent
        dm = app.download_manager

        def make_action(task, action):
            def _action():
                action(task)
                Clock.schedule_once(lambda dt: self._refresh())
            return _action

        self.active_rv.data = []
        for task in dm.active_downloads:
            if task.status == "downloading":
                action = make_action(task, dm.pause_download)
            else:
                action = make_action(task, dm.cancel_download)
            self.active_rv.data.append({
                "title": task.title, "progress": task.get_progress(),
                "status": task.status, "speed": task.get_speed_str(),
                "downloaded": task.get_downloaded_str(), "error": task.error,
                "on_action": action,
            })

        self.completed_rv.data = []
        for task in dm.completed_downloads:
            self.completed_rv.data.append({
                "title": task.title, "progress": 100, "status": "completed",
                "speed": "", "downloaded": task.get_downloaded_str(), "error": "",
                "on_action": None,
            })

        self.failed_rv.data = []
        for task in dm.failed_downloads:
            self.failed_rv.data.append({
                "title": task.title, "progress": task.get_progress(), "status": "failed",
                "speed": "", "downloaded": task.get_downloaded_str(), "error": task.error,
                "on_action": make_action(task, dm.retry_download),
            })
