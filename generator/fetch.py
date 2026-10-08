"""Pobieranie danych meczowych.

Jedynym źródłem jest oficjalne, licencjonowane API football-data.org (darmowy
plan, klucz w zmiennej FOOTBALL_DATA_TOKEN). Strona NIE scrapuje cudzych
typów ani artykułów - pobiera wyłącznie surowe fakty (terminarz, wyniki),
a typy liczy własnym modelem statystycznym.

Bez klucza generator działa w trybie DEMO na danych syntetycznych.
"""

import json
import os
import random
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://api.football-data.org/v4"
# Darmowy plan: 10 zapytań / minutę.
REQUEST_GAP_S = 6.5


class Client:
    def __init__(self, token, cache_dir=".cache"):
        self.token = token
        self.cache_dir = cache_dir
        self._last = 0.0
        os.makedirs(cache_dir, exist_ok=True)

    def get(self, path, params=None):
        query = "&".join(f"{k}={v}" for k, v in (params or {}).items())
        url = f"{API}{path}" + (f"?{query}" if query else "")
        for attempt in range(4):
            wait = REQUEST_GAP_S - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
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
        "dateTo": (today + timedelta(days=2)).isoformat(),
        "competitions": ",".join(competitions),
    })
    window_matches = [_match(m) for m in window.get("matches", []) if m.get("homeTeam", {}).get("id")]

    upcoming = {m["competition"] for m in window_matches if m["status"] in ("SCHEDULED", "TIMED")}
    history = {}
    for code in sorted(upcoming):
        data = client.get(f"/competitions/{code}/matches", {"status": "FINISHED"})
        history[code] = [_match(m) for m in data.get("matches", [])]
    return window_matches, history


# --------------------------------------------------------------------------
# Tryb DEMO - deterministyczne dane syntetyczne do podglądu i testów.

DEMO_LEAGUES = {
    "DEMO1": ("Demo League A", ["Northport", "Riverside", "Eastvale", "Kingsbridge", "Westham Park",
                                "Stonebury", "Ashford City", "Millbrook", "Harbor Town", "Oakridge"]),
    "DEMO2": ("Demo League B", ["Bergstadt", "Talheim", "Seeburg", "Waldfeld", "Rosenau",
                                "Felsbach", "Lindenhof", "Kronberg"]),
}


def fetch_demo(today):
    rng = random.Random(today.isoformat())
    strength = {}
    history, window = {}, []
    next_id = 1
    for code, (name, teams) in DEMO_LEAGUES.items():
        for t in teams:
            strength[t] = (rng.uniform(0.7, 1.4), rng.uniform(0.7, 1.3))
        played = []
        start = datetime.combine(today - timedelta(days=70), datetime.min.time(), timezone.utc)
        for rnd in range(10):
            order = teams[:]
            rng.shuffle(order)
            for i in range(0, len(order) - 1, 2):
                h, a = order[i], order[i + 1]
                lh = 1.45 * strength[h][0] * strength[a][1]
                la = 1.15 * strength[a][0] * strength[h][1]
                played.append({
                    "id": next_id, "utc": (start + timedelta(days=7 * rnd, hours=18)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "status": "FINISHED", "competition": code, "competition_name": name,
                    "home": h, "away": a, "home_id": h, "away_id": a,
                    "home_goals": _poisson(rng, lh), "away_goals": _poisson(rng, la),
                })
                next_id += 1
        history[code] = played
        for offset in (0, 1):
            order = teams[:]
            rng.shuffle(order)
            day = datetime.combine(today + timedelta(days=offset), datetime.min.time(), timezone.utc)
            for i in range(0, 8, 2):
                window.append({
                    "id": next_id, "utc": (day + timedelta(hours=15 + i // 2 * 2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "status": "TIMED", "competition": code, "competition_name": name,
                    "home": order[i], "away": order[i + 1], "home_id": order[i], "away_id": order[i + 1],
                    "home_goals": None, "away_goals": None,
                })
                next_id += 1
    return window, history


def _poisson(rng, lam):
    # Algorytm Knutha - wystarczający dla małych lambda.
    limit, k, p = pow(2.718281828459045, -lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1
