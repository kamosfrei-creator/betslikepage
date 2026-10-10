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


# ------------------------------------------------------------- indeks formy

FORM_WEIGHTS = (1.0, 0.85, 0.7, 0.55, 0.4)  # najświeższy mecz waży najwięcej


def form_index(team_id, matches, elo, before, venue=None, n=5):
    """Indeks formy 0-100 z ostatnich n meczów (wszystkie rozgrywki, które znamy).

    Za mecz: punkty (3/1/0) + 0,2 za każdą bramkę różnicy (maks. ±2), przemnożone
    przez siłę rywala (Elo rywala / 1500, w granicach 0,8-1,2). Mecze ważone
    świeżością. venue="home"/"away" - tylko mecze u siebie / na wyjeździe.
    """
    games = sorted((m for m in finished(matches)
                    if team_id in (m["home_id"], m["away_id"]) and m["utc"] < before
                    and (venue is None or (m["home_id"] == team_id) == (venue == "home"))),
                   key=lambda m: m["utc"], reverse=True)[:n]
    if not games:
        return None
    total = wsum = 0.0
    for w, m in zip(FORM_WEIGHTS, games):
        home = m["home_id"] == team_id
        gf, ga = (m["home_goals"], m["away_goals"]) if home else (m["away_goals"], m["home_goals"])
        pts = 3 if gf > ga else 1 if gf == ga else 0
        score = pts + 0.2 * max(-2, min(2, gf - ga))
        opp = m["away_id"] if home else m["home_id"]
        strength = max(0.8, min(1.2, elo.get(opp, 1500.0) / 1500.0))
        total += w * score * strength
        wsum += w
    return round(max(0.0, min(100.0, total / wsum / 3.4 * 100)))


def load(team_id, matches, before, days=14):
    """Obciążenie: liczba meczów w ostatnich `days` dniach i dni odpoczynku."""
    from datetime import datetime, timedelta
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    t = datetime.strptime(before, fmt)
    since = (t - timedelta(days=days)).strftime(fmt)
    played = [m["utc"] for m in finished(matches) if team_id in (m["home_id"], m["away_id"]) and since <= m["utc"] < before]
    last = max(played) if played else last_played(team_id, matches, before)
    rest = round((t - datetime.strptime(last, fmt)).total_seconds() / 86400, 1) if last else None
    return {"m14": len(played), "rest": rest}


def h2h_balance(home_name, games):
    """Bilans H2H z perspektywy gospodarza tego meczu: (wygrane, remisy, porażki)."""
    w = d = l = 0
    for g in games:
        hg, ag = map(int, g["score"].split(":"))
        if hg == ag:
            d += 1
        elif (hg > ag) == (g["home"] == home_name):
            w += 1
        else:
            l += 1
    return w, d, l
