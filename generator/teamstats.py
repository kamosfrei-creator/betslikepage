"""Statystyki drużyn liczone z wyników: ostatnie mecze, gole, BTTS, over 2,5, H2H."""


def finished(matches):
    return [m for m in matches if m.get("home_goals") is not None and m.get("status", "FINISHED") == "FINISHED"]


def recent(team_id, matches, n=10):
    games = sorted((m for m in finished(matches) if team_id in (m["home_id"], m["away_id"])),
                   key=lambda m: m["utc"], reverse=True)[:n]
    out = []
    for m in games:
        home = m["home_id"] == team_id
        gf, ga = (m["home_goals"], m["away_goals"]) if home else (m["away_goals"], m["home_goals"])
        out.append({"utc": m["utc"], "home": m["home"], "away": m["away"],
                    "score": f'{m["home_goals"]}:{m["away_goals"]}',
                    "res": "W" if gf > ga else "D" if gf == ga else "L"})
    return out


def season(team_id, matches):
    games = [m for m in finished(matches) if team_id in (m["home_id"], m["away_id"])]
    n = len(games)
    if not n:
        return None
    gf = ga = btts = over = clean = 0
    for m in games:
        home = m["home_id"] == team_id
        f, a = (m["home_goals"], m["away_goals"]) if home else (m["away_goals"], m["home_goals"])
        gf += f
        ga += a
        btts += f > 0 and a > 0
        over += f + a >= 3
        clean += a == 0
    return {"games": n, "gf": gf / n, "ga": ga / n, "btts": btts / n, "over25": over / n, "clean": clean / n}


def h2h(home_id, away_id, matches, n=10):
    games = [m for m in finished(matches) if {m["home_id"], m["away_id"]} == {home_id, away_id}]
    games.sort(key=lambda m: m["utc"], reverse=True)
    return [{"utc": m["utc"], "home": m["home"], "away": m["away"],
             "score": f'{m["home_goals"]}:{m["away_goals"]}'} for m in games[:n]]


def last_played(team_id, matches, before):
    dates = [m["utc"] for m in finished(matches) if team_id in (m["home_id"], m["away_id"]) and m["utc"] < before]
    return max(dates) if dates else None
