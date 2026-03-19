import json
import os
import statistics
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


class BreakpointMomentumAgent:
    """Historical + live cross-analysis agent for player/robot turning-point detection."""

    def __init__(self, root_dir, log_dir, memory_dir):
        self.root_dir = root_dir
        self.log_dir = log_dir
        self.memory_dir = memory_dir
        self.gazi_dir = os.path.join(self.log_dir, "gazi")
        self.agent_log_path = os.path.join(self.gazi_dir, "breakpoint_agent_log.jsonl")

        self.historical_profiles = {10: {}, 20: {}, 30: {}}
        self.rulebook = {10: [], 20: [], 30: []}
        self.recent_human = deque(maxlen=120)
        self.recent_robot = deque(maxlen=120)
        self.last_signal = {}

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

    def _candidate_log_dirs(self):
        dirs = []
        if os.path.isdir(self.log_dir):
            dirs.append(self.log_dir)
        alt_dist_logs = os.path.join(self.root_dir, "dist", "logs")
        if os.path.isdir(alt_dist_logs):
            dirs.append(alt_dist_logs)
        return dirs

    def _iter_log_files(self):
        files = []
        for d in self._candidate_log_dirs():
            try:
                for name in os.listdir(d):
                    if not str(name).lower().endswith(".jsonl"):
                        continue
                    if "gazi" in str(name).lower() or "breakpoint" in str(name).lower():
                        continue
                    files.append(os.path.join(d, name))
            except Exception:
                continue
        files = sorted(set(files), key=lambda p: os.path.getmtime(p))
        return files

    def _parse_file(self, fp):
        rows = []
        try:
            with open(fp, "r", encoding="utf-8") as f:
                for line in f:
                    raw = line.strip()
                    if not raw:
                        continue
                    try:
                        item = json.loads(raw)
                    except Exception:
                        continue
                    rows.append(item)
        except Exception:
            return []
        return rows

    def _window_rows(self, rows, n):
        humans = [x for x in rows if x.get("player") == "Human"]
        if len(humans) < n:
            return []
        return humans[-n:]

    def _cluster_ratio(self, rows):
        cols = []
        for row in rows:
            move = row.get("move_decision") or {}
            c = move.get("col")
            if isinstance(c, int):
                cols.append(c)
        if len(cols) <= 1:
            return 0.0
        close_steps = 0
        for i in range(1, len(cols)):
            if abs(cols[i] - cols[i - 1]) <= 1:
                close_steps += 1
        return close_steps / max(1, len(cols) - 1)

    def _special_usage_rate(self, rows):
        if not rows:
            return 0.0
        cnt = 0
        for row in rows:
            num = row.get("num")
            if num in ("J", "B", "L"):
                cnt += 1
        return cnt / max(1, len(rows))

    def _special_tile_intent_metrics(self, rows):
        special_rows = [x for x in rows if x.get("num") in ("J", "B", "L")]
        total = len(special_rows)
        if total <= 0:
            return {
                "special_total": 0,
                "special_effective": 0,
                "special_wasted": 0,
                "special_logic_score": 0.5,
                "special_types": {},
            }

        effective = 0
        wasted = 0
        kind_counter = Counter()
        for row in special_rows:
            kind = str(row.get("num"))
            kind_counter[kind] += 1
            exploded = float(row.get("exploded_cells", 0) or 0)
            expl = float(row.get("explosions", 0) or 0)
            points = float(row.get("points", 0) or 0)

            # Ozel tas, gercek bir temizleme/puan avantajina donustuyse mantikli kabul edilir.
            if expl >= 1 or exploded >= 3 or points >= 9:
                effective += 1
            if expl <= 0 and exploded <= 0 and points <= 2:
                wasted += 1

        logic_score = effective / max(1, total)
        return {
            "special_total": total,
            "special_effective": effective,
            "special_wasted": wasted,
            "special_logic_score": logic_score,
            "special_types": dict(kind_counter),
        }

    def _sum9_intent_metrics(self, rows):
        numeric_rows = [x for x in rows if isinstance(x.get("num"), int)]
        total = len(numeric_rows)
        if total <= 0:
            return {
                "sum9_intent_rate": 0.0,
                "sum9_non_intent_rate": 0.0,
                "sum9_intent_count": 0,
            }

        intent_count = 0
        for row in numeric_rows:
            potential = float(row.get("potential_explosions", 0) or 0)
            if potential >= 1.0:
                intent_count += 1

        intent_rate = intent_count / max(1, total)
        return {
            "sum9_intent_rate": intent_rate,
            "sum9_non_intent_rate": max(0.0, 1.0 - intent_rate),
            "sum9_intent_count": intent_count,
        }

    def _future_planning_metrics(self, rows, horizon=3):
        if not rows:
            return {
                "future_data_coverage": 0.0,
                "future_plan_rate": 0.0,
                "future_plan_candidates": 0,
                "future_plan_hits": 0,
            }

        with_future = 0
        plan_candidates = 0
        plan_hits = 0

        for i, row in enumerate(rows):
            has_future = ("next_num" in row) or ("next_next_num" in row)
            if has_future:
                with_future += 1

            # Mevcut hamlede aninda patlama yoksa ama sonraki hamlelerde getirisi varsa "planlama" sinyali.
            potential = float(row.get("potential_explosions", 0) or 0)
            if potential > 0.0:
                continue
            plan_candidates += 1

            hit = False
            upper = min(len(rows), i + 1 + max(1, horizon))
            for j in range(i + 1, upper):
                nxt = rows[j]
                n_points = float(nxt.get("points", 0) or 0)
                n_expl = float(nxt.get("explosions", 0) or 0)
                n_combo = float(nxt.get("combo_mult", 1.0) or 1.0)
                if n_expl >= 1 or n_points >= 10 or n_combo >= 1.25:
                    hit = True
                    break
            if hit:
                plan_hits += 1

        return {
            "future_data_coverage": with_future / max(1, len(rows)),
            "future_plan_rate": plan_hits / max(1, plan_candidates),
            "future_plan_candidates": plan_candidates,
            "future_plan_hits": plan_hits,
        }

    def _explosion_value(self, row):
        exploded = float(row.get("exploded_cells", 0) or 0)
        explosions = float(row.get("explosions", 0) or 0)
        combo = float(row.get("combo_mult", 1.0) or 1.0)
        return (exploded * 0.6) + (explosions * 1.8) + (max(0.0, combo - 1.0) * 2.2)

    def _summarize_window(self, rows):
        if not rows:
            return {
                "count": 0,
                "avg_points": 0.0,
                "avg_exploded_cells": 0.0,
                "avg_explosions": 0.0,
                "avg_combo": 0.0,
                "avg_explosion_value": 0.0,
                "special_usage_rate": 0.0,
                "cluster_ratio": 0.0,
                "top_cols": [],
                "special_logic_score": 0.0,
                "special_wasted": 0,
                "sum9_intent_rate": 0.0,
                "sum9_non_intent_rate": 0.0,
                "future_plan_rate": 0.0,
                "future_data_coverage": 0.0,
            }

        points = [float(x.get("points", 0) or 0) for x in rows]
        exploded_cells = [float(x.get("exploded_cells", 0) or 0) for x in rows]
        explosions = [float(x.get("explosions", 0) or 0) for x in rows]
        combos = [float(x.get("combo_mult", 1.0) or 1.0) for x in rows]
        explosion_values = [self._explosion_value(x) for x in rows]

        col_counter = Counter()
        for row in rows:
            mv = row.get("move_decision") or {}
            c = mv.get("col")
            if isinstance(c, int):
                col_counter[c] += 1

        special = self._special_tile_intent_metrics(rows)
        sum9 = self._sum9_intent_metrics(rows)
        planning = self._future_planning_metrics(rows)

        return {
            "count": len(rows),
            "avg_points": statistics.fmean(points) if points else 0.0,
            "avg_exploded_cells": statistics.fmean(exploded_cells) if exploded_cells else 0.0,
            "avg_explosions": statistics.fmean(explosions) if explosions else 0.0,
            "avg_combo": statistics.fmean(combos) if combos else 0.0,
            "avg_explosion_value": statistics.fmean(explosion_values) if explosion_values else 0.0,
            "special_usage_rate": self._special_usage_rate(rows),
            "cluster_ratio": self._cluster_ratio(rows),
            "top_cols": [c for c, _ in col_counter.most_common(3)],
            "special_logic_score": special.get("special_logic_score", 0.0),
            "special_wasted": int(special.get("special_wasted", 0) or 0),
            "sum9_intent_rate": sum9.get("sum9_intent_rate", 0.0),
            "sum9_non_intent_rate": sum9.get("sum9_non_intent_rate", 0.0),
            "future_plan_rate": planning.get("future_plan_rate", 0.0),
            "future_data_coverage": planning.get("future_data_coverage", 0.0),
        }

    def _infer_objective(self, profile):
        ev = float(profile.get("avg_explosion_value", 0.0) or 0.0)
        special = float(profile.get("special_usage_rate", 0.0) or 0.0)
        special_logic = float(profile.get("special_logic_score", 0.0) or 0.0)
        cluster = float(profile.get("cluster_ratio", 0.0) or 0.0)
        combo = float(profile.get("avg_combo", 0.0) or 0.0)
        planning = float(profile.get("future_plan_rate", 0.0) or 0.0)
        sum9_intent = float(profile.get("sum9_intent_rate", 0.0) or 0.0)

        if ev >= 6.0 and combo >= 1.25:
            return "zincir_patlama_uzerinden_skor"
        if special >= 0.22 and special_logic >= 0.55:
            return "ozel_tas_tetikleme_odakli"
        if special >= 0.22 and special_logic < 0.45:
            return "ozel_tas_israfina_egilim"
        if planning >= 0.45 and sum9_intent >= 0.35:
            return "gelecek_tasa_gore_kurulum"
        if cluster >= 0.68:
            return "yigin_kurup_alan_kapatma"
        return "dengeli_ilerleme"

    def _build_rules(self, profile, window):
        rules = []
        objective = self._infer_objective(profile)
        sum9_rate = float(profile.get("sum9_intent_rate", 0.0) or 0.0)
        planning = float(profile.get("future_plan_rate", 0.0) or 0.0)
        special_logic = float(profile.get("special_logic_score", 0.0) or 0.0)

        if objective == "zincir_patlama_uzerinden_skor":
            rules.append("Oyuncu patlama verimini kullanarak skor topluyor")
            rules.append("Robot risk dengeleme ve tahtayi acik tutma agirligini arttirmali")
        if objective == "ozel_tas_tetikleme_odakli":
            rules.append("Oyuncu ozel taslari surekli avantaj penceresinde kullaniyor")
            rules.append("Robot ozel tas sonrasi bosluk olusumuna gore kolon hedeflemeli")
        if objective == "ozel_tas_israfina_egilim":
            rules.append("Oyuncu ozel tasi etkisiz kullaniyor; robot kontrayi hizlandirabilir")
            rules.append("Robot agresif skor penceresini one cekebilir")
        if objective == "gelecek_tasa_gore_kurulum":
            rules.append("Oyuncu gelecek taslara gore setup yapiyor")
            rules.append("Robot 2-3 hamle sonrasini hedefleyen savunma agirligini arttirmali")
        if objective == "yigin_kurup_alan_kapatma":
            rules.append("Oyuncu yan yana/yukaridan dizilimle baski kuruyor")
            rules.append("Robot ayni kolonlara erken mudahale etmeli")
        if not rules:
            rules.append("Oyuncu dengeli oynuyor; ani kirilma gorulmedi")

        if sum9_rate >= 0.45:
            rules.append("Oyuncu toplam-9 firsatini belirgin sekilde gozetiyor")
        elif sum9_rate <= 0.20:
            rules.append("Oyuncu toplam-9 hedefini ikincil plana atiyor")

        if planning >= 0.45:
            rules.append("Oyuncu gelecek tas planlamasi yapiyor")
        else:
            rules.append("Oyuncu daha cok anlik getirili hamlelerle ilerliyor")

        if special_logic >= 0.60:
            rules.append("Ozel tas kullanimi mantikli ve verimli")
        elif special_logic <= 0.40:
            rules.append("Ozel tas kullanimi dağinik; robot baski kurabilir")

        rules.append(f"Degerlendirme penceresi: son {window} insan hamlesi")
        return rules

    def run_historical_analysis(self, deep=True):
        files = self._iter_log_files()
        if not deep:
            files = files[-10:]

        window_profiles = {10: [], 20: [], 30: []}
        total_rows = 0

        for fp in files:
            rows = self._parse_file(fp)
            total_rows += len(rows)
            for window in (10, 20, 30):
                wr = self._window_rows(rows, window)
                if not wr:
                    continue
                prof = self._summarize_window(wr)
                prof["objective"] = self._infer_objective(prof)
                window_profiles[window].append(prof)

        for window in (10, 20, 30):
            profs = window_profiles[window]
            if not profs:
                self.historical_profiles[window] = {
                    "samples": 0,
                    "avg_points": 0.0,
                    "avg_exploded_cells": 0.0,
                    "avg_explosions": 0.0,
                    "avg_combo": 0.0,
                    "avg_explosion_value": 0.0,
                    "special_usage_rate": 0.0,
                    "cluster_ratio": 0.0,
                    "special_logic_score": 0.0,
                    "sum9_intent_rate": 0.0,
                    "future_plan_rate": 0.0,
                    "future_data_coverage": 0.0,
                    "top_cols": [],
                    "dominant_objective": "veri_yetersiz",
                }
                self.rulebook[window] = ["Tarihsel veri yetersiz"]
                continue

            objective_counts = Counter([str(x.get("objective", "dengeli_ilerleme")) for x in profs])
            top_cols = Counter()
            for p in profs:
                for c in p.get("top_cols", []):
                    if isinstance(c, int):
                        top_cols[c] += 1

            agg = {
                "samples": len(profs),
                "avg_points": statistics.fmean([x.get("avg_points", 0.0) for x in profs]),
                "avg_exploded_cells": statistics.fmean([x.get("avg_exploded_cells", 0.0) for x in profs]),
                "avg_explosions": statistics.fmean([x.get("avg_explosions", 0.0) for x in profs]),
                "avg_combo": statistics.fmean([x.get("avg_combo", 0.0) for x in profs]),
                "avg_explosion_value": statistics.fmean([x.get("avg_explosion_value", 0.0) for x in profs]),
                "special_usage_rate": statistics.fmean([x.get("special_usage_rate", 0.0) for x in profs]),
                "cluster_ratio": statistics.fmean([x.get("cluster_ratio", 0.0) for x in profs]),
                "special_logic_score": statistics.fmean([x.get("special_logic_score", 0.0) for x in profs]),
                "sum9_intent_rate": statistics.fmean([x.get("sum9_intent_rate", 0.0) for x in profs]),
                "future_plan_rate": statistics.fmean([x.get("future_plan_rate", 0.0) for x in profs]),
                "future_data_coverage": statistics.fmean([x.get("future_data_coverage", 0.0) for x in profs]),
                "top_cols": [c for c, _ in top_cols.most_common(3)],
                "dominant_objective": objective_counts.most_common(1)[0][0],
            }
            self.historical_profiles[window] = agg
            self.rulebook[window] = self._build_rules(agg, window)

        payload = {
            "files": len(files),
            "rows": total_rows,
            "historical_profiles": self.historical_profiles,
            "rulebook": self.rulebook,
        }
        self._append_agent_log("historical_analysis", payload)
        return payload

    def observe_turn(self, player_log, robot_log):
        if isinstance(player_log, dict) and player_log.get("player") == "Human":
            self.recent_human.append(player_log)
        if isinstance(robot_log, dict) and robot_log.get("player") == "Robot":
            self.recent_robot.append(robot_log)

    def _window_signal(self, window):
        if len(self.recent_human) < window:
            return {"window": window, "ready": False}

        live_rows = list(self.recent_human)[-window:]
        live = self._summarize_window(live_rows)
        live["objective"] = self._infer_objective(live)
        base = self.historical_profiles.get(window, {}) or {}

        diff = {
            "explosion_value_delta": float(live.get("avg_explosion_value", 0.0) or 0.0) - float(base.get("avg_explosion_value", 0.0) or 0.0),
            "special_usage_delta": float(live.get("special_usage_rate", 0.0) or 0.0) - float(base.get("special_usage_rate", 0.0) or 0.0),
            "cluster_ratio_delta": float(live.get("cluster_ratio", 0.0) or 0.0) - float(base.get("cluster_ratio", 0.0) or 0.0),
            "special_logic_delta": float(live.get("special_logic_score", 0.0) or 0.0) - float(base.get("special_logic_score", 0.0) or 0.0),
            "sum9_intent_delta": float(live.get("sum9_intent_rate", 0.0) or 0.0) - float(base.get("sum9_intent_rate", 0.0) or 0.0),
            "future_plan_delta": float(live.get("future_plan_rate", 0.0) or 0.0) - float(base.get("future_plan_rate", 0.0) or 0.0),
        }

        warnings = []
        if diff["explosion_value_delta"] > 1.2:
            warnings.append("Oyuncu patlama verimini tarihsele gore hizli yukseltti")
        if diff["special_usage_delta"] > 0.10:
            warnings.append("Oyuncu ozel tas kullanimini belirgin artirdi")
        if diff["cluster_ratio_delta"] > 0.12:
            warnings.append("Oyuncu yan yana/yigin dizilim ile baski kuruyor")
        if diff["special_logic_delta"] > 0.12:
            warnings.append("Oyuncu ozel taslari daha mantikli kullanmaya basladi")
        if diff["sum9_intent_delta"] > 0.12:
            warnings.append("Oyuncu toplam-9 hedefini belirgin sekilde arttirdi")
        if diff["future_plan_delta"] > 0.15:
            warnings.append("Oyuncu gelecek tas planlamasina gecis yapti")

        return {
            "window": window,
            "ready": True,
            "live": live,
            "baseline": base,
            "diff": diff,
            "warnings": warnings,
        }

    def build_live_warning(self, turn):
        signals = {10: self._window_signal(10), 20: self._window_signal(20), 30: self._window_signal(30)}

        all_warnings = []
        target_counter = Counter()
        strategy_weights = {name: 0.0 for name in DEFAULT_STRATEGIES}
        proposal_weights = {name: 0.0 for name in DEFAULT_PROPOSAL_ENGINES}

        for window in (10, 20, 30):
            sig = signals[window]
            if not sig.get("ready"):
                continue
            all_warnings.extend(sig.get("warnings", []))
            live = sig.get("live", {}) or {}
            for c in live.get("top_cols", []):
                if isinstance(c, int):
                    target_counter[c] += 1

            diff = sig.get("diff", {}) or {}
            if float(diff.get("explosion_value_delta", 0.0) or 0.0) > 1.2:
                strategy_weights["low_risk"] += 0.10
                strategy_weights["safe_stack"] += 0.12
                proposal_weights["risk_balancer"] += 0.16
                proposal_weights["stability_guard"] += 0.12
            if float(diff.get("special_usage_delta", 0.0) or 0.0) > 0.08:
                strategy_weights["lock_builder"] += 0.10
                strategy_weights["sum9_focus"] += 0.08
                proposal_weights["combo_amplifier"] += 0.12
            if float(diff.get("cluster_ratio_delta", 0.0) or 0.0) > 0.10:
                strategy_weights["center_control"] += 0.10
                strategy_weights["edge_pressure"] += 0.08
                proposal_weights["mutate_light"] += 0.10

        if all_warnings:
            command_hint = "Kirilma Ajan Uyarisi: " + " | ".join(sorted(set(all_warnings))[:3])
        else:
            command_hint = "Kirilma Ajan Uyarisi: Anlik sapma dusuk, standart Gazi plani surdurulebilir"

        signal = {
            "turn": int(turn),
            "signals": signals,
            "warnings": sorted(set(all_warnings)),
            "target_cols": [c for c, _ in target_counter.most_common(3)],
            "strategy_weights": strategy_weights,
            "proposal_weights": proposal_weights,
            "command_hint": command_hint,
            "dominant_historical_objective": self.historical_profiles.get(30, {}).get("dominant_objective", "veri_yetersiz"),
        }
        self.last_signal = signal
        self._append_agent_log("live_signal", signal)
        return signal

    def snapshot(self):
        return {
            "historical_profiles": self.historical_profiles,
            "rulebook": self.rulebook,
            "last_signal": self.last_signal,
            "agent_log": self.agent_log_path,
        }
