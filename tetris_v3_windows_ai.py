import json
import math
import os
import random
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, simpledialog
import uuid
from collections import deque
from datetime import datetime
import io
import struct
import wave
from sid_player import SidMusicManager

try:
    import winsound
except Exception:
    winsound = None

ROWS, COLS = 18, 8
EMPTY = None

CELL = 30
BOARD_PADDING = 20
GAP_BETWEEN_BOARDS = 80
PANEL_WIDTH = 300

BOARD_W = COLS * CELL
BOARD_H = ROWS * CELL
LEFT_X = BOARD_PADDING
TOP_Y = BOARD_PADDING + 45
RIGHT_X = LEFT_X + BOARD_W + GAP_BETWEEN_BOARDS
PANEL_X = RIGHT_X + BOARD_W + 30

WIN_W = PANEL_X + PANEL_WIDTH
REASON_FEED_HEIGHT = 210
WIN_H = TOP_Y + BOARD_H + REASON_FEED_HEIGHT + 40

BASE_FALL_DELAY = 0.55
MIN_FALL_DELAY = 0.12
IDLE_ANALYZE_SECONDS = 5.0
MAX_TURNS = 250
MAX_SHIFT_ACTIONS = int(COLS * 2.5)
EARLY_LEARNING_TURNS = 80
EARLY_EPSILON = 0.22
EARLY_TOP_CHOICES = 2

# Puanlama sabitleri (degistirildiginde oyun odul dagilimi degisir)
SUM9_PAIR_POINTS = 5
LOCK_PATTERN_POINTS = 9
LOCK_EXTRA_CELL_POINTS = 1
UP_PUSH_LOCK_BONUS = 5
UP_PUSH_COLLISION_BASE = 5
UP_PUSH_COLLISION_EXTRA = 1
JOKER_BASE_POINTS = 7
JOKER_AROUND_POINTS = 2
BOMB_BASE_POINTS = 10
BOMB_PER_CELL_POINTS = 1

COMBO_MULT_TWO = 1.25
COMBO_MULT_THREE = 1.55
COMBO_MULT_FOUR_PLUS = 2.1

if getattr(sys, "frozen", False):
    ROOT_DIR = os.path.dirname(sys.executable)
else:
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(ROOT_DIR, "logs")
MEMORY_DIR = os.path.join(ROOT_DIR, "ai_memory")
MODEL_PATH = os.path.join(MEMORY_DIR, "robot_brain.json")
PROFILE_PATH = os.path.join(MEMORY_DIR, "player_profile.json")
AUDIO_SETTINGS_PATH = os.path.join(MEMORY_DIR, "audio_settings.json")
SID_DIR = os.path.join(ROOT_DIR, "sid")

SOUND_MODE_SILENT = "silent"
SOUND_MODE_NO_MUSIC = "no_music"
SOUND_MODE_NO_EFFECTS = "no_effects"
SOUND_MODE_WARNING_ONLY = "warning_only"
SOUND_MODE_FULL = "full"

SOUND_MODE_LABELS = {
    SOUND_MODE_SILENT: "Sesiz",
    SOUND_MODE_NO_MUSIC: "Muziksiz",
    SOUND_MODE_NO_EFFECTS: "Efektsiz",
    SOUND_MODE_WARNING_ONLY: "Sadece Uyari",
    SOUND_MODE_FULL: "Tam Ses",
}

GAME_MODE_EASY = "easy"
GAME_MODE_NORMAL = "normal"
GAME_MODE_HARD = "hard"
GAME_MODE_LABELS = {
    GAME_MODE_EASY: "Kolay Mod",
    GAME_MODE_NORMAL: "Normal Mod",
    GAME_MODE_HARD: "Zor Mod",
}

ROBOT_PROFILE_BALANCED = "balanced"
ROBOT_PROFILE_AGGRESSIVE = "aggressive"
ROBOT_PROFILE_DEFENSIVE = "defensive"
ROBOT_PROFILE_LABELS = {
    ROBOT_PROFILE_BALANCED: "Dengeli",
    ROBOT_PROFILE_AGGRESSIVE: "Agresif",
    ROBOT_PROFILE_DEFENSIVE: "Savunmaci",
}


def ensure_dirs():
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(MEMORY_DIR, exist_ok=True)
    os.makedirs(SID_DIR, exist_ok=True)


def default_profile():
    return {
        "player_name": "Oyuncu",
        "total_matches": 0,
        "player_wins": 0,
        "player_losses": 0,
        "robot_wins": 0,
        "robot_losses": 0,
        "draws": 0,
        "best_player_score": 0,
        "best_robot_score": 0,
        "best_level": 1,
        "updated_at": datetime.utcnow().isoformat(),
    }


def load_profile():
    if not os.path.exists(PROFILE_PATH):
        return default_profile()
    try:
        with open(PROFILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        base = default_profile()
        if isinstance(data, dict):
            base.update(data)
        return base
    except Exception:
        return default_profile()


def save_profile(profile):
    payload = dict(default_profile())
    if isinstance(profile, dict):
        payload.update(profile)
    payload["updated_at"] = datetime.utcnow().isoformat()
    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def load_audio_settings():
    default = {"sound_mode": SOUND_MODE_WARNING_ONLY}
    if not os.path.exists(AUDIO_SETTINGS_PATH):
        return default
    try:
        with open(AUDIO_SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            default.update(data)
        return default
    except Exception:
        return default


def save_audio_settings(settings):
    payload = {"sound_mode": SOUND_MODE_WARNING_ONLY}
    if isinstance(settings, dict):
        payload.update(settings)
    with open(AUDIO_SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def clone_board(board):
    return [row[:] for row in board]


def board_full(board):
    for c in range(COLS):
        if board[0][c] is EMPTY:
            return False
    return True


def board_touches_top(board):
    for c in range(COLS):
        if board[0][c] is not EMPTY:
            return True
    return False


def piece_count(board):
    return sum(1 for r in range(ROWS) for c in range(COLS) if board[r][c] is not EMPTY)


def is_number(v):
    return isinstance(v, int) and 0 <= v <= 9


def neighbours8(r, c):
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            rr, cc = r + dr, c + dc
            if 0 <= rr < ROWS and 0 <= cc < COLS:
                yield rr, cc


def spawn_value(level):
    if level >= 20 and random.random() < 0.10:
        return "B"
    if level >= 15 and random.random() < 0.12:
        return "J"
    if level >= 9 and random.random() < 0.10:
        return "L"
    return random.randint(0, 9)


def color_for(value):
    if value is EMPTY:
        return "#1f2937", ""
    if value == "J":
        return "#f4c430", "J"
    if value == "B":
        return "#a855f7", "B"
    if value == "L":
        return "#ef4444", "L"

    palette = {
        0: "#60a5fa",
        1: "#22c55e",
        2: "#06b6d4",
        3: "#3b82f6",
        4: "#6366f1",
        5: "#f97316",
        6: "#14b8a6",
        7: "#84cc16",
        8: "#eab308",
        9: "#ec4899",
    }
    return palette.get(value, "#38bdf8"), str(value)


def apply_gravity(board):
    for c in range(COLS):
        stack = []
        for r in range(ROWS - 1, -1, -1):
            if board[r][c] is not EMPTY:
                stack.append(board[r][c])
        for r in range(ROWS - 1, -1, -1):
            idx = ROWS - 1 - r
            board[r][c] = stack[idx] if idx < len(stack) else EMPTY


def clear_cells(board, cells, visual_events):
    cleared = 0
    for r, c in cells:
        if 0 <= r < ROWS and 0 <= c < COLS and board[r][c] is not EMPTY:
            visual_events.append((r, c))
            board[r][c] = EMPTY
            cleared += 1
    return cleared


def random_surrounding_clear(board, base_cells, limit=3):
    pool = []
    seen = set()
    for r, c in base_cells:
        for rr, cc in neighbours8(r, c):
            if (rr, cc) in base_cells or (rr, cc) in seen:
                continue
            if board[rr][cc] is not EMPTY:
                seen.add((rr, cc))
                pool.append((rr, cc))

    if not pool:
        return set()

    random.shuffle(pool)
    return set(pool[: min(limit, len(pool))])


def find_lock_patterns(board):
    patterns = []

    for r in range(ROWS - 1):
        for c in range(COLS - 1):
            quad = [board[r][c], board[r][c + 1], board[r + 1][c], board[r + 1][c + 1]]
            cells = {(r, c), (r, c + 1), (r + 1, c), (r + 1, c + 1)}
            if not is_number(quad[0]) and quad.count("L") != 4:
                continue
            if quad.count("L") == 4:
                patterns.append(cells)
            elif all(is_number(v) and v == quad[0] for v in quad):
                patterns.append(cells)

    for r in range(ROWS):
        for c in range(COLS - 3):
            seq = [board[r][c + i] for i in range(4)]
            if all(is_number(v) and v == seq[0] for v in seq):
                patterns.append({(r, c + i) for i in range(4)})

    for r in range(ROWS - 3):
        for c in range(COLS):
            seq = [board[r + i][c] for i in range(4)]
            if all(is_number(v) and v == seq[0] for v in seq):
                patterns.append({(r + i, c) for i in range(4)})

    return patterns


def apply_lock_explosions(board, visual_events, up_push_mode=False):
    total_points = 0
    total_cleared = 0
    explosion_count = 0
    had_lock = False

    while True:
        patterns = find_lock_patterns(board)
        if not patterns:
            break

        wave_points = 0
        wave_clear = set()

        for cells in patterns:
            had_lock = True
            explosion_count += 1
            wave_points += LOCK_PATTERN_POINTS
            if up_push_mode:
                wave_points += UP_PUSH_LOCK_BONUS
            wave_clear |= cells

            extra = random_surrounding_clear(board, cells, limit=3)
            wave_clear |= extra
            wave_points += len(extra) * LOCK_EXTRA_CELL_POINTS

        cleared_now = clear_cells(board, wave_clear, visual_events)
        total_cleared += cleared_now
        total_points += wave_points
        apply_gravity(board)

    return total_points, total_cleared, explosion_count, had_lock


def apply_sum9_explosions(board, visual_events):
    to_clear = set()
    points = 0
    explosions = 0

    for r in range(ROWS):
        for c in range(COLS):
            v = board[r][c]
            if not is_number(v):
                continue

            if c + 1 < COLS and is_number(board[r][c + 1]) and v + board[r][c + 1] == 9:
                to_clear.update({(r, c), (r, c + 1)})
                points += SUM9_PAIR_POINTS
                explosions += 1

            if r + 1 < ROWS and is_number(board[r + 1][c]) and v + board[r + 1][c] == 9:
                to_clear.update({(r, c), (r + 1, c)})
                points += SUM9_PAIR_POINTS
                explosions += 1

    cleared = clear_cells(board, to_clear, visual_events)
    if cleared:
        apply_gravity(board)

    return points, cleared, explosions


def trigger_joker(board, target_r, target_c, visual_events):
    clear_set = {(target_r, target_c)}

    around = [(rr, cc) for rr, cc in neighbours8(target_r, target_c) if board[rr][cc] is not EMPTY]
    random.shuffle(around)
    around = around[:3]
    clear_set.update(around)

    cleared = clear_cells(board, clear_set, visual_events)
    points = JOKER_BASE_POINTS + JOKER_AROUND_POINTS * len(around)
    apply_gravity(board)

    return points, cleared, 1


def trigger_bomb(board, center_r, center_c, visual_events):
    radius = random.choice((1, 2))
    clear_set = set()
    for rr in range(center_r - radius, center_r + radius + 1):
        for cc in range(center_c - radius, center_c + radius + 1):
            if 0 <= rr < ROWS and 0 <= cc < COLS and board[rr][cc] is not EMPTY:
                clear_set.add((rr, cc))

    cleared = clear_cells(board, clear_set, visual_events)
    points = BOMB_BASE_POINTS + BOMB_PER_CELL_POINTS * cleared
    apply_gravity(board)

    return points, cleared, 1


def apply_up_push_if_needed(board, level, visual_events):
    if level < 13:
        return 0, 0, 0, False

    occupied_cols = [c for c in range(COLS) if any(board[r][c] is not EMPTY for r in range(ROWS))]
    if not occupied_cols:
        return 0, 0, 0, False

    c = random.choice(occupied_cols)

    # Tum sutunu bir satir yukari it: fiziksel davranis daha tutarlidir.
    if board[0][c] is EMPTY:
        for r in range(0, ROWS - 1):
            board[r][c] = board[r + 1][c]
        board[ROWS - 1][c] = EMPTY
        return 0, 0, 0, False

    collided_cells = {(0, c), (1, c)} if ROWS > 1 else {(0, c)}
    clear_extra = random_surrounding_clear(board, collided_cells, limit=3)
    collided_cells |= clear_extra

    cleared = clear_cells(board, collided_cells, visual_events)
    points = UP_PUSH_COLLISION_BASE + UP_PUSH_COLLISION_EXTRA * len(clear_extra)
    apply_gravity(board)

    lock_points, lock_cleared, lock_expl, lock_flag = apply_lock_explosions(board, visual_events, up_push_mode=True)
    return points + lock_points, cleared + lock_cleared, 1 + lock_expl, lock_flag


def combo_multiplier(explosion_count):
    if explosion_count >= 4:
        return COMBO_MULT_FOUR_PLUS
    if explosion_count == 3:
        return COMBO_MULT_THREE
    if explosion_count == 2:
        return COMBO_MULT_TWO
    return 1.0


def first_empty_from_bottom(board, col):
    for r in range(ROWS - 1, -1, -1):
        if board[r][col] is EMPTY:
            return r
    return None


def column_heights(board):
    heights = []
    for c in range(COLS):
        h = 0
        for r in range(ROWS):
            if board[r][c] is not EMPTY:
                h = ROWS - r
                break
        heights.append(h)
    return heights


def hole_count(board):
    holes = 0
    for c in range(COLS):
        seen_block = False
        for r in range(ROWS):
            if board[r][c] is not EMPTY:
                seen_block = True
            elif seen_block:
                holes += 1
    return holes


def potential_sum9_count(board, num, col):
    row = first_empty_from_bottom(board, col)
    if row is None:
        return 0

    count = 0
    if col - 1 >= 0 and is_number(board[row][col - 1]) and is_number(num) and board[row][col - 1] + num == 9:
        count += 1
    if col + 1 < COLS and is_number(board[row][col + 1]) and is_number(num) and board[row][col + 1] + num == 9:
        count += 1
    if row + 1 < ROWS and is_number(board[row + 1][col]) and is_number(num) and board[row + 1][col] + num == 9:
        count += 1
    return count


def potential_lock_count(board, num, col):
    row = first_empty_from_bottom(board, col)
    if row is None:
        return 0

    trial = clone_board(board)
    trial[row][col] = num
    return len(find_lock_patterns(trial))


def risk_score(board, col):
    row = first_empty_from_bottom(board, col)
    if row is None:
        return 1.0

    h = ROWS - row
    col_fill = sum(1 for r in range(ROWS) if board[r][col] is not EMPTY)
    return min(1.0, (h / ROWS) * 0.65 + (col_fill / ROWS) * 0.35)


class MiniNN:
    def __init__(self, input_size=12, hidden_size=16):
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.lr = 0.015

        self.w1 = [[random.uniform(-0.2, 0.2) for _ in range(input_size)] for _ in range(hidden_size)]
        self.b1 = [0.0 for _ in range(hidden_size)]
        self.w2 = [random.uniform(-0.2, 0.2) for _ in range(hidden_size)]
        self.b2 = 0.0

    def tanh(self, x):
        return math.tanh(x)

    def dtanh(self, y):
        return 1.0 - y * y

    def predict(self, x):
        h_raw = []
        h = []
        for i in range(self.hidden_size):
            s = self.b1[i]
            row = self.w1[i]
            for j in range(self.input_size):
                s += row[j] * x[j]
            h_raw.append(s)
            h.append(self.tanh(s))

        y = self.b2
        for i in range(self.hidden_size):
            y += self.w2[i] * h[i]

        return y, h

    def train_step(self, x, target):
        y, h = self.predict(x)
        err = y - target

        for i in range(self.hidden_size):
            grad_w2 = err * h[i]
            self.w2[i] -= self.lr * grad_w2
        self.b2 -= self.lr * err

        for i in range(self.hidden_size):
            back = err * self.w2[i] * self.dtanh(h[i])
            for j in range(self.input_size):
                grad_w1 = back * x[j]
                self.w1[i][j] -= self.lr * grad_w1
            self.b1[i] -= self.lr * back

        return abs(err)

    def to_dict(self):
        return {
            "input_size": self.input_size,
            "hidden_size": self.hidden_size,
            "lr": self.lr,
            "w1": self.w1,
            "b1": self.b1,
            "w2": self.w2,
            "b2": self.b2,
        }

    @classmethod
    def from_dict(cls, data):
        obj = cls(data.get("input_size", 12), data.get("hidden_size", 16))
        obj.lr = data.get("lr", 0.015)
        obj.w1 = data.get("w1", obj.w1)
        obj.b1 = data.get("b1", obj.b1)
        obj.w2 = data.get("w2", obj.w2)
        obj.b2 = data.get("b2", obj.b2)
        return obj


class StrategyGenerator:
    def __init__(self):
        self.pool = [
            {"name": "safe_stack", "w": [0.15, 0.10, 0.05, 0.30, -0.25, 0.10]},
            {"name": "max_potential", "w": [0.10, 0.35, 0.30, 0.10, -0.10, 0.05]},
            {"name": "balance", "w": [0.20, 0.20, 0.15, 0.20, -0.20, 0.05]},
            {"name": "combo_hunter", "w": [0.08, 0.30, 0.35, 0.05, -0.10, 0.06]},
            {"name": "low_risk", "w": [0.25, 0.08, 0.08, 0.28, -0.35, 0.02]},
            {"name": "center_control", "w": [0.22, 0.12, 0.10, 0.22, -0.18, 0.04]},
            {"name": "edge_pressure", "w": [0.12, 0.22, 0.18, 0.16, -0.16, 0.09]},
            {"name": "lock_builder", "w": [0.10, 0.15, 0.42, 0.08, -0.12, 0.03]},
            {"name": "sum9_focus", "w": [0.10, 0.44, 0.14, 0.10, -0.10, 0.03]},
            {"name": "survival_mix", "w": [0.28, 0.10, 0.08, 0.25, -0.30, 0.01]},
        ]
        self.scores = {s["name"]: 1.0 for s in self.pool}
        self.proposal_engines = [
            {"name": "mutate_light", "jitter": 0.05, "focus": [0.9, 1.1, 1.0, 1.0, 1.0, 1.0]},
            {"name": "mutate_aggressive", "jitter": 0.12, "focus": [0.8, 1.3, 1.25, 0.9, 0.8, 1.0]},
            {"name": "risk_balancer", "jitter": 0.07, "focus": [1.2, 0.9, 0.95, 1.15, 1.35, 0.8]},
            {"name": "combo_amplifier", "jitter": 0.09, "focus": [0.9, 1.25, 1.35, 0.85, 0.9, 1.05]},
            {"name": "stability_guard", "jitter": 0.04, "focus": [1.25, 0.85, 0.90, 1.20, 1.40, 0.6]},
        ]

    def active_count(self):
        return len(self.pool)

    def proposal_engine_count(self):
        return len(self.proposal_engines)

    def _score_with_strategy(self, features, strategy):
        w = strategy["w"]
        # features order: fill, sum9, lock, low_height, low_risk, random
        return (
            w[0] * features[0]
            + w[1] * features[1]
            + w[2] * features[2]
            + w[3] * features[3]
            + w[4] * features[4]
            + w[5] * features[5]
        )

    def suggest(self, board, num, next_num, level, turn_index=0):
        if level < 10:
            return None

        base = max(self.pool, key=lambda s: self.scores.get(s["name"], 0.0))
        engine = self.proposal_engines[turn_index % len(self.proposal_engines)]
        new_w = []
        for idx, val in enumerate(base["w"]):
            jitter = random.uniform(-engine["jitter"], engine["jitter"])
            focused = (val + jitter) * engine["focus"][idx]
            new_w.append(focused)

        name = "gen_" + uuid.uuid4().hex[:6]
        candidate = {"name": name, "w": new_w}

        best_col = None
        best_score = -1e9
        best_reason = ""

        for col in range(COLS):
            row = first_empty_from_bottom(board, col)
            if row is None:
                continue
            fill = 1.0 - ((ROWS - row) / ROWS)
            p9 = potential_sum9_count(board, num, col) / 3.0
            plock = min(1.0, potential_lock_count(board, num, col) / 2.0)
            low_height = 1.0 - ((ROWS - row) / ROWS)
            low_risk = 1.0 - risk_score(board, col)
            rnd = random.random() * 0.2
            feat = [fill, p9, plock, low_height, low_risk, rnd]
            sc = self._score_with_strategy(feat, candidate)
            if sc > best_score:
                best_score = sc
                best_col = col
                best_reason = f"{engine['name']} motoru, patlama potansiyeli ve risk dengesini yuksek buldu"

        if best_col is None:
            return None

        confidence = max(0.05, min(0.95, 0.5 + best_score * 0.25))
        return {
            "candidate": candidate,
            "col": best_col,
            "confidence": confidence,
            "reason": best_reason,
            "next_num_known": next_num,
            "engine_name": engine["name"],
        }

    def decide_apply(self, proposal, base_score, proposal_score, risk_value):
        if proposal is None:
            return False

        score_gain = proposal_score - base_score
        threshold = 0.07 + risk_value * 0.20
        return proposal["confidence"] > 0.42 and score_gain > threshold

    def update_after_move(self, strategy_name, reward):
        old = self.scores.get(strategy_name, 1.0)
        self.scores[strategy_name] = old * 0.92 + reward * 0.08

    def maybe_add_strategy(self, candidate):
        if candidate is None:
            return False
        if len(self.pool) >= 30:
            return False
        self.pool.append(candidate)
        self.scores[candidate["name"]] = 1.0
        return True

    def to_dict(self):
        return {"pool": self.pool, "scores": self.scores, "proposal_engines": self.proposal_engines}

    @classmethod
    def from_dict(cls, data):
        obj = cls()
        if not data:
            return obj
        obj.pool = data.get("pool", obj.pool)
        obj.scores = data.get("scores", obj.scores)
        obj.proposal_engines = data.get("proposal_engines", obj.proposal_engines)
        return obj


class RobotLearner:
    def __init__(self):
        self.nn = MiniNN(input_size=12, hidden_size=16)
        self.strategy_engine = StrategyGenerator()
        self.epsilon = 0.08
        self.total_updates = 0
        self.last_train_error = 0.0
        self.last_reason = ""
        self.decision_count = 0

        self._load_memory()

    def _load_memory(self):
        if not os.path.exists(MODEL_PATH):
            return
        try:
            with open(MODEL_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.nn = MiniNN.from_dict(data.get("nn", {}))
            self.strategy_engine = StrategyGenerator.from_dict(data.get("strategy_engine", {}))
            self.epsilon = data.get("epsilon", self.epsilon)
            self.total_updates = data.get("total_updates", 0)
            self.decision_count = data.get("decision_count", 0)
        except Exception:
            pass

    def save_memory(self):
        payload = {
            "nn": self.nn.to_dict(),
            "strategy_engine": self.strategy_engine.to_dict(),
            "epsilon": self.epsilon,
            "total_updates": self.total_updates,
            "decision_count": self.decision_count,
            "updated_at": datetime.utcnow().isoformat(),
        }
        with open(MODEL_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def _features_for_col(self, board, current_num, next_num, level, col):
        row = first_empty_from_bottom(board, col)
        if row is None:
            return None

        heights = column_heights(board)
        fill_ratio = sum(1 for r in range(ROWS) for c in range(COLS) if board[r][c] is not EMPTY) / (ROWS * COLS)
        holes = hole_count(board) / (ROWS * COLS)
        risk = risk_score(board, col)
        p9 = potential_sum9_count(board, current_num, col) / 3.0
        plock = min(1.0, potential_lock_count(board, current_num, col) / 3.0)

        cur_num = (current_num if is_number(current_num) else 9) / 9.0
        nxt_num = (next_num if is_number(next_num) else 9) / 9.0

        col_h = heights[col] / ROWS
        col_balance = (sum(heights) / (len(heights) * ROWS))
        low_height = 1.0 - col_h
        low_risk = 1.0 - risk

        x = [
            1.0,
            col / max(1, COLS - 1),
            cur_num,
            nxt_num,
            col_h,
            col_balance,
            holes,
            fill_ratio,
            p9,
            plock,
            low_height,
            low_risk,
        ]
        return x

    def choose_action(self, board, current_num, next_num, level, game_mode=GAME_MODE_NORMAL, robot_profile=ROBOT_PROFILE_BALANCED):
        self.decision_count += 1
        candidates = []
        for col in range(COLS):
            x = self._features_for_col(board, current_num, next_num, level, col)
            if x is None:
                continue
            nn_score, _ = self.nn.predict(x)
            heuristics = [
                1.0 - x[7],
                x[8],
                x[9],
                x[10],
                x[11],
                random.random() * 0.2,
            ]

            best_str = max(self.strategy_engine.pool, key=lambda s: self.strategy_engine.scores.get(s["name"], 1.0))
            sw = best_str["w"]
            strat_score = (
                sw[0] * heuristics[0]
                + sw[1] * heuristics[1]
                + sw[2] * heuristics[2]
                + sw[3] * heuristics[3]
                + sw[4] * heuristics[4]
                + sw[5] * heuristics[5]
            )
            nn_weight = 0.65
            strat_weight = 0.35
            if robot_profile == ROBOT_PROFILE_AGGRESSIVE:
                nn_weight = 0.55
                strat_weight = 0.45
            elif robot_profile == ROBOT_PROFILE_DEFENSIVE:
                nn_weight = 0.72
                strat_weight = 0.28
            potential_raw = potential_sum9_count(board, current_num, col) + potential_lock_count(board, current_num, col)
            risk_val = risk_score(board, col)
            score_drive = (x[8] * 1.4) + (x[9] * 1.7) + (max(0.0, 1.0 - risk_val) * 0.9)
            safety_drive = (x[11] * 1.2) + (x[10] * 0.6) - (x[6] * 0.8)

            profile_bias = 0.0
            if robot_profile == ROBOT_PROFILE_AGGRESSIVE:
                profile_bias = (potential_raw * 0.12) - (risk_val * 0.05)
            elif robot_profile == ROBOT_PROFILE_DEFENSIVE:
                profile_bias = (safety_drive * 0.14) - (potential_raw * 0.03)
            else:
                profile_bias = (potential_raw * 0.06) + (safety_drive * 0.06)

            mode_bias = 0.0
            if game_mode == GAME_MODE_HARD:
                mode_bias = (potential_raw * 0.18) + (score_drive * 0.35) - (max(0.0, risk_val - 0.45) * 0.25)
            elif game_mode == GAME_MODE_EASY:
                mode_bias = (safety_drive * 0.20) - (potential_raw * 0.04)
            else:
                mode_bias = (potential_raw * 0.08) + (safety_drive * 0.10)

            final = nn_score * nn_weight + strat_score * strat_weight + profile_bias + mode_bias
            candidates.append((col, x, nn_score, strat_score, final, best_str["name"], potential_raw, risk_val, score_drive, safety_drive))

        if not candidates:
            return 0, {
                "strategy": "fallback",
                "reason": "Tum sutunlar dolu oldugu icin varsayilan secim",
                "potential_explosions": 0,
                "risk": 1.0,
                "priority": "Hayatta kalma",
                "proposal": None,
                "used_proposal": False,
                "decision": "fallback",
            }

        effective_epsilon = self.epsilon
        if game_mode == GAME_MODE_EASY:
            effective_epsilon = max(effective_epsilon, 0.14)
        elif game_mode == GAME_MODE_HARD:
            effective_epsilon = min(effective_epsilon, 0.06)
        if self.decision_count <= EARLY_LEARNING_TURNS:
            effective_epsilon = max(self.epsilon, EARLY_EPSILON)

        if random.random() < effective_epsilon:
            top_count = min(EARLY_TOP_CHOICES, len(candidates))
            top_candidates = sorted(candidates, key=lambda t: t[4], reverse=True)[:top_count]
            chosen = random.choice(top_candidates)
            reason = f"Kesif modu: ilk {top_count} iyi secenek arasindan deneme"
        else:
            chosen = max(candidates, key=lambda t: t[4])
            reason = "Ogrenme modeli + strateji puanina gore secim"

        chosen_col, x, nn_score, strat_score, final_score, strategy_name, potential_hint, risk_hint, score_drive, safety_drive = chosen

        proposal = self.strategy_engine.suggest(board, current_num, next_num, level, turn_index=self.decision_count)
        used_proposal = False
        decision = "base"

        if proposal is not None:
            pcol = proposal["col"]
            px = self._features_for_col(board, current_num, next_num, level, pcol)
            if px is not None:
                p_nn, _ = self.nn.predict(px)
                p_h = [1.0 - px[7], px[8], px[9], px[10], px[11], random.random() * 0.2]
                cw = proposal["candidate"]["w"]
                p_str = cw[0] * p_h[0] + cw[1] * p_h[1] + cw[2] * p_h[2] + cw[3] * p_h[3] + cw[4] * p_h[4] + cw[5] * p_h[5]
                proposal_score = p_nn * 0.58 + p_str * 0.42

                r = risk_score(board, chosen_col)
                if game_mode == GAME_MODE_HARD:
                    p_potential = potential_sum9_count(board, current_num, pcol) + potential_lock_count(board, current_num, pcol)
                    p_risk = risk_score(board, pcol)
                    p_score_drive = (px[8] * 1.4) + (px[9] * 1.7) + (max(0.0, 1.0 - p_risk) * 0.9)
                    proposal_score += (p_potential * 0.18) + (p_score_drive * 0.35) - (max(0.0, p_risk - 0.45) * 0.25)
                elif game_mode == GAME_MODE_EASY:
                    proposal_score -= 0.04

                gate_pass = self.strategy_engine.decide_apply(proposal, final_score, proposal_score, r)
                if game_mode == GAME_MODE_HARD and proposal_score > final_score + 0.02:
                    gate_pass = True

                if gate_pass:
                    used_proposal = True
                    chosen_col = pcol
                    x = px
                    nn_score = p_nn
                    strat_score = p_str
                    final_score = proposal_score
                    strategy_name = proposal["candidate"]["name"]
                    potential_hint = potential_sum9_count(board, current_num, chosen_col) + potential_lock_count(board, current_num, chosen_col)
                    risk_hint = risk_score(board, chosen_col)
                    score_drive = (x[8] * 1.4) + (x[9] * 1.7) + (max(0.0, 1.0 - risk_hint) * 0.9)
                    safety_drive = (x[11] * 1.2) + (x[10] * 0.6) - (x[6] * 0.8)
                    decision = "proposal_applied"
                    reason = f"Yeni strateji onerisi kabul edildi ({proposal.get('engine_name', 'unknown_engine')})"
                    self.strategy_engine.maybe_add_strategy(proposal["candidate"])
                else:
                    decision = "proposal_rejected"
                    reason = f"Yeni strateji onerisi reddedildi ({proposal.get('engine_name', 'unknown_engine')})"

        potential = potential_hint
        risk_val = risk_hint
        objective = {
            GAME_MODE_EASY: "Hata toleransi yuksek, guvenli oyna",
            GAME_MODE_NORMAL: "Dengeyi koru, puani artisli topla",
            GAME_MODE_HARD: "Maksimum puan ve hamle ustunlugu",
        }.get(game_mode, "Dengeli karar")
        profile_style = {
            ROBOT_PROFILE_BALANCED: "Dengeli risk ve puan",
            ROBOT_PROFILE_AGGRESSIVE: "Yuksek patlama ve skor baskisi",
            ROBOT_PROFILE_DEFENSIVE: "Dusuk risk ve guvenli kurulum",
        }.get(robot_profile, "Dengeli risk ve puan")

        if game_mode == GAME_MODE_HARD:
            priority = "Skor Patlamasi" if potential > 0 else "Skor Baskisi"
        elif robot_profile == ROBOT_PROFILE_DEFENSIVE:
            priority = "Guvenli Kurulum" if risk_val < 0.45 else "Savunma"
        else:
            priority = "Patlama" if potential > 0 else ("Puan" if risk_val < 0.5 else "Guvenlik")

        meta = {
            "strategy": strategy_name,
            "reason": reason,
            "potential_explosions": potential,
            "risk": round(risk_val, 3),
            "priority": priority,
            "objective": objective,
            "profile_style": profile_style,
            "score_drive": round(score_drive, 3),
            "safety_drive": round(safety_drive, 3),
            "mode": game_mode,
            "profile": robot_profile,
            "proposal": proposal,
            "used_proposal": used_proposal,
            "decision": decision,
            "x": x,
            "nn_score": nn_score,
            "strat_score": strat_score,
            "final_score": final_score,
            "strategy_count": self.strategy_engine.active_count(),
            "proposal_engine_count": self.strategy_engine.proposal_engine_count(),
            "proposal_text": proposal.get("reason") if proposal else "Yeni onerisi yok",
        }
        return chosen_col, meta

    def learn_from_move(self, x, reward, strategy_name):
        target = reward / 25.0
        err = self.nn.train_step(x, target)
        self.last_train_error = err
        self.total_updates += 1
        self.strategy_engine.update_after_move(strategy_name, reward)
        self.epsilon = max(0.02, self.epsilon * 0.999)

    def _features_from_log_item(self, item):
        board = item.get("board")
        move = item.get("move_decision") or {}
        col = move.get("col")

        if not isinstance(board, list) or len(board) != ROWS:
            return None
        if not isinstance(col, int) or not (0 <= col < COLS):
            return None

        normalized_board = []
        for row in board:
            if not isinstance(row, list) or len(row) != COLS:
                return None
            normalized_row = []
            for cell in row:
                if cell is None or is_number(cell) or cell in ("J", "B", "L"):
                    normalized_row.append(cell)
                else:
                    normalized_row.append(EMPTY)
            normalized_board.append(normalized_row)

        current_num = item.get("num", 0)
        next_num = item.get("next_num", 0)
        turn = item.get("turn", 1)
        level_guess = max(1, int(turn) // 12 + 1) if isinstance(turn, int) else 1
        return self._features_for_col(normalized_board, current_num, next_num, level_guess, col)

    def analyze_previous_logs(self, max_files=6, max_lines=350):
        files = sorted(
            [os.path.join(LOG_DIR, f) for f in os.listdir(LOG_DIR) if f.lower().endswith(".jsonl")],
            key=lambda p: os.path.getmtime(p),
            reverse=True,
        )
        files = files[:max_files]

        trained = 0
        total_reward = 0.0
        robot_replays = 0
        human_replays = 0

        for fp in files:
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                for line in lines[-max_lines:]:
                    item = json.loads(line)
                    player = item.get("player")
                    reward = float(item.get("points", 0))

                    if player == "Robot":
                        x = item.get("robot_features")
                        strat = item.get("selected_strategy", "balance")
                        if not isinstance(x, list) or len(x) != 12:
                            continue
                        robot_replays += 1
                    elif player == "Human":
                        # Bekleme modunda rakibin kazandiran hamleleri de ogrenilir.
                        x = self._features_from_log_item(item)
                        if not isinstance(x, list) or len(x) != 12:
                            continue
                        strat = "human_replay"
                        reward = max(0.0, reward) * 0.85
                        human_replays += 1
                    else:
                        continue

                    self.learn_from_move(x, reward, strat)
                    trained += 1
                    total_reward += reward
            except Exception:
                continue

        self.save_memory()
        return trained, total_reward, robot_replays, human_replays


class GameLogger:
    def __init__(self):
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        uid = uuid.uuid4().hex[:8]
        self.path = os.path.join(LOG_DIR, f"game_{stamp}_{uid}.jsonl")

    def write(self, obj):
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")


class VersusGame:
    def __init__(self, root):
        ensure_dirs()

        self.root = root

        self.profile = load_profile()
        self.audio_settings = load_audio_settings()
        self._ensure_player_name()
        self.player_name = str(self.profile.get("player_name", "Oyuncu"))
        self.match_recorded = False

        self.root.title(f"Sayisal Tetris V3 - {self.player_name} vs Robot AI")
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        start_w = min(max(WIN_W, 1180), max(900, screen_w - 48))
        start_h = min(max(WIN_H, 860), max(700, screen_h - 96))
        self.root.geometry(f"{start_w}x{start_h}")
        self.root.resizable(True, True)
        self.root.minsize(WIN_W, WIN_H)

        self.wait_mode_var = tk.BooleanVar(value=False)
        self.feed_filter_var = tk.StringVar(value="all")
        mode = str(self.audio_settings.get("sound_mode", SOUND_MODE_WARNING_ONLY))
        if mode not in SOUND_MODE_LABELS:
            mode = SOUND_MODE_WARNING_ONLY
        self.sound_mode_var = tk.StringVar(value=mode)
        self.game_mode_var = tk.StringVar(value=GAME_MODE_NORMAL)
        self.robot_profile_var = tk.StringVar(value=ROBOT_PROFILE_BALANCED)
        self.fullscreen_var = tk.BooleanVar(value=False)
        self._build_menu()

        self.canvas = tk.Canvas(root, width=WIN_W, height=WIN_H, bg="#0b1220", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.player_board = [[EMPTY for _ in range(COLS)] for _ in range(ROWS)]
        self.robot_board = [[EMPTY for _ in range(COLS)] for _ in range(ROWS)]

        self.player_score = 0
        self.robot_score = 0

        self.turn = 1
        self.level = 1

        self.current_num = spawn_value(self.level)
        self.next_num = spawn_value(self.level)

        self.player_col = COLS // 2
        self.player_fast = False
        self.player_shift_actions = 0

        self.robot_ai = RobotLearner()
        self.robot_col = COLS // 2
        self.robot_fast = True
        self.robot_meta = None

        self.logger = GameLogger()
        self.music = SidMusicManager(
            root_dir=ROOT_DIR,
            memory_dir=MEMORY_DIR,
            sid_dir=SID_DIR,
            player_cmd="sidplayfp",
        )

        self.flash_player = []
        self.flash_robot = []
        self.flash_until = 0.0
        self.player_impact_until = 0.0
        self.robot_impact_until = 0.0
        self.player_impact_color = "#34d399"
        self.robot_impact_color = "#f472b6"

        self.phase = "player_input"
        self.player_active_piece = None
        self.robot_active_piece = None
        self.player_result = None
        self.robot_result = None
        self.robot_target_col = COLS // 2
        self.normal_player_shift_actions = 0
        self.normal_turn_started_at = time.time()
        self.last_fall_tick = time.time()
        self.game_over = False
        self.game_winner = None
        self.game_end_reason = ""
        self.last_input_time = time.time()
        self.last_idle_analysis = 0.0
        self.status = "Insan hamlesini bekliyor"
        self.reason_feed = deque(maxlen=9)
        self.last_proposal_banner = "Henüz öneri yok"

        self.root.bind("<Left>", self.on_left)
        self.root.bind("<Right>", self.on_right)
        self.root.bind("<a>", self.on_left)
        self.root.bind("<A>", self.on_left)
        self.root.bind("<d>", self.on_right)
        self.root.bind("<D>", self.on_right)
        self.root.bind("<Down>", self.on_drop_fast)
        self.root.bind("<s>", self.on_drop_fast)
        self.root.bind("<S>", self.on_drop_fast)
        self.root.bind("<space>", self.on_drop_normal)
        self.root.bind("<Return>", self.on_drop_normal)
        self.root.bind("<b>", self.on_toggle_wait_mode)
        self.root.bind("<B>", self.on_toggle_wait_mode)
        self.root.bind("<r>", self.restart_match)
        self.root.bind("<R>", self.restart_match)
        self.root.bind("<q>", self.on_quit)
        self.root.bind("<Q>", self.on_quit)
        self.root.bind("<Escape>", self.on_quit)
        self.root.bind("<F11>", self.on_toggle_fullscreen)

        self.push_reason("Robot beyni hazırlandı. İnsan hamlesi bekleniyor.", "system")
        self.apply_sound_mode(push_message=False)
        self._initialize_turn_flow()
        self.tick()

    def _build_menu(self):
        menubar = tk.Menu(self.root)

        menu_features = tk.Menu(menubar, tearoff=0)
        menu_features.add_checkbutton(
            label="Bekleme Modu (B)",
            variable=self.wait_mode_var,
            command=self.toggle_wait_mode,
        )
        menu_filter = tk.Menu(menu_features, tearoff=0)
        menu_filter.add_radiobutton(label="Tum Akis", variable=self.feed_filter_var, value="all", command=self.set_feed_filter)
        menu_filter.add_radiobutton(label="Sadece Oneriler", variable=self.feed_filter_var, value="proposal", command=self.set_feed_filter)
        menu_filter.add_radiobutton(label="Sadece Reddedilen", variable=self.feed_filter_var, value="rejected", command=self.set_feed_filter)
        menu_filter.add_radiobutton(label="Sadece Uygulanan", variable=self.feed_filter_var, value="applied", command=self.set_feed_filter)
        menu_features.add_cascade(label="Akil Yurutme Filtresi", menu=menu_filter)
        menu_sound = tk.Menu(menu_features, tearoff=0)
        for mode_key, mode_label in SOUND_MODE_LABELS.items():
            menu_sound.add_radiobutton(
                label=mode_label,
                variable=self.sound_mode_var,
                value=mode_key,
                command=self.apply_sound_mode,
            )
        menu_features.add_cascade(label="Ses Modu", menu=menu_sound)
        menu_game_mode = tk.Menu(menu_features, tearoff=0)
        for mode_key, mode_label in GAME_MODE_LABELS.items():
            menu_game_mode.add_radiobutton(
                label=mode_label,
                variable=self.game_mode_var,
                value=mode_key,
                command=self.on_game_mode_changed,
            )
        menu_features.add_cascade(label="Oyun Modu", menu=menu_game_mode)
        menu_robot_profile = tk.Menu(menu_features, tearoff=0)
        for key, label in ROBOT_PROFILE_LABELS.items():
            menu_robot_profile.add_radiobutton(
                label=label,
                variable=self.robot_profile_var,
                value=key,
                command=self.on_robot_profile_changed,
            )
        menu_features.add_cascade(label="Robot Profili", menu=menu_robot_profile)
        menu_features.add_checkbutton(
            label="Tam Ekran (F11)",
            variable=self.fullscreen_var,
            command=self.toggle_fullscreen,
        )
        menu_features.add_command(label="Simdi Log Analizi", command=self.manual_idle_analysis)
        menu_features.add_command(label="Tum Loglari Isle (Uzun Surer)", command=self.manual_full_log_analysis)
        menu_features.add_command(label="Yeniden Baslat (R)", command=self.restart_match)
        menu_features.add_separator()
        menu_features.add_command(label="Cikis", command=self.on_quit)
        menubar.add_cascade(label="Ozellikler", menu=menu_features)

        menu_help = tk.Menu(menubar, tearoff=0)
        menu_help.add_command(label="Hakkinda", command=self.show_about)
        menubar.add_cascade(label="Yardim", menu=menu_help)

        self.root.config(menu=menubar)

    def show_about(self):
        messagebox.showinfo(
            "Hakkinda",
            "Sayisal Tetris V3\n"
            "Windows Human vs Robot AI\n\n"
            "- 10 aktif robot stratejisi\n"
            "- 5 öneri motoru\n"
            "- Kalıcı öğrenme belleği\n"
            "- Benzersiz log kaydı ve bekleme analiz modu\n\n"
            "Zuhtu Mete DINLER\n"
            "@2026\n"
            "Tum Haklari Saklidir.\n"
            "zmetedinler@gmail.com\n\n"
            "VAO dan ogrendiklerim, kendi bildigim, biraz eski oyunlar,\n"
            "birazda arastirma, ve gpt codex 5.3 yardimiyla yazildi",
        )

    def push_reason(self, text, reason_type="general"):
        ts = datetime.now().strftime("%H:%M:%S")
        self.reason_feed.append({"time": ts, "text": text, "type": reason_type})

    def set_feed_filter(self):
        choice = self.feed_filter_var.get()
        title = {
            "all": "Tum akis",
            "proposal": "Sadece oneriler",
            "rejected": "Sadece reddedilen oneriler",
            "applied": "Sadece uygulanan oneriler",
        }.get(choice, "Tum akis")
        self.status = f"Akil yurutme filtresi: {title}"

    def get_filtered_reason_feed(self):
        mode = self.feed_filter_var.get()
        items = list(self.reason_feed)
        if mode == "all":
            return items
        if mode == "proposal":
            return [x for x in items if x.get("type") in ("proposal", "applied", "rejected")]
        if mode == "rejected":
            return [x for x in items if x.get("type") == "rejected"]
        if mode == "applied":
            return [x for x in items if x.get("type") == "applied"]
        return items

    def toggle_wait_mode(self):
        enabled = self.wait_mode_var.get()
        if enabled:
            self.status = "Bekleme modu acik: Bosta analiz var, otomatik birakma yok"
            self.push_reason("Bekleme modu açıldı. Bosta sadece analiz yapilacak.", "system")
        else:
            self.status = "Bekleme modu kapali: 5s sonra analiz + otomatik hamle"
            self.push_reason("Bekleme modu kapatıldı. Eski otomatik akışa dönüldü.", "system")

    def on_toggle_wait_mode(self, _event=None):
        self.wait_mode_var.set(not self.wait_mode_var.get())
        self.toggle_wait_mode()

    def toggle_fullscreen(self):
        enabled = bool(self.fullscreen_var.get())
        self.root.attributes("-fullscreen", enabled)
        self.status = f"Tam ekran: {'ACIK' if enabled else 'KAPALI'}"

    def on_toggle_fullscreen(self, _event=None):
        self.fullscreen_var.set(not self.fullscreen_var.get())
        self.toggle_fullscreen()

    def _effects_enabled(self):
        mode = self.sound_mode_var.get()
        return mode in (SOUND_MODE_NO_MUSIC, SOUND_MODE_WARNING_ONLY, SOUND_MODE_FULL)

    def _music_enabled(self):
        mode = self.sound_mode_var.get()
        return mode in (SOUND_MODE_NO_EFFECTS, SOUND_MODE_FULL)

    def apply_sound_mode(self, push_message=True):
        mode = self.sound_mode_var.get()
        self.audio_settings["sound_mode"] = mode
        save_audio_settings(self.audio_settings)

        if self._music_enabled():
            started = self.music.start()
            if push_message:
                self.push_reason(
                    f"Ses modu: {SOUND_MODE_LABELS.get(mode, mode)} | SID muzik {'acildi' if started else 'baslatilamadi'}",
                    "system",
                )
        else:
            self.music.stop()
            if push_message:
                self.push_reason(f"Ses modu: {SOUND_MODE_LABELS.get(mode, mode)} | SID muzik kapali", "system")

    def manual_idle_analysis(self):
        trained, reward, robot_replays, human_replays = self.robot_ai.analyze_previous_logs()
        self.status = (
            f"Manuel analiz: {trained} replay (Robot {robot_replays}, Insan {human_replays}), "
            f"toplam odul {int(reward)}"
        )
        self.push_reason(self.status, "analysis")

    def manual_full_log_analysis(self):
        trained, reward, robot_replays, human_replays = self.robot_ai.analyze_previous_logs(max_files=10**6, max_lines=10**6)
        self.status = (
            f"Tum log analizi: {trained} replay (Robot {robot_replays}, Insan {human_replays}), "
            f"toplam odul {int(reward)}"
        )
        self.push_reason(self.status, "analysis")

    def _ensure_player_name(self):
        current_name = str(self.profile.get("player_name", "")).strip()
        if current_name and current_name != "Oyuncu":
            return

        asked = simpledialog.askstring("Oyuncu", "Oyuncu adini giriniz:", parent=self.root)
        asked = (asked or "").strip()
        self.profile["player_name"] = asked if asked else "Oyuncu"
        save_profile(self.profile)

    def _record_match_result(self):
        if self.match_recorded:
            return

        player_win = self.game_winner == "player"
        robot_win = self.game_winner == "robot"
        is_draw = self.game_winner == "draw"

        if not (player_win or robot_win or is_draw):
            if self.player_score > self.robot_score:
                player_win = True
            elif self.robot_score > self.player_score:
                robot_win = True
            else:
                is_draw = True

        self.profile["total_matches"] = int(self.profile.get("total_matches", 0)) + 1
        if player_win:
            self.profile["player_wins"] = int(self.profile.get("player_wins", 0)) + 1
            self.profile["robot_losses"] = int(self.profile.get("robot_losses", 0)) + 1
        elif robot_win:
            self.profile["robot_wins"] = int(self.profile.get("robot_wins", 0)) + 1
            self.profile["player_losses"] = int(self.profile.get("player_losses", 0)) + 1
        else:
            self.profile["draws"] = int(self.profile.get("draws", 0)) + 1

        self.profile["best_player_score"] = max(int(self.profile.get("best_player_score", 0)), int(self.player_score))
        self.profile["best_robot_score"] = max(int(self.profile.get("best_robot_score", 0)), int(self.robot_score))
        self.profile["best_level"] = max(int(self.profile.get("best_level", 1)), int(self.level))

        save_profile(self.profile)
        self.match_recorded = True

        if player_win:
            result_text = f"Mac sonucu kaydedildi: {self.player_name} kazandi"
        elif robot_win:
            result_text = "Mac sonucu kaydedildi: Robot kazandi"
        else:
            result_text = "Mac sonucu kaydedildi: Berabere"
        self.push_reason(result_text, "system")

    def _set_game_over(self, winner, reason):
        self.game_over = True
        self.game_winner = winner
        self.game_end_reason = reason

        if winner == "player":
            self.status = f"Tebrikler {self.player_name} kazandi"
        elif winner == "robot":
            self.status = "Tebrikler Robot kazandi"
        else:
            self.status = "Mac berabere bitti"

    def on_quit(self, _event=None):
        self.robot_ai.save_memory()
        save_audio_settings(self.audio_settings)
        self.music.stop()
        save_profile(self.profile)
        self.root.destroy()

    def restart_match(self, _event=None):
        # Yeni mac baslatilirken robotun ogrenme belleigi korunur.
        self.player_board = [[EMPTY for _ in range(COLS)] for _ in range(ROWS)]
        self.robot_board = [[EMPTY for _ in range(COLS)] for _ in range(ROWS)]

        self.player_score = 0
        self.robot_score = 0
        self.turn = 1
        self.level = 1

        self.current_num = spawn_value(self.level)
        self.next_num = spawn_value(self.level)

        self.player_col = COLS // 2
        self.player_fast = False
        self.player_shift_actions = 0

        self.robot_col = COLS // 2
        self.robot_fast = True
        self.robot_meta = None

        self.logger = GameLogger()

        self.flash_player = []
        self.flash_robot = []
        self.flash_until = 0.0
        self.player_impact_until = 0.0
        self.robot_impact_until = 0.0
        self.player_impact_color = "#34d399"
        self.robot_impact_color = "#f472b6"

        self.phase = "player_input"
        self.player_active_piece = None
        self.robot_active_piece = None
        self.player_result = None
        self.robot_result = None
        self.robot_target_col = COLS // 2
        self.normal_player_shift_actions = 0
        self.normal_turn_started_at = time.time()
        self.last_fall_tick = time.time()
        self.game_over = False
        self.game_winner = None
        self.game_end_reason = ""
        self.match_recorded = False
        self.last_input_time = time.time()
        self.last_idle_analysis = 0.0
        self.status = "Yeni mac basladi: insan hamlesini bekliyor"
        self.reason_feed.clear()
        self.last_proposal_banner = "Henüz öneri yok"

        self.push_reason("Yeni mac baslatildi. Robot belleigi korunarak oyun sifirlandi.", "system")
        self._initialize_turn_flow()

    def _is_normal_mode(self):
        return True

    def on_game_mode_changed(self):
        mode = self.game_mode_var.get()
        self.push_reason(f"Oyun modu degisti: {GAME_MODE_LABELS.get(mode, mode)}", "system")
        self.restart_match()

    def on_robot_profile_changed(self):
        profile = self.robot_profile_var.get()
        self.push_reason(f"Robot profili: {ROBOT_PROFILE_LABELS.get(profile, profile)}", "system")

    def _initialize_turn_flow(self):
        if self._is_normal_mode():
            self._start_normal_mode_turn()
        else:
            self.phase = "player_input"
            self.prepare_robot_move()

    def _can_place(self, board, col):
        return first_empty_from_bottom(board, col) is not None

    def _find_spawn_col(self, board, preferred_col):
        if 0 <= preferred_col < COLS and board[0][preferred_col] is EMPTY:
            return preferred_col
        for radius in range(1, COLS):
            left = preferred_col - radius
            right = preferred_col + radius
            if left >= 0 and board[0][left] is EMPTY:
                return left
            if right < COLS and board[0][right] is EMPTY:
                return right
        return None

    def _start_normal_mode_turn(self):
        if self.game_over:
            return

        self.phase = "falling"
        self.flash_player = []
        self.flash_robot = []
        self.normal_player_shift_actions = 0
        self.normal_turn_started_at = time.time()
        self.last_fall_tick = time.time()

        self.prepare_robot_move()
        self.robot_target_col = self.robot_col

        player_spawn_col = self._find_spawn_col(self.player_board, self.player_col)
        if player_spawn_col is None:
            self._set_game_over("robot", "Insan icin giris kolonu dolu")
            return

        robot_spawn_col = self._find_spawn_col(self.robot_board, COLS // 2)
        if robot_spawn_col is None:
            self._set_game_over("player", "Robot icin giris kolonu dolu")
            return

        self.player_col = player_spawn_col
        self.player_active_piece = {"row": 0, "col": player_spawn_col, "num": self.current_num}
        self.robot_active_piece = {"row": 0, "col": robot_spawn_col, "num": self.current_num}
        self.status = "Parcalar dusuyor: her iki taraf saga/sola hareket edebilir"

    def _can_active_move_side(self, board, piece, new_col):
        if piece is None:
            return False
        if not (0 <= new_col < COLS):
            return False
        return board[piece["row"]][new_col] is EMPTY

    def _active_can_fall(self, board, piece):
        if piece is None:
            return False
        next_row = piece["row"] + 1
        if next_row >= ROWS:
            return False
        return board[next_row][piece["col"]] is EMPTY

    def _resolve_locked_piece(self, board, num, row, col, level, visual_events):
        points = 0
        exploded_cells = 0
        explosion_count = 0

        if num == "J":
            if row + 1 < ROWS and board[row + 1][col] is not EMPTY:
                p, c, e = trigger_joker(board, row + 1, col, visual_events)
                points += p
                exploded_cells += c
                explosion_count += e
            else:
                board[row][col] = "J"
        elif num == "B":
            board[row][col] = "B"
            p, c, e = trigger_bomb(board, row, col, visual_events)
            points += p
            exploded_cells += c
            explosion_count += e
        else:
            board[row][col] = num

        after = self._resolve_after_lock(
            board,
            level,
            visual_events,
            joker_triggered=(num == "J"),
            bomb_triggered=(num == "B"),
        )

        points += after["points"]
        exploded_cells += after["cleared"]
        explosion_count += after["explosions"]

        return {
            "row": row,
            "col": col,
            "points": points,
            "exploded_cells": exploded_cells,
            "explosions": explosion_count,
            "combo_mult": after["combo_mult"],
        }

    def _normal_mode_step(self):
        if self.game_over or not self._is_normal_mode() or self.phase != "falling":
            return

        now = time.time()
        fall_delay = max(MIN_FALL_DELAY, BASE_FALL_DELAY - (self.level - 1) * 0.02)
        if now - self.last_fall_tick < fall_delay:
            return
        self.last_fall_tick = now

        if self.robot_active_piece is not None:
            target = self.robot_target_col
            current_col = self.robot_active_piece["col"]
            if target < current_col and self._can_active_move_side(self.robot_board, self.robot_active_piece, current_col - 1):
                self.robot_active_piece["col"] = current_col - 1
            elif target > current_col and self._can_active_move_side(self.robot_board, self.robot_active_piece, current_col + 1):
                self.robot_active_piece["col"] = current_col + 1

        if self.player_active_piece is not None:
            if self._active_can_fall(self.player_board, self.player_active_piece):
                self.player_active_piece["row"] += 1
            else:
                p = self.player_active_piece
                self.player_active_piece = None
                self.player_result = self._resolve_locked_piece(
                    self.player_board,
                    p["num"],
                    p["row"],
                    p["col"],
                    self.level,
                    self.flash_player,
                )

        if self.robot_active_piece is not None:
            if self._active_can_fall(self.robot_board, self.robot_active_piece):
                self.robot_active_piece["row"] += 1
            else:
                p = self.robot_active_piece
                self.robot_active_piece = None
                self.robot_result = self._resolve_locked_piece(
                    self.robot_board,
                    p["num"],
                    p["row"],
                    p["col"],
                    self.level,
                    self.flash_robot,
                )

        if self.player_active_piece is None and self.robot_active_piece is None:
            move_player = {
                "col": self.player_result.get("col", self.player_col),
                "fast": False,
                "shift_actions": self.normal_player_shift_actions,
                "auto_reason": "normal_continuous_fall",
            }
            move_robot = {
                "col": self.robot_result.get("col", self.robot_col),
                "fast": False,
                "shift_actions": 0,
                "auto_reason": "normal_continuous_fall",
            }
            self._finalize_turn(self.player_result, self.robot_result, move_player, move_robot)
            self.player_result = None
            self.robot_result = None

    def _drop_number(self, board, num, col, fast):
        row = first_empty_from_bottom(board, col)
        if row is None:
            return None

        if not fast:
            # yavas birakmada ustten asagi adim adim varmis gibi davranir
            r = 0
            while r < row and board[r + 1][col] is EMPTY:
                r += 1
            row = r

        board[row][col] = num
        return row

    def _resolve_after_lock(self, board, level, visual_events, joker_triggered=False, bomb_triggered=False):
        points = 0
        total_explosions = 0
        total_cleared = 0
        has_lock = False
        has_joker = joker_triggered
        has_bomb = bomb_triggered

        p, c, e = apply_sum9_explosions(board, visual_events)
        points += p
        total_cleared += c
        total_explosions += e

        p, c, e, lock_flag = apply_lock_explosions(board, visual_events, up_push_mode=False)
        points += p
        total_cleared += c
        total_explosions += e
        has_lock = has_lock or lock_flag

        if joker_triggered and total_cleared > 0:
            points += total_cleared

        p, c, e, lock_from_push = apply_up_push_if_needed(board, level, visual_events)
        points += p
        total_cleared += c
        total_explosions += e
        has_lock = has_lock or lock_from_push

        mult = combo_multiplier(total_explosions)
        if has_bomb and (has_joker or has_lock):
            mult *= 1.5

        final_points = int(points * mult)
        return {
            "points": final_points,
            "explosions": total_explosions,
            "cleared": total_cleared,
            "combo_mult": mult,
        }

    def _build_fx_wave(self, side, intensity):
        sample_rate = 22050
        duration = 0.18 if intensity >= 2 else 0.12
        total_samples = int(sample_rate * duration)
        start_freq = 780 if side == "player" else 430
        end_freq = 1240 if side == "player" else 300
        volume = 0.45 if intensity >= 2 else 0.32

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            for i in range(total_samples):
                t = i / sample_rate
                blend = i / max(1, total_samples - 1)
                freq = start_freq + (end_freq - start_freq) * blend
                env = max(0.0, 1.0 - blend * 1.2)
                tone = math.sin(2.0 * math.pi * freq * t)
                sample = int(32767 * volume * env * tone)
                wf.writeframesraw(struct.pack("<h", sample))
        return buffer.getvalue()

    def _play_explosion_sound(self, side, intensity):
        if winsound is None or not self._effects_enabled():
            return

        mode = self.sound_mode_var.get()

        def _beep_pattern():
            try:
                if mode == SOUND_MODE_FULL:
                    blob = self._build_fx_wave(side, intensity)
                    winsound.PlaySound(blob, winsound.SND_MEMORY)
                else:
                    if side == "player":
                        if intensity >= 2:
                            winsound.Beep(520, 55)
                            winsound.Beep(690, 75)
                            winsound.Beep(820, 95)
                        else:
                            winsound.Beep(630, 45)
                            winsound.Beep(760, 55)
                    else:
                        if intensity >= 2:
                            winsound.Beep(260, 65)
                            winsound.Beep(330, 80)
                            winsound.Beep(410, 100)
                        else:
                            winsound.Beep(320, 50)
                            winsound.Beep(380, 60)
            except Exception:
                pass

        threading.Thread(target=_beep_pattern, daemon=True).start()

    def _trigger_explosion_feedback(self, side, explosion_count, cleared_cells):
        if explosion_count <= 0 and cleared_cells <= 0:
            return
        if not self._effects_enabled():
            return

        big_blast = explosion_count >= 3 or cleared_cells >= 8
        if side == "player":
            self.player_impact_color = "#10b981" if big_blast else "#86efac"
            self.player_impact_until = time.time() + (0.34 if big_blast else 0.22)
        else:
            self.robot_impact_color = "#f43f5e" if big_blast else "#f9a8d4"
            self.robot_impact_until = time.time() + (0.34 if big_blast else 0.22)
        self._play_explosion_sound(side, 2 if big_blast else 1)

    def _apply_piece(self, board, num, col, fast, level, visual_events):
        row = self._drop_number(board, num, col, fast)
        if row is None:
            return None

        points = 0
        exploded_cells = 0
        explosion_count = 0

        if num == "J":
            if row + 1 < ROWS and board[row + 1][col] is not EMPTY:
                p, c, e = trigger_joker(board, row + 1, col, visual_events)
                points += p
                exploded_cells += c
                explosion_count += e
            else:
                board[row][col] = "J"
        elif num == "B":
            board[row][col] = "B"
            p, c, e = trigger_bomb(board, row, col, visual_events)
            points += p
            exploded_cells += c
            explosion_count += e
        else:
            board[row][col] = num

        after = self._resolve_after_lock(
            board,
            level,
            visual_events,
            joker_triggered=(num == "J"),
            bomb_triggered=(num == "B"),
        )

        points += after["points"]
        exploded_cells += after["cleared"]
        explosion_count += after["explosions"]

        return {
            "row": row,
            "col": col,
            "points": points,
            "exploded_cells": exploded_cells,
            "explosions": explosion_count,
            "combo_mult": after["combo_mult"],
        }

    def _robot_rule_bonus(self, robot_result):
        if not self.robot_meta:
            return 0.0
        potential = float(self.robot_meta.get("potential_explosions", 0) or 0)
        risk_val = float(self.robot_meta.get("risk", 0.0) or 0.0)
        cleared = float(robot_result.get("exploded_cells", 0) or 0)
        bonus = 0.0
        if potential > 0 and cleared > 0:
            bonus += 2.0
        bonus += min(3.0, cleared * 0.15)
        bonus += max(0.0, (0.45 - risk_val) * 2.0)
        if str(self.robot_meta.get("priority", "")).lower().startswith("g") and risk_val < 0.35:
            bonus += 1.0
        return bonus

    def _finalize_turn(self, player_result, robot_result, move_player, move_robot):
        if player_result is None or robot_result is None:
            self._set_game_over("draw", "Hamle uygulanamadi")
            return

        self.player_score += player_result["points"]
        self.robot_score += robot_result["points"]

        self._trigger_explosion_feedback("player", player_result["explosions"], player_result["exploded_cells"])
        self._trigger_explosion_feedback("robot", robot_result["explosions"], robot_result["exploded_cells"])

        self.level = max(1, max(self.player_score, self.robot_score) // 60 + 1)

        strategy_update = "none"
        if self.robot_meta and self.robot_meta.get("used_proposal"):
            strategy_update = "new_strategy_applied"
        elif self.robot_meta and self.robot_meta.get("proposal"):
            strategy_update = "proposal_evaluated_rejected"

        if self.robot_meta and isinstance(self.robot_meta.get("x"), list):
            mode = self.game_mode_var.get()
            profile = self.robot_profile_var.get()
            player_points = float(player_result.get("points", 0) or 0)
            robot_points = float(robot_result.get("points", 0) or 0)
            penalty = max(0.0, player_points - robot_points)
            risk_penalty = max(0.0, float(self.robot_meta.get("risk", 0.0)) * 2.0)
            score_gap = robot_points - player_points
            rule_bonus = self._robot_rule_bonus(robot_result)
            potential = float(self.robot_meta.get("potential_explosions", 0) or 0)
            risk_val = float(self.robot_meta.get("risk", 0.0) or 0.0)
            guided_reward = robot_points
            if mode == GAME_MODE_NORMAL:
                guided_reward = robot_points - (penalty * 0.45) - risk_penalty + (rule_bonus * 0.5)
            elif mode == GAME_MODE_HARD:
                guided_reward = (robot_points * 1.35) + (score_gap * 0.85) - (penalty * 1.15) - (risk_penalty * 1.35) + (rule_bonus * 1.25)
                if profile == ROBOT_PROFILE_AGGRESSIVE:
                    guided_reward += (potential * 0.8) + (max(0.0, score_gap) * 0.35)
                elif profile == ROBOT_PROFILE_DEFENSIVE:
                    guided_reward += (max(0.0, 0.50 - risk_val) * 1.8) - (max(0.0, -score_gap) * 0.25)
                else:
                    guided_reward += (max(0.0, 0.40 - risk_val) * 1.0) + (score_gap * 0.2)
            self.robot_ai.learn_from_move(
                self.robot_meta["x"],
                guided_reward,
                self.robot_meta.get("strategy", "balance"),
            )

        player_log = self._compose_log_entry(
            "Human",
            self.player_board,
            self.current_num,
            self.next_num,
            "human",
            move_player,
            player_result,
            "Insan, gelen sayiyi stratejik konuma birakti",
            {
                "strategy_update": "none",
                "potential_explosions": potential_sum9_count(self.player_board, self.current_num, move_player["col"]),
                "risk": risk_score(self.player_board, move_player["col"]),
                "priority": "Kullanici tercihi",
                "proposal_decision": "N/A",
            },
        )

        robot_logic = self.robot_meta.get("reason", "Robot secimi") if self.robot_meta else "Robot secimi"
        robot_extra = {
            "strategy_update": strategy_update,
            "potential_explosions": self.robot_meta.get("potential_explosions", 0) if self.robot_meta else 0,
            "risk": self.robot_meta.get("risk", 0.0) if self.robot_meta else 0.0,
            "priority": self.robot_meta.get("priority", "N/A") if self.robot_meta else "N/A",
            "proposal": self.robot_meta.get("proposal", None) if self.robot_meta else None,
            "proposal_decision": self.robot_meta.get("decision", "N/A") if self.robot_meta else "N/A",
            "robot_features": self.robot_meta.get("x", None) if self.robot_meta else None,
        }
        robot_log = self._compose_log_entry(
            "Robot",
            self.robot_board,
            self.current_num,
            self.next_num,
            self.robot_meta.get("strategy", "balance") if self.robot_meta else "balance",
            move_robot,
            robot_result,
            robot_logic,
            robot_extra,
        )

        self.logger.write(player_log)
        self.logger.write(robot_log)

        self.push_reason(
            f"Tur {self.turn}: Insan +{player_result['points']} puan, Robot +{robot_result['points']} puan, robot karar={robot_extra.get('proposal_decision', 'N/A')}",
            "result",
        )
        if self.robot_meta and self.robot_meta.get("proposal"):
            p = self.robot_meta["proposal"]
            decision_type = "applied" if self.robot_meta.get("used_proposal") else "rejected"
            self.push_reason(
                f"Yeni strateji onerisi goruldu: {p['candidate']['name']} ({p.get('engine_name', 'unknown')}) -> {'uygulandi' if self.robot_meta.get('used_proposal') else 'reddedildi'}",
                decision_type,
            )

        self.flash_until = time.time() + 0.34

        if self.turn > 10:
            player_top = board_touches_top(self.player_board)
            robot_top = board_touches_top(self.robot_board)
            if player_top and not robot_top:
                self._set_game_over("robot", "Insan ust satira ulasti ve kaybetti")
            elif robot_top and not player_top:
                self._set_game_over("player", "Robot ust satira ulasti ve kaybetti")
            elif player_top and robot_top:
                self._set_game_over("draw", "Iki taraf da ust satira ulasti")

            player_pieces = piece_count(self.player_board)
            robot_pieces = piece_count(self.robot_board)
            if not self.game_over:
                if player_pieces <= 1 and robot_pieces > 1:
                    self._set_game_over("player", "Insan tahtada 1/0 tasla kazandi")
                elif robot_pieces <= 1 and player_pieces > 1:
                    self._set_game_over("robot", "Robot tahtada 1/0 tasla kazandi")
                elif player_pieces <= 1 and robot_pieces <= 1:
                    self._set_game_over("draw", "Iki taraf da 1/0 tasa indi")

        self.turn += 1
        self.current_num = self.next_num
        self.next_num = spawn_value(self.level)

        self.player_col = COLS // 2
        self.player_fast = False
        self.player_shift_actions = 0

        self.robot_ai.save_memory()

        if self.game_over:
            return

        self.last_input_time = time.time()
        self._initialize_turn_flow()

    def _compose_log_entry(self, player_type, board, num, next_num, strategy, move, result, logic, extra):
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "turn": self.turn,
            "player": player_type,
            "num": num,
            "next_num": next_num,
            "board": clone_board(board),
            "open_strategies": self.robot_ai.strategy_engine.active_count(),
            "selected_strategy": strategy,
            "move_decision": move,
            "points": result.get("points", 0),
            "exploded_cells": result.get("exploded_cells", 0),
            "explosions": result.get("explosions", 0),
            "strategy_update": extra.get("strategy_update", "none"),
            "logic": logic,
            "potential_explosions": extra.get("potential_explosions", 0),
            "risk": extra.get("risk", 0.0),
            "priority": extra.get("priority", "N/A"),
            "proposal": extra.get("proposal", None),
            "proposal_decision": extra.get("proposal_decision", "N/A"),
            "robot_features": extra.get("robot_features", None),
        }

    def prepare_robot_move(self):
        col, meta = self.robot_ai.choose_action(
            self.robot_board,
            self.current_num,
            self.next_num,
            self.level,
            game_mode=self.game_mode_var.get(),
            robot_profile=self.robot_profile_var.get(),
        )
        self.robot_col = col
        self.robot_fast = True
        self.robot_meta = meta
        if meta and meta.get("proposal"):
            engine = meta["proposal"].get("engine_name", "unknown")
            self.last_proposal_banner = f"Oneri: {meta['proposal']['candidate']['name']} [{engine}] -> Sutun {meta['proposal']['col']}"
        else:
            self.last_proposal_banner = "Bu tur yeni strateji onerisi yok"

        if meta:
            self.push_reason(
                f"Robot secimi: sutun {self.robot_col}, strateji {meta.get('strategy', 'N/A')}, karar {meta.get('decision', 'N/A')}, oncelik {meta.get('priority', 'N/A')}, risk {meta.get('risk', 0)}",
                "decision",
            )

    def perform_turn(self, human_fast=False, auto_reason=None):
        if self.game_over:
            return

        self.flash_player = []
        self.flash_robot = []

        if not self._can_place(self.player_board, self.player_col):
            self._set_game_over("robot", "Insan icin giris kolonu dolu")
            return
        if not self._can_place(self.robot_board, self.robot_col):
            self._set_game_over("player", "Robot icin giris kolonu dolu")
            return

        player_result = self._apply_piece(
            self.player_board,
            self.current_num,
            self.player_col,
            human_fast,
            self.level,
            self.flash_player,
        )
        robot_result = self._apply_piece(
            self.robot_board,
            self.current_num,
            self.robot_col,
            self.robot_fast,
            self.level,
            self.flash_robot,
        )

        move_player = {
            "col": self.player_col,
            "fast": bool(human_fast),
            "shift_actions": self.player_shift_actions,
            "auto_reason": auto_reason,
        }
        move_robot = {
            "col": self.robot_col,
            "fast": bool(self.robot_fast),
            "shift_actions": 0,
            "auto_reason": None,
        }
        self._finalize_turn(player_result, robot_result, move_player, move_robot)

    def _draw_board(self, board, x0, y0, title, active_col=None, active_num=None, active_piece=None, flash_cells=None, flash_style="player"):
        self.canvas.create_text(x0, y0 - 22, anchor="nw", text=title, fill="#e5e7eb", font=("Segoe UI", 13, "bold"))
        self.canvas.create_rectangle(x0 - 2, y0 - 2, x0 + BOARD_W + 2, y0 + BOARD_H + 2, outline="#94a3b8", width=2)

        flash_set = set(flash_cells or [])
        flashing = time.time() < self.flash_until
        pulse = int(time.time() * 28) % 2

        for r in range(ROWS):
            for c in range(COLS):
                v = board[r][c]
                x1 = x0 + c * CELL
                y1 = y0 + r * CELL
                x2 = x1 + CELL
                y2 = y1 + CELL

                fill, label = color_for(v)
                if active_col is not None and active_num is not None and r == 0 and c == active_col and v is EMPTY and not self.game_over:
                    afill, alabel = color_for(active_num)
                    fill = afill
                    label = alabel
                if (
                    active_piece is not None
                    and r == active_piece.get("row")
                    and c == active_piece.get("col")
                    and v is EMPTY
                    and not self.game_over
                ):
                    afill, alabel = color_for(active_piece.get("num"))
                    fill = afill
                    label = alabel

                if flashing and (r, c) in flash_set:
                    if flash_style == "player":
                        fill = "#ecfdf5" if pulse == 0 else "#86efac"
                    else:
                        fill = "#fff1f2" if pulse == 0 else "#fda4af"

                self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline="#0b1220", width=1)
                if label:
                    self.canvas.create_text((x1 + x2) // 2, (y1 + y2) // 2, text=label, fill="#f8fafc", font=("Segoe UI", 12, "bold"))

                if flashing and (r, c) in flash_set and pulse == 1:
                    marker = "+X" if flash_style == "player" else "X+"
                    self.canvas.create_text(
                        (x1 + x2) // 2,
                        (y1 + y2) // 2,
                        text=marker,
                        fill="#0f172a",
                        font=("Consolas", 10, "bold"),
                    )

    def draw(self):
        self.canvas.delete("all")

        # Pencere buyudukce sag panel ve alt akis alani da genisler.
        win_w = max(WIN_W, self.canvas.winfo_width())
        win_h = max(WIN_H, self.canvas.winfo_height())
        extra_w = max(0, win_w - WIN_W)
        right_x = RIGHT_X + (extra_w // 2)
        panel_x = PANEL_X + extra_w

        self.canvas.create_text(BOARD_PADDING, 10, anchor="nw", text="Sayisal Tetris V3 - Human vs Robot (Windows)", fill="#f8fafc", font=("Segoe UI", 16, "bold"))

        self._draw_board(
            self.player_board,
            LEFT_X,
            TOP_Y,
            self.player_name,
            active_col=self.player_col if self.phase == "player_input" and not self.game_over else None,
            active_num=self.current_num,
            active_piece=self.player_active_piece if self._is_normal_mode() else None,
            flash_cells=self.flash_player,
            flash_style="player",
        )

        self._draw_board(
            self.robot_board,
            right_x,
            TOP_Y,
            "Robot",
            active_col=self.robot_col if self.phase == "player_input" and not self.game_over else None,
            active_num=self.current_num,
            active_piece=self.robot_active_piece if self._is_normal_mode() else None,
            flash_cells=self.flash_robot,
            flash_style="robot",
        )

        # Orta panel: tur/seviye + anlik sayi kutulari
        mid_x1 = LEFT_X + BOARD_W + 16
        mid_x2 = right_x - 16
        if mid_x2 - mid_x1 < 170:
            mid_x2 = mid_x1 + 170
        mid_y1 = TOP_Y
        mid_y2 = TOP_Y + 230
        mid_cx = (mid_x1 + mid_x2) // 2

        self.canvas.create_rectangle(mid_x1, mid_y1, mid_x2, mid_y2, outline="#475569", width=2, fill="#111827")
        self.canvas.create_text(mid_cx, mid_y1 + 18, text=f"Tur: {self.turn}   Seviye: {self.level}", fill="#cbd5e1", font=("Segoe UI", 11, "bold"))
        self.canvas.create_text(mid_cx, mid_y1 + 40, text=f"{self.player_name}: {self.player_score}   |   Robot: {self.robot_score}", fill="#e5e7eb", font=("Segoe UI", 10, "bold"))

        self.canvas.create_text(mid_x1 + 20, mid_y1 + 68, anchor="nw", text="Gelen", fill="#cbd5e1", font=("Segoe UI", 10, "bold"))
        cfill, clabel = color_for(self.current_num)
        self.canvas.create_rectangle(mid_x1 + 14, mid_y1 + 86, mid_x1 + 14 + CELL * 2, mid_y1 + 86 + CELL * 2, fill=cfill, outline="#334155", width=2)
        if clabel:
            self.canvas.create_text(mid_x1 + 14 + CELL, mid_y1 + 86 + CELL, text=clabel, fill="#f8fafc", font=("Segoe UI", 14, "bold"))

        self.canvas.create_text(mid_x2 - 20 - CELL * 2, mid_y1 + 68, anchor="nw", text="Sonraki", fill="#cbd5e1", font=("Segoe UI", 10, "bold"))
        nfill, nlabel = color_for(self.next_num)
        self.canvas.create_rectangle(mid_x2 - 14 - CELL * 2, mid_y1 + 86, mid_x2 - 14, mid_y1 + 86 + CELL * 2, fill=nfill, outline="#334155", width=2)
        if nlabel:
            self.canvas.create_text(mid_x2 - 14 - CELL, mid_y1 + 86 + CELL, text=nlabel, fill="#f8fafc", font=("Segoe UI", 14, "bold"))

        self.canvas.create_text(mid_cx, mid_y1 + 170, text=f"Durum: {self.status}", fill="#93c5fd", font=("Segoe UI", 9, "bold"), width=max(130, mid_x2 - mid_x1 - 16))

        nx = panel_x
        ny = TOP_Y

        lines = [
            "Profil ve Robot Durumu",
            "",
            "Kontroller",
            "A/D: Kaydir  |  S: Hizli  |  Space: Normal",
            "B: Bekleme Modu  |  R: Yeni Mac  |  Q/Esc: Cikis",
            "",
            f"Oyuncu: {self.player_name}",
            f"Toplam mac: {int(self.profile.get('total_matches', 0))}",
            f"{self.player_name} W/L: {int(self.profile.get('player_wins', 0))}/{int(self.profile.get('player_losses', 0))}",
            f"Robot W/L: {int(self.profile.get('robot_wins', 0))}/{int(self.profile.get('robot_losses', 0))}",
            f"Berabere: {int(self.profile.get('draws', 0))}",
            f"En yuksek skor ({self.player_name}): {int(self.profile.get('best_player_score', 0))}",
            f"En yuksek skor (Robot): {int(self.profile.get('best_robot_score', 0))}",
            f"En yuksek seviye: {int(self.profile.get('best_level', 1))}",
            "",
            f"Oyun modu: {GAME_MODE_LABELS.get(self.game_mode_var.get(), self.game_mode_var.get())}",
            f"Robot profili: {ROBOT_PROFILE_LABELS.get(self.robot_profile_var.get(), self.robot_profile_var.get())}",
            f"Hedef: {self.robot_meta.get('objective', 'Veri toplama') if self.robot_meta else 'Veri toplama'}",
            f"Profil davranisi: {self.robot_meta.get('profile_style', 'Dengeli risk ve puan') if self.robot_meta else 'Dengeli risk ve puan'}",
            f"Skor itkisi: {self.robot_meta.get('score_drive', 0) if self.robot_meta else 0} | Guvenlik itkisi: {self.robot_meta.get('safety_drive', 0) if self.robot_meta else 0}",
            "",
            f"Robot strateji havuzu: {self.robot_ai.strategy_engine.active_count()}",
            f"Strateji Slotlari: ACIK {self.robot_ai.strategy_engine.active_count()} / KAPALI {max(0, 30 - self.robot_ai.strategy_engine.active_count())}",
            f"Oneri motoru sayisi: {self.robot_ai.strategy_engine.proposal_engine_count()}",
            f"Oneri Kapisi: {'ACIK' if self.robot_meta and self.robot_meta.get('proposal') else 'KAPALI'}",
            f"Model guncelleme: {self.robot_ai.total_updates}",
            f"Son egitim hatasi: {self.robot_ai.last_train_error:.4f}",
            f"Bekleme modu: {'ACIK' if self.wait_mode_var.get() else 'KAPALI'}",
            f"Akis filtresi: {self.feed_filter_var.get()}",
            "",
            f"Son onerisi: {self.last_proposal_banner}",
            f"Log dosyasi: {os.path.basename(self.logger.path)}",
        ]

        y = ny + 14
        row_step = 20 if win_h >= 940 else 18
        for i, line in enumerate(lines):
            self.canvas.create_text(
                nx,
                y + i * row_step,
                anchor="nw",
                text=line,
                fill="#cbd5e1" if i != 0 else "#e2e8f0",
                font=("Segoe UI", 11 if i != 0 else 12, "bold" if i == 0 else "normal"),
            )

        info_bottom = y + len(lines) * row_step

        if self.game_over:
            bx1 = LEFT_X + 80
            by1 = TOP_Y + 210
            bx2 = right_x + BOARD_W - 80
            by2 = by1 + 175
            self.canvas.create_rectangle(bx1, by1, bx2, by2, fill="#111827", outline="#f87171", width=2)
            self.canvas.create_text((bx1 + bx2) // 2, by1 + 38, text="GAME OVER", fill="#fca5a5", font=("Segoe UI", 24, "bold"))
            self.canvas.create_text(
                (bx1 + bx2) // 2,
                by1 + 80,
                text=f"{self.player_name} {self.player_score}  |  Robot {self.robot_score}",
                fill="#e5e7eb",
                font=("Segoe UI", 13, "bold"),
            )
            self.canvas.create_text((bx1 + bx2) // 2, by1 + 108, text=self.status, fill="#86efac", font=("Segoe UI", 12, "bold"))
            self.canvas.create_text((bx1 + bx2) // 2, by1 + 128, text=f"Neden: {self.game_end_reason}", fill="#cbd5e1", font=("Segoe UI", 10))
            if self.game_winner in ("player", "robot"):
                winner_score = self.player_score if self.game_winner == "player" else self.robot_score
                loser_score = self.robot_score if self.game_winner == "player" else self.player_score
                if winner_score < loser_score:
                    self.canvas.create_text(
                        (bx1 + bx2) // 2,
                        by1 + 146,
                        text="Not: Kazanan bitis kuralina gore belirlenir, yalnizca skora gore degil.",
                        fill="#fcd34d",
                        font=("Segoe UI", 10, "bold"),
                    )
            self.canvas.create_text((bx1 + bx2) // 2, by1 + 162, text="R tusu veya Ozellikler > Yeniden Baslat ile yeni maca gec", fill="#93c5fd", font=("Segoe UI", 10, "bold"))

        feed_x1 = LEFT_X + 140
        # Robot bildirim panelini iki sayi yuksekligi kadar daha asagi al.
        feed_height_reduction = CELL * 6
        feed_y1 = max(TOP_Y + BOARD_H - 120, info_bottom + 8) + feed_height_reduction
        feed_x2 = min(win_w - 28, panel_x - 70)
        if feed_x2 - feed_x1 < 240:
            feed_x2 = feed_x1 + 240
        feed_y2 = win_h - 20
        if feed_y2 - feed_y1 < 90:
            feed_y1 = feed_y2 - 90
        self.canvas.create_rectangle(feed_x1, feed_y1, feed_x2, feed_y2, outline="#475569", width=2, fill="#0f172a")
        self.canvas.create_text(feed_x1 + 10, feed_y1 + 8, anchor="nw", text="Robot Akil Yurutme Akisi", fill="#cbd5e1", font=("Segoe UI", 11, "bold"))

        if time.time() < self.player_impact_until:
            self.canvas.create_rectangle(
                LEFT_X,
                TOP_Y,
                LEFT_X + BOARD_W,
                TOP_Y + BOARD_H,
                fill=self.player_impact_color,
                stipple="gray50",
                outline="",
            )

        if time.time() < self.robot_impact_until:
            self.canvas.create_rectangle(
                right_x,
                TOP_Y,
                right_x + BOARD_W,
                TOP_Y + BOARD_H,
                fill=self.robot_impact_color,
                stipple="gray50",
                outline="",
            )

        filtered_feed = self.get_filtered_reason_feed()
        feed_line_step = 19
        max_feed_rows = max(1, int((feed_y2 - feed_y1 - 36) / feed_line_step))
        for i, item in enumerate(filtered_feed[-max_feed_rows:]):
            line = f"[{item['time']}] ({item['type']}) {item['text']}"
            self.canvas.create_text(
                feed_x1 + 10,
            feed_y1 + 32 + i * feed_line_step,
                anchor="nw",
                text=line,
                fill="#93c5fd",
                font=("Consolas", 10),
                width=max(120, feed_x2 - feed_x1 - 20),
            )

    def _idle_analyze_if_needed(self):
        if self.game_over or self.phase != "player_input":
            return

        now = time.time()
        idle = now - self.last_input_time
        if idle < IDLE_ANALYZE_SECONDS:
            return
        if now - self.last_idle_analysis < IDLE_ANALYZE_SECONDS:
            return

        trained, reward, robot_replays, human_replays = self.robot_ai.analyze_previous_logs()
        self.last_idle_analysis = now
        self.status = (
            f"Boslukta analiz: {trained} replay (Robot {robot_replays}, Insan {human_replays}), "
            f"toplam odul {int(reward)}"
        )
        self.push_reason(self.status, "analysis")

        if not self.wait_mode_var.get():
            self.perform_turn(human_fast=False, auto_reason="5s_idle_auto_drop")

    def on_left(self, _event=None):
        if self.game_over:
            return
        if self._is_normal_mode() and self.phase == "falling":
            if self.player_active_piece and self._can_active_move_side(self.player_board, self.player_active_piece, self.player_active_piece["col"] - 1):
                self.player_active_piece["col"] -= 1
                self.normal_player_shift_actions += 1
                self.last_input_time = time.time()
            return
        if self.phase != "player_input":
            return
        if self.player_col > 0:
            self.player_col -= 1
            self.player_shift_actions += 1
            self.last_input_time = time.time()
            if self.player_shift_actions >= MAX_SHIFT_ACTIONS:
                self.perform_turn(human_fast=False, auto_reason="max_shift_auto_drop")

    def on_right(self, _event=None):
        if self.game_over:
            return
        if self._is_normal_mode() and self.phase == "falling":
            if self.player_active_piece and self._can_active_move_side(self.player_board, self.player_active_piece, self.player_active_piece["col"] + 1):
                self.player_active_piece["col"] += 1
                self.normal_player_shift_actions += 1
                self.last_input_time = time.time()
            return
        if self.phase != "player_input":
            return
        if self.player_col < COLS - 1:
            self.player_col += 1
            self.player_shift_actions += 1
            self.last_input_time = time.time()
            if self.player_shift_actions >= MAX_SHIFT_ACTIONS:
                self.perform_turn(human_fast=False, auto_reason="max_shift_auto_drop")

    def on_drop_fast(self, _event=None):
        if self.game_over:
            return
        if self._is_normal_mode() and self.phase == "falling":
            self.last_input_time = time.time()
            if self.player_active_piece and self._active_can_fall(self.player_board, self.player_active_piece):
                self.player_active_piece["row"] += 1
            if self.robot_active_piece and self._active_can_fall(self.robot_board, self.robot_active_piece):
                self.robot_active_piece["row"] += 1
            return
        if self.phase != "player_input":
            return
        self.last_input_time = time.time()
        self.perform_turn(human_fast=True, auto_reason=None)

    def on_drop_normal(self, _event=None):
        if self.game_over:
            return
        if self._is_normal_mode() and self.phase == "falling":
            return
        if self.phase != "player_input":
            return
        self.last_input_time = time.time()
        self.perform_turn(human_fast=False, auto_reason=None)

    def tick(self):
        if self._is_normal_mode():
            self._normal_mode_step()
        else:
            self._idle_analyze_if_needed()
        if self._music_enabled():
            self.music.update()
        if self.game_over and not self.match_recorded:
            self._record_match_result()
        self.draw()
        self.root.after(33, self.tick)


def main():
    root = tk.Tk()
    app = VersusGame(root)
    root.protocol("WM_DELETE_WINDOW", app.on_quit)
    root.mainloop()


if __name__ == "__main__":
    main()
