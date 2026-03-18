import json
import os
import shutil
import subprocess
import atexit
from datetime import datetime


class SidMusicManager:
    def __init__(self, root_dir, memory_dir, sid_dir, player_cmd="sidplayfp"):
        self.root_dir = root_dir
        self.memory_dir = memory_dir
        self.sid_dir = sid_dir
        self.player_cmd = player_cmd

        self.playlist_path = os.path.join(self.memory_dir, "sid_playlist.txt")
        self.state_path = os.path.join(self.memory_dir, "sid_state.json")

        self.playlist = []
        self.current_index = -1
        self.current_track = ""
        self.proc = None
        self.player_path = self._resolve_player_path()
        self.available = self.player_path is not None
        atexit.register(self.stop)

    def _resolve_player_path(self):
        candidates = [
            self.player_cmd,
            f"{self.player_cmd}.exe",
            os.path.join(self.root_dir, f"{self.player_cmd}.exe"),
            os.path.join(self.root_dir, self.player_cmd),
            os.path.join(self.sid_dir, f"{self.player_cmd}.exe"),
            os.path.join(self.sid_dir, self.player_cmd),
        ]
        for item in candidates:
            if os.path.isfile(item):
                return item
            resolved = shutil.which(item)
            if resolved:
                return resolved
        return None

    def _read_text_lines(self, path):
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                return [x.strip() for x in f.readlines() if x.strip()]
        except Exception:
            return []

    def _write_text_lines(self, path, lines):
        with open(path, "w", encoding="utf-8") as f:
            for item in lines:
                f.write(f"{item}\n")

    def _load_state(self):
        default = {"last_track": "", "last_index": -1}
        if not os.path.exists(self.state_path):
            return default
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                default.update(data)
            return default
        except Exception:
            return default

    def _save_state(self, track_name, index):
        payload = {
            "last_track": track_name,
            "last_index": int(index),
            "updated_at": datetime.utcnow().isoformat(),
        }
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def rebuild_playlist(self):
        existing = self._read_text_lines(self.playlist_path)
        files = [
            x
            for x in os.listdir(self.sid_dir)
            if os.path.isfile(os.path.join(self.sid_dir, x)) and x.lower().endswith(".sid")
        ]
        files_sorted = sorted(files, key=lambda x: x.lower())

        preserved = [x for x in existing if x in files_sorted]
        new_items = [x for x in files_sorted if x not in existing]
        merged = preserved + sorted(new_items, key=lambda x: x.lower())

        self.playlist = merged
        self._write_text_lines(self.playlist_path, merged)

    def start(self):
        self.rebuild_playlist()
        if not self.available or not self.playlist:
            return False

        state = self._load_state()
        next_index = 0
        last_track = state.get("last_track", "")
        if last_track in self.playlist:
            next_index = (self.playlist.index(last_track) + 1) % len(self.playlist)
        else:
            idx = int(state.get("last_index", -1))
            if 0 <= idx < len(self.playlist):
                next_index = (idx + 1) % len(self.playlist)

        return self.play_index(next_index)

    def play_index(self, index):
        if not self.available or not self.playlist:
            return False
        index = index % len(self.playlist)
        path = os.path.join(self.sid_dir, self.playlist[index])
        if not os.path.exists(path):
            return False

        self.stop()
        try:
            creation_flags = 0
            startup_info = None
            if os.name == "nt":
                creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                startup_info = subprocess.STARTUPINFO()
                startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            self.proc = subprocess.Popen(
                [self.player_path, "-q", "-os", path],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creation_flags,
                startupinfo=startup_info,
            )
            self.current_index = index
            self.current_track = self.playlist[index]
            self._save_state(self.current_track, self.current_index)
            return True
        except Exception:
            self.proc = None
            return False

    def update(self):
        if not self.available or not self.playlist:
            return
        if self.proc is None:
            return
        if self.proc.poll() is not None:
            self.play_index((self.current_index + 1) % len(self.playlist))

    def stop(self):
        if self.proc is None:
            return
        pid = self.proc.pid
        try:
            if self.proc.poll() is None:
                self.proc.terminate()
                self.proc.wait(timeout=1.5)
        except Exception:
            pass
        try:
            if self.proc.poll() is None:
                self.proc.kill()
                self.proc.wait(timeout=1.0)
        except Exception:
            pass
        # Some SID players may create helper/child processes; ensure full tree is closed on Windows.
        if os.name == "nt" and pid:
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except Exception:
                pass
        self.proc = None
