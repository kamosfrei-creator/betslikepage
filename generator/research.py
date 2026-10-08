"""Research wiadomości o drużynach przez Claude (najtańszy model) z wyszukiwarką.

Jedno zapytanie na ligę (do kilkunastu meczów naraz), najwyżej raz na
`refresh_hours` - tak koszt zostaje rzędu kilku-kilkunastu dolarów miesięcznie.

Krok 1: model szuka w internecie faktów (kontuzje, zawieszenia, przewidywane
        składy, motywacja, rotacja, zmiana trenera) i spisuje krótkie notatki.
Krok 2: drugie, tanie zapytanie bez narzędzi zamienia notatki na JSON wg
        schematu (structured outputs).

Model ma ignorować cudze typy, przewidywania i kursy - zbieramy tylko fakty.
Na stronę trafiają wyłącznie dane (nazwiska, pozycje, oceny), a teksty
analiz piszą nasze szablony.
"""

import json
from datetime import datetime, timedelta, timezone

DEFAULTS = {
    "model": "claude-haiku-5-5",
    "max_searches_per_league": 4,
    "refresh_hours": 20,
    "max_leagues_per_run": 12,
    "max_matches_per_call": 12,
}

SYSTEM = """You are a football data researcher. For each listed fixture, search the web for the latest
FACTS only: injured or suspended players (with position and how important they are to the team),
doubtful players, probable starting lineups, coaching changes, what is at stake for each team
(title race, European places, relegation, derby, nothing to play for) and whether a team is likely
to rotate because of another fixture within a few days.
Rules:
- Ignore betting tips, predictions, previews' picks and odds from any website. Do not use them.
- Use recent sources (last 7 days). If you find nothing reliable for a team, say so.
- Write short factual notes in English in your own words; do not copy sentences from articles.
- Be economical: one or two searches that cover the whole round (e.g. "<league> team news injuries
  this weekend") are better than one search per team."""

TEAM_SCHEMA = {
    "type": "object",
    "properties": {
        "absences": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "player": {"type": "string"},
                    "position": {"type": "string", "enum": ["GK", "DEF", "MID", "FWD", "UNK"]},
                    "importance": {"type": "string", "enum": ["key", "regular", "backup"]},
                    "status": {"type": "string", "enum": ["out", "doubtful"]},
                },
                "required": ["player", "position", "importance", "status"],
                "additionalProperties": False,
            },
        },
        "probable_lineup": {"type": "array", "items": {"type": "string"}},
        "motivation": {"type": "integer", "description": "-2 nothing at stake .. 0 normal .. 2 must-win"},
        "rotation_risk": {"type": "integer", "description": "0 none, 1 possible, 2 likely"},
        "new_coach": {"type": "boolean"},
    },
    "required": ["absences", "probable_lineup", "motivation", "rotation_risk", "new_coach"],
    "additionalProperties": False,
}

SCHEMA = {
    "type": "object",
    "properties": {
        "matches": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "home": TEAM_SCHEMA,
                    "away": TEAM_SCHEMA,
                    "confidence": {"type": "number", "description": "0..1 how reliable the found info is"},
                },
                "required": ["id", "home", "away", "confidence"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["matches"],
    "additionalProperties": False,
}


def _fixture_lines(matches, ranks):
    out = []
    for m in matches:
        rh, ra = ranks.get(m["home_id"]), ranks.get(m["away_id"])
        table = f" (table: {m['home']} #{rh}, {m['away']} #{ra})" if rh and ra else ""
        out.append(f"- id {m['id']}: {m['home']} vs {m['away']}, kickoff {m['utc']} UTC{table}")
    return "\n".join(out)


def _text(response):
    return "\n".join(b.text for b in response.content if b.type == "text")


def _research_league(client, cfg, league_name, matches, ranks, log):
    fixtures = _fixture_lines(matches, ranks)
    messages = [{"role": "user", "content": f"League: {league_name}\nFixtures:\n{fixtures}\n\n"
                                            "Research these fixtures and write the notes per fixture id."}]
    tools = [{"type": "web_search_20250305", "name": "web_search", "max_uses": cfg["max_searches_per_league"]}]
    notes, searches = [], 0
    for _ in range(3):  # pause_turn: serwer przerwał długą turę - wysyłamy ją z powrotem
        resp = client.messages.create(model=cfg["model"], max_tokens=8000, system=SYSTEM,
                                      tools=tools, messages=messages, output_config={"effort": "low"})
        notes.append(_text(resp))
        usage = getattr(resp.usage, "server_tool_use", None)
        searches += getattr(usage, "web_search_requests", 0) or 0
        if resp.stop_reason != "pause_turn":
            break
        messages = messages[:1] + [{"role": "assistant", "content": resp.content}]

    extract = client.messages.create(
        model=cfg["model"], max_tokens=8000, output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content":
                   f"Fixtures:\n{fixtures}\n\nResearch notes:\n{''.join(notes)}\n\n"
                   "Convert the notes into the JSON schema, one entry per fixture id listed above. "
                   "Use empty lists, motivation 0, rotation_risk 0, new_coach false and low confidence "
                   "where the notes have no information. Use player names exactly as in the notes."}])
    if extract.stop_reason == "refusal":
        log(f"[research] {league_name}: odmowa modelu")
        return {}, searches
    data = json.loads(_text(extract))
    return {m["id"]: m for m in data.get("matches", [])}, searches


def run(cfg_all, upcoming, models, cache, now, log=print):
    """Uzupełnia cache {str(id): {"at": iso, "data": {...}}} researchem dla nadchodzących meczów."""
    import os
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    cfg = {**DEFAULTS, **cfg_all.get("research", {})}
    if not key or not cfg_all.get("research", {}).get("enabled", True):
        return cache
    try:
        import anthropic
    except ImportError:
        log("[research] brak pakietu anthropic - pomijam (pip install -r requirements.txt)")
        return cache

    client = anthropic.Anthropic()
    fresh_after = now - timedelta(hours=cfg["refresh_hours"])
    stale = [m for m in upcoming
             if str(m["id"]) not in cache
             or datetime.fromisoformat(cache[str(m["id"])]["at"]) < fresh_after]
    by_league = {}
    for m in stale:
        by_league.setdefault(m["competition"], []).append(m)

    total_searches = 0
    for code, matches in list(by_league.items())[:cfg["max_leagues_per_run"]]:
        model = models.get(code)
        ranks = {r["id"]: r["rank"] for r in model.table} if model else {}
        for i in range(0, len(matches), cfg["max_matches_per_call"]):
            chunk = matches[i:i + cfg["max_matches_per_call"]]
            try:
                found, searches = _research_league(client, cfg, chunk[0]["competition_name"], chunk, ranks, log)
            except anthropic.APIError as e:
                log(f"[research] {code}: błąd API {e}")
                continue
            except (json.JSONDecodeError, KeyError) as e:
                log(f"[research] {code}: niepoprawna odpowiedź {e}")
                continue
            total_searches += searches
            stamp = now.astimezone(timezone.utc).isoformat()
            for m in chunk:
                if m["id"] in found:
                    cache[str(m["id"])] = {"at": stamp, "data": found[m["id"]]}
    log(f"[research] ligi: {len(by_league)}, wyszukiwania: {total_searches}")
    return cache


# ------------------------------------------------------------ wpływ na model

POSITION_IMPACT = {  # (spadek ataku, wzrost straconych) dla kluczowego zawodnika
    "FWD": (0.07, 0.0), "MID": (0.04, 0.02), "DEF": (0.01, 0.05), "GK": (0.0, 0.07), "UNK": (0.02, 0.02),
}
IMPORTANCE = {"key": 1.0, "regular": 0.45, "backup": 0.1}
DOUBTFUL = 0.4
CAP = 0.20


def team_factors(team, confidence):
    """Mnożniki (atak, obrona) i lista czynników do wyświetlenia."""
    att_loss = def_gain = 0.0
    for a in team.get("absences", []):
        w = IMPORTANCE.get(a.get("importance"), 0.3) * (DOUBTFUL if a.get("status") == "doubtful" else 1.0)
        pa, pd = POSITION_IMPACT.get(a.get("position"), POSITION_IMPACT["UNK"])
        att_loss += pa * w
        def_gain += pd * w
    motivation = max(-2, min(2, int(team.get("motivation", 0))))
    rotation = max(0, min(2, int(team.get("rotation_risk", 0))))
    c = max(0.3, min(1.0, float(confidence or 0.5)))
    att = 1 - c * min(CAP, att_loss) + c * 0.03 * motivation - c * 0.03 * rotation
    dfn = 1 + c * min(CAP, def_gain) - c * 0.02 * motivation + c * 0.025 * rotation
    flags = []
    if any(a.get("status") == "out" for a in team.get("absences", [])):
        flags.append("absence")
    if motivation > 0:
        flags.append("motivation_up")
    elif motivation < 0:
        flags.append("motivation_down")
    if rotation:
        flags.append("rotation")
    if team.get("new_coach"):
        flags.append("coach")
    return att, dfn, flags


def demo(upcoming):
    """Przykładowe dane do podglądu w trybie DEMO."""
    out = {}
    for i, m in enumerate(upcoming):
        if i % 2:
            continue
        out[str(m["id"])] = {"at": "demo", "data": {
            "id": m["id"], "confidence": 0.8,
            "home": {"absences": [{"player": "J. Demo", "position": "FWD", "importance": "key", "status": "out"},
                                  {"player": "P. Sample", "position": "DEF", "importance": "regular", "status": "doubtful"}],
                     "probable_lineup": ["A. Keeper", "B. Back", "C. Stone", "D. Wall", "E. Wing", "F. Mid",
                                         "G. Pass", "H. Runner", "I. Ten", "K. Nine", "L. Pace"],
                     "motivation": 1, "rotation_risk": 0, "new_coach": False},
            "away": {"absences": [], "probable_lineup": [], "motivation": 0 if i % 4 else -1,
                     "rotation_risk": 1 if i % 4 == 0 else 0, "new_coach": i % 4 == 2},
        }}
    return out
