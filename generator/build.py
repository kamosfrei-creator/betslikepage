"""Punkt wejścia: pobiera dane, liczy typy, rozlicza historię i buduje stronę.

Użycie:
    python -m generator.build            # dane z API (FOOTBALL_DATA_TOKEN) albo DEMO
    python -m generator.build --demo     # wymuszony tryb DEMO
"""

import argparse
import json
import os
import shutil
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from . import coupons as cp
from . import fetch, news, odds, render, research, stats, teamstats
from .model import LeagueModel
from .texts import LANGS, analysis

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOT_STARTED = ("SCHEDULED", "TIMED")
VOID = ("POSTPONED", "CANCELLED", "SUSPENDED", "AWARDED")


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def local_date(utc, tz):
    return datetime.strptime(utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).astimezone(tz).date()


FATIGUE_DAYS = 3.5


def _days_between(a, b):
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    return (datetime.strptime(b, fmt) - datetime.strptime(a, fmt)).total_seconds() / 86400


def predict_match(m, model, cfg, ctx):
    """ctx: news (stare źródła), research, all_matches (wyniki z wszystkich lig), league_matches, h2h, odds."""
    flags = {"home": [], "away": []}
    rec = ctx.get("research")
    if rec:
        conf = rec.get("confidence", 0.5)
        ah, dh, fh = research.team_factors(rec["home"], conf)
        aa, da, fa = research.team_factors(rec["away"], conf)
        flags = {"home": fh, "away": fa}
        adjusted = True
    else:
        ah, dh, aa, da, adjusted = news.adjustments(ctx.get("news"))

    fatigue = {}
    for side, tid in (("home", m["home_id"]), ("away", m["away_id"])):
        last = teamstats.last_played(tid, ctx["all_matches"], m["utc"])
        days = _days_between(last, m["utc"]) if last else None
        if days is not None and days <= FATIGUE_DAYS:
            fatigue[side] = round(days)
            flags[side].append("fatigue")
            adjusted = True
            if side == "home":
                ah, dh = ah * 0.97, dh * 1.03
            else:
                aa, da = aa * 0.97, da * 1.03

    pred = model.predict(m["home_id"], m["away_id"], (ah, dh, aa, da))
    probs = pred["probs"]
    pick = cp.main_pick(probs)
    home_info, away_info = model.team_info(m["home_id"]), model.team_info(m["away_id"])
    ranks = (model.rank(m["home_id"]), model.rank(m["away_id"]))
    lm = ctx["league_matches"]
    h2h = ctx.get("h2h") or teamstats.h2h(m["home_id"], m["away_id"], lm)
    extra = {"flags": flags, "fatigue": fatigue, "ranks": ranks, "elo": (pred["elo_home"], pred["elo_away"])}
    m["research"] = rec
    m.update({
        "prediction": pred,
        "pick": pick,
        "alternatives": cp.alternatives(probs, pick["market"]),
        "xg_home": pred["xg_home"], "xg_away": pred["xg_away"],
        "likely_score": probs["score"],
        "home_form": home_info["form"] if home_info else "",
        "away_form": away_info["form"] if away_info else "",
        "low_data": pred["games"] < cfg["min_team_games"],
        "news": ctx.get("news") or {},
        "flags": flags,
        "ranks": ranks,
        "adjusted": adjusted,
        "recent_home": teamstats.recent(m["home_id"], ctx["all_matches"]),
        "recent_away": teamstats.recent(m["away_id"], ctx["all_matches"]),
        "stats_home": teamstats.season(m["home_id"], lm),
        "stats_away": teamstats.season(m["away_id"], lm),
        "h2h": [h for h in h2h if h.get("utc", "") < m["utc"]][:10],
        "odds": odds.view(ctx.get("odds"), probs, cfg),
        "analysis": {lang: analysis(lang, m, pred, home_info, away_info, ctx.get("news"), extra)
                     for lang in cfg["languages"]},
    })


def settle_history(history, window):
    by_id = {str(m["id"]): m for m in window}
    for key, rec in history["picks"].items():
        m = by_id.get(key)
        if rec.get("result") or not m:
            continue
        if m["status"] == "FINISHED" and m["home_goals"] is not None:
            rec["score"] = f'{m["home_goals"]}:{m["away_goals"]}'
            rec["result"] = "won" if cp.settle(rec["market"], m["home_goals"], m["away_goals"]) else "lost"
        elif m["status"] in VOID:
            rec["result"] = "void"
    for day in history.setdefault("coupons", {}).values():
        for coupon in day.values():
            for leg in coupon["legs"]:
                rec = history["picks"].get(str(leg["id"]), {})
                if rec.get("score"):
                    hg, ag = map(int, rec["score"].split(":"))
                    leg["result"] = "won" if cp.settle(leg["market"], hg, ag) else "lost"
                elif rec.get("result") == "void":
                    leg["result"] = "void"
            results = [leg.get("result") for leg in coupon["legs"]]
            if "lost" in results:
                coupon["result"] = "lost"
            elif all(results):
                coupon["result"] = "won"


def build(demo=False, now=None, langs=None):
    cfg = load_json(os.path.join(ROOT, "config.json"), {})
    if langs:
        cfg["languages"] = [l for l in cfg["languages"] if l in langs]
    missing = [l for l in cfg["languages"] if l not in LANGS]
    if missing:
        print(f"Brak tłumaczeń dla: {', '.join(missing)} - pomijam")
    cfg["languages"] = [l for l in cfg["languages"] if l in LANGS]
    tz = ZoneInfo(cfg["timezone"])
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(tz).date()
    days = [today, today + timedelta(days=1)]

    token = os.environ.get("FOOTBALL_DATA_TOKEN", "").strip()
    demo = demo or not token
    if demo:
        window, seasons = fetch.fetch_demo(today, now)
    else:
        window, seasons = fetch.fetch_live(token, cfg["competitions"], today)

    hist_path = os.path.join(ROOT, "data", "demo-history.json" if demo else "history.json")
    history = load_json(hist_path, {"picks": {}, "coupons": {}})
    history.setdefault("coupons", {})

    # Typy starsze niż okno pobierania (np. po przerwie w aktualizacjach) dociągamy po id.
    extra = []
    oldest = (today - timedelta(days=3)).isoformat()
    stale = [int(k) for k, v in history["picks"].items() if not v.get("result") and v["date"] < oldest]
    if stale and not demo:
        window_ids = {m["id"] for m in window}
        extra = [m for m in fetch.fetch_by_ids(token, stale[:200]) if m["id"] not in window_ids]
    settle_history(history, window + extra)
    now_s = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    naive_now = now.replace(tzinfo=None)
    models = {code: LeagueModel(matches, naive_now) for code, matches in seasons.items()}

    # Status w API bywa opóźniony, więc "nierozpoczęty" = status i godzina w przyszłości.
    for m in window:
        m["open"] = m["status"] in NOT_STARTED and m["utc"] > now_s
    upcoming = [m for m in window if m["open"] and local_date(m["utc"], tz) in days]
    team_news = news.collect(cfg, upcoming, days, now, os.environ.get("API_FOOTBALL_KEY", "").strip(), demo)

    # Wszystkie znane wyniki (sezony lig + okno) - do formy, zmęczenia i H2H.
    all_matches = [m for ms in seasons.values() for m in ms] + [m for m in window if m["status"] == "FINISHED"]
    data_dir = os.path.join(ROOT, "data")
    prefix = "demo-" if demo else ""
    research_path = os.path.join(data_dir, prefix + "research.json")
    odds_path = os.path.join(data_dir, prefix + "odds.json")
    h2h_path = os.path.join(data_dir, prefix + "h2h.json")
    if demo:
        research_cache = research.demo(upcoming)
        h2h_cache = {}
    else:
        research_cache = research.run(cfg, upcoming, models, load_json(research_path, {}), now)
        h2h_cache = fetch.fetch_h2h(token, [m["id"] for m in upcoming], load_json(h2h_path, {}),
                                    cfg.get("h2h_per_run", 20))
    odds_store = load_json(odds_path, {})
    odds_key = os.environ.get("ODDS_API_KEY", "").strip()
    local_hour = now.astimezone(tz).hour
    if odds_key and not demo and local_hour in cfg.get("odds", {}).get("hours", [8, 16]):
        events = odds.fetch(odds_key, sorted({m["competition"] for m in upcoming}))
        odds_store = odds.update(odds_store, events, upcoming, now)

    out_days = []
    for d in days:
        ds = d.isoformat()
        day_matches = sorted((m for m in window if local_date(m["utc"], tz) == d), key=lambda m: (m["utc"], m["home"]))
        shown = []
        for m in day_matches:
            key = str(m["id"])
            if m["open"] and m["competition"] in models:
                code = m["competition"]
                predict_match(m, models[code], cfg, {
                    "news": team_news.get(m["id"]),
                    "research": (research_cache.get(str(m["id"])) or {}).get("data"),
                    "all_matches": all_matches,
                    "league_matches": seasons.get(code, []),
                    "h2h": h2h_cache.get(str(m["id"])),
                    "odds": odds_store.get(str(m["id"])),
                })
                # Typ zamrażamy dopiero w momencie rozpoczęcia meczu - do tego czasu
                # każda aktualizacja nadpisuje go świeższą wersją.
                history["picks"][key] = {
                    "date": ds, "utc": m["utc"], "competition": m["competition"],
                    "home": m["home"], "away": m["away"],
                    "market": m["pick"]["market"], "p": round(m["pick"]["p"], 4), "result": None,
                    "adjusted": m["adjusted"],
                }
                shown.append(m)
            elif key in history["picks"]:
                rec = history["picks"][key]
                m["pick"] = {"market": rec["market"], "p": rec["p"], "result": rec.get("result")}
                shown.append(m)

        stored = history["coupons"].get(ds, {})
        fresh = cp.build_coupons([m for m in shown if m["open"] and not m.get("low_data")])
        day_coupons = {}
        for key in ("safe", "standard", "bold"):
            old = stored.get(key)
            started = old and any(leg["utc"] <= now_s for leg in old["legs"])
            if started:
                day_coupons[key] = old
            elif key in fresh:
                c = fresh[key]
                day_coupons[key] = {
                    "p": round(c["p"], 4), "fair_odds": round(c["fair_odds"], 2),
                    "legs": [{"id": l["match"]["id"], "home": l["match"]["home"], "away": l["match"]["away"],
                              "utc": l["match"]["utc"], "market": l["market"], "p": round(l["p"], 4)}
                             for l in c["legs"]],
                }
        if day_coupons:
            history["coupons"][ds] = day_coupons
        out_days.append({"date": ds, "matches": shown, "coupons": day_coupons})

    if demo:
        # Kursy demo liczone z gotowych prognoz - podgląd sekcji kursów i value bet.
        demo_odds = odds.demo(upcoming, {m["id"]: m["prediction"]["probs"] for m in upcoming if "prediction" in m})
        for m in upcoming:
            if "prediction" in m:
                m["odds"] = odds.view(demo_odds.get(str(m["id"])), m["prediction"]["probs"], cfg)

    # Historia jest trzymana w całości - jest podstawą publicznej skuteczności.
    write(hist_path, json.dumps(history, ensure_ascii=False, indent=1, sort_keys=True))
    if not demo:
        keep = {str(m["id"]) for m in window}
        write(research_path, json.dumps({k: v for k, v in research_cache.items() if k in keep}, ensure_ascii=False, indent=1))
        write(odds_path, json.dumps({k: v for k, v in odds_store.items() if k in keep}, ensure_ascii=False))
        write(h2h_path, json.dumps({k: v for k, v in h2h_cache.items() if k in keep}, ensure_ascii=False))

    leagues = {code: {"name": ms[0]["competition_name"] if ms else code, "table": models[code].table}
               for code, ms in seasons.items() if code in models}
    for m in window:
        leagues.setdefault(m["competition"], {"name": m["competition_name"], "table": []})
    render_site(cfg, out_days, history, today, now, demo, leagues)
    return out_days


def render_site(cfg, out_days, history, today, now, demo, leagues):
    out = os.path.join(ROOT, "_site")
    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(os.path.join(ROOT, "static"), os.path.join(out, "assets"))
    updated = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    summary = stats.summarize(history, today)

    # Menu lig: kolejność z config.json, licznik meczów dziś + jutro.
    order = {c: i for i, c in enumerate(cfg["competitions"])}
    counts = {}
    for d in out_days:
        for m in d["matches"]:
            counts[m["competition"]] = counts.get(m["competition"], 0) + 1
    menu = {code: {**lg, "count": counts.get(code, 0)}
            for code, lg in sorted(leagues.items(), key=lambda kv: order.get(kv[0], 99))}
    match_pages = [m for d in out_days for m in d["matches"] if "prediction" in m]

    pages = []
    for lang in cfg["languages"]:
        d = os.path.join(out, lang)

        def page(name, html):
            write(os.path.join(d, name), html)
            if lang == cfg["languages"][0]:
                pages.append(name)

        page("index.html", render.index_page(cfg, lang, out_days, updated, demo, menu))
        page("results.html", render.results_page(cfg, lang, summary, updated, demo, menu))
        for month, month_days in summary["months"].items():
            page(f"archive-{month}.html",
                 render.archive_page(cfg, lang, month, month_days, summary["months"], updated, demo, menu))
        for name in ("about", "advertise", "responsible"):
            page(f"{name}.html", render.static_page(cfg, lang, name, updated, demo, menu))
        for code, lg in menu.items():
            page(f"league-{code}.html", render.league_page(cfg, lang, code, lg, out_days,
                                                           summary["by_comp"].get(code), updated, demo, menu))
        for m in match_pages:
            page(f"match-{m['id']}.html", render.match_page(cfg, lang, m, updated, demo, menu))

    write(os.path.join(out, "index.html"), render.root_redirect(cfg))
    base = cfg["base_url"].rstrip("/")
    urls = "".join(f"<url><loc>{base}/{l}/{p}</loc><lastmod>{today.isoformat()}</lastmod></url>"
                   for l in cfg["languages"] for p in pages)
    write(os.path.join(out, "sitemap.xml"),
          f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>')
    write(os.path.join(out, "robots.txt"), f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n")
    write(os.path.join(out, ".nojekyll"), "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="dane syntetyczne zamiast API")
    ap.add_argument("--langs", help="tylko wybrane języki, np. pl,en (szybki podgląd)")
    ap.add_argument("--now", help="symulowany czas UTC, np. 2026-10-01T06:00:00 (testy)")
    args = ap.parse_args()
    now = datetime.fromisoformat(args.now).replace(tzinfo=timezone.utc) if args.now else None
    days = build(demo=args.demo, now=now, langs=args.langs.split(",") if args.langs else None)
    for d in days:
        print(f'{d["date"]}: {len(d["matches"])} meczów, kupony: {", ".join(d["coupons"]) or "brak"}')


if __name__ == "__main__":
    main()
