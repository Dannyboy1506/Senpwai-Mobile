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

from main import BG_CARD, ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, SUCCESS, ERROR


class AnimeFolderCard(ButtonBehavior, RecycleDataViewBehavior, BoxLayout):
    name = StringProperty("")
    episodes = StringProperty("")
    size = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.size_hint_y = None
        self.height = dp(70)
        self.padding = [dp(12), dp(8)]
        self.spacing = dp(4)

        self.title_label = Label(text="", halign="left", valign="middle",
                                color=TEXT_PRIMARY, font_size=dp(14), size_hint_y=None, height=dp(25))
        self.title_label.bind(size=self.title_label.setter("text_size"))
        self.add_widget(self.title_label)

        info_row = BoxLayout(size_hint_y=None, height=dp(20))
        self.info_label = Label(text="", halign="left", valign="middle",
                               color=TEXT_SECONDARY, font_size=dp(11))
        info_row.add_widget(self.info_label)

        self.del_btn = Button(text="Delete", size_hint_x=None, width=dp(60),
                             background_color=ERROR, color=TEXT_PRIMARY, font_size=dp(10))
        info_row.add_widget(self.del_btn)
        self.add_widget(info_row)

    def refresh_view_attrs(self, rv, index, data):
        self.name = data.get("name", "")
        self.episodes = str(data.get("episode_count", 0))
        self.size = data.get("size_str", "0MB")
        self.title_label.text = self.name
        self.info_label.text = f"{self.episodes} episodes  •  {self.size}"


class EpisodeRow(ButtonBehavior, RecycleDataViewBehavior, BoxLayout):
    name = StringProperty("")
    size = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = dp(48)
        self.padding = [dp(12), dp(4)]
        self.spacing = dp(10)

        self.ep_label = Label(text="", halign="left", valign="middle",
                             color=TEXT_PRIMARY, font_size=dp(12))
        self.add_widget(self.ep_label)

        self.play_btn = Button(text="▶", size_hint_x=None, width=dp(45),
                              background_color=SUCCESS, color=TEXT_PRIMARY, font_size=dp(14))
        self.add_widget(self.play_btn)

    def refresh_view_attrs(self, rv, index, data):
        self.name = data.get("name", "")
        self.size = data.get("size_str", "")
        self.ep_label.text = f"{self.name}  ({self.size})"


class LibraryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))

        self.storage_label = Label(text="", size_hint_y=None, height=dp(28),
                                   color=TEXT_SECONDARY, font_size=dp(11))
        self.layout.add_widget(self.storage_label)

        self.anime_rv = RecycleView()
        self.anime_rv.add_widget(RecycleBoxLayout(
            default_size=(None, dp(70)), default_size_hint=(1, None),
            size_hint_y=None, orientation="vertical",
        ))
        self.anime_rv.bind(minimum_height=self.anime_rv.setter("height"))
        self.layout.add_widget(self.anime_rv)

        self.ep_panel = BoxLayout(orientation="vertical", spacing=dp(8))
        self.ep_panel.opacity = 0
        self.ep_panel.disabled = True

        ep_header = BoxLayout(size_hint_y=None, height=dp(38))
        self.back_btn = Button(text="← Back", size_hint_x=None, width=dp(70),
                              background_color=BG_CARD, color=TEXT_PRIMARY, font_size=dp(13))
        self.back_btn.bind(on_press=lambda x: self._show_list())
        ep_header.add_widget(self.back_btn)
        self.ep_title_label = Label(text="", color=TEXT_PRIMARY, font_size=dp(14))
        ep_header.add_widget(self.ep_title_label)
        self.ep_panel.add_widget(ep_header)

        self.ep_rv = RecycleView()
        self.ep_rv.add_widget(RecycleBoxLayout(
            default_size=(None, dp(48)), default_size_hint=(1, None),
            size_hint_y=None, orientation="vertical",
        ))
        self.ep_rv.bind(minimum_height=self.ep_rv.setter("height"))
        self.ep_panel.add_widget(self.ep_rv)

        self.layout.add_widget(self.ep_panel)
        self.add_widget(self.layout)

    def on_enter(self):
        self._refresh()

    def _refresh(self):
        app = self.manager.parent
        storage = app.storage
        info = storage.get_storage_info()
        self.storage_label.text = f"Storage: {storage.format_size(info['used'])} used  •  {storage.format_size(info['free'])} free"

        anime_list = storage.list_anime_folders()
        self.anime_rv.data = []
        for anime in anime_list:
            self.anime_rv.data.append({
                "name": anime["name"], "episode_count": anime["episode_count"],
                "size_str": storage.format_size(anime["total_size"]),
                "path": anime["path"], "episodes": anime["episodes"],
            })

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
                                self.manager.parent.switch_screen("player")
                                player = self.manager.get_screen("player")
                                player.play_file(ep_data["path"], ep_data["name"])
                            return True
        return False

    def _show_episodes(self, anime_data):
        self.anime_rv.opacity = 0
        self.anime_rv.disabled = True
        self.ep_panel.opacity = 1
        self.ep_panel.disabled = False
        self.ep_title_label.text = anime_data["name"]

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
