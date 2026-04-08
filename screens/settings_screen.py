from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.switch import Switch
from kivy.uix.slider import Slider
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp

from constants import BG_CARD, BG_INPUT, ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_HINT


class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))

        header = BoxLayout(size_hint_y=None, height=dp(50))
        self.back_btn = Button(text="← Back", size_hint_x=None, width=dp(80),
                              background_color=BG_CARD, color=TEXT_PRIMARY, font_size=dp(14))
        self.back_btn.bind(on_press=lambda x: self._go_back())
        header.add_widget(self.back_btn)
        header.add_widget(Label(text="Settings", color=TEXT_PRIMARY, font_size=dp(18)))
        layout.add_widget(header)

        scroll = ScrollView()
        self.content = BoxLayout(orientation="vertical", padding=dp(15), spacing=dp(12),
                                size_hint_y=None)
        self.content.bind(minimum_height=self.content.setter("height"))

        self.content.add_widget(Label(text="Quality", size_hint_y=None, height=dp(22),
                                      color=TEXT_SECONDARY, font_size=dp(13)))
        self.quality_spinner = Spinner(text="1080p", values=["1080p", "720p", "480p", "360p"],
                                       size_hint_y=None, height=dp(42),
                                       background_color=BG_CARD, color=TEXT_PRIMARY, font_size=dp(14))
        self.quality_spinner.bind(text=lambda s, v: self._save("quality", v))
        self.content.add_widget(self.quality_spinner)

        self.content.add_widget(Label(text="Sub or Dub", size_hint_y=None, height=dp(22),
                                      color=TEXT_SECONDARY, font_size=dp(13)))
        sub_row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(10))
        self.sub_label = Label(text="Sub", color=TEXT_PRIMARY, size_hint_x=None, width=dp(50))
        sub_row.add_widget(self.sub_label)
        self.sub_switch = Switch(active=True, size_hint_x=None, width=dp(50))
        self.sub_switch.bind(active=self._on_sub_change)
        sub_row.add_widget(self.sub_switch)
        self.dub_label = Label(text="Dub", color=TEXT_HINT, size_hint_x=None, width=dp(50))
        sub_row.add_widget(self.dub_label)
        self.content.add_widget(sub_row)

        self.content.add_widget(Label(text="Default Site", size_hint_y=None, height=dp(22),
                                      color=TEXT_SECONDARY, font_size=dp(13)))
        self.site_spinner = Spinner(text="pahe", values=["pahe", "gogo"],
                                    size_hint_y=None, height=dp(42),
                                    background_color=BG_CARD, color=TEXT_PRIMARY, font_size=dp(14))
        self.site_spinner.bind(text=lambda s, v: self._save("site", v))
        self.content.add_widget(self.site_spinner)

        self.content.add_widget(Label(text="Max Simultaneous Downloads", size_hint_y=None, height=dp(22),
                                      color=TEXT_SECONDARY, font_size=dp(13)))
        msd_row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(10))
        self.msd_slider = Slider(min=1, max=5, step=1, value=2, size_hint_x=1)
        self.msd_slider.bind(value=self._on_msd_change)
        msd_row.add_widget(self.msd_slider)
        self.msd_label = Label(text="2", color=TEXT_PRIMARY, size_hint_x=None, width=dp(30))
        msd_row.add_widget(self.msd_label)
        self.content.add_widget(msd_row)

        self.content.add_widget(Label(text="Ignore Filler Episodes", size_hint_y=None, height=dp(22),
                                      color=TEXT_SECONDARY, font_size=dp(13)))
        filler_row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(10))
        filler_row.add_widget(Label(text="Skip filler episodes during download",
                                   color=TEXT_SECONDARY, size_hint_x=1))
        self.filler_switch = Switch(active=False, size_hint_x=None, width=dp(50))
        self.filler_switch.bind(active=lambda s, v: self._save("ignore_fillers", v))
        filler_row.add_widget(self.filler_switch)
        self.content.add_widget(filler_row)

        self.content.add_widget(Label(text="Download Folder", size_hint_y=None, height=dp(22),
                                      color=TEXT_SECONDARY, font_size=dp(13)))
        self.folder_label = Label(text="", color=TEXT_HINT, font_size=dp(11),
                                  halign="left", size_hint_y=None, height=dp(30))
        self.folder_label.bind(size=self.folder_label.setter("text_size"))
        self.content.add_widget(self.folder_label)

        self.change_folder_btn = Button(text="Change Folder", size_hint_y=None, height=dp(44),
                                        background_color=ACCENT, color=TEXT_PRIMARY, font_size=dp(13))
        self.change_folder_btn.bind(on_press=self._change_folder)
        self.content.add_widget(self.change_folder_btn)

        self.content.add_widget(Label(size_hint_y=1))
        self.content.add_widget(Label(text="Senpcli Mobile v1.0.0", size_hint_y=None, height=dp(25),
                                      color=TEXT_HINT, font_size=dp(11)))

        scroll.add_widget(self.content)
        layout.add_widget(scroll)
        self.add_widget(layout)

    def _go_back(self):
        if self.manager:
            self.manager.current = "home"

    def _save(self, key, value):
        try:
            if self.manager and self.manager.parent:
                self.manager.parent.on_config_change(key, value)
        except Exception:
            pass

    def _on_sub_change(self, switch, value):
        self._save("sub_or_dub", "sub" if value else "dub")
        self.sub_label.color = TEXT_PRIMARY if value else TEXT_HINT
        self.dub_label.color = TEXT_HINT if value else TEXT_PRIMARY

    def _on_msd_change(self, slider, value):
        self._save("max_simultaneous_downloads", int(value))
        self.msd_label.text = str(int(value))

    def _change_folder(self):
        try:
            from plyer import filechooser
            path = filechooser.open_file(title="Select Download Folder",
                                        dirselection=True)
            if path:
                folder = path[0] if isinstance(path, list) else path
                self._save("download_folder", folder)
                self.folder_label.text = folder
        except Exception as e:
            self.folder_label.text = f"Error: {str(e)[:40]}"

    def on_enter(self):
        if not self.manager or not self.manager.parent:
            return
        try:
            app = self.manager.parent
            config = app.config
            self.quality_spinner.text = config.quality
            self.sub_switch.active = config.sub_or_dub == "sub"
            self.sub_label.color = TEXT_PRIMARY if self.sub_switch.active else TEXT_HINT
            self.dub_label.color = TEXT_HINT if self.sub_switch.active else TEXT_PRIMARY
            self.site_spinner.text = config.site
            self.msd_slider.value = config.max_simultaneous_downloads
            self.filler_switch.active = config.ignore_fillers
            self.folder_label.text = config.download_folder
        except Exception:
            pass
