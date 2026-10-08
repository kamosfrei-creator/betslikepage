"""Kursy bukmacherskie (opcjonalnie, The Odds API - klucz w ODDS_API_KEY).

Zapisujemy migawki kursów 1X2 w data/odds.json, żeby pokazać ruch kursu
(otwarcie -> teraz), i liczymy value: prawdopodobieństwo modelu × kurs.

Prawo: nazwy i linki pokazujemy tylko dla bukmacherów z listy
config.json -> "bookmakers" (wpisz tam wyłącznie licencjonowanych operatorów
dla danego rynku/języka). Bez listy strona pokazuje tylko średni kurs rynku,
bez nazw bukmacherów i bez linków.
"""

import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from .news import _similar

API = "https://api.the-odds-api.com/v4/sports/{sport}/odds"
SPORTS = {
    "PL": "soccer_epl", "ELC": "soccer_efl_champ", "BL1": "soccer_germany_bundesliga",
    "SA": "soccer_italy_serie_a", "PD": "soccer_spain_la_liga", "FL1": "soccer_france_ligue_one",
    "DED": "soccer_netherlands_eredivisie", "PPL": "soccer_portugal_primeira_liga",
    "CL": "soccer_uefa_champs_league", "BSA": "soccer_brazil_campeonato",
}
VALUE_THRESHOLD = 1.05


def fetch(key, competitions, log=print):
    events = []
    for code in competitions:
        sport = SPORTS.get(code)
        if not sport:
            continue
        url = API.format(sport=sport) + "?" + urllib.parse.urlencode(
            {"apiKey": key, "regions": "eu", "markets": "h2h", "oddsFormat": "decimal", "dateFormat": "iso"})
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                events += json.load(resp)
        except Exception as e:  # brak kursów nie może zatrzymać budowy strony
            log(f"[odds] {code}: {e}")
    return events


def _prices(event, home, away):
    """{bookmaker_key: {"title":..., "1":..., "X":..., "2":...}}"""
    out = {}
    for b in event.get("bookmakers", []):
        for market in b.get("markets", []):
            if market.get("key") != "h2h":
                continue
            row = {"title": b.get("title", b["key"])}
            for o in market.get("outcomes", []):
                if o["name"] == "Draw":
                    row["X"] = o["price"]
                elif _similar(o["name"], home):
                    row["1"] = o["price"]
                elif _similar(o["name"], away):
                    row["2"] = o["price"]
            if all(k in row for k in ("1", "X", "2")):
                out[b["key"]] = row
    return out


def update(store, events, matches, now):
    """Dopasowuje wydarzenia do meczów i dopisuje migawki do store[str(id)]."""
    stamp = now.astimezone(timezone.utc).isoformat()
    for m in matches:
        kick = datetime.strptime(m["utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        for ev in events:
            t = datetime.fromisoformat(ev["commence_time"].replace("Z", "+00:00"))
            if abs((t - kick).total_seconds()) > 1800:
                continue
            if not (_similar(ev["home_team"], m["home"]) and _similar(ev["away_team"], m["away"])):
                continue
            prices = _prices(ev, ev["home_team"], ev["away_team"])
            if not prices:
                break
            rec = store.setdefault(str(m["id"]), {"opening": None, "current": None, "at": None})
            avg = {k: round(sum(p[k] for p in prices.values()) / len(prices), 2) for k in ("1", "X", "2")}
            snap = {"avg": avg, "books": prices}
            if rec["opening"] is None:
                rec["opening"] = snap
            rec["current"] = snap
            rec["at"] = stamp
            break
    return store


def view(rec, probs, cfg):
    """Dane do wyświetlenia: średnie kursy, ruch, najlepszy kurs od dozwolonego bukmachera, value."""
    if not rec or not rec.get("current"):
        return None
    allowed = cfg.get("bookmakers", {})
    cur, opening = rec["current"], rec.get("opening") or rec["current"]
    rows = []
    for k in ("1", "X", "2"):
        best = None
        for key, row in cur["books"].items():
            if key in allowed and (best is None or row[k] > best[1]):
                best = (key, row[k])
        price = best[1] if best else cur["avg"][k]
        value = probs[k] * price
        rows.append({
            "outcome": k, "open": opening["avg"][k], "now": cur["avg"][k],
            "move": round(cur["avg"][k] - opening["avg"][k], 2),
            "best": price, "book": best[0] if best else None,
            "book_name": allowed[best[0]].get("name", best[0]) if best else None,
            "url": allowed[best[0]].get("url") if best else None,
            "book_langs": allowed[best[0]].get("languages") if best else None,
            "value": round(value, 3), "is_value": value >= VALUE_THRESHOLD,
        })
    return rows


def demo(matches, probs_by_id):
    """Syntetyczne kursy (marża ~6%, lekki szum) do podglądu w trybie DEMO."""
    import random
    store = {}
    books = {"bookie_a": "Bookie A", "bookie_b": "Bookie B", "bookie_c": "Bookie C"}
    for m in matches:
        p = probs_by_id.get(m["id"])
        if not p:
            continue
        rng = random.Random(m["id"])
        def snap(drift):
            rows = {}
            for key, title in books.items():
                rows[key] = {"title": title, **{k: round(1 / (p[k] * 1.06) * rng.uniform(0.95, 1.07) * drift.get(k, 1), 2)
                                               for k in ("1", "X", "2")}}
            avg = {k: round(sum(r[k] for r in rows.values()) / len(rows), 2) for k in ("1", "X", "2")}
            return {"avg": avg, "books": rows}
        store[str(m["id"])] = {"opening": snap({"1": 1.06, "2": 0.95}), "current": snap({}), "at": "demo"}
    return store
