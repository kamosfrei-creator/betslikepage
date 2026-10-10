"""Dodatkowe ligi z darmowych plików CSV football-data.co.uk.

Uzupełnia football-data.org (darmowy plan ma tylko 12 rozgrywek) o drugie
ligi i ligi spoza głównej piątki. Pliki zawierają też średnie kursy
bukmacherów (1X2), dzięki którym działają value bety bez płatnego API kursów.

  wyniki (główne ligi):  /mmz4281/<sezon>/<KOD>.csv     np. 2627/D2.csv
  wyniki (nowe ligi):    /new/<KOD>.csv                  wszystkie sezony w jednym pliku
  terminarz:             /fixtures.csv, /new_league_fixtures.csv

Każdy błąd (brak pliku, zmiana formatu) jest logowany i pomijany - strona
buduje się dalej z pozostałych lig.
"""

import csv
import hashlib
import io
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

BASE = "https://www.football-data.co.uk"
UK = ZoneInfo("Europe/London")

MAIN = {  # kod: (nazwa, kraj)
    "E2": ("League One", "England"), "E3": ("League Two", "England"),
    "D2": ("2. Bundesliga", "Germany"), "I2": ("Serie B", "Italy"),
    "SP2": ("Segunda División", "Spain"), "F2": ("Ligue 2", "France"),
    "SC0": ("Scottish Premiership", "Scotland"), "B1": ("Jupiler Pro League", "Belgium"),
    "T1": ("Süper Lig", "Turkey"), "G1": ("Super League", "Greece"),
}
NEW = {  # kod: (nazwa, kraj w kolumnie Country)
    "POL": ("Ekstraklasa", "Poland"), "NOR": ("Eliteserien", "Norway"),
    "SWE": ("Allsvenskan", "Sweden"), "DNK": ("Superliga", "Denmark"),
    "AUT": ("Bundesliga", "Austria"), "SWZ": ("Super League", "Switzerland"),
    "ROU": ("Liga 1", "Romania"), "FIN": ("Veikkausliiga", "Finland"),
}
HEADERS = {"User-Agent": "OnePickAwayBot/1.0"}


def _get_csv(url, log):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=30) as resp:
            raw = resp.read()
    except Exception as e:
        log(f"[fdcouk] {url}: {e}")
        return []
    for enc in ("utf-8-sig", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    return [{(k or "").strip(): (v or "").strip() for k, v in row.items()} for row in csv.DictReader(io.StringIO(text))]


def _utc(date, time):
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            d = datetime.strptime(date, fmt)
            break
        except ValueError:
            continue
    else:
        return None
    hh, mm = (time or "15:00").split(":")[:2] if ":" in (time or "") else ("15", "00")
    local = d.replace(hour=int(hh), minute=int(mm), tzinfo=UK)
    return local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _id(code, utc, home, away):
    """Stabilny identyfikator meczu (poza zakresem id football-data.org)."""
    h = hashlib.md5(f"{code}|{utc[:10]}|{home}|{away}".encode()).hexdigest()
    return 10 ** 12 + int(h[:10], 16) % 10 ** 12


def _int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _odds(row):
    for h, d, a in (("AvgH", "AvgD", "AvgA"), ("AvgCH", "AvgCD", "AvgCA"), ("BbAvH", "BbAvD", "BbAvA"),
                    ("PSH", "PSD", "PSA"), ("B365H", "B365D", "B365A")):
        try:
            o = {"1": float(row[h]), "X": float(row[d]), "2": float(row[a])}
            if all(v > 1 for v in o.values()):
                return o
        except (KeyError, ValueError):
            continue
    return None


def _match(code, name, country, row, home_key, away_key, hg_key, ag_key):
    utc = _utc(row.get("Date", ""), row.get("Time", ""))
    home, away = row.get(home_key), row.get(away_key)
    if not (utc and home and away):
        return None
    hg, ag = _int(row.get(hg_key)), _int(row.get(ag_key))
    return {
        "id": _id(code, utc, home, away), "utc": utc, "status": "FINISHED" if hg is not None and ag is not None else "TIMED",
        "competition": code, "competition_name": name, "area": country, "flag": None, "emblem": None,
        "home": home, "away": away, "home_id": f"{code}:{home}", "away_id": f"{code}:{away}",
        "home_names": [home], "away_names": [away], "home_crest": None, "away_crest": None,
        "home_goals": hg, "away_goals": ag, "_odds": _odds(row),
    }


def _season(today):
    y = today.year % 100
    return f"{y:02d}{y + 1:02d}" if today.month >= 7 else f"{y - 1:02d}{y:02d}"


def fetch(codes, today, log=print):
    """Zwraca (mecze z okna -10..+3 dni, {kod: wyniki z ostatnich 365 dni})."""
    window, seasons = [], {}
    lo = (today - timedelta(days=10)).isoformat()
    hi = (today + timedelta(days=3)).isoformat()
    year_ago = (today - timedelta(days=365)).isoformat()
    main = [c for c in codes if c in MAIN]
    new = [c for c in codes if c in NEW]

    for code in main:
        name, country = MAIN[code]
        rows = []
        for season in {_season(today), _season(today - timedelta(days=200))}:
            rows += _get_csv(f"{BASE}/mmz4281/{season}/{code}.csv", log)
        ms = [m for m in (_match(code, name, country, r, "HomeTeam", "AwayTeam", "FTHG", "FTAG") for r in rows) if m]
        seasons[code] = [m for m in ms if m["status"] == "FINISHED" and m["utc"][:10] >= year_ago]
        window += [m for m in seasons[code] if m["utc"][:10] >= lo]
    if main:
        for r in _get_csv(f"{BASE}/fixtures.csv", log):
            code = r.get("Div")
            if code in main:
                m = _match(code, *MAIN[code], r, "HomeTeam", "AwayTeam", "FTHG", "FTAG")
                if m and m["status"] == "TIMED" and lo <= m["utc"][:10] <= hi:
                    window.append(m)

    by_country = {NEW[c][1]: c for c in new}
    for code in new:
        name, country = NEW[code]
        ms = [m for m in (_match(code, name, country, r, "Home", "Away", "HG", "AG")
                          for r in _get_csv(f"{BASE}/new/{code}.csv", log)) if m]
        seasons[code] = [m for m in ms if m["status"] == "FINISHED" and m["utc"][:10] >= year_ago]
        window += [m for m in seasons[code] if m["utc"][:10] >= lo]
        window += [m for m in ms if m["status"] == "TIMED" and lo <= m["utc"][:10] <= hi]
    if new:
        for r in _get_csv(f"{BASE}/new_league_fixtures.csv", log):
            code = by_country.get(r.get("Country"))
            if code:
                m = _match(code, *NEW[code], r, "Home", "Away", "HG", "AG")
                if m and lo <= m["utc"][:10] <= hi:
                    window.append(m)

    unique = {}
    for m in window:
        unique.setdefault(m["id"], m)
    log(f"[fdcouk] ligi: {len(seasons)}, mecze w oknie: {len(unique)}")
    return list(unique.values()), seasons


def odds_snapshots(store, matches, now):
    """Średnie kursy 1X2 z plików CSV jako migawki dla odds.view (bez nazw bukmacherów)."""
    stamp = now.astimezone(timezone.utc).isoformat()
    for m in matches:
        o = m.pop("_odds", None)
        if not o or m["status"] != "TIMED":
            continue
        rec = store.setdefault(str(m["id"]), {"opening": None, "current": None, "at": None})
        snap = {"avg": {k: round(v, 2) for k, v in o.items()}, "books": {}}
        if rec["opening"] is None:
            rec["opening"] = snap
        rec["current"] = snap
        rec["at"] = stamp
    return store
