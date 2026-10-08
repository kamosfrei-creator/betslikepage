"""Własny model statystyczny: Poisson z korektą Dixona-Colesa.

Siła ataku/obrony liczona jest z wyników bieżącego sezonu, z wagą malejącą
w czasie i ściąganiem do średniej ligowej (shrinkage), żeby na początku
sezonu kilka meczów nie dawało skrajnych wartości.
"""

import math
from datetime import datetime

HALF_LIFE_DAYS = 90
SHRINK_GOALS = 4.0
RHO = -0.08
MAX_GOALS = 10


def _parse(utc):
    return datetime.strptime(utc, "%Y-%m-%dT%H:%M:%SZ")


class LeagueModel:
    def __init__(self, finished, now):
        self.teams = {}
        weighted = []
        for m in finished:
            if m["home_goals"] is None:
                continue
            age = max(0.0, (now - _parse(m["utc"])).total_seconds() / 86400)
            weighted.append((m, 0.5 ** (age / HALF_LIFE_DAYS)))

        wsum = sum(w for _, w in weighted) or 1.0
        self.avg_home = sum(m["home_goals"] * w for m, w in weighted) / wsum if weighted else 1.5
        self.avg_away = sum(m["away_goals"] * w for m, w in weighted) / wsum if weighted else 1.2
        self.avg_home = max(self.avg_home, 0.5)
        self.avg_away = max(self.avg_away, 0.4)

        for m, w in weighted:
            self._add(m["home_id"], m, w, home=True)
            self._add(m["away_id"], m, w, home=False)
        for t in self.teams.values():
            t["form"] = [r for _, r in sorted(t["results"], reverse=True)[:5]]

    def _add(self, tid, m, w, home):
        t = self.teams.setdefault(tid, {
            "gs": 0.0, "gc": 0.0, "exp_s": 0.0, "exp_c": 0.0, "games": 0,
            "home": [0, 0, 0], "away": [0, 0, 0], "results": [],
        })
        scored, conceded = (m["home_goals"], m["away_goals"]) if home else (m["away_goals"], m["home_goals"])
        t["gs"] += scored * w
        t["gc"] += conceded * w
        t["exp_s"] += (self.avg_home if home else self.avg_away) * w
        t["exp_c"] += (self.avg_away if home else self.avg_home) * w
        t["games"] += 1
        venue = t["home" if home else "away"]
        venue[0] += 1
        venue[1] += scored
        venue[2] += conceded
        res = "W" if scored > conceded else "D" if scored == conceded else "L"
        t["results"].append((m["utc"], res))

    def strength(self, tid):
        t = self.teams.get(tid)
        if not t:
            return 1.0, 1.0, 0
        attack = (t["gs"] + SHRINK_GOALS) / (t["exp_s"] + SHRINK_GOALS)
        defence = (t["gc"] + SHRINK_GOALS) / (t["exp_c"] + SHRINK_GOALS)
        return attack, defence, t["games"]

    def predict(self, home_id, away_id, adjust=(1.0, 1.0, 1.0, 1.0)):
        """adjust: mnożniki (atak, obrona) gospodarzy i gości z wiadomości o drużynach;
        obrona > 1 oznacza więcej traconych goli."""
        ah, dh, gh = self.strength(home_id)
        aa, da, ga = self.strength(away_id)
        att_h, def_h, att_a, def_a = adjust
        lh = self.avg_home * ah * att_h * da * def_a
        la = self.avg_away * aa * att_a * dh * def_h
        probs = markets(score_matrix(lh, la))
        return {"xg_home": lh, "xg_away": la, "games": min(gh, ga), "probs": probs}

    def team_info(self, tid):
        t = self.teams.get(tid)
        if not t:
            return None
        h, a = t["home"], t["away"]
        return {
            "form": "".join(t["form"]),
            "home_scored": h[1] / h[0] if h[0] else None,
            "home_conceded": h[2] / h[0] if h[0] else None,
            "away_scored": a[1] / a[0] if a[0] else None,
            "away_conceded": a[2] / a[0] if a[0] else None,
            "games": t["games"],
        }


def _pois(k, lam):
    return math.exp(-lam) * lam ** k / math.factorial(k)


def _tau(x, y, lh, la):
    if x == 0 and y == 0:
        return 1 - lh * la * RHO
    if x == 0 and y == 1:
        return 1 + lh * RHO
    if x == 1 and y == 0:
        return 1 + la * RHO
    if x == 1 and y == 1:
        return 1 - RHO
    return 1.0


def score_matrix(lh, la):
    m = [[_pois(x, lh) * _pois(y, la) * _tau(x, y, lh, la) for y in range(MAX_GOALS + 1)]
         for x in range(MAX_GOALS + 1)]
    total = sum(map(sum, m))
    return [[v / total for v in row] for row in m]


def markets(mx):
    p = {k: 0.0 for k in ("1", "X", "2", "O15", "O25", "O35", "BTTS")}
    best, best_p = (0, 0), -1.0
    for x, row in enumerate(mx):
        for y, v in enumerate(row):
            if x > y:
                p["1"] += v
            elif x == y:
                p["X"] += v
            else:
                p["2"] += v
            g = x + y
            if g >= 2:
                p["O15"] += v
            if g >= 3:
                p["O25"] += v
            if g >= 4:
                p["O35"] += v
            if x and y:
                p["BTTS"] += v
            if v > best_p:
                best, best_p = (x, y), v
    p["1X"] = p["1"] + p["X"]
    p["X2"] = p["X"] + p["2"]
    p["12"] = p["1"] + p["2"]
    p["U25"] = 1 - p["O25"]
    p["U35"] = 1 - p["O35"]
    p["NOBTTS"] = 1 - p["BTTS"]
    p["score"] = best
    return p
