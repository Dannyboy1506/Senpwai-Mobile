from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.properties import StringProperty, NumericProperty, ObjectProperty
from kivy.clock import Clock
from kivy.metrics import dp

from constants import BG_CARD, BG_INPUT, ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, SUCCESS, ERROR, WARNING, BG_PRIMARY


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
        self.radius = [dp(4)]

    def _on_touch(self, widget, touch):
        if self.collide_point(*touch.pos) and self._on_action:
            self._on_action()
            return True


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
        self.height = dp(90)
        self.padding = [dp(12), dp(8)]
        self.spacing = dp(6)
        self.background_color = BG_CARD + [1]
        self.radius = [dp(8)]

        title_row = BoxLayout(size_hint_y=None, height=dp(24))
        self.title_label = Label(text="", halign="left", valign="middle",
                                color=TEXT_PRIMARY, font_size=dp(14), shorten=True)
        self.title_label.bind(size=self.title_label.setter("text_size"))
        title_row.add_widget(self.title_label)
        self.status_label = Label(text="", halign="right", valign="middle",
                                 color=TEXT_SECONDARY, font_size=dp(10), size_hint_x=None, width=dp(70))
        title_row.add_widget(self.status_label)
        self.add_widget(title_row)

        self.progress_bar = BoxLayout(size_hint_y=None, height=dp(8), background_color=BG_INPUT + [1], radius=[dp(4)])
        self.progress_fill = BoxLayout(size_hint_x=None, height=dp(8), background_color=ACCENT + [1], radius=[dp(4)])
        self.progress_bar.add_widget(self.progress_fill)
        self.add_widget(self.progress_bar)

        info_row = BoxLayout(size_hint_y=None, height=dp(24), spacing=dp(8))
        self.info_label = Label(text="", halign="left", valign="middle",
                               color=TEXT_SECONDARY, font_size=dp(11))
        info_row.add_widget(self.info_label)
        self.action_btn = ActionButton(text="", on_action=None,
                                       color=TEXT_PRIMARY, size_hint_x=None, width=dp(70),
                                       background_color=BG_INPUT)
        info_row.add_widget(self.action_btn)
        self.add_widget(info_row)

    def refresh_view_attrs(self, rv, index, data):
        self.title = data.get("title", "")
        self.progress = data.get("progress", 0)
        self.status = data.get("status", "pending")
        self.speed = data.get("speed", "")
        self.downloaded = data.get("downloaded", "")
        self.error = data.get("error", "")
        on_action = data.get("on_action", None)

        self.title_label.text = self.title
        self.status_label.text = self.status.upper()
        
        self.progress_fill.size_hint_x = self.progress / 100
        
        if self.status == "downloading":
            self.progress_bar.background_color = ACCENT + [1]
        elif self.status == "completed":
            self.progress_bar.background_color = SUCCESS + [1]
        elif self.status == "failed":
            self.progress_bar.background_color = ERROR + [1]
        else:
            self.progress_bar.background_color = BG_INPUT + [1]

        info_text = f"{self.downloaded}"
        if self.speed:
            info_text += f"  \u2022  {self.speed}"
        if self.status == "downloading":
            eta = data.get("eta", "")
            if eta:
                info_text += f"  \u2022  ETA: {eta}"
        if self.error:
            info_text += f"  \u2022  {self.error}"
        self.info_label.text = info_text

        if self.status == "completed":
            self.status_label.color = SUCCESS
            self.action_btn.text = "Done"
            self.action_btn.color = TEXT_SECONDARY
            self.action_btn.background_color = BG_INPUT
            self.action_btn._on_action = None
        elif self.status == "failed":
            self.status_label.color = ERROR
            self.action_btn.text = "Retry"
            self.action_btn.color = WARNING
            self.action_btn.background_color = BG_INPUT
            self.action_btn._on_action = on_action
        elif self.status == "paused":
            self.status_label.color = WARNING
            self.action_btn.text = "Resume"
            self.action_btn.color = ACCENT
            self.action_btn.background_color = BG_INPUT
            self.action_btn._on_action = on_action
        elif self.status == "downloading":
            self.status_label.color = ACCENT
            self.action_btn.text = "Pause"
            self.action_btn.color = TEXT_PRIMARY
            self.action_btn.background_color = BG_INPUT
            self.action_btn._on_action = on_action
        else:
            self.status_label.color = TEXT_SECONDARY
            self.action_btn.text = "Cancel"
            self.action_btn.color = ERROR
            self.action_btn.background_color = BG_INPUT
            self.action_btn._on_action = on_action


class DownloadScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation="vertical", padding=0, spacing=0)

        nav_row = BoxLayout(size_hint_y=None, height=dp(56), padding=[dp(16), dp(8)], spacing=dp(12))
        self.back_btn = Button(text="\u2190", size_hint_x=None, width=dp(48),
                              background_color=BG_CARD, color=TEXT_PRIMARY, font_size=dp(20),
                              background_normal="", background_down="")
        self.back_btn.bind(on_press=lambda x: self._go_back())
        nav_row.add_widget(self.back_btn)
        nav_row.add_widget(Label(text="Downloads", color=TEXT_PRIMARY, font_size=dp(18), size_hint_x=1))
        
        home_btn = Button(text="Home", size_hint_x=None, width=dp(70),
                         background_color=BG_CARD, color=TEXT_PRIMARY, font_size=dp(12),
                         background_normal="", background_down="")
        home_btn.bind(on_press=lambda x: self._go_home())
        nav_row.add_widget(home_btn)
        layout.add_widget(nav_row)

        self.panel = TabbedPanel(do_default_tab=False, tab_width=dp(100),
                                background_color=BG_PRIMARY + [1])

        self.active_tab = TabbedPanelItem(text="Active", background_normal="", background_down="",
                                         background_color=BG_PRIMARY + [1])
        self.active_rv = self._make_rv()
        self.active_tab.add_widget(self.active_rv)

        self.completed_tab = TabbedPanelItem(text="Done", background_normal="", background_down="",
                                           background_color=BG_PRIMARY + [1])
        self.completed_rv = self._make_rv()
        self.completed_tab.add_widget(self.completed_rv)

        self.failed_tab = TabbedPanelItem(text="Failed", background_normal="", background_down="",
                                        background_color=BG_PRIMARY + [1])
        self.failed_rv = self._make_rv()
        self.failed_tab.add_widget(self.failed_rv)

        self.panel.add_widget(self.active_tab)
        self.panel.add_widget(self.completed_tab)
        self.panel.add_widget(self.failed_tab)
        layout.add_widget(self.panel)
        self.add_widget(layout)

    def _make_rv(self):
        rv = RecycleView()
        rv.add_widget(RecycleBoxLayout(
            default_size=(None, dp(90)), default_size_hint=(1, None),
            size_hint_y=None, orientation="vertical", padding=dp(16), spacing=dp(8)
        ))
        rv.bind(minimum_height=rv.setter("height"))
        return rv

    def _go_back(self):
        if self.manager:
            self.manager.current = "home"

    def _go_home(self):
        if self.manager:
            self.manager.current = "home"

    def on_enter(self):
        self._refresh()
        try:
            if self.manager and self.manager.parent:
                app = self.manager.parent
                app.download_manager.register_callback(lambda e, t: Clock.schedule_once(lambda dt: self._refresh()))
        except Exception:
            pass

    def _refresh(self):
        if not self.manager or not self.manager.parent:
            return
        try:
            app = self.manager.parent
            dm = app.download_manager
        except Exception:
            return

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
                "eta": task.get_eta_str() if task.status == "downloading" else "",
                "on_action": action,
            })

        self.completed_rv.data = []
        for task in dm.completed_downloads:
            self.completed_rv.data.append({
                "title": task.title, "progress": 100, "status": "completed",
                "speed": "", "downloaded": task.get_downloaded_str(), "error": "",
                "eta": "", "on_action": None,
            })

        self.failed_rv.data = []
        for task in dm.failed_downloads:
            self.failed_rv.data.append({
                "title": task.title, "progress": task.get_progress(), "status": "failed",
                "speed": "", "downloaded": task.get_downloaded_str(), "error": task.error,
                "eta": "", "on_action": make_action(task, dm.retry_download),
            })
