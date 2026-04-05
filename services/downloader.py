import os
import time
import threading
from kivy.clock import Clock

from services.scraper import Download, IBYTES_TO_MBS_DIVISOR, SpeedTracker


class DownloadTask:
    STATUS_PENDING = "pending"
    STATUS_DOWNLOADING = "downloading"
    STATUS_PAUSED = "paused"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"

    def __init__(self, url, title, folder, total_size, is_hls=False, file_ext=".mp4"):
        self.url = url
        self.title = title
        self.folder = folder
        self.total_size = total_size
        self.is_hls = is_hls
        self.file_ext = file_ext
        self.downloaded = 0
        self.status = self.STATUS_PENDING
        self.speed = 0
        self.eta = 0
        self.error = ""
        self.download_instance = None
        self.thread = None
        self._speed_tracker = SpeedTracker()
        self._lock = threading.Lock()
        self._last_progress_time = 0

    def progress_callback(self, added_bytes):
        with self._lock:
            self.downloaded += added_bytes
            self._speed_tracker.update(added_bytes)
            self.speed = self._speed_tracker.speed()
            self.eta = self._speed_tracker.eta(self.total_size)
        now = time.time()
        if now - self._last_progress_time >= 0.5:
            self._last_progress_time = now

    def get_progress(self):
        if self.total_size <= 0:
            return 0
        return min(self.downloaded / self.total_size * 100, 100)

    def get_downloaded_str(self):
        return f"{self.downloaded / IBYTES_TO_MBS_DIVISOR:.1f}MB / {self.total_size / IBYTES_TO_MBS_DIVISOR:.1f}MB"

    def get_speed_str(self):
        return SpeedTracker.fmt_speed(self.speed)

    def get_eta_str(self):
        return SpeedTracker.fmt_eta(self.eta)


class DownloadManager:
    def __init__(self, app):
        self.app = app
        self.active_downloads = []
        self.completed_downloads = []
        self.failed_downloads = []
        self.queue = []
        self.lock = threading.Lock()
        self.shutdown_event = threading.Event()
        self._callbacks = []

    def add_download(self, url, title, folder, total_size, is_hls=False, file_ext=".mp4"):
        task = DownloadTask(url, title, folder, total_size, is_hls, file_ext)
        with self.lock:
            self.queue.append(task)
            self.active_downloads.append(task)
        self._notify("added", task)
        self._process_queue()

    def _process_queue(self):
        max_sim = self.app.config.max_simultaneous_downloads
        with self.lock:
            running = sum(1 for t in self.active_downloads if t.status == DownloadTask.STATUS_DOWNLOADING)
            pending = [t for t in self.queue if t.status == DownloadTask.STATUS_PENDING]

        while running < max_sim and pending:
            task = pending.pop(0)
            self._start_download(task)
            running += 1

    def _start_download(self, task):
        task.status = DownloadTask.STATUS_DOWNLOADING
        task.thread = threading.Thread(target=self._download_worker, args=(task,), daemon=True)
        task.thread.start()

    def _download_worker(self, task):
        try:
            download = Download(
                task.url, task.title, task.folder, task.total_size,
                task.progress_callback, file_extension=task.file_ext,
                is_hls_download=task.is_hls,
            )
            task.download_instance = download
            success = download.start_download()

            def _on_done():
                with self.lock:
                    if success:
                        task.status = DownloadTask.STATUS_COMPLETED
                        if task in self.active_downloads:
                            self.active_downloads.remove(task)
                        self.completed_downloads.append(task)
                        try:
                            self.app.show_notification("Download Complete", task.title)
                        except Exception:
                            pass
                        self._notify("completed", task)
                    elif download.cancelled:
                        task.status = DownloadTask.STATUS_CANCELLED
                        task.error = "Cancelled"
                        self._notify("cancelled", task)
                    else:
                        task.status = DownloadTask.STATUS_FAILED
                        task.error = download._last_error or "Unknown error"
                        if task in self.active_downloads:
                            self.active_downloads.remove(task)
                        self.failed_downloads.append(task)
                        self._notify("failed", task)
                self._process_queue()

            Clock.schedule_once(lambda dt: _on_done())

        except Exception as e:
            def _on_error():
                task.status = DownloadTask.STATUS_FAILED
                task.error = str(e)[:100]
                with self.lock:
                    if task in self.active_downloads:
                        self.active_downloads.remove(task)
                    self.failed_downloads.append(task)
                self._notify("failed", task)
                self._process_queue()

            Clock.schedule_once(lambda dt: _on_error())

    def pause_download(self, task):
        if task.download_instance:
            task.download_instance.pause_or_resume()
            if task.download_instance.resume.is_set():
                task.status = DownloadTask.STATUS_DOWNLOADING
            else:
                task.status = DownloadTask.STATUS_PAUSED
            self._notify("status_change", task)

    def cancel_download(self, task):
        if task.download_instance:
            task.download_instance.cancel()
        task.status = DownloadTask.STATUS_CANCELLED
        self._notify("cancelled", task)

    def retry_download(self, task):
        with self.lock:
            if task in self.failed_downloads:
                self.failed_downloads.remove(task)
            task.status = DownloadTask.STATUS_PENDING
            task.error = ""
            task.speed = 0
            task.eta = 0
            task._speed_tracker = SpeedTracker()
            task.downloaded = 0
            if task not in self.queue:
                self.queue.append(task)
        self._process_queue()

    def scan_and_resume(self):
        partials = self.app.storage.scan_partials()
        for p in partials:
            meta = p["meta"]
            url = meta.get("url")
            if not url:
                continue
            title = meta.get("title", "Unknown")
            folder = p["folder"]
            total_size = meta.get("total_size", 0)
            file_ext = ".mp4"
            final_path = meta.get("final_path", "")
            if final_path:
                _, file_ext = os.path.splitext(final_path)
                if not file_ext:
                    file_ext = ".mp4"

            task = DownloadTask(url, title, folder, total_size, file_ext=file_ext)
            task.downloaded = p["current_size"]
            with self.lock:
                self.queue.append(task)
                self.active_downloads.append(task)
        self._process_queue()

    def register_callback(self, callback):
        self._callbacks.append(callback)

    def _notify(self, event_type, task):
        for cb in self._callbacks:
            try:
                cb(event_type, task)
            except Exception:
                pass

    def shutdown(self):
        self.shutdown_event.set()
        with self.lock:
            for task in self.active_downloads:
                if task.download_instance:
                    task.download_instance.cancel()
