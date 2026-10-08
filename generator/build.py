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
from . import fetch, news, render, stats
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


def predict_match(m, model, cfg, team_news):
    *factors, adjusted = news.adjustments(team_news)
    pred = model.predict(m["home_id"], m["away_id"], tuple(factors))
    probs = pred["probs"]
    pick = cp.main_pick(probs)
    home_info, away_info = model.team_info(m["home_id"]), model.team_info(m["away_id"])
    m.update({
        "prediction": pred,
        "pick": pick,
        "alternatives": cp.alternatives(probs, pick["market"]),
        "xg_home": pred["xg_home"], "xg_away": pred["xg_away"],
        "likely_score": probs["score"],
        "home_form": home_info["form"] if home_info else "",
        "away_form": away_info["form"] if away_info else "",
        "low_data": pred["games"] < cfg["min_team_games"],
        "news": team_news or {},
        "adjusted": adjusted,
        "analysis": {lang: analysis(lang, m, pred, home_info, away_info, team_news) for lang in cfg["languages"]},
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


def build(demo=False, now=None):
    cfg = load_json(os.path.join(ROOT, "config.json"), {})
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

    out_days = []
    for d in days:
        ds = d.isoformat()
        day_matches = sorted((m for m in window if local_date(m["utc"], tz) == d), key=lambda m: (m["utc"], m["home"]))
        shown = []
        for m in day_matches:
            key = str(m["id"])
            if m["open"] and m["competition"] in models:
                predict_match(m, models[m["competition"]], cfg, team_news.get(m["id"]))
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

    # Historia jest trzymana w całości - jest podstawą publicznej skuteczności.
    write(hist_path, json.dumps(history, ensure_ascii=False, indent=1, sort_keys=True))

    render_site(cfg, out_days, history, today, now, demo)
    return out_days


def render_site(cfg, out_days, history, today, now, demo):
    out = os.path.join(ROOT, "_site")
    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(os.path.join(ROOT, "static"), os.path.join(out, "assets"))
    updated = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    summary = stats.summarize(history, today)

    for lang in cfg["languages"]:
        d = os.path.join(out, lang)
        write(os.path.join(d, "index.html"), render.index_page(cfg, lang, out_days, updated, demo))
        write(os.path.join(d, "results.html"), render.results_page(cfg, lang, summary, updated, demo))
        for month, month_days in summary["months"].items():
            write(os.path.join(d, f"archive-{month}.html"),
                  render.archive_page(cfg, lang, month, month_days, summary["months"], updated, demo))
        for page in ("about", "advertise", "responsible"):
            write(os.path.join(d, f"{page}.html"), render.static_page(cfg, lang, page, updated, demo))

    write(os.path.join(out, "index.html"), render.root_redirect(cfg))
    base = cfg["base_url"].rstrip("/")
    pages = [render._file(p) for p in render.PAGES] + [f"archive-{m}.html" for m in summary["months"]]
    urls = "".join(f"<url><loc>{base}/{l}/{p}</loc><lastmod>{today.isoformat()}</lastmod></url>"
                   for l in cfg["languages"] for p in pages)
    write(os.path.join(out, "sitemap.xml"),
          f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>')
    write(os.path.join(out, "robots.txt"), f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n")
    write(os.path.join(out, ".nojekyll"), "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="dane syntetyczne zamiast API")
    ap.add_argument("--now", help="symulowany czas UTC, np. 2026-10-01T06:00:00 (testy)")
    args = ap.parse_args()
    now = datetime.fromisoformat(args.now).replace(tzinfo=timezone.utc) if args.now else None
    days = build(demo=args.demo, now=now)
    for d in days:
        print(f'{d["date"]}: {len(d["matches"])} meczów, kupony: {", ".join(d["coupons"]) or "brak"}')


if __name__ == "__main__":
    main()
