import re
import os
import time
import random
import json
import threading
from typing import cast
from collections import deque
import requests

IBYTES_TO_MBS_DIVISOR = 1024 * 1024

PAHE_DOMAIN = "animepahe.com"
GOGO_DOMAIN = "gogoanime.consumet.org"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

QUALITY_REGEX = re.compile(r"\b(\d{3,4})p\b")
KWIK_PAGE_RE = re.compile(r'action=\"([^\"]+)\"')
PARAM_RE = re.compile(r"va\s*=\s*(\d+);")


class NoResourceLengthException(Exception):
    def __init__(self, url):
        super().__init__(f'No Content-Length from "{url}"')


def strip_title(title, all=False, exclude=""):
    from string import ascii_letters, digits, printable
    if all:
        allowed = set(ascii_letters + digits + exclude)
    else:
        allowed = set(printable) - set('\\/:*?"<>|')
        title = title.replace(":", " -")
    return "".join(c for c in title.rstrip(".") if c in allowed)[:255].rstrip()


class SpeedTracker:
    """Deque-based sliding window speed tracker with ETA."""
    def __init__(self, window=5):
        self.total_bytes = 0
        self.history = deque(maxlen=window)

    def update(self, chunk):
        now = time.time()
        self.total_bytes += chunk
        self.history.append((now, self.total_bytes))

    def speed(self):
        if len(self.history) < 2:
            return 0
        t0, b0 = self.history[0]
        t1, b1 = self.history[-1]
        return (b1 - b0) / (t1 - t0) if t1 != t0 else 0

    def eta(self, total):
        s = self.speed()
        if s == 0:
            return float("inf")
        return (total - self.total_bytes) / s

    @staticmethod
    def fmt_speed(s):
        if s < 1024:
            return f"{s:.0f}B/s"
        elif s < IBYTES_TO_MBS_DIVISOR:
            return f"{s / 1024:.1f}KB/s"
        return f"{s / IBYTES_TO_MBS_DIVISOR:.1f}MB/s"

    @staticmethod
    def fmt_eta(sec):
        if sec == float("inf"):
            return "--:--"
        m, s = divmod(int(sec), 60)
        h, m = divmod(m, 60)
        return f"{h:02}:{m:02}:{s:02}" if h else f"{m:02}:{s:02}"


class Client:
    def __init__(self):
        self.session = requests.Session()
        self._refresh_ua()
        self._cookies = {}

    def _refresh_ua(self):
        self.session.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": f"https://{PAHE_DOMAIN}/",
        })

    def _retry_get(self, url, **kwargs):
        for attempt in range(5):
            try:
                resp = self.session.get(url, **kwargs)
                resp.raise_for_status()
                return resp
            except requests.exceptions.RequestException as e:
                if attempt == 4:
                    raise
                time.sleep(2 ** attempt + random.uniform(0, 1))

    def get(self, url, stream=False, headers=None, timeout=None, allow_redirects=False):
        h = dict(self.session.headers)
        if headers:
            h.update(headers)
        return self._retry_get(url, stream=stream, headers=h, timeout=timeout,
                               allow_redirects=allow_redirects, cookies=self._cookies)

    def post(self, url, data=None, json_data=None, headers=None, timeout=None):
        h = dict(self.session.headers)
        if headers:
            h.update(headers)
        for attempt in range(5):
            try:
                resp = self.session.post(url, data=data, json=json_data, headers=h,
                                        timeout=timeout, cookies=self._cookies)
                resp.raise_for_status()
                return resp
            except requests.exceptions.RequestException as e:
                if attempt == 4:
                    raise
                time.sleep(2 ** attempt + random.uniform(0, 1))


CLIENT = Client()


def search_pahe(query):
    url = f"https://{PAHE_DOMAIN}/api?m=search&q={requests.utils.quote(query)}"
    resp = CLIENT.get(url, allow_redirects=True, timeout=15)
    data = resp.json()
    results = []
    for item in data.get("data", []):
        results.append({
            "title": item.get("title", ""),
            "episodes": item.get("episodes", "?"),
            "year": item.get("year", ""),
            "id": item.get("id", ""),
            "session": item.get("session", ""),
        })
    return results


def search_gogo(query):
    url = f"https://ajax.gogocdn.net/site/loadAjaxSearch?keyword={requests.utils.quote(query)}"
    resp = CLIENT.get(url, allow_redirects=True, timeout=15)
    data = resp.json()
    results = []
    if data.get("status"):
        for item in data.get("content", []):
            name = item.get("name", "")
            name = re.sub(r'<[^>]+>', '', name)
            link = item.get("link", "")
            anime_id = link.split("/")[-1] if link else ""
            results.append({
                "title": name,
                "episodes": "?",
                "year": "",
                "id": anime_id,
                "link": f"https://gogoanime.consumet.org{link}",
            })
    return results


def get_pahe_episodes(anime_id, page=1):
    url = f"https://{PAHE_DOMAIN}/api?m=release&id={anime_id}&sort=episode_asc&page={page}"
    resp = CLIENT.get(url, timeout=15)
    data = resp.json()
    episodes = data.get("data", [])
    total = data.get("total", 0)
    current_page = page
    while len(episodes) < total:
        current_page += 1
        url2 = url.replace(f"page={page}", f"page={current_page}")
        resp2 = CLIENT.get(url2, timeout=15)
        episodes.extend(resp2.json().get("data", []))
    return episodes


def get_pahe_download_links(anime_id, session, quality, sub_or_dub):
    url = f"https://{PAHE_DOMAIN}/api?m=links&id={anime_id}&p=download&session={session}"
    resp = CLIENT.get(url, timeout=15)
    data = resp.json()
    links = data.get("data", [])

    filtered = []
    for link in links:
        audio = link.get("audio", "eng")
        if sub_or_dub == "dub" and audio == "jpn":
            continue
        if sub_or_dub == "sub" and audio == "eng" and len(links) > 1:
            continue

        res = str(link.get("resolution", ""))
        match = QUALITY_REGEX.search(res)
        if match and match.group(1) == quality.replace("p", ""):
            kwik_url = link.get("url", "")
            size_mb = link.get("size", 0)
            filtered.append({"kwik_url": kwik_url, "size": size_mb * IBYTES_TO_MBS_DIVISOR, "audio": audio})

    if not filtered:
        for link in links:
            audio = link.get("audio", "eng")
            if sub_or_dub == "dub" and audio == "jpn":
                continue
            if sub_or_dub == "sub" and audio == "eng" and len(links) > 1:
                continue
            kwik_url = link.get("url", "")
            size_mb = link.get("size", 0)
            filtered.append({"kwik_url": kwik_url, "size": size_mb * IBYTES_TO_MBS_DIVISOR, "audio": audio})

    return filtered


def decrypt_kwik(kwik_url):
    try:
        resp = CLIENT.get(kwik_url, allow_redirects=True, timeout=15)
        html = resp.text

        match = KWIK_PAGE_RE.search(html)
        if not match:
            return None
        action_url = match.group(1)

        match2 = PARAM_RE.search(html)
        if not match2:
            resp2 = CLIENT.get(action_url, allow_redirects=True, timeout=15,
                              headers={"Referer": kwik_url})
            return resp2.url

        va = int(match2.group(1))
        form_data = {"_token": "", "d": va}
        resp3 = CLIENT.post(action_url, data=form_data, timeout=15,
                           headers={"Referer": kwik_url})
        return resp3.url
    except Exception:
        return None


def get_gogo_episodes(anime_id, ep_from, ep_to):
    episodes = []
    for ep in range(ep_from, ep_to + 1):
        episodes.append({
            "ep_num": ep,
            "url": f"https://gogoanime.consumet.org/{anime_id}-episode-{ep}",
        })
    return episodes


def get_gogo_download_links(episode_url, quality):
    ep_id = episode_url.split("/")[-1]
    api_url = f"https://api.consumet.org/anime/gogoanime/watch/{ep_id}"
    resp = CLIENT.get(api_url, timeout=15)
    data = resp.json()
    sources = data.get("sources", [])

    for src in sources:
        url = src.get("url", "")
        is_m3u8 = src.get("isM3U8", False)
        if is_m3u8:
            return {"is_hls": True, "url": url, "quality": quality}

    for src in sources:
        url = src.get("url", "")
        if url and not src.get("isM3U8", False):
            return {"is_hls": False, "url": url, "quality": quality}

    return None


def open_url_in_browser(url):
    """Open a URL in the device's default browser or show a picker."""
    try:
        from kivy.utils import platform
        if platform == "android":
            from android.runnable import run_on_ui_thread
            from jnius import autoclass

            @run_on_ui_thread
            def _open():
                Intent = autoclass("android.content.Intent")
                Uri = autoclass("android.net.Uri")
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                activity = PythonActivity.mActivity
                intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                chooser = Intent.createChooser(intent, "Open with...")
                activity.startActivity(chooser)

            _open()
            return True
        else:
            import webbrowser
            webbrowser.open(url)
            return True
    except Exception:
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:
            pass
        return True


class ProgressFunction:
    def __init__(self):
        from threading import Event
        self.resume = Event()
        self.resume.set()
        self.cancelled = False

    def pause_or_resume(self):
        if self.resume.is_set():
            self.resume.clear()
        else:
            self.resume.set()

    def cancel(self):
        if self.resume.is_set():
            self.cancelled = True


class Download(ProgressFunction):
    """Browser-grade downloader with crash-proof resume, parallel IDM, speed tracking, ETA."""

    DEFAULT_CHUNK_SIZE = IBYTES_TO_MBS_DIVISOR * 4
    DEFAULT_TIMEOUT_TIERS = [((15, 30), 3), ((30, 60), 3)]
    RETRY_DELAY = 2
    MAX_PARALLEL_THREADS = 4
    DEFAULT_PART_SIZE = 5 * IBYTES_TO_MBS_DIVISOR
    PROGRESS_THROTTLE = 0.5

    def __init__(self, link_or_segment_urls, episode_title, download_folder_path,
                 download_size=None, progress_update_callback=lambda _: None,
                 file_extension=".mp4", is_hls_download=False,
                 timeout_tiers=None, max_part_size=0) -> None:
        super().__init__()
        self.link_or_segment_urls = link_or_segment_urls
        self.episode_title = episode_title
        self.download_folder_path = download_folder_path
        self.download_size = download_size
        self.progress_update_callback = progress_update_callback
        self.is_hls_download = is_hls_download
        self.timeout_tiers = timeout_tiers or self.DEFAULT_TIMEOUT_TIERS
        self.max_part_size = max_part_size

        file_title = f"{strip_title(self.episode_title)}{file_extension}"
        self.file_path = os.path.join(self.download_folder_path, file_title)
        ext = ".ts" if is_hls_download else file_extension

        temp_file_title = f"{strip_title(self.episode_title)} [Downloading]{ext}"
        self.temp_path = os.path.join(self.download_folder_path, temp_file_title)
        self.meta_path = self.temp_path + ".json"
        self._last_error = ""
        self._response_buffer = None
        self._speed_tracker = SpeedTracker()
        self._last_progress_time = 0
        self._total_downloaded = 0
        self._lock = threading.Lock()

    @staticmethod
    def get_total_download_size(url):
        response = requests.head(url, allow_redirects=True, timeout=30)
        size = response.headers.get("Content-Length")
        if size is None:
            raise NoResourceLengthException(url)
        return int(size), response.url

    def _save_meta(self, **extra):
        try:
            meta = {
                "url": self.link_or_segment_urls if isinstance(self.link_or_segment_urls, str) else None,
                "title": self.episode_title,
                "final_path": self.file_path,
                "temp_path": self.temp_path,
                "total_size": self.download_size or 0,
                "is_hls": self.is_hls_download,
                "timestamp": time.time(),
            }
            meta.update(extra)
            with open(self.meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)
        except Exception:
            pass

    def _load_meta(self):
        if not os.path.exists(self.meta_path):
            return None
        try:
            with open(self.meta_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _clean_meta(self):
        try:
            os.remove(self.meta_path)
        except Exception:
            pass

    def _classify_error(self, e):
        msg = str(e).lower()
        if "timeout" in msg or isinstance(e, TimeoutError):
            return "timeout"
        if "ssl" in msg or "certificate" in msg:
            return "ssl"
        if "connection" in msg or "reset" in msg or "refused" in msg:
            return "connection"
        if "resolve" in msg or "getaddrinfo" in msg:
            return "dns"
        return "unknown"

    def _retry_with_tiers(self, callback):
        for tier_idx, ((conn_timeout, read_timeout), max_retries) in enumerate(self.timeout_tiers):
            for retry in range(max_retries + 1):
                if self.cancelled:
                    return False, "cancelled"
                try:
                    self._response_buffer = callback((conn_timeout, read_timeout))
                    self._response_buffer.raise_for_status()
                    cl = self._response_buffer.headers.get("Content-Length")
                    if cl is not None and int(cl) == 0:
                        raise Exception("Empty response body")
                    return True, ""
                except Exception as e:
                    err_type = self._classify_error(e)
                    self._last_error = f"[{err_type.upper()}] {str(e)[:80]}"
                    if retry < max_retries:
                        delay = self.RETRY_DELAY * (2 ** retry) + random.uniform(0, 1)
                        time.sleep(delay)
            if tier_idx < len(self.timeout_tiers) - 1:
                nc, nr = self.timeout_tiers[tier_idx + 1][0]
                self._last_error = f"timeout: increasing to {nc}s/{nr}s read..."
                time.sleep(self.RETRY_DELAY * 2)
        return False, self._last_error

    def _supports_range(self, url, resume_from):
        try:
            r = requests.get(url, stream=True,
                           headers={"Range": f"bytes={resume_from}-{resume_from}"},
                           timeout=30, allow_redirects=True)
            return r.status_code == 206
        except Exception:
            return False

    def _report_progress(self, added):
        with self._lock:
            self._total_downloaded += added
            self._speed_tracker.update(added)
        now = time.time()
        if now - self._last_progress_time >= self.PROGRESS_THROTTLE:
            self._last_progress_time = now
            self.progress_update_callback(added)

    def _single_download(self, resume_from):
        url = cast(str, self.link_or_segment_urls)
        if resume_from > 0 and not self._supports_range(url, resume_from):
            resume_from = 0
        if resume_from == 0 and os.path.exists(self.temp_path):
            try:
                os.remove(self.temp_path)
            except Exception:
                pass

        max_stream_retries = 20
        stream_retry = 0

        while stream_retry <= max_stream_retries:
            headers = {}
            current_size = os.path.getsize(self.temp_path) if os.path.exists(self.temp_path) else 0
            if current_size > 0:
                headers["Range"] = f"bytes={current_size}-"

            def fetch(timeout):
                return requests.get(url, stream=True, headers=headers, timeout=timeout)

            success, error = self._retry_with_tiers(fetch)
            if not success:
                return False

            mode = "ab" if current_size > 0 else "wb"
            save_counter = 0
            try:
                with open(self.temp_path, mode) as f:
                    for chunk in self._response_buffer.iter_content(chunk_size=self.DEFAULT_CHUNK_SIZE):
                        if self.cancelled:
                            return False
                        self.resume.wait()
                        if chunk:
                            f.write(chunk)
                            self._report_progress(len(chunk))
                            save_counter += 1
                            if save_counter % 10 == 0:
                                self._save_meta(downloaded_bytes=self._total_downloaded)
                return True
            except (requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                    requests.exceptions.ChunkedEncodingError,
                    ConnectionResetError,
                    OSError):
                stream_retry += 1
                self._save_meta(downloaded_bytes=self._total_downloaded)
                if stream_retry > max_stream_retries:
                    self._last_error = f"[NETWORK] Connection lost ({max_stream_retries} reconnect attempts failed)"
                    return False
                wait_time = min(2 ** stream_retry, 30) + random.uniform(0, 2)
                self._last_error = f"[NETWORK] Reconnecting in {wait_time:.0f}s ({stream_retry}/{max_stream_retries})"
                time.sleep(wait_time)
                continue

        return False

    def _parallel_download(self):
        url = cast(str, self.link_or_segment_urls)
        if not self._supports_range(url, 0):
            return False

        total_size = self.download_size or 0
        if total_size == 0:
            return False

        part_size = self.max_part_size if self.max_part_size > 0 else self.DEFAULT_PART_SIZE
        num_parts = min(
            max(1, (total_size + part_size - 1) // part_size),
            self.MAX_PARALLEL_THREADS,
        )
        if num_parts == 1:
            return self._single_download(0)

        meta = self._load_meta()
        parts = None
        if meta and "parts" in meta and meta.get("total_size") == total_size:
            parts = meta["parts"]
        else:
            parts = []
            for s in range(0, total_size, part_size):
                e = min(s + part_size - 1, total_size - 1)
                parts.append({"start": s, "end": e, "done": 0})
            self._save_meta(parts=parts)

        with open(self.temp_path, "wb") as f:
            f.truncate(total_size)

        session = requests.Session()
        session.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "*/*",
        })

        def worker(part_idx):
            p = parts[part_idx]
            cur = p["start"] + p["done"]
            end = p["end"]
            retries = 0
            max_retries = 20

            while cur <= end and retries < max_retries and not self.cancelled:
                try:
                    r = session.get(
                        url,
                        headers={"Range": f"bytes={cur}-{end}"},
                        stream=True,
                        timeout=30,
                    )
                    with open(self.temp_path, "r+b") as f:
                        f.seek(cur)
                        for chunk in r.iter_content(self.DEFAULT_CHUNK_SIZE):
                            if not chunk or self.cancelled:
                                break
                            f.write(chunk)
                            chunk_len = len(chunk)
                            cur += chunk_len
                            with self._lock:
                                p["done"] += chunk_len
                                self._report_progress(chunk_len)
                                if p["done"] % IBYTES_TO_MBS_DIVISOR == 0:
                                    self._save_meta(parts=parts)
                    return
                except (requests.exceptions.ConnectionError,
                        requests.exceptions.Timeout,
                        requests.exceptions.ChunkedEncodingError,
                        ConnectionResetError,
                        OSError):
                    retries += 1
                    if retries > max_retries:
                        return
                    wait_time = min(2 ** retries, 30) + random.uniform(0, 2)
                    time.sleep(wait_time)
                    cur = p["start"] + p["done"]

        for i in range(0, len(parts), self.MAX_PARALLEL_THREADS):
            batch = parts[i:i + self.MAX_PARALLEL_THREADS]
            threads = []
            for j in range(len(batch)):
                idx = i + j
                p = parts[idx]
                if p["done"] >= (p["end"] - p["start"] + 1):
                    continue
                t = threading.Thread(target=worker, args=(idx,))
                t.start()
                threads.append(t)
            for t in threads:
                t.join()
            if self.cancelled:
                return False

        if not all(p["done"] >= (p["end"] - p["start"] + 1) for p in parts):
            self._last_error = "[VALIDATION] Not all parts downloaded"
            return False

        return True

    def _download_hls(self):
        seg_urls = cast(list, self.link_or_segment_urls)
        meta = self._load_meta() or {}
        next_seg = meta.get("next_seg_idx", 0)

        with open(self.temp_path, "ab" if next_seg > 0 else "wb") as f:
            for i, seg in enumerate(seg_urls):
                if i < next_seg:
                    continue
                if self.cancelled:
                    self._save_meta(next_seg_idx=i)
                    return False
                self.resume.wait()
                try:
                    response = CLIENT.get(seg)
                    response.raise_for_status()
                    f.write(response.content)
                    self.progress_update_callback(1)
                    if (i + 1) % 5 == 0:
                        self._save_meta(next_seg_idx=i + 1)
                except Exception as e:
                    self._last_error = f"[{self._classify_error(e).upper()}] {str(e)[:80]}"
                    self._save_meta(next_seg_idx=i)
                    return False
        return True

    def _validate(self):
        if not os.path.exists(self.temp_path):
            self._last_error = "[VALIDATION] Temp file missing"
            return False
        if self.download_size is not None and not self.is_hls_download:
            actual = os.path.getsize(self.temp_path)
            if actual != self.download_size:
                self._last_error = f"[VALIDATION] Size mismatch: expected {self.download_size}, got {actual}"
                return False
        return True

    def start_download(self):
        if self.is_hls_download:
            success = self._download_hls()
        elif self.max_part_size > 0 and self.download_size and self.download_size >= self.DEFAULT_PART_SIZE:
            success = self._parallel_download()
            if not success and not self.cancelled:
                self.rm_temp_path()
                self._total_downloaded = 0
                self._speed_tracker = SpeedTracker()
                success = self._single_download(0)
        else:
            resume_from = 0
            if os.path.exists(self.temp_path):
                resume_from = os.path.getsize(self.temp_path)
                self._save_meta(downloaded_bytes=resume_from)
            success = self._single_download(resume_from)

        if self.cancelled or not success or not self._validate():
            return False

        try:
            if os.path.exists(self.file_path):
                os.remove(self.file_path)
        except Exception:
            pass

        try:
            os.rename(self.temp_path, self.file_path)
        except PermissionError:
            pass

        self._clean_meta()
        return True

    def rm_temp_path(self):
        import shutil
        try:
            if os.path.isdir(self.temp_path):
                shutil.rmtree(self.temp_path)
            elif os.path.exists(self.temp_path):
                os.remove(self.temp_path)
        except Exception:
            pass

    @property
    def speed(self):
        return self._speed_tracker.speed()

    @property
    def speed_str(self):
        return SpeedTracker.fmt_speed(self._speed_tracker.speed())

    @property
    def eta_str(self):
        return SpeedTracker.fmt_eta(self._speed_tracker.eta(self.download_size or 0))

    @property
    def total_downloaded(self):
        return self._total_downloaded
