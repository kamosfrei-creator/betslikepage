"""Własny model statystyczny - kilka niezależnych składników:

1. Poisson z korektą Dixona-Colesa: siła ataku i obrony liczona osobno
   dla gry u siebie i na wyjeździe (ściągana do ogólnej siły drużyny),
   z wagą malejącą w czasie i ściąganiem do średniej ligowej (shrinkage),
   żeby na początku sezonu kilka meczów nie dawało skrajnych wartości.
2. Ranking Elo (z uwzględnieniem różnicy bramek) - drugi, niezależny
   szacunek szans 1X2, mieszany z Poissonem.
3. Tabela ligowa liczona z wyników (miejsce, punkty) - kontekst dla
   analizy motywacji.
Korekty z zewnątrz (kontuzje, motywacja, zmęczenie) podawane są jako
mnożniki oczekiwanych goli w predict().
"""

import math
from datetime import datetime

HALF_LIFE_DAYS = 90
SHRINK_GOALS = 4.0
RHO = -0.08
MAX_GOALS = 10
VENUE_SHRINK = 4.0     # ile "goli" ogólnej siły dodajemy do statystyk u siebie/na wyjeździe
ELO_START, ELO_K, ELO_HOME = 1500.0, 22.0, 65.0
ELO_WEIGHT = 0.3       # udział Elo w prawdopodobieństwach 1X2


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

        self.elo = {}
        for m in sorted((m for m, _ in weighted), key=lambda m: m["utc"]):
            self._elo_update(m)
        self.table = self._table([m for m, _ in weighted])

    def _elo_update(self, m):
        rh = self.elo.get(m["home_id"], ELO_START)
        ra = self.elo.get(m["away_id"], ELO_START)
        expected = 1 / (1 + 10 ** (-(rh + ELO_HOME - ra) / 400))
        diff = m["home_goals"] - m["away_goals"]
        score = 1.0 if diff > 0 else 0.5 if diff == 0 else 0.0
        margin = math.log(abs(diff) + 1) + 1 if diff else 1.0
        delta = ELO_K * margin * (score - expected)
        self.elo[m["home_id"]] = rh + delta
        self.elo[m["away_id"]] = ra - delta

    @staticmethod
    def _table(matches):
        rows = {}
        for m in matches:
            for tid, name, gf, ga in ((m["home_id"], m.get("home", m["home_id"]), m["home_goals"], m["away_goals"]),
                                      (m["away_id"], m.get("away", m["away_id"]), m["away_goals"], m["home_goals"])):
                r = rows.setdefault(tid, {"id": tid, "team": name, "p": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "pts": 0})
                r["p"] += 1
                r["gf"] += gf
                r["ga"] += ga
                if gf > ga:
                    r["w"] += 1
                    r["pts"] += 3
                elif gf == ga:
                    r["d"] += 1
                    r["pts"] += 1
                else:
                    r["l"] += 1
        table = sorted(rows.values(), key=lambda r: (-r["pts"], -(r["gf"] - r["ga"]), -r["gf"], r["team"]))
        for i, r in enumerate(table, 1):
            r["rank"] = i
        return table

    def _add(self, tid, m, w, home):
        t = self.teams.setdefault(tid, {
            "gs": 0.0, "gc": 0.0, "exp_s": 0.0, "exp_c": 0.0, "games": 0,
            "v": {True: [0.0, 0.0, 0.0, 0.0], False: [0.0, 0.0, 0.0, 0.0]},  # gs, gc, exp_s, exp_c
            "home": [0, 0, 0], "away": [0, 0, 0], "results": [],
        })
        scored, conceded = (m["home_goals"], m["away_goals"]) if home else (m["away_goals"], m["home_goals"])
        t["gs"] += scored * w
        t["gc"] += conceded * w
        t["exp_s"] += (self.avg_home if home else self.avg_away) * w
        t["exp_c"] += (self.avg_away if home else self.avg_home) * w
        v = t["v"][home]
        v[0] += scored * w
        v[1] += conceded * w
        v[2] += (self.avg_home if home else self.avg_away) * w
        v[3] += (self.avg_away if home else self.avg_home) * w
        t["games"] += 1
        venue = t["home" if home else "away"]
        venue[0] += 1
        venue[1] += scored
        venue[2] += conceded
        res = "W" if scored > conceded else "D" if scored == conceded else "L"
        t["results"].append((m["utc"], res))

    def strength(self, tid, home=None):
        """(atak, obrona, mecze). Z home=True/False - siła w danej roli, ściągnięta do ogólnej."""
        t = self.teams.get(tid)
        if not t:
            return 1.0, 1.0, 0
        attack = (t["gs"] + SHRINK_GOALS) / (t["exp_s"] + SHRINK_GOALS)
        defence = (t["gc"] + SHRINK_GOALS) / (t["exp_c"] + SHRINK_GOALS)
        if home is not None:
            v = t["v"][home]
            attack = (v[0] + VENUE_SHRINK * attack) / (v[2] + VENUE_SHRINK)
            defence = (v[1] + VENUE_SHRINK * defence) / (v[3] + VENUE_SHRINK)
        return attack, defence, t["games"]

    def predict(self, home_id, away_id, adjust=(1.0, 1.0, 1.0, 1.0)):
        """adjust: mnożniki (atak, obrona) gospodarzy i gości z wiadomości o drużynach;
        obrona > 1 oznacza więcej traconych goli."""
        ah, dh, gh = self.strength(home_id, home=True)
        aa, da, ga = self.strength(away_id, home=False)
        att_h, def_h, att_a, def_a = adjust
        lh = self.avg_home * ah * att_h * da * def_a
        la = self.avg_away * aa * att_a * dh * def_h
        mx = score_matrix(lh, la)
        probs = markets(mx)
        top = sorted(((mx[x][y], x, y) for x in range(6) for y in range(6)), reverse=True)[:9]

        # Elo jako drugi głos dla 1X2; szansę remisu zostawiamy z Poissona.
        rh, ra = self.elo.get(home_id, ELO_START), self.elo.get(away_id, ELO_START)
        e = 1 / (1 + 10 ** (-(rh + ELO_HOME - ra) / 400))
        rest = 1 - probs["X"]
        probs["1"] = (1 - ELO_WEIGHT) * probs["1"] + ELO_WEIGHT * rest * e
        probs["2"] = 1 - probs["X"] - probs["1"]
        probs["1X"], probs["X2"], probs["12"] = probs["1"] + probs["X"], probs["X"] + probs["2"], probs["1"] + probs["2"]
        return {"xg_home": lh, "xg_away": la, "games": min(gh, ga), "probs": probs,
                "elo_home": round(rh), "elo_away": round(ra),
                "top_scores": [(x, y, p) for p, x, y in top]}

    def rank(self, tid):
        return next((r["rank"] for r in self.table if r["id"] == tid), None)

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
