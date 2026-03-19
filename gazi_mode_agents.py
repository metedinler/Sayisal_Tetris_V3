import json
import os
import shutil
import statistics
import time
from collections import Counter, deque
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


class _BaseObserver:
    def __init__(self, name):
        self.name = name
        self.total_turns = 0
        self.col_counter = Counter()
        self.fast_count = 0
        self.points_history = []
        self.explosion_history = []
        self.combo_history = []
        self.win_like_moves = 0
        self.last_30_moves = deque(maxlen=30)
        self.col_effect = {}

    def observe(self, log_item):
        if not isinstance(log_item, dict):
            return
        move = log_item.get("move_decision") or {}
        col = move.get("col")
        if isinstance(col, int):
            self.col_counter[col] += 1

        if bool(move.get("fast", False)):
            self.fast_count += 1

        points = float(log_item.get("points", 0) or 0)
        explosions = float(log_item.get("explosions", 0) or 0)
        combo_mult = float(log_item.get("combo_mult", 1.0) or 1.0)
        self.points_history.append(points)
        self.explosion_history.append(explosions)
        self.combo_history.append(combo_mult)

        if points >= 12 or explosions >= 2 or combo_mult >= 1.5:
            self.win_like_moves += 1

        if isinstance(col, int):
            col_stats = self.col_effect.setdefault(col, {"count": 0, "points": 0.0, "explosions": 0.0, "combo": 0.0})
            col_stats["count"] += 1
            col_stats["points"] += points
            col_stats["explosions"] += explosions
            col_stats["combo"] += combo_mult

        self.last_30_moves.append(
            {
                "turn": int(log_item.get("turn", 0) or 0),
                "col": col,
                "points": points,
                "explosions": explosions,
                "combo_mult": combo_mult,
                "risk": float(log_item.get("risk", 0) or 0),
                "potential_explosions": float(log_item.get("potential_explosions", 0) or 0),
            }
        )

        self.total_turns += 1

    def _last_30_summary(self):
        if not self.last_30_moves:
            return {
                "move_count": 0,
                "avg_points": 0.0,
                "avg_explosions": 0.0,
                "avg_combo": 0.0,
                "counterfactual_gap": 0.0,
                "top_effect_cols": [],
            }

        rows = list(self.last_30_moves)
        move_count = len(rows)
        avg_points = statistics.fmean(x["points"] for x in rows)
        avg_explosions = statistics.fmean(x["explosions"] for x in rows)
        avg_combo = statistics.fmean(x["combo_mult"] for x in rows)

        effect_cols = []
        for col, stats in self.col_effect.items():
            cnt = int(stats.get("count", 0) or 0)
            if cnt <= 0:
                continue
            effect_cols.append(
                {
                    "col": col,
                    "count": cnt,
                    "avg_points": round(float(stats.get("points", 0.0) or 0.0) / cnt, 3),
                    "avg_explosions": round(float(stats.get("explosions", 0.0) or 0.0) / cnt, 3),
                }
            )
        effect_cols.sort(key=lambda x: (x["avg_points"], x["avg_explosions"]), reverse=True)
        top_effect_cols = effect_cols[:3]

        observed_cols = [x["col"] for x in rows if isinstance(x.get("col"), int)]
        baseline = {}
        for c in set(observed_cols):
            stats = self.col_effect.get(c, {})
            cnt = int(stats.get("count", 0) or 0)
            if cnt > 0:
                baseline[c] = float(stats.get("points", 0.0) or 0.0) / cnt
        best_alt = max(baseline.values()) if baseline else 0.0

        gaps = []
        for item in rows:
            c = item.get("col")
            if not isinstance(c, int):
                continue
            current = baseline.get(c, item.get("points", 0.0) or 0.0)
            gaps.append(max(0.0, best_alt - current))

        counterfactual_gap = statistics.fmean(gaps) if gaps else 0.0
        return {
            "move_count": move_count,
            "avg_points": round(avg_points, 3),
            "avg_explosions": round(avg_explosions, 3),
            "avg_combo": round(avg_combo, 3),
            "counterfactual_gap": round(counterfactual_gap, 3),
            "top_effect_cols": top_effect_cols,
        }

    def _skill_score(self):
        if self.total_turns <= 0:
            return 0.0
        avg_points = statistics.fmean(self.points_history) if self.points_history else 0.0
        avg_expl = statistics.fmean(self.explosion_history) if self.explosion_history else 0.0
        combo_rate = sum(1 for x in self.combo_history if x > 1.0) / max(1, len(self.combo_history))
        win_like_rate = self.win_like_moves / max(1, self.total_turns)
        return (avg_points * 0.35) + (avg_expl * 0.25) + (combo_rate * 5.0 * 0.20) + (win_like_rate * 5.0 * 0.20)

    def snapshot(self):
        most_common = self.col_counter.most_common(3)
        top_cols = [c for c, _ in most_common]
        fast_ratio = self.fast_count / max(1, self.total_turns)
        skill = self._skill_score()
        skill_label = "dusuk"
        if skill >= 4.8:
            skill_label = "yuksek"
        elif skill >= 2.6:
            skill_label = "orta"

        return {
            "name": self.name,
            "turns": self.total_turns,
            "top_cols": top_cols,
            "fast_ratio": round(fast_ratio, 3),
            "skill_score": round(skill, 3),
            "skill_label": skill_label,
            "avg_points": round(statistics.fmean(self.points_history), 3) if self.points_history else 0.0,
            "avg_explosions": round(statistics.fmean(self.explosion_history), 3) if self.explosion_history else 0.0,
            "win_like_rate": round(self.win_like_moves / max(1, self.total_turns), 3),
            "last_30": self._last_30_summary(),
        }


class EnemyObserverAgent(_BaseObserver):
    def __init__(self):
        super().__init__("dusman_izleme")


class RobotObserverAgent(_BaseObserver):
    def __init__(self):
        super().__init__("robot_izleme")


class DecisionFusionAgent:
    def __init__(self):
        self.total_directives = 0
        self.random_reject_events = 0
        self.logic_choice_events = 0
        self.last_directive = {}

    def _board_stack_profile(self, board):
        if not board or not isinstance(board, list):
            return {"heights": [], "dense_cols": [], "holes": 0}

        rows = len(board)
        cols = len(board[0]) if rows else 0
        heights = []
        holes = 0
        for c in range(cols):
            h = 0
            seen = False
            for r in range(rows):
                cell = board[r][c]
                if cell is not None:
                    if not seen:
                        h = rows - r
                        seen = True
                elif seen:
                    holes += 1
            heights.append(h)

        dense_cols = sorted(range(cols), key=lambda x: heights[x], reverse=True)[:3]
        return {"heights": heights, "dense_cols": dense_cols, "holes": holes}

    def build_directive(self, enemy_snap, robot_snap, player_board, robot_board, turn, level):
        self.total_directives += 1

        e_skill = float(enemy_snap.get("skill_score", 0.0) or 0.0)
        r_skill = float(robot_snap.get("skill_score", 0.0) or 0.0)
        e_cols = list(enemy_snap.get("top_cols", []))
        r_cols = list(robot_snap.get("top_cols", []))

        player_stack = self._board_stack_profile(player_board)
        robot_stack = self._board_stack_profile(robot_board)

        target_cols = []
        target_cols.extend(e_cols[:2])
        target_cols.extend(player_stack.get("dense_cols", [])[:1])
        target_cols.extend([c for c in r_cols[:1] if c not in target_cols])

        strategy_weights = {name: 0.0 for name in DEFAULT_STRATEGIES}
        proposal_weights = {name: 0.0 for name in DEFAULT_PROPOSAL_ENGINES}

        strategy_weights["balance"] += 0.10
        strategy_weights["sum9_focus"] += 0.10
        strategy_weights["lock_builder"] += 0.08
        proposal_weights["mutate_light"] += 0.08
        proposal_weights["combo_amplifier"] += 0.08

        if e_skill >= r_skill:
            strategy_weights["survival_mix"] += 0.18
            strategy_weights["low_risk"] += 0.14
            proposal_weights["stability_guard"] += 0.20
            proposal_weights["risk_balancer"] += 0.14
            directive_style = "karsi_oyun_ve_denge"
        else:
            strategy_weights["max_potential"] += 0.20
            strategy_weights["combo_hunter"] += 0.18
            strategy_weights["edge_pressure"] += 0.12
            proposal_weights["mutate_aggressive"] += 0.20
            proposal_weights["combo_amplifier"] += 0.12
            directive_style = "baski_ve_hizli_skor"

        if level >= 12:
            strategy_weights["safe_stack"] += 0.08
            strategy_weights["center_control"] += 0.10

        holes_penalty = min(0.25, float(robot_stack.get("holes", 0)) * 0.01)
        strategy_weights["low_risk"] += holes_penalty
        strategy_weights["safe_stack"] += holes_penalty * 0.7

        freedom_ratio = 0.30
        reject_chance = 0.12
        reject_cap_ratio = 0.30
        logical_ratio = 0.88

        command_text = (
            "Gazi emri: 10 standart ve 5 onerici baglantili hibrit karar. "
            "Oyuncu/robot paternleri, yiginilim ve gelecek tas etkisi birlikte agirliklanir."
        )

        self.last_directive = {
            "turn": int(turn),
            "style": directive_style,
            "target_cols": sorted(set([c for c in target_cols if isinstance(c, int)])),
            "strategy_weights": strategy_weights,
            "proposal_weights": proposal_weights,
            "freedom_ratio": freedom_ratio,
            "reject_chance": reject_chance,
            "reject_cap_ratio": reject_cap_ratio,
            "logical_ratio": logical_ratio,
            "command_text": command_text,
            "skill_enemy": round(e_skill, 3),
            "skill_robot": round(r_skill, 3),
            "enemy_last_30": enemy_snap.get("last_30", {}),
            "robot_last_30": robot_snap.get("last_30", {}),
            "player_dense_cols": player_stack.get("dense_cols", []),
            "robot_dense_cols": robot_stack.get("dense_cols", []),
            "robot_holes": int(robot_stack.get("holes", 0)),
            "created_at": datetime.utcnow().isoformat(),
        }
        return dict(self.last_directive)

    def mark_random_reject(self):
        self.random_reject_events += 1

    def mark_logic_choice(self):
        self.logic_choice_events += 1

    def snapshot(self):
        return {
            "total_directives": self.total_directives,
            "random_reject_events": self.random_reject_events,
            "logic_choice_events": self.logic_choice_events,
            "last_directive": self.last_directive,
        }


class GaziModeCoordinator:
    def __init__(self, memory_dir, log_dir):
        self.memory_dir = memory_dir
        self.log_dir = log_dir
        self.gazi_log_dir = os.path.join(self.log_dir, "gazi")
        self.enemy = EnemyObserverAgent()
        self.robot = RobotObserverAgent()
        self.fusion = DecisionFusionAgent()

        self.legacy_agent_log_path = os.path.join(self.memory_dir, "gazi_agents_log.jsonl")
        self.agent_log_path = os.path.join(self.gazi_log_dir, "gazi_agents_log.jsonl")
        self._bootstrap_agent_log()
        self.known_offsets = {}
        self.last_follow_at = 0.0

    def _bootstrap_agent_log(self):
        try:
            os.makedirs(self.gazi_log_dir, exist_ok=True)
            os.makedirs(self.memory_dir, exist_ok=True)
            if os.path.exists(self.legacy_agent_log_path):
                if not os.path.exists(self.agent_log_path):
                    shutil.copy2(self.legacy_agent_log_path, self.agent_log_path)
                else:
                    self._merge_jsonl_logs(self.legacy_agent_log_path, self.agent_log_path)
        except Exception:
            pass

    def _merge_jsonl_logs(self, src_path, dst_path):
        try:
            with open(dst_path, "r", encoding="utf-8") as f:
                existing = set(line.strip() for line in f if line.strip())
            with open(src_path, "r", encoding="utf-8") as src, open(dst_path, "a", encoding="utf-8") as dst:
                for line in src:
                    raw = line.strip()
                    if not raw or raw in existing:
                        continue
                    dst.write(raw + "\n")
                    existing.add(raw)
        except Exception:
            pass

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

    def observe_turn(self, player_log, robot_log, board_state=None):
        self.enemy.observe(player_log)
        self.robot.observe(robot_log)
        self._append_agent_log(
            "turn_observed",
            {
                "player_points": player_log.get("points", 0) if isinstance(player_log, dict) else 0,
                "robot_points": robot_log.get("points", 0) if isinstance(robot_log, dict) else 0,
                "board_state": board_state or {},
            },
        )

    def build_guidance(self, player_board, robot_board, turn, level):
        enemy_snap = self.enemy.snapshot()
        robot_snap = self.robot.snapshot()
        directive = self.fusion.build_directive(enemy_snap, robot_snap, player_board, robot_board, turn, level)
        self._append_agent_log("directive_generated", directive)
        return directive

    def mark_random_reject(self):
        self.fusion.mark_random_reject()

    def mark_logic_choice(self):
        self.fusion.mark_logic_choice()

    def _iter_log_files(self):
        if not os.path.isdir(self.log_dir):
            return []
        files = []
        for name in os.listdir(self.log_dir):
            if name.lower().endswith(".jsonl"):
                files.append(os.path.join(self.log_dir, name))
        files.sort(key=lambda p: os.path.getmtime(p))
        return files

    def run_historical_analysis(self, deep=False):
        files = self._iter_log_files()
        if not deep:
            files = files[-8:]

        rows = 0
        for fp in files:
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                if not deep:
                    lines = lines[-500:]
                for line in lines:
                    item = json.loads(line)
                    if item.get("player") == "Human":
                        self.enemy.observe(item)
                    elif item.get("player") == "Robot":
                        self.robot.observe(item)
                    rows += 1
            except Exception:
                continue

        self._append_agent_log("historical_analysis", {"deep": bool(deep), "rows": rows, "files": len(files)})
        return {"files": len(files), "rows": rows, "deep": bool(deep)}

    def follow_log_updates(self, throttle_seconds=2.0):
        now = time.time()
        if now - self.last_follow_at < throttle_seconds:
            return 0
        self.last_follow_at = now

        new_rows = 0
        for fp in self._iter_log_files():
            last = self.known_offsets.get(fp, 0)
            try:
                size = os.path.getsize(fp)
                if size < last:
                    last = 0
                if size == last:
                    continue
                with open(fp, "r", encoding="utf-8") as f:
                    f.seek(last)
                    chunk = f.read()
                    self.known_offsets[fp] = f.tell()
                for line in chunk.splitlines():
                    if not line.strip():
                        continue
                    item = json.loads(line)
                    if item.get("player") == "Human":
                        self.enemy.observe(item)
                    elif item.get("player") == "Robot":
                        self.robot.observe(item)
                    new_rows += 1
            except Exception:
                continue

        if new_rows > 0:
            self._append_agent_log("follow_updates", {"rows": new_rows})
        return new_rows

    def snapshot(self):
        return {
            "enemy": self.enemy.snapshot(),
            "robot": self.robot.snapshot(),
            "fusion": self.fusion.snapshot(),
            "agent_log": self.agent_log_path,
        }
