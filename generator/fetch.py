"""Pobieranie danych meczowych.

Jedynym źródłem jest oficjalne, licencjonowane API football-data.org (darmowy
plan, klucz w zmiennej FOOTBALL_DATA_TOKEN). Strona NIE scrapuje cudzych
typów ani artykułów - pobiera wyłącznie surowe fakty (terminarz, wyniki),
a typy liczy własnym modelem statystycznym.

Bez klucza generator działa w trybie DEMO na danych syntetycznych.
"""

import json
import random
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://api.football-data.org/v4"
# Darmowy plan: 10 zapytań / minutę.
REQUEST_GAP_S = 6.5


class Client:
    _last = 0.0  # wspólne dla wszystkich instancji - limit dotyczy klucza

    def __init__(self, token):
        self.token = token

    def get(self, path, params=None):
        query = "&".join(f"{k}={v}" for k, v in (params or {}).items())
        url = f"{API}{path}" + (f"?{query}" if query else "")
        for attempt in range(4):
            wait = REQUEST_GAP_S - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            Client._last = time.monotonic()
            req = urllib.request.Request(url, headers={"X-Auth-Token": self.token})
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return json.load(resp)
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < 3:
                    time.sleep(61)
                    continue
                raise
        raise RuntimeError(f"Nie udało się pobrać {url}")


def _match(m):
    ft = (m.get("score") or {}).get("fullTime") or {}
    return {
        "id": m["id"],
        "utc": m["utcDate"],
        "status": m["status"],
        "competition": m["competition"]["code"],
        "competition_name": m["competition"]["name"],
        "home": m["homeTeam"].get("shortName") or m["homeTeam"].get("name") or "?",
        "away": m["awayTeam"].get("shortName") or m["awayTeam"].get("name") or "?",
        "home_names": [n for n in (m["homeTeam"].get("name"), m["homeTeam"].get("shortName")) if n],
        "away_names": [n for n in (m["awayTeam"].get("name"), m["awayTeam"].get("shortName")) if n],
        "home_crest": m["homeTeam"].get("crest"),
        "away_crest": m["awayTeam"].get("crest"),
        "emblem": m["competition"].get("emblem"),
        "area": (m.get("area") or {}).get("name"),
        "flag": (m.get("area") or {}).get("flag"),
        "home_id": m["homeTeam"].get("id"),
        "away_id": m["awayTeam"].get("id"),
        "home_goals": ft.get("home"),
        "away_goals": ft.get("away"),
    }


def fetch_live(token, competitions, today):
    """Zwraca (mecze z okna -3..+2 dni, {kod_ligi: zakończone mecze sezonu})."""
    client = Client(token)
    window = client.get("/matches", {
        "dateFrom": (today - timedelta(days=3)).isoformat(),
        "dateTo": (today + timedelta(days=3)).isoformat(),
        "competitions": ",".join(competitions),
    })
    window_matches = [_match(m) for m in window.get("matches", []) if m.get("homeTeam", {}).get("id")]

    upcoming = {m["competition"] for m in window_matches if m["status"] in ("SCHEDULED", "TIMED")}
    history = {}
    for code in sorted(upcoming):
        data = client.get(f"/competitions/{code}/matches", {"status": "FINISHED"})
        history[code] = [_match(m) for m in data.get("matches", [])]
    return window_matches, history


def fetch_by_ids(token, ids):
    """Mecze o podanych id - do rozliczenia starszych typów spoza okna dat."""
    client, out = Client(token), []
    for i in range(0, len(ids), 50):
        data = client.get("/matches", {"ids": ",".join(map(str, ids[i:i + 50]))})
        out += [_match(m) for m in data.get("matches", []) if m.get("homeTeam", {}).get("id")]
    return out


def fetch_h2h(token, match_ids, cache, limit, log=print):
    """Bezpośrednie mecze (także z poprzednich sezonów) - raz na mecz, wynik w cache."""
    client = Client(token)
    for mid in [i for i in match_ids if str(i) not in cache][:limit]:
        try:
            data = client.get(f"/matches/{mid}/head2head", {"limit": 10})
        except Exception as e:
            log(f"[h2h] {mid}: {e}")
            continue
        cache[str(mid)] = [_match(m) for m in data.get("matches", []) if m.get("homeTeam", {}).get("id")]
    return cache


# --------------------------------------------------------------------------
# Tryb DEMO - deterministyczne dane syntetyczne do podglądu i testów.

DEMO_LEAGUES = {
    "DEMO1": ("Demo League A", ["Northport", "Riverside", "Eastvale", "Kingsbridge", "Westham Park",
                                "Stonebury", "Ashford City", "Millbrook", "Harbor Town", "Oakridge"]),
    "DEMO2": ("Demo League B", ["Bergstadt", "Talheim", "Seeburg", "Waldfeld", "Rosenau",
                                "Felsbach", "Lindenhof", "Kronberg"]),
    "DEMO3": ("Demo League C", ["Portavera", "Monteluce", "Sanrocco", "Valbruna", "Castelmare",
                                "Rivabella", "Torrefino", "Campolungo"]),
}


def fetch_demo(today, now):
    """Sezon syntetyczny + mecze z okna -3..+1 dni. Mecze danego dnia zależą tylko
    od daty, więc kolejne przebiegi widzą te same mecze (można testować rozliczanie)."""
    rng = random.Random("demo-season")
    strength, history, window = {}, {}, []
    next_id = 1
    for code, (name, teams) in DEMO_LEAGUES.items():
        for t in teams:
            strength[t] = (rng.uniform(0.7, 1.4), rng.uniform(0.7, 1.3))
        played = []
        start = datetime.combine(today - timedelta(days=75), datetime.min.time(), timezone.utc)
        for rnd in range(10):
            order = teams[:]
            rng.shuffle(order)
            for i in range(0, len(order) - 1, 2):
                h, a = order[i], order[i + 1]
                played.append(_demo_match(next_id, start + timedelta(days=7 * rnd, hours=18), code, name, h, a,
                                          "FINISHED", rng, strength))
                next_id += 1
        history[code] = played

    for offset in range(-3, 3):
        day = today + timedelta(days=offset)
        drng = random.Random(f"demo-{day.isoformat()}")
        base = datetime.combine(day, datetime.min.time(), timezone.utc)
        k = 0
        for code, (name, teams) in DEMO_LEAGUES.items():
            order = teams[:]
            drng.shuffle(order)
            for i in range(0, 8, 2):
                kick = base + timedelta(hours=15 + i // 2 * 2)
                status = "FINISHED" if kick + timedelta(hours=2) <= now else "TIMED"
                window.append(_demo_match(day.toordinal() * 100 + k, kick, code, name, order[i], order[i + 1],
                                          status, drng, strength))
                k += 1
    return window, history


def _demo_match(mid, kick, code, name, h, a, status, rng, strength):
    hg = _poisson(rng, 1.45 * strength[h][0] * strength[a][1])
    ag = _poisson(rng, 1.15 * strength[a][0] * strength[h][1])
    done = status == "FINISHED"
    return {
        "id": mid, "utc": kick.strftime("%Y-%m-%dT%H:%M:%SZ"), "status": status,
        "competition": code, "competition_name": name, "home": h, "away": a,
        "home_names": [h], "away_names": [a], "home_id": h, "away_id": a,
        "home_goals": hg if done else None, "away_goals": ag if done else None,
    }


def _poisson(rng, lam):
    # Algorytm Knutha - wystarczający dla małych lambda.
    limit, k, p = pow(2.718281828459045, -lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1
