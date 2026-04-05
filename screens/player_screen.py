import os
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.properties import StringProperty
from kivy.metrics import dp

from main import BG_CARD, ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, SUCCESS


class PlayerScreen(Screen):
    current_file = StringProperty("")
    current_title = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation="vertical", padding=dp(15), spacing=dp(10))

        # Info area
        self.layout.add_widget(Label(
            text="Video Player",
            size_hint_y=None,
            height=dp(40),
            color=TEXT_PRIMARY,
            font_size=dp(18),
        ))

        self.file_label = Label(
            text="No file selected",
            size_hint_y=None,
            height=dp(30),
            color=TEXT_SECONDARY,
            font_size=dp(13),
            halign="left",
        )
        self.file_label.bind(size=self.file_label.setter("text_size"))
        self.layout.add_widget(self.file_label)

        # Spacer
        self.layout.add_widget(Label(size_hint_y=1))

        # Instructions
        self.layout.add_widget(Label(
            text="Tap an episode in the Library to play it.\n"
                 "Your device's video player will open automatically.",
            size_hint_y=None,
            height=dp(50),
            color=TEXT_SECONDARY,
            font_size=dp(12),
            halign="center",
        ))

        # Buttons
        btn_row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))

        self.open_btn = Button(
            text="Open in Player",
            background_color=SUCCESS,
            color=TEXT_PRIMARY,
            font_size=dp(14),
        )
        self.open_btn.bind(on_press=lambda x: self._open_native_player())
        btn_row.add_widget(self.open_btn)

        self.back_btn = Button(
            text="Back to Library",
            background_color=BG_CARD,
            color=TEXT_PRIMARY,
            font_size=dp(14),
        )
        self.back_btn.bind(on_press=lambda x: self._go_back())
        btn_row.add_widget(self.back_btn)

        self.layout.add_widget(btn_row)
        self.add_widget(self.layout)

    def play_file(self, file_path, title=""):
        self.current_file = file_path
        self.current_title = title or os.path.basename(file_path)
        self.file_label.text = self.current_title
        self._open_native_player()

    def _open_native_player(self):
        if not self.current_file or not os.path.exists(self.current_file):
            self.file_label.text = "File not found"
            return

        try:
            from kivy.utils import platform
            if platform == "android":
                from jnius import autoclass
                Intent = autoclass("android.content.Intent")
                Uri = autoclass("android.net.Uri")
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                activity = PythonActivity.mActivity

                intent = Intent(Intent.ACTION_VIEW)
                file_uri = Uri.parse("file:///" + self.current_file)
                intent.setDataAndType(file_uri, "video/*")
                intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                activity.startActivity(intent)
            else:
                # Desktop fallback
                import subprocess
                import sys
                if sys.platform == "win32":
                    os.startfile(self.current_file)
                elif sys.platform == "darwin":
                    subprocess.call(["open", self.current_file])
                else:
                    subprocess.call(["xdg-open", self.current_file])
        except Exception as e:
            self.file_label.text = f"Error: {str(e)[:60]}"

    def _go_back(self):
        self.manager.current = "library"

    def on_leave(self):
        pass
