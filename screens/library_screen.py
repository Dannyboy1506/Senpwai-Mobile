from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.properties import StringProperty
from kivy.clock import Clock
from kivy.metrics import dp

from constants import BG_CARD, ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, SUCCESS, ERROR, BG_PRIMARY


class AnimeFolderCard(ButtonBehavior, RecycleDataViewBehavior, BoxLayout):
    name = StringProperty("")
    episodes = StringProperty("")
    size = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = dp(72)
        self.padding = [dp(16), dp(12)]
        self.spacing = dp(12)
        self.background_color = BG_CARD + [1]
        self.radius = [dp(8)]

        self.icon = Label(text="\u25b6", color=ACCENT, size_hint_x=None, width=dp(40),
                        font_size=dp(24), halign="center", valign="middle")
        self.add_widget(self.icon)

        info = BoxLayout(orientation="vertical", size_hint_x=1)
        self.title_label = Label(text="", halign="left", valign="middle",
                                color=TEXT_PRIMARY, font_size=dp(14), shorten=True)
        self.title_label.bind(size=self.title_label.setter("text_size"))
        info.add_widget(self.title_label)

        self.info_label = Label(text="", halign="left", valign="middle",
                               color=TEXT_SECONDARY, font_size=dp(12))
        self.info_label.bind(size=self.info_label.setter("text_size"))
        info.add_widget(self.info_label)
        self.add_widget(info)

    def refresh_view_attrs(self, rv, index, data):
        self.name = data.get("name", "")
        self.episodes = str(data.get("episode_count", 0))
        self.size = data.get("size_str", "0MB")
        self.title_label.text = self.name
        self.info_label.text = f"{self.episodes} episodes  \u2022  {self.size}"


class EpisodeRow(ButtonBehavior, RecycleDataViewBehavior, BoxLayout):
    name = StringProperty("")
    size = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = dp(56)
        self.padding = [dp(16), dp(8)]
        self.spacing = dp(12)
        self.background_color = BG_CARD + [1]
        self.radius = [dp(6)]

        self.ep_label = Label(text="", halign="left", valign="middle",
                             color=TEXT_PRIMARY, font_size=dp(13), size_hint_x=1)
        self.add_widget(self.ep_label)

        self.play_btn = Button(text="\u25b6", size_hint_x=None, width=dp(44),
                              background_color=SUCCESS, color=TEXT_PRIMARY, font_size=dp(14),
                              background_normal="", background_down="")
        self.add_widget(self.play_btn)

    def refresh_view_attrs(self, rv, index, data):
        self.name = data.get("name", "")
        self.size = data.get("size_str", "")
        self.ep_label.text = f"{self.name}  ({self.size})"


class LibraryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation="vertical", padding=0, spacing=0)

        nav_row = BoxLayout(size_hint_y=None, height=dp(56), padding=[dp(16), dp(8)], spacing=dp(12))
        nav_row.add_widget(Label(text="Library", color=TEXT_PRIMARY, font_size=dp(18), size_hint_x=1))
        
        home_btn = Button(text="Home", size_hint_x=None, width=dp(70),
                         background_color=BG_CARD, color=TEXT_PRIMARY, font_size=dp(12),
                         background_normal="", background_down="")
        home_btn.bind(on_press=lambda x: self._go_home())
        nav_row.add_widget(home_btn)
        
        settings_btn = Button(text="Settings", size_hint_x=None, width=dp(80),
                             background_color=BG_CARD, color=TEXT_PRIMARY, font_size=dp(12),
                             background_normal="", background_down="")
        settings_btn.bind(on_press=lambda x: self._go_settings())
        nav_row.add_widget(settings_btn)
        layout.add_widget(nav_row)

        self.storage_label = Label(text="", size_hint_y=None, height=dp(32),
                                   color=TEXT_SECONDARY, font_size=dp(12), padding=[dp(16), 0])
        layout.add_widget(self.storage_label)

        self.anime_rv = RecycleView()
        self.anime_rv.add_widget(RecycleBoxLayout(
            default_size=(None, dp(72)), default_size_hint=(1, None),
            size_hint_y=None, orientation="vertical", padding=dp(16), spacing=dp(8)
        ))
        self.anime_rv.bind(minimum_height=self.anime_rv.setter("height"))
        layout.add_widget(self.anime_rv)

        self.ep_panel = BoxLayout(orientation="vertical", padding=0, spacing=0)
        self.ep_panel.opacity = 0
        self.ep_panel.disabled = True

        ep_header = BoxLayout(size_hint_y=None, height=dp(56), padding=[dp(16), dp(8)], spacing=dp(12))
        self.back_btn = Button(text="\u2190", size_hint_x=None, width=dp(48),
                              background_color=BG_CARD, color=TEXT_PRIMARY, font_size=dp(20),
                              background_normal="", background_down="")
        self.back_btn.bind(on_press=lambda x: self._show_list())
        ep_header.add_widget(self.back_btn)
        self.ep_title_label = Label(text="", color=TEXT_PRIMARY, font_size=dp(16), size_hint_x=1)
        ep_header.add_widget(self.ep_title_label)
        self.ep_panel.add_widget(ep_header)

        self.ep_rv = RecycleView()
        self.ep_rv.add_widget(RecycleBoxLayout(
            default_size=(None, dp(56)), default_size_hint=(1, None),
            size_hint_y=None, orientation="vertical", padding=dp(16), spacing=dp(6)
        ))
        self.ep_rv.bind(minimum_height=self.ep_rv.setter("height"))
        self.ep_panel.add_widget(self.ep_rv)

        layout.add_widget(self.ep_panel)
        self.add_widget(layout)

    def _go_home(self):
        if self.manager:
            self.manager.current = "home"

    def _go_settings(self):
        if self.manager:
            self.manager.current = "settings"

    def on_enter(self):
        self._refresh()

    def _refresh(self):
        if not self.manager or not self.manager.parent:
            return
        try:
            app = self.manager.parent
            storage = app.storage
            info = storage.get_storage_info()
            self.storage_label.text = f"Storage: {storage.format_size(info['used'])} used  \u2022  {storage.format_size(info['free'])} free"

            anime_list = storage.list_anime_folders()
            self.anime_rv.data = []
            for anime in anime_list:
                self.anime_rv.data.append({
                    "name": anime["name"], "episode_count": anime["episode_count"],
                    "size_str": storage.format_size(anime["total_size"]),
                    "path": anime["path"], "episodes": anime["episodes"],
                })
        except Exception:
            self.storage_label.text = "Error loading library"

    def on_touch_down(self, touch):
        if super().on_touch_down(touch):
            return True
        if self.anime_rv.opacity > 0:
            for child in self.anime_rv.children:
                if hasattr(child, 'children'):
                    for card in child.children:
                        if isinstance(card, AnimeFolderCard) and card.collide_point(*touch.pos):
                            idx = self.anime_rv.data.index(card)
                            if idx < len(self.anime_rv.data):
                                self._show_episodes(self.anime_rv.data[idx])
                            return True
        elif self.ep_panel.opacity > 0:
            for child in self.ep_rv.children:
                if hasattr(child, 'children'):
                    for row in child.children:
                        if isinstance(row, EpisodeRow) and row.collide_point(*touch.pos):
                            idx = self.ep_rv.data.index(row)
                            if idx < len(self.ep_rv.data):
                                ep_data = self.ep_rv.data[idx]
                                self._play_episode(ep_data)
                            return True
        return False

    def _play_episode(self, ep_data):
        if not self.manager or not self.manager.parent:
            return
        try:
            app = self.manager.parent
            player = app.root.get_screen("player")
            player.play_file(ep_data["path"], ep_data["name"])
            app.root.current = "player"
        except Exception as e:
            self.storage_label.text = f"Error: {str(e)[:60]}"

    def _show_episodes(self, anime_data):
        self.anime_rv.opacity = 0
        self.anime_rv.disabled = True
        self.ep_panel.opacity = 1
        self.ep_panel.disabled = False
        self.ep_title_label.text = anime_data["name"]

        if not self.manager or not self.manager.parent:
            return
        app = self.manager.parent
        self.ep_rv.data = []
        for ep in anime_data.get("episodes", []):
            self.ep_rv.data.append({
                "name": ep["name"], "size_str": app.storage.format_size(ep["size"]),
                "path": ep["path"],
            })

    def _show_list(self):
        self.anime_rv.opacity = 1
        self.anime_rv.disabled = False
        self.ep_panel.opacity = 0
        self.ep_panel.disabled = True
