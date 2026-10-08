"""Teksty interfejsu i szablony analiz - ładowane z plików i18n/<język>.json.

Analizy są składane z szablonów na podstawie liczb z modelu - bez LLM,
więc generowanie nie zużywa żadnych tokenów. Brakujące klucze w danym
języku uzupełniane są wersją angielską.
"""

import json
import os

I18N_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "i18n")


def _load():
    langs = {}
    for name in sorted(os.listdir(I18N_DIR)):
        if name.endswith(".json"):
            with open(os.path.join(I18N_DIR, name), encoding="utf-8") as f:
                langs[name[:-5]] = json.load(f)
    en = langs["en"]
    for data in langs.values():
        for section in ("meta", "ui", "markets", "analysis"):
            data[section] = {**en[section], **data.get(section, {})}
    return langs


LANGS = _load()
META = {k: v["meta"] for k, v in LANGS.items()}
UI = {k: v["ui"] for k, v in LANGS.items()}
MARKETS = {k: v["markets"] for k, v in LANGS.items()}
ANALYSIS = {k: v["analysis"] for k, v in LANGS.items()}


def pct(p):
    return f"{round(p * 100)}%"


def num(x, lang):
    s = f"{x:.1f}"
    return s.replace(".", ",") if META.get(lang, {}).get("decimal") == "," else s


def analysis(lang, match, pred, home_info, away_info, news=None):
    t = ANALYSIS[lang]
    home, away = match["home"], match["away"]
    probs = pred["probs"]
    seed = match["id"] if isinstance(match["id"], int) else sum(map(ord, str(match["id"])))
    out = [t["intro"][seed % len(t["intro"])].format(
        home=home, away=away, xh=num(pred["xg_home"], lang), xa=num(pred["xg_away"], lang))]

    if home_info and home_info["home_scored"] is not None:
        out.append(t["home_record"].format(home=home, s=num(home_info["home_scored"], lang),
                                           c=num(home_info["home_conceded"], lang)))
    if away_info and away_info["away_scored"] is not None:
        out.append(t["away_record"].format(away=away, s=num(away_info["away_scored"], lang),
                                           c=num(away_info["away_conceded"], lang)))
    for team, info in ((home, home_info), (away, away_info)):
        if info and len(info["form"]) >= 4:
            wins, losses = info["form"].count("W"), info["form"].count("L")
            if wins >= 3:
                out.append(t["form_good"].format(team=team, form=info["form"]))
            elif losses >= 3:
                out.append(t["form_bad"].format(team=team, form=info["form"]))

    for team, side in ((home, "home"), (away, "away")):
        n = (news or {}).get(side) or {}
        if n.get("out"):
            out.append(t["injuries"].format(team=team, n=len(n["out"]), names=", ".join(n["out"][:4])))
        elif n.get("absence"):
            out.append(t["news_absence"].format(team=team))
        if n.get("return") and not n.get("out"):
            out.append(t["news_return"].format(team=team))
        if n.get("coach"):
            out.append(t["news_coach"].format(team=team))
    lineups = (news or {}).get("lineups")
    if lineups:
        out.append(t["lineups"].format(home=home, away=away, fh=lineups[0], fa=lineups[1]))

    if probs["1"] >= 0.5:
        out.append(t["fav_home"].format(p=pct(probs["1"])))
    elif probs["2"] >= 0.42 and probs["2"] > probs["1"]:
        out.append(t["fav_away"].format(p=pct(probs["2"])))
    elif probs["X"] >= 0.28:
        out.append(t["balanced"].format(p=pct(probs["X"])))
    if probs["O25"] >= 0.58:
        out.append(t["goals_high"].format(p=pct(probs["O25"])))
    elif probs["U25"] >= 0.58:
        out.append(t["goals_low"].format(p=pct(probs["U25"])))
    return " ".join(out)
