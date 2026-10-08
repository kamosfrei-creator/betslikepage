"""Wiadomości o drużynach: kontuzje, zawieszenia, składy i nagłówki newsów.

Dwa niezależne, opcjonalne źródła:

1. API-Football (klucz w API_FOOTBALL_KEY) - ustrukturyzowane listy
   niedostępnych zawodników i potwierdzone składy.
2. Kanały RSS portali sportowych (lista w config.json -> news_feeds) -
   czytamy tylko tytuły i zajawki i szukamy w nich sygnałów (kontuzja,
   powrót, zmiana trenera) dla drużyn grających danego dnia.

Z tekstów wyciągamy wyłącznie fakty/sygnały. Na stronie nigdy nie
publikujemy cudzych tekstów - analizy piszą nasze szablony.
"""

import json
import re
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

API_FOOTBALL = "https://v3.football.api-sports.io"
USER_AGENT = "BetsLikeBot/1.0 (+https://github.com/kamosfrei-creator/betslikepage)"
NEWS_MAX_AGE_H = 72

# Słowa kluczowe sygnałów w kilku językach. Teksty normalizujemy do ASCII
# (bez akcentów i polskich znaków), więc słowa też zapisujemy bez nich.
KEYWORDS = {
    "absence": [
        # en
        "injury", "injured", "ruled out", "sidelined", "out for", "suspended", "suspension", "red card ban",
        "doubt for", "doubtful", "hamstring", "fitness concern", "will miss", "set to miss", "absence",
        # pl
        "kontuzj", "uraz", "zawieszon", "pauzuj", "nie zagra", "wypada z", "absencj",
        # de
        "verletz", "fallt aus", "gesperrt", "sperre", "muss passen",
        # es / pt
        "lesion", "lesionado", "sancionado", "suspenso", "desfalque", "contusao", "fora do jogo",
        # it / fr / nl
        "infortun", "squalificat", "indisponibil", "blessure", "blesse", "forfait", "suspendu",
        "geblesseerd", "geschorst",
    ],
    "return": [
        "returns from injury", "back in training", "back from injury", "fit again", "available again",
        "wraca po kontuzji", "wraca do skladu", "wraca do treningow",
        "zuruck im training", "wieder fit",
        "vuelve tras", "recuperado", "de regreso",
        "rientra", "recuperato", "de retour", "terug van blessure",
    ],
    "coach": [
        "sacked", "fired", "new manager", "new head coach", "appointed manager", "parts ways with manager",
        "zwolniony trener", "nowy trener", "zwolnil trenera", "rozstal sie z trenerem",
        "trainer entlassen", "neuer trainer", "trennt sich von trainer",
        "destituido", "nuevo entrenador", "cesado", "novo treinador", "demitido",
        "esonerato", "nuovo allenatore", "limoge", "nouvel entraineur", "ontslagen", "nieuwe trainer",
    ],
}

# Wpływ na model (mnożniki oczekiwanych goli). Celowo ostrożne - listy
# kontuzji obejmują też zawodników, których brak jest już widoczny w wynikach.
OUT_ATTACK = 0.015
OUT_DEFENCE = 0.012
DOUBT_WEIGHT = 0.4
CAP = 0.10
NEWS_ABSENCE = 0.03
NEWS_RETURN = 0.015


def norm(text):
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", text)


def team_aliases(names):
    """Warianty nazwy drużyny do wyszukiwania w tekstach."""
    out = set()
    for name in names:
        n = norm(name)
        if not n:
            continue
        out.add(n)
        stripped = re.sub(r"\b(fc|cf|afc|sc|ac|ssc|as|ss|rc|cd|ud|sv|vfl|vfb|tsg|fk|sk|nk|bk|if|ks|club|de|the)\b", " ", n)
        stripped = re.sub(r"\s+", " ", stripped).strip()
        if len(stripped) >= 4:
            out.add(stripped)
    return {a for a in out if len(a) >= 4}


def _get(url, headers=None, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


# ---------------------------------------------------------------- RSS

def fetch_headlines(feeds, now, log=print):
    items = []
    for url in feeds:
        try:
            root = ET.fromstring(_get(url))
        except Exception as e:  # pojedynczy niedziałający kanał nie może zatrzymać budowy
            log(f"[news] pomijam {url}: {e}")
            continue
        for item in root.iter():
            tag = item.tag.rsplit("}", 1)[-1]
            if tag not in ("item", "entry"):
                continue
            fields = {c.tag.rsplit("}", 1)[-1]: (c.text or "") for c in item}
            published = fields.get("pubDate") or fields.get("published") or fields.get("updated")
            try:
                when = parsedate_to_datetime(published) if "," in published else datetime.fromisoformat(published.replace("Z", "+00:00"))
                if when.tzinfo is None:
                    when = when.replace(tzinfo=timezone.utc)
            except Exception:
                when = now
            if now - when > timedelta(hours=NEWS_MAX_AGE_H):
                continue
            text = re.sub(r"<[^>]+>", " ", fields.get("title", "") + ". " + fields.get("description", fields.get("summary", "")))
            items.append(norm(text))
    return items


def headline_signals(items, aliases):
    """Zwraca {"absence": n, "return": n, "coach": n} dla drużyny."""
    pattern = re.compile(r"\b(" + "|".join(re.escape(a) for a in sorted(aliases, key=len, reverse=True)) + r")\b")
    signals = {k: 0 for k in KEYWORDS}
    for text in items:
        if not pattern.search(text):
            continue
        # Słowo kluczowe musi być w tym samym zdaniu co nazwa drużyny (tytuł i zajawka
        # to osobne zdania), żeby kontuzja jednej drużyny nie trafiła do rywala.
        for sentence in re.split(r"[.;|]\s", text):
            if not pattern.search(sentence):
                continue
            for kind, words in KEYWORDS.items():
                if any(w in sentence for w in words):
                    signals[kind] += 1
    return signals


# ---------------------------------------------------------- API-Football

class ApiFootball:
    def __init__(self, key, budget):
        self.key = key
        self.budget = budget

    def get(self, path, **params):
        if self.budget <= 0:
            raise RuntimeError("wyczerpany limit zapytań API-Football na ten przebieg")
        self.budget -= 1
        url = f"{API_FOOTBALL}{path}?{urllib.parse.urlencode(params)}"
        data = json.loads(_get(url, {"x-apisports-key": self.key}))
        if data.get("errors"):
            raise RuntimeError(f"API-Football: {data['errors']}")
        return data.get("response", [])


def _similar(a, b):
    ta, tb = set(norm(a).split()), set(norm(b).split())
    ta -= {"fc", "cf", "afc", "sc", "ac"}
    tb -= {"fc", "cf", "afc", "sc", "ac"}
    return bool(ta & tb) or norm(a) in norm(b) or norm(b) in norm(a)


def _chunks(seq, n):
    return [seq[i:i + n] for i in range(0, len(seq), n)]


def fetch_team_news_api(key, matches, days, now, budget, log=print):
    """Zwraca {id_meczu: {"home": {...}, "away": {...}, "lineups": (fh, fa)}}."""
    api = ApiFootball(key, budget)
    out = {}
    by_fixture = {}
    try:
        for d in days:
            for fx in api.get("/fixtures", date=d.isoformat()):
                kick = datetime.fromisoformat(fx["fixture"]["date"]).astimezone(timezone.utc)
                for m in matches:
                    ours = datetime.strptime(m["utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                    if (abs((ours - kick).total_seconds()) <= 1800
                            and _similar(m["home"], fx["teams"]["home"]["name"])
                            and _similar(m["away"], fx["teams"]["away"]["name"])):
                        by_fixture[fx["fixture"]["id"]] = (m, fx["teams"]["home"]["id"], kick)

        ids = list(by_fixture)
        for chunk in _chunks(ids, 20):
            for inj in api.get("/injuries", ids="-".join(map(str, chunk))):
                fid = inj["fixture"]["id"]
                if fid not in by_fixture:
                    continue
                m, home_team_id, _ = by_fixture[fid]
                side = "home" if inj["team"]["id"] == home_team_id else "away"
                entry = out.setdefault(m["id"], {}).setdefault(side, {"out": [], "doubtful": []})
                kind = "doubtful" if "question" in (inj["player"].get("type") or "").lower() else "out"
                entry[kind].append(inj["player"]["name"])

        # Składy publikowane są ok. godzinę przed meczem - pytamy tylko o bliskie mecze.
        soon = [fid for fid, (_, _, kick) in by_fixture.items() if timedelta(0) < kick - now <= timedelta(hours=2)]
        for chunk in _chunks(soon, 20):
            for fx in api.get("/fixtures", ids="-".join(map(str, chunk))):
                lineups = fx.get("lineups") or []
                if len(lineups) == 2 and all(l.get("formation") for l in lineups):
                    m = by_fixture[fx["fixture"]["id"]][0]
                    out.setdefault(m["id"], {})["lineups"] = (lineups[0]["formation"], lineups[1]["formation"])
    except Exception as e:
        log(f"[news] API-Football: {e}")
    return out


# --------------------------------------------------------------- łączenie

def collect(cfg, matches, days, now, api_key, demo=False, log=print):
    """Zbiera wiadomości dla listy meczów; zwraca {id_meczu: news}."""
    if demo:
        return demo_news(matches)
    news = {}
    if api_key and matches:
        news = fetch_team_news_api(api_key, matches, days, now, cfg.get("api_football_budget", 12), log)
    feeds = cfg.get("news_feeds", [])
    items = fetch_headlines(feeds, now, log) if feeds and matches else []
    for m in matches:
        entry = news.setdefault(m["id"], {})
        for side in ("home", "away"):
            s = headline_signals(items, team_aliases(m.get(side + "_names", [m[side]]))) if items else {}
            team = entry.setdefault(side, {"out": [], "doubtful": []})
            team["absence"] = s.get("absence", 0)
            team["return"] = s.get("return", 0)
            team["coach"] = s.get("coach", 0)
    return news


def adjustments(news):
    """Mnożniki (atak_gosp, obrona_gosp, atak_gości, obrona_gości) i flaga korekty."""
    factors = {}
    for side in ("home", "away"):
        t = (news or {}).get(side) or {}
        missing = len(t.get("out", [])) + DOUBT_WEIGHT * len(t.get("doubtful", []))
        if missing:
            att = 1 - min(CAP, OUT_ATTACK * missing)
            dfn = 1 + min(CAP, OUT_DEFENCE * missing)
        else:
            # Bez twardych danych korzystamy ze słabszego sygnału z nagłówków.
            att = 1 - (NEWS_ABSENCE if t.get("absence") else 0) + (NEWS_RETURN if t.get("return") else 0)
            dfn = 1 + (NEWS_ABSENCE / 2 if t.get("absence") else 0)
        factors[side] = (att, dfn)
    adjusted = any(abs(a - 1) > 1e-9 or abs(d - 1) > 1e-9 for a, d in factors.values())
    return factors["home"][0], factors["home"][1], factors["away"][0], factors["away"][1], adjusted


def demo_news(matches):
    news = {}
    for i, m in enumerate(matches):
        if i % 3 == 0:
            news[m["id"]] = {"home": {"out": ["J. Demo", "A. Example"], "doubtful": []}, "away": {}}
        elif i % 4 == 1:
            news[m["id"]] = {"away": {"out": [], "doubtful": [], "absence": 1}, "home": {"coach": 1}}
    return news
