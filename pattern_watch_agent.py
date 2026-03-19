import json
import os
import statistics
import time
from collections import Counter
from datetime import datetime


DEFAULT_STRATEGIES = [
    "safe_stack",
    "max_potential",
    "balance",
    "combo_hunter",
    "low_risk",
    "center_control",
    "edge_pressure",
    "lock_builder",
    "sum9_focus",
    "survival_mix",
]

DEFAULT_PROPOSAL_ENGINES = [
    "mutate_light",
    "mutate_aggressive",
    "risk_balancer",
    "combo_amplifier",
    "stability_guard",
]


class PatternWatchAgent:
    """Continuously analyzes all game logs independent of active gameplay."""

    def __init__(self, root_dir, log_dir, memory_dir):
        self.root_dir = root_dir
        self.log_dir = log_dir
        self.memory_dir = memory_dir
        self.gazi_dir = os.path.join(self.log_dir, "gazi")
        self.agent_log_path = os.path.join(self.gazi_dir, "pattern_watch_agent_log.jsonl")
        self.last_scan_at = 0.0
        self.scan_interval = 12.0
        self.last_signal = {}
        self.rolling_summary = {}

        os.makedirs(self.gazi_dir, exist_ok=True)
        os.makedirs(self.memory_dir, exist_ok=True)

    def _append_agent_log(self, event, payload):
        row = {
            "time": datetime.utcnow().isoformat(),
            "event": event,
            "payload": payload,
        }
        try:
            with open(self.agent_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def _candidate_dirs(self):
        dirs = []
        if os.path.isdir(self.log_dir):
            dirs.append(self.log_dir)
        dist_logs = os.path.join(self.root_dir, "dist", "logs")
        if os.path.isdir(dist_logs):
            dirs.append(dist_logs)
        return dirs

    def _iter_game_log_files(self):
        files = []
        for d in self._candidate_dirs():
            try:
                for name in os.listdir(d):
                    low = str(name).lower()
                    if not low.endswith(".jsonl"):
                        continue
                    if "gazi" in low or "breakpoint" in low or "pattern_watch" in low:
                        continue
                    files.append(os.path.join(d, name))
            except Exception:
                continue
        return sorted(set(files), key=lambda p: os.path.getmtime(p))

    def _read_recent_rows(self, max_files=18, max_lines=1200):
        files = self._iter_game_log_files()[-max_files:]
        rows = []
        for fp in files:
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                lines = lines[-max_lines:]
                for line in lines:
                    raw = line.strip()
                    if not raw:
                        continue
                    try:
                        item = json.loads(raw)
                    except Exception:
                        continue
                    rows.append(item)
            except Exception:
                continue
        return rows

    def _special_efficiency(self, rows):
        special = [x for x in rows if x.get("num") in ("J", "B", "L")]
        if not special:
            return 0.0
        good = 0
        for row in special:
            exploded = float(row.get("exploded_cells", 0) or 0)
            expl = float(row.get("explosions", 0) or 0)
            points = float(row.get("points", 0) or 0)
            if expl >= 1 or exploded >= 3 or points >= 9:
                good += 1
        return good / max(1, len(special))

    def _sum9_focus_ratio(self, rows):
        numeric = [x for x in rows if isinstance(x.get("num"), int)]
        if not numeric:
            return 0.0
        hit = 0
        for row in numeric:
            potential = float(row.get("potential_explosions", 0) or 0)
            if potential >= 1.0:
                hit += 1
        return hit / max(1, len(numeric))

    def _cluster_cols(self, rows):
        cols = []
        for row in rows:
            mv = row.get("move_decision") or {}
            c = mv.get("col")
            if isinstance(c, int):
                cols.append(c)
        if len(cols) <= 1:
            return 0.0, []
        near = 0
        for i in range(1, len(cols)):
            if abs(cols[i] - cols[i - 1]) <= 1:
                near += 1
        ratio = near / max(1, len(cols) - 1)
        top = [c for c, _ in Counter(cols).most_common(3)]
        return ratio, top

    def _future_plan_rate(self, rows, horizon=3):
        if not rows:
            return 0.0
        candidates = 0
        hits = 0
        for i, row in enumerate(rows):
            potential = float(row.get("potential_explosions", 0) or 0)
            if potential > 0:
                continue
            candidates += 1
            upper = min(len(rows), i + 1 + max(1, horizon))
            ok = False
            for j in range(i + 1, upper):
                nxt = rows[j]
                if float(nxt.get("explosions", 0) or 0) >= 1 or float(nxt.get("points", 0) or 0) >= 10:
                    ok = True
                    break
            if ok:
                hits += 1
        return hits / max(1, candidates)

    def analyze_all_logs(self, deep=False):
        rows = self._read_recent_rows(max_files=40 if deep else 18, max_lines=5000 if deep else 1200)
        human = [x for x in rows if x.get("player") == "Human"]
        robot = [x for x in rows if x.get("player") == "Robot"]

        h_points = statistics.fmean([float(x.get("points", 0) or 0) for x in human]) if human else 0.0
        r_points = statistics.fmean([float(x.get("points", 0) or 0) for x in robot]) if robot else 0.0
        h_expl = statistics.fmean([float(x.get("explosions", 0) or 0) for x in human]) if human else 0.0
        r_expl = statistics.fmean([float(x.get("explosions", 0) or 0) for x in robot]) if robot else 0.0

        h_special_eff = self._special_efficiency(human)
        h_sum9 = self._sum9_focus_ratio(human)
        h_cluster_ratio, h_top_cols = self._cluster_cols(human)
        h_future_plan = self._future_plan_rate(human)

        strategy_weights = {name: 0.0 for name in DEFAULT_STRATEGIES}
        proposal_weights = {name: 0.0 for name in DEFAULT_PROPOSAL_ENGINES}
        warnings = []

        if h_expl >= r_expl + 0.45:
            warnings.append("PatternWatch: Oyuncu patlama temposu ile onde")
            strategy_weights["low_risk"] += 0.12
            strategy_weights["safe_stack"] += 0.10
            proposal_weights["risk_balancer"] += 0.16

        if h_special_eff >= 0.62:
            warnings.append("PatternWatch: Oyuncu ozel taslari verimli kullaniyor")
            strategy_weights["lock_builder"] += 0.10
            proposal_weights["stability_guard"] += 0.12

        if h_sum9 >= 0.42:
            warnings.append("PatternWatch: Oyuncu toplam-9 odagini guclendirdi")
            strategy_weights["sum9_focus"] += 0.14
            proposal_weights["combo_amplifier"] += 0.10

        if h_future_plan >= 0.45:
            warnings.append("PatternWatch: Oyuncu gelecek tas planlamasi yapiyor")
            strategy_weights["center_control"] += 0.10
            proposal_weights["mutate_light"] += 0.08

        if h_cluster_ratio >= 0.70:
            warnings.append("PatternWatch: Oyuncu yigin/kume kolon baskisi kuruyor")
            strategy_weights["edge_pressure"] += 0.09

        self.rolling_summary = {
            "rows": len(rows),
            "human_rows": len(human),
            "robot_rows": len(robot),
            "human_avg_points": h_points,
            "robot_avg_points": r_points,
            "human_avg_explosions": h_expl,
            "robot_avg_explosions": r_expl,
            "human_special_efficiency": h_special_eff,
            "human_sum9_focus_rate": h_sum9,
            "human_future_plan_rate": h_future_plan,
            "human_cluster_ratio": h_cluster_ratio,
            "human_top_cols": h_top_cols,
        }

        command_hint = "PatternWatch: " + (warnings[0] if warnings else "Belirgin sapma yok")
        self.last_signal = {
            "warnings": warnings,
            "target_cols": h_top_cols,
            "strategy_weights": strategy_weights,
            "proposal_weights": proposal_weights,
            "command_hint": command_hint,
            "summary": self.rolling_summary,
        }

        self._append_agent_log("analyze_all_logs", self.last_signal)
        return self.last_signal

    def follow_independent(self, force=False):
        now = time.time()
        if (not force) and (now - self.last_scan_at < self.scan_interval):
            return None
        self.last_scan_at = now
        return self.analyze_all_logs(deep=False)

    def snapshot(self):
        return {
            "last_signal": self.last_signal,
            "rolling_summary": self.rolling_summary,
            "agent_log": self.agent_log_path,
            "last_scan_at": self.last_scan_at,
        }
