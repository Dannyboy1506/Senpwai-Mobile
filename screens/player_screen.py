import os
import time
import threading
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.slider import Slider
from kivy.uix.widget import Widget
from kivy.properties import StringProperty, NumericProperty, BooleanProperty
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle

from main import BG_PRIMARY, BG_SECONDARY, BG_CARD, ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, dp


class VideoPlayerWidget(Widget):
    """ffpyplayer video renderer"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.player = None
        self._texture = None
        self._rect = None

    def set_player(self, player):
        self.player = player

    def on_size(self, *args):
        self._update_texture_size()

    def _update_texture_size(self):
        if self.player and hasattr(self.player, 'get_size'):
            w, h = self.player.get_size()
            if w and h:
                self.canvas.before.clear()
                with self.canvas.before:
                    Color(0, 0, 0, 1)
                    self._rect = Rectangle(pos=self.pos, size=self.size)

    def update_frame(self, frame, pts):
        if frame is None:
            return
        img, t = frame
        if img is None:
            return
        size = img.get_size()
        if size[0] == 0 or size[1] == 0:
            return
        try:
            from kivy.graphics.texture import Texture
            if self._texture is None or self._texture.size != size:
                self._texture = Texture.create(size=size, colorfmt='rgba')
                self._texture.flip_vertical()
            self._texture.blit_buffer(img.to_bytearray(), colorfmt='rgba')
            self.canvas.clear()
            with self.canvas:
                Color(1, 1, 1, 1)
                self._rect = Rectangle(texture=self._texture, pos=self.pos, size=self.size)
        except Exception:
            pass


class PlayerScreen(Screen):
    current_file = StringProperty("")
    current_title = StringProperty("")
    is_playing = BooleanProperty(False)
    duration = NumericProperty(0)
    position = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.player = None
        self._update_clock = None
        self._layout = BoxLayout(orientation="vertical", padding=0, spacing=0)

        # Video area
        self.video_widget = VideoPlayerWidget()
        self.video_area = BoxLayout()
        self.video_area.add_widget(self.video_widget)
        self._layout.add_widget(self.video_area)

        # Controls overlay
        self.controls = BoxLayout(
            orientation="vertical",
            padding=[15, 10],
            spacing=8,
            size_hint_y=None,
            height=dp(120),
        )

        # Title
        self.title_label = Label(
            text="",
            size_hint_y=None,
            height=25,
            color=TEXT_PRIMARY,
            font_size=14,
            halign="left",
        )
        self.controls.add_widget(self.title_label)

        # Seek bar
        seek_row = BoxLayout(size_hint_y=None, height=30, spacing=10)
        self.time_label = Label(
            text="0:00 / 0:00",
            size_hint_x=None,
            width=100,
            color=TEXT_SECONDARY,
            font_size=11,
        )
        seek_row.add_widget(self.time_label)

        self.seek_slider = Slider(min=0, max=100, value=0, size_hint_x=1)
        self.seek_slider.bind(on_touch_down=self._on_seek_start, on_touch_up=self._on_seek_end)
        seek_row.add_widget(self.seek_slider)
        self.controls.add_widget(seek_row)

        # Playback buttons
        btn_row = BoxLayout(size_hint_y=None, height=40, spacing=15)

        self.prev_btn = Button(
            text="⏮",
            size_hint_x=None,
            width=50,
            background_color=BG_CARD,
            color=TEXT_PRIMARY,
            font_size=20,
        )
        self.prev_btn.bind(on_press=lambda x: self.seek_to(0))
        btn_row.add_widget(self.prev_btn)

        self.play_btn = Button(
            text="▶",
            size_hint_x=None,
            width=60,
            background_color=ACCENT,
            color=TEXT_PRIMARY,
            font_size=22,
        )
        self.play_btn.bind(on_press=lambda x: self.toggle_play())
        btn_row.add_widget(self.play_btn)

        self.stop_btn = Button(
            text="⏹",
            size_hint_x=None,
            width=50,
            background_color=BG_CARD,
            color=TEXT_PRIMARY,
            font_size=20,
        )
        self.stop_btn.bind(on_press=lambda x: self.stop())
        btn_row.add_widget(self.stop_btn)

        self.back_btn = Button(
            text="← Back",
            size_hint_x=None,
            width=70,
            background_color=BG_CARD,
            color=TEXT_PRIMARY,
            font_size=13,
        )
        self.back_btn.bind(on_press=lambda x: self._go_back())
        btn_row.add_widget(self.back_btn)

        self.controls.add_widget(btn_row)
        self._layout.add_widget(self.controls)
        self.add_widget(self._layout)

    def play_file(self, file_path, title=""):
        self.current_file = file_path
        self.current_title = title or os.path.basename(file_path)
        self.title_label.text = self.current_title

        try:
            from ffpyplayer.player import MediaPlayer
            self.stop()
            self.player = MediaPlayer(file_path, loglevel="quiet")
            self.video_widget.set_player(self.player)
            self.is_playing = True
            self.play_btn.text = "⏸"
            self._update_clock = Clock.schedule_interval(self._update, 0.1)
        except Exception as e:
            self.title_label.text = f"Error: {str(e)[:50]}"

    def toggle_play(self):
        if not self.player:
            return
        if self.is_playing:
            self.player.toggle_pause()
            self.is_playing = False
            self.play_btn.text = "▶"
        else:
            self.player.toggle_pause()
            self.is_playing = True
            self.play_btn.text = "⏸"

    def stop(self):
        if self._update_clock:
            self._update_clock.cancel()
            self._update_clock = None
        if self.player:
            self.player.close_player()
            self.player = None
        self.is_playing = False
        self.play_btn.text = "▶"
        self.position = 0
        self.duration = 0
        self.seek_slider.value = 0

    def seek_to(self, pos):
        if self.player and self.duration > 0:
            self.player.seek(pos, relative=False)

    def _on_seek_start(self, widget, touch):
        if self._update_clock:
            self._update_clock.cancel()

    def _on_seek_end(self, widget, touch):
        if self.player and self.duration > 0:
            pos = (self.seek_slider.value / 100.0) * self.duration
            self.player.seek(pos, relative=False)
        self._update_clock = Clock.schedule_interval(self._update, 0.1)

    def _update(self, dt):
        if not self.player:
            return
        frame, val = self.player.get_frame()
        if val != "eof" and frame is not None and val is not None:
            img, pts = frame
            if img:
                self.video_widget.update_frame(frame, pts)
            if self.duration == 0:
                dur = self.player.get_metadata().get("duration", 0)
                if dur:
                    self.duration = float(dur)
            pos = float(val)
            self.position = pos
            if self.duration > 0:
                self.seek_slider.value = (pos / self.duration) * 100
                self.time_label.text = f"{self._fmt(pos)} / {self._fmt(self.duration)}"
        elif val == "eof":
            self.is_playing = False
            self.play_btn.text = "▶"

    def _fmt(self, seconds):
        m = int(seconds) // 60
        s = int(seconds) % 60
        return f"{m}:{s:02d}"

    def _go_back(self):
        self.stop()
        self.manager.current = "library"

    def on_leave(self):
        self.stop()
