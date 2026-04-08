from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.switch import Switch
from kivy.uix.slider import Slider
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp

from constants import BG_CARD, BG_INPUT, ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_HINT, BG_PRIMARY


class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation="vertical", padding=0, spacing=0)

        header = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(56),
                         padding=[dp(16), dp(8)], spacing=dp(12))
        self.back_btn = Button(text="\u2190", size_hint_x=None, width=dp(48),
                              background_color=BG_CARD, color=TEXT_PRIMARY, font_size=dp(20),
                              background_normal="", background_down="")
        self.back_btn.bind(on_press=lambda x: self._go_back())
        header.add_widget(self.back_btn)
        header.add_widget(Label(text="Settings", color=TEXT_PRIMARY, font_size=dp(18), size_hint_x=1))
        
        home_btn = Button(text="Home", size_hint_x=None, width=dp(70),
                         background_color=BG_CARD, color=TEXT_PRIMARY, font_size=dp(12),
                         background_normal="", background_down="")
        home_btn.bind(on_press=lambda x: self._go_home())
        header.add_widget(home_btn)
        layout.add_widget(header)

        scroll = ScrollView(background_color=BG_PRIMARY + [1])
        content = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(16),
                           size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))

        section = self._make_section("Quality")
        self.quality_spinner = Spinner(text="1080p", values=["1080p", "720p", "480p", "360p"],
                                      size_hint_y=None, height=dp(48),
                                      background_color=BG_CARD, color=TEXT_PRIMARY, font_size=dp(14),
                                      option_cls="SpinnerOption")
        self.quality_spinner.bind(text=lambda s, v: self._save("quality", v))
        section.add_widget(self.quality_spinner)
        content.add_widget(section)

        section = self._make_section("Sub or Dub")
        sub_row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(16))
        self.sub_label = Label(text="Sub", color=TEXT_PRIMARY, size_hint_x=1, font_size=dp(14))
        sub_row.add_widget(self.sub_label)
        self.sub_switch = Switch(active=True, size_hint_x=None, width=dp(50))
        self.sub_switch.bind(active=self._on_sub_change)
        sub_row.add_widget(self.sub_switch)
        self.dub_label = Label(text="Dub", color=TEXT_HINT, size_hint_x=1, font_size=dp(14))
        sub_row.add_widget(self.dub_label)
        section.add_widget(sub_row)
        content.add_widget(section)

        section = self._make_section("Default Site")
        self.site_spinner = Spinner(text="pahe", values=["pahe", "gogo"],
                                   size_hint_y=None, height=dp(48),
                                   background_color=BG_CARD, color=TEXT_PRIMARY, font_size=dp(14),
                                   option_cls="SpinnerOption")
        self.site_spinner.bind(text=lambda s, v: self._save("site", v))
        section.add_widget(self.site_spinner)
        content.add_widget(section)

        section = self._make_section("Max Simultaneous Downloads")
        msd_row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(12))
        self.msd_slider = Slider(min=1, max=5, step=1, value=2, size_hint_x=1,
                                 cursor_color=ACCENT, value_track_color=[ACCENT[0], ACCENT[1], ACCENT[2], 0.5])
        self.msd_slider.bind(value=self._on_msd_change)
        msd_row.add_widget(self.msd_slider)
        self.msd_label = Label(text="2", color=TEXT_PRIMARY, size_hint_x=None, width=dp(40),
                             font_size=dp(14), halign="center")
        msd_row.add_widget(self.msd_label)
        section.add_widget(msd_row)
        content.add_widget(section)

        section = self._make_section("Ignore Filler Episodes")
        filler_row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(12))
        filler_row.add_widget(Label(text="Skip filler episodes during download",
                                   color=TEXT_SECONDARY, size_hint_x=1, font_size=dp(13)))
        self.filler_switch = Switch(active=False, size_hint_x=None, width=dp(50))
        self.filler_switch.bind(active=lambda s, v: self._save("ignore_fillers", v))
        filler_row.add_widget(self.filler_switch)
        section.add_widget(filler_row)
        content.add_widget(section)

        section = self._make_section("Download Folder")
        self.folder_label = Label(text="", color=TEXT_SECONDARY, font_size=dp(12),
                                halign="left", size_hint_y=None, height=dp(40),
                                shorten=True, text_size=(None, None))
        self.folder_label.bind(size=lambda s,w: setattr(s, 'text_size', (self.width - dp(32), None)))
        section.add_widget(self.folder_label)

        self.change_folder_btn = Button(text="Change Folder", size_hint_y=None, height=dp(48),
                                        background_color=ACCENT, color=TEXT_PRIMARY, font_size=dp(14),
                                        background_normal="", background_down="")
        self.change_folder_btn.bind(on_press=self._change_folder)
        section.add_widget(self.change_folder_btn)
        content.add_widget(section)

        section = self._make_section("")
        section.add_widget(Label(text="Senpcli Mobile v1.0.0", size_hint_y=None, height=dp(40),
                               color=TEXT_HINT, font_size=dp(12)))
        content.add_widget(section)

        scroll.add_widget(content)
        layout.add_widget(scroll)
        self.add_widget(layout)

    def _make_section(self, title):
        box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8),
                       padding=[0, dp(8), 0, 0])
        if title:
            box.add_widget(Label(text=title, size_hint_y=None, height=dp(24),
                               color=TEXT_SECONDARY, font_size=dp(13), halign="left"))
        return box

    def _go_back(self):
        if self.manager:
            self.manager.current = "home"

    def _go_home(self):
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
            self.folder_label.text = f"Error selecting folder"

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
