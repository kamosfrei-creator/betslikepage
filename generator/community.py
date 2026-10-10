"""Wysyłka meczów do Supabase (tabela matches) dla typowania i rankingu typerów.

Działa tylko, gdy ustawione są config.json -> supabase.url oraz sekret
SUPABASE_SERVICE_KEY (klucz service_role - nigdy nie trafia na stronę).
Baza na tej podstawie zamyka typowanie o godzinie meczu i liczy punkty.
"""

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone

BATCH = 200


def rows(matches):
    out = []
    for m in matches:
        if not isinstance(m.get("id"), int):
            continue
        p = (m.get("prediction") or {}).get("probs") or {}
        out.append({
            "id": m["id"], "utc": m["utc"], "comp": m["competition"], "home": m["home"], "away": m["away"],
            "status": m["status"], "hg": m.get("home_goals"), "ag": m.get("away_goals"),
            "p1": round(p["1"], 4) if "1" in p else None, "px": round(p["X"], 4) if "X" in p else None,
            "p2": round(p["2"], 4) if "2" in p else None,
            "pick": (m.get("pick") or {}).get("market"), "pickr": (m.get("pick_range") or {}).get("market"),
        })
    return out


def _kind(key):
    key = key or ""
    return "sb_secret" if key.startswith("sb_secret") else "jwt" if key.startswith("eyJ") else "brak" if not key else "inny"


def _headers(key):
    h = {"apikey": key, "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates,return=minimal"}
    if key.startswith("eyJ"):  # stary klucz JWT service_role; nowe klucze sb_secret_ idą tylko w apikey
        h["Authorization"] = f"Bearer {key}"
    return h


def sync(url, key, matches, log=print, status_path=None):
    """Wysyła mecze; wynik (bez kluczy) zapisuje w status_path do podglądu."""
    errors = []
    sent = _sync(url, key, matches, lambda msg: (errors.append(msg), log(msg)))
    if status_path:
        with open(status_path, "w") as f:
            json.dump({"at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "key_set": bool(key),
                       "key_type": _kind(key),
                       "sent": sent, "log": errors[-5:]}, f, indent=1)
    return sent


def _sync(url, key, matches, log):
    data = rows(matches)
    if not (url and key and data):
        log(f"[community] pomijam: url={'tak' if url else 'brak'}, klucz={'tak' if key else 'brak'}, mecze={len(data)}")
        return 0
    # Wynik zakończonego meczu nie może skasować prawdopodobieństw zapisanych wcześniej.
    for r in data:
        if r["p1"] is None:
            for k in ("p1", "px", "p2", "pick", "pickr"):
                r.pop(k)
    sent = 0
    groups = {}
    for r in data:  # PostgREST wymaga tych samych kolumn w jednej paczce
        groups.setdefault(tuple(sorted(r)), []).append(r)
    for group in groups.values():
        for i in range(0, len(group), BATCH):
            req = urllib.request.Request(
                url.rstrip("/") + "/rest/v1/matches?on_conflict=id", method="POST",
                data=json.dumps(group[i:i + BATCH]).encode(),
                headers=_headers(key))
            try:
                urllib.request.urlopen(req, timeout=30).close()
                sent += len(group[i:i + BATCH])
            except urllib.error.HTTPError as e:
                log(f"[community] HTTP {e.code}: {e.read()[:300].decode('utf-8', 'replace')}")
                return sent
            except Exception as e:
                log(f"[community] {e}")
                return sent
    log(f"[community] mecze w bazie: {sent}")
    return sent
