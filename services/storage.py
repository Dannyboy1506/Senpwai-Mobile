import os
import json
import shutil

IBYTES_TO_MBS_DIVISOR = 1024 * 1024


class StorageManager:
    def __init__(self, download_folder):
        self.download_folder = download_folder

    def ensure_download_dir(self):
        try:
            os.makedirs(self.download_folder, exist_ok=True)
        except Exception:
            pass

    def get_storage_info(self):
        try:
            total, used, free = shutil.disk_usage(self.download_folder)
            return {"total": total, "used": used, "free": free}
        except Exception:
            return {"total": 0, "used": 0, "free": 0}

    def list_anime_folders(self):
        if not os.path.exists(self.download_folder):
            return []
        results = []
        try:
            for entry in sorted(os.listdir(self.download_folder)):
                full_path = os.path.join(self.download_folder, entry)
                if os.path.isdir(full_path):
                    episodes = []
                    poster = None
                    total_size = 0
                    try:
                        for f in sorted(os.listdir(full_path)):
                            fp = os.path.join(full_path, f)
                            if os.path.isfile(fp):
                                if f.endswith((".mp4", ".mkv", ".avi", ".ts")):
                                    try:
                                        size = os.path.getsize(fp)
                                    except OSError:
                                        size = 0
                                    episodes.append({"name": f, "path": fp, "size": size})
                                    total_size += size
                                elif f.endswith((".jpg", ".png", ".webp")):
                                    poster = fp
                    except OSError:
                        continue
                    results.append({
                        "name": entry, "path": full_path, "episodes": episodes,
                        "poster": poster, "total_size": total_size,
                        "episode_count": len(episodes),
                    })
        except OSError:
            pass
        return results

    def delete_episode(self, episode_path):
        try:
            os.remove(episode_path)
            return True
        except Exception:
            return False

    def delete_anime_folder(self, folder_path):
        try:
            shutil.rmtree(folder_path)
            return True
        except Exception:
            return False

    def scan_partials(self):
        partials = []
        if not os.path.exists(self.download_folder):
            return partials
        try:
            for root, _, files in os.walk(self.download_folder):
                for file in files:
                    if "[Downloading]" in file:
                        meta_path = os.path.join(root, file + ".json")
                        if os.path.exists(meta_path):
                            try:
                                with open(meta_path, encoding="utf-8") as f:
                                    meta = json.load(f)
                                temp_path = os.path.join(root, file)
                                try:
                                    current_size = os.path.getsize(temp_path)
                                except OSError:
                                    current_size = 0
                                total_size = meta.get("total_size", 0)
                                pct = (current_size / total_size * 100) if total_size > 0 else 0
                                partials.append({
                                    "temp_path": temp_path, "meta": meta, "folder": root,
                                    "current_size": current_size, "total_size": total_size,
                                    "pct": pct, "title": meta.get("title", file),
                                })
                            except Exception:
                                pass
        except OSError:
            pass
        return partials

    def cleanup_orphans(self):
        if not os.path.exists(self.download_folder):
            return
        try:
            for root, _, files in os.walk(self.download_folder):
                for file in files:
                    if "[Downloading]" in file:
                        meta_path = os.path.join(root, file + ".json")
                        if not os.path.exists(meta_path):
                            try:
                                os.remove(os.path.join(root, file))
                            except Exception:
                                pass
        except OSError:
            pass

    def format_size(self, size_bytes):
        if size_bytes < 0:
            return "0B"
        if size_bytes < 1024:
            return f"{size_bytes}B"
        elif size_bytes < IBYTES_TO_MBS_DIVISOR:
            return f"{size_bytes / 1024:.1f}KB"
        elif size_bytes < IBYTES_TO_MBS_DIVISOR * 1024:
            return f"{size_bytes / IBYTES_TO_MBS_DIVISOR:.1f}MB"
        else:
            return f"{size_bytes / (IBYTES_TO_MBS_DIVISOR * 1024):.2f}GB"
