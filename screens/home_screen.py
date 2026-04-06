import os
import re
import threading
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.popup import Popup
from kivy.properties import StringProperty
from kivy.clock import Clock
from kivy.metrics import dp

try:
    from kivy.core.window import Clipboard
    HAS_CLIPBOARD = True
except Exception:
    HAS_CLIPBOARD = False

try:
    from services.scraper import (
        search_pahe, search_gogo, get_pahe_episodes, get_pahe_download_links,
        decrypt_kwik, get_gogo_episodes, get_gogo_download_links,
        strip_title, IBYTES_TO_MBS_DIVISOR, CLIENT, open_url_in_browser,
    )
    SCRAPER_AVAILABLE = True
except Exception as e:
    print(f"Warning: Could not import scraper: {e}")
    SCRAPER_AVAILABLE = False
    search_pahe = search_gogo = get_pahe_episodes = get_pahe_download_links = None
    decrypt_kwik = get_gogo_episodes = get_gogo_download_links = None
    strip_title = None
    IBYTES_TO_MBS_DIVISOR = 1024 * 1024
    CLIENT = None
    open_url_in_browser = None

from constants import BG_CARD, BG_INPUT, ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_HINT, SUCCESS, ERROR


class AnimeCard(ButtonBehavior, RecycleDataViewBehavior, BoxLayout):
    title = StringProperty("")
    episodes = StringProperty("")
    year = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = dp(70)
        self.padding = [dp(15), dp(10)]
        self.spacing = dp(10)

        self.title_label = Label(text="", halign="left", valign="middle",
                                color=TEXT_PRIMARY, font_size=dp(14))
        self.title_label.bind(size=self.title_label.setter("text_size"))
        self.add_widget(self.title_label)

        self.info_label = Label(text="", halign="right", valign="middle",
                               color=TEXT_SECONDARY, font_size=dp(11), size_hint_x=None, width=dp(80))
        self.info_label.bind(size=self.info_label.setter("text_size"))
        self.add_widget(self.info_label)

    def refresh_view_attrs(self, rv, index, data):
        self.title = data.get("title", "")
        self.episodes = str(data.get("episodes", "?"))
        self.year = str(data.get("year", ""))
        self.title_label.text = self.title
        self.info_label.text = f"{self.episodes} eps\n{self.year}"


class HomeScreen(Screen):
    current_anime = None
    _search_thread = None
    _download_thread = None
    _ddl_thread = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))

        search_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        self.site_spinner = Spinner(text="pahe", values=["pahe", "gogo"],
                                    size_hint_x=None, width=dp(75),
                                    background_color=BG_CARD, color=TEXT_PRIMARY, font_size=dp(13))
        self.search_input = TextInput(hint_text="Search anime...", multiline=False,
                                      background_color=BG_INPUT, foreground_color=TEXT_PRIMARY,
                                      cursor_color=TEXT_PRIMARY, font_size=dp(14),
                                      padding=[dp(12), dp(10)])
        self.search_input.bind(on_text_validate=lambda x: self.do_search())
        search_btn = Button(text="Search", size_hint_x=None, width=dp(80),
                           background_color=ACCENT, color=TEXT_PRIMARY, font_size=dp(13))
        search_btn.bind(on_press=lambda x: self.do_search())
        search_row.add_widget(self.site_spinner)
        search_row.add_widget(self.search_input)
        search_row.add_widget(search_btn)

        self.status_label = Label(text="Search for an anime to get started",
                                  color=TEXT_HINT, font_size=dp(14), size_hint_y=None, height=dp(30))

        self.results_rv = RecycleView()
        self.results_rv.add_widget(RecycleBoxLayout(
            default_size=(None, dp(70)), default_size_hint=(1, None),
            size_hint_y=None, orientation="vertical",
        ))
        self.results_rv.bind(minimum_height=self.results_rv.setter("height"))

        self.ep_area = BoxLayout(orientation="vertical", spacing=dp(8))
        self.ep_area.add_widget(Label(text="Episode Selection", size_hint_y=None, height=dp(25),
                                      color=TEXT_SECONDARY, font_size=dp(13)))
        ep_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        ep_row.add_widget(Label(text="From:", color=TEXT_SECONDARY, size_hint_x=None, width=dp(45), font_size=dp(13)))
        self.ep_from = TextInput(text="1", multiline=False, size_hint_x=None, width=dp(55),
                                background_color=BG_INPUT, foreground_color=TEXT_PRIMARY,
                                font_size=dp(14), padding=[dp(8), dp(8)])
        ep_row.add_widget(self.ep_from)
        ep_row.add_widget(Label(text="To:", color=TEXT_SECONDARY, size_hint_x=None, width=dp(35), font_size=dp(13)))
        self.ep_to = TextInput(text="", multiline=False, size_hint_x=None, width=dp(55),
                              background_color=BG_INPUT, foreground_color=TEXT_PRIMARY,
                              font_size=dp(14), padding=[dp(8), dp(8)])
        ep_row.add_widget(self.ep_to)
        self.ep_area.add_widget(ep_row)

        self.dl_btn = Button(text="Download All", size_hint_y=None, height=dp(48),
                            background_color=SUCCESS, color=TEXT_PRIMARY, font_size=dp(14))
        self.dl_btn.bind(on_press=lambda x: self.start_download())

        self.ddl_btn = Button(text="Get DDL Links", size_hint_y=None, height=dp(48),
                             background_color=ACCENT, color=TEXT_PRIMARY, font_size=dp(14))
        self.ddl_btn.bind(on_press=lambda x: self.get_ddl_links())

        btn_row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        btn_row.add_widget(self.dl_btn)
        btn_row.add_widget(self.ddl_btn)
        self.ep_area.add_widget(btn_row)
        self.ep_area.opacity = 0
        self.ep_area.disabled = True

        self.layout.add_widget(search_row)
        self.layout.add_widget(self.status_label)
        self.layout.add_widget(self.results_rv)
        self.layout.add_widget(self.ep_area)
        self.add_widget(self.layout)

    def do_search(self):
        if not SCRAPER_AVAILABLE:
            self.status_label.text = "Search unavailable"
            return
        query = self.search_input.text.strip()
        if not query:
            return
        self.status_label.text = "Searching..."
        self.results_rv.data = []
        self.ep_area.opacity = 0
        self.ep_area.disabled = True
        site = self.site_spinner.text
        threading.Thread(target=lambda: self._search(query, site), daemon=True).start()

    def _search(self, query, site):
        try:
            results = search_pahe(query) if site == "pahe" else search_gogo(query)
            def _update():
                if not results:
                    self.status_label.text = "No results found"
                    self.results_rv.data = []
                else:
                    self.status_label.text = f"Found {len(results)} results"
                    self.results_rv.data = results
            Clock.schedule_once(lambda dt: _update())
        except Exception as e:
            Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', f"Error: {str(e)[:60]}"))

    def select_anime(self, anime_data):
        self.current_anime = anime_data
        eps = str(anime_data.get("episodes", ""))
        if eps and eps.isdigit():
            self.ep_to.text = eps
        self.ep_area.opacity = 1
        self.ep_area.disabled = False

    def start_download(self):
        if not self.current_anime:
            return
        if self._download_thread and self._download_thread.is_alive():
            Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', "Download already in progress"))
            return
        try:
            ep_from = int(self.ep_from.text)
            ep_to = int(self.ep_to.text) if self.ep_to.text else ep_from
        except ValueError:
            self.status_label.text = "Invalid episode numbers"
            return
        if ep_to < ep_from:
            self.status_label.text = "End episode must be >= start"
            return
        if ep_from < 1:
            self.status_label.text = "Start episode must be >= 1"
            return
        app = self.manager.parent
        site = self.site_spinner.text
        self.status_label.text = "Preparing downloads..."
        self._download_thread = threading.Thread(
            target=lambda: self._dl(site, ep_from, ep_to, app.config.quality, app.config.sub_or_dub), daemon=True
        )
        self._download_thread.start()

    def _dl(self, site, ep_from, ep_to, quality, sub_or_dub):
        try:
            if site == "pahe":
                self._dl_pahe(ep_from, ep_to, quality, sub_or_dub)
            else:
                self._dl_gogo(ep_from, ep_to, quality)
            Clock.schedule_once(lambda dt: self.manager.parent.switch_screen("downloads"))
        except Exception as e:
            Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', f"Error: {str(e)[:80]}"))

    def _dl_pahe(self, ep_from, ep_to, quality, sub_or_dub):
        anime = self.current_anime
        if not anime:
            return
        anime_id = anime.get("id", "")
        app = self.manager.parent
        folder = os.path.join(app.config.download_folder, strip_title(anime.get("title", "Unknown")))
        os.makedirs(folder, exist_ok=True)
        episodes = get_pahe_episodes(anime_id)
        if not episodes:
            Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', "No episodes found"))
            return
        count = 0
        for ep in episodes:
            ep_num = ep.get("episode", 0)
            if not ep_num or ep_num < ep_from or ep_num > ep_to:
                continue
            existing = os.path.join(folder, f"{strip_title(anime.get('title', ''))} E{ep_num:02d}.mp4")
            if os.path.exists(existing):
                continue
            session = ep.get("session", "")
            if not session:
                continue
            links = get_pahe_download_links(anime_id, session, quality, sub_or_dub)
            if not links:
                continue
            direct_url = decrypt_kwik(links[0]["kwik_url"])
            if not direct_url:
                continue
            title = f"{strip_title(anime.get('title', ''))} E{ep_num:02d}"
            app.download_manager.add_download(direct_url, title, folder, links[0]["size"], file_ext=".mp4")
            count += 1
        Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', f"Queued {count} episodes"))

    def _dl_gogo(self, ep_from, ep_to, quality):
        anime = self.current_anime
        if not anime:
            return
        anime_id = anime.get("id", "")
        app = self.manager.parent
        folder = os.path.join(app.config.download_folder, strip_title(anime.get("title", "Unknown")))
        os.makedirs(folder, exist_ok=True)
        episodes = get_gogo_episodes(anime_id, ep_from, ep_to)
        count = 0
        for ep_info in episodes:
            ep_num = ep_info["ep_num"]
            existing = os.path.join(folder, f"{strip_title(anime.get('title', ''))} E{ep_num:02d}.mp4")
            if os.path.exists(existing):
                continue
            dl_info = get_gogo_download_links(ep_info["url"], quality)
            if not dl_info:
                continue
            if dl_info.get("is_hls"):
                title = f"{strip_title(anime.get('title', ''))} E{ep_num:02d}"
                app.download_manager.add_download(dl_info["url"], title, folder, 0, is_hls=True, file_ext=".ts")
            else:
                try:
                    r = CLIENT.get(dl_info["url"], stream=True, timeout=10, allow_redirects=True)
                    size = int(r.headers.get("Content-Length", 0))
                except Exception:
                    size = 0
                title = f"{strip_title(anime.get('title', ''))} E{ep_num:02d}"
                app.download_manager.add_download(dl_info["url"], title, folder, size, file_ext=".mp4")
            count += 1
        Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', f"Queued {count} episodes"))

    def get_ddl_links(self):
        if not self.current_anime:
            return
        if self._ddl_thread and self._ddl_thread.is_alive():
            Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', "Fetching links already in progress"))
            return
        try:
            ep_from = int(self.ep_from.text)
            ep_to = int(self.ep_to.text) if self.ep_to.text else ep_from
        except ValueError:
            self.status_label.text = "Invalid episode numbers"
            return
        if ep_to < ep_from:
            self.status_label.text = "End episode must be >= start"
            return
        if ep_from < 1:
            self.status_label.text = "Start episode must be >= 1"
            return
        app = self.manager.parent
        site = self.site_spinner.text
        self.status_label.text = "Fetching DDL links..."
        self._ddl_thread = threading.Thread(
            target=lambda: self._get_ddl(site, ep_from, ep_to, app.config.quality, app.config.sub_or_dub), daemon=True
        )
        self._ddl_thread.start()

    def _get_ddl(self, site, ep_from, ep_to, quality, sub_or_dub):
        try:
            links = []
            if site == "pahe":
                links = self._get_ddl_pahe(ep_from, ep_to, quality, sub_or_dub)
            else:
                links = self._get_ddl_gogo(ep_from, ep_to, quality)

            def _show():
                if not links:
                    self.status_label.text = "No DDL links found"
                    return
                self._show_ddl_popup(links)
            Clock.schedule_once(lambda dt: _show())
        except Exception as e:
            Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', f"DDL error: {str(e)[:80]}"))

    def _get_ddl_pahe(self, ep_from, ep_to, quality, sub_or_dub):
        anime = self.current_anime
        if not anime:
            return []
        anime_id = anime.get("id", "")
        episodes = get_pahe_episodes(anime_id)
        links = []
        for ep in episodes:
            ep_num = ep.get("episode", 0)
            if not ep_num or ep_num < ep_from or ep_num > ep_to:
                continue
            session = ep.get("session", "")
            if not session:
                continue
            dl_links = get_pahe_download_links(anime_id, session, quality, sub_or_dub)
            if not dl_links:
                continue
            direct_url = decrypt_kwik(dl_links[0]["kwik_url"])
            if direct_url:
                title = f"E{ep_num:02d} - {anime.get('title', '')}"
                links.append({"title": title, "url": direct_url})
        return links

    def _get_ddl_gogo(self, ep_from, ep_to, quality):
        anime = self.current_anime
        if not anime:
            return []
        anime_id = anime.get("id", "")
        episodes = get_gogo_episodes(anime_id, ep_from, ep_to)
        links = []
        for ep_info in episodes:
            ep_num = ep_info["ep_num"]
            dl_info = get_gogo_download_links(ep_info["url"], quality)
            if not dl_info:
                continue
            title = f"E{ep_num:02d} - {anime.get('title', '')}"
            links.append({"title": title, "url": dl_info["url"]})
        return links

    def _show_ddl_popup(self, links):
        content = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
        content.add_widget(Label(text=f"Found {len(links)} DDL links", size_hint_y=None, height=dp(30),
                                color=TEXT_PRIMARY, font_size=dp(14)))

        scroll = RecycleView()
        scroll_layout = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(6))
        scroll_layout.bind(minimum_height=scroll_layout.setter("height"))

        for link_info in links:
            row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
            row.add_widget(Label(text=link_info["title"], color=TEXT_PRIMARY,
                               font_size=dp(11), halign="left", size_hint_x=0.5))
            url_display = link_info["url"]
            if len(url_display) > 40:
                url_display = url_display[:40] + "..."
            row.add_widget(Label(text=url_display, color=TEXT_SECONDARY,
                               font_size=dp(9), halign="left", size_hint_x=0.5))

            copy_btn = Button(text="Copy", size_hint_x=None, width=dp(55),
                            background_color=BG_CARD, color=TEXT_PRIMARY, font_size=dp(10))
            copy_btn.bind(on_press=lambda x, u=link_info["url"]: self._copy_link(u))
            row.add_widget(copy_btn)

            open_btn = Button(text="Open", size_hint_x=None, width=dp(55),
                            background_color=ACCENT, color=TEXT_PRIMARY, font_size=dp(10))
            open_btn.bind(on_press=lambda x, u=link_info["url"]: open_url_in_browser(u))
            row.add_widget(open_btn)

            scroll_layout.add_widget(row)

        scroll.add_widget(scroll_layout)
        content.add_widget(scroll)

        popup = Popup(title="Direct Download Links", content=content,
                     size_hint=(0.95, 0.8), background_color=[0.12, 0.12, 0.16, 1])
        popup.open()

    def _copy_link(self, url):
        try:
            if HAS_CLIPBOARD:
                Clipboard.copy(url)
                self.status_label.text = "Link copied to clipboard"
        except Exception:
            self.status_label.text = "Could not copy link"
