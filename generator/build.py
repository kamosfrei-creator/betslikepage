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
from . import fetch, render
from .model import LeagueModel
from .texts import UI, analysis

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOT_STARTED = ("SCHEDULED", "TIMED")
VOID = ("POSTPONED", "CANCELLED", "SUSPENDED", "AWARDED")
HISTORY_DAYS = 180


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


def predict_match(m, model, cfg):
    pred = model.predict(m["home_id"], m["away_id"])
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
        "analysis": {lang: analysis(lang, m, pred, home_info, away_info) for lang in cfg["languages"]},
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


def build(demo=False):
    cfg = load_json(os.path.join(ROOT, "config.json"), {})
    tz = ZoneInfo(cfg["timezone"])
    now = datetime.now(timezone.utc)
    today = now.astimezone(tz).date()
    days = [today, today + timedelta(days=1)]

    token = os.environ.get("FOOTBALL_DATA_TOKEN", "").strip()
    demo = demo or not token
    if demo:
        window, seasons = fetch.fetch_demo(today)
    else:
        window, seasons = fetch.fetch_live(token, cfg["competitions"], today)

    hist_path = os.path.join(ROOT, "data", "demo-history.json" if demo else "history.json")
    history = load_json(hist_path, {"picks": {}, "coupons": {}})
    history.setdefault("coupons", {})

    settle_history(history, window)
    now_s = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    naive_now = now.replace(tzinfo=None)
    models = {code: LeagueModel(matches, naive_now) for code, matches in seasons.items()}

    out_days = []
    for d in days:
        ds = d.isoformat()
        day_matches = sorted((m for m in window if local_date(m["utc"], tz) == d), key=lambda m: (m["utc"], m["home"]))
        shown = []
        for m in day_matches:
            key = str(m["id"])
            if m["status"] in NOT_STARTED and m["competition"] in models:
                predict_match(m, models[m["competition"]], cfg)
                # Typ zamrażamy dopiero w momencie rozpoczęcia meczu - do tego czasu
                # każda aktualizacja nadpisuje go świeższą wersją.
                history["picks"][key] = {
                    "date": ds, "utc": m["utc"], "competition": m["competition"],
                    "home": m["home"], "away": m["away"],
                    "market": m["pick"]["market"], "p": round(m["pick"]["p"], 4), "result": None,
                }
                shown.append(m)
            elif key in history["picks"]:
                rec = history["picks"][key]
                m["pick"] = {"market": rec["market"], "p": rec["p"], "result": rec.get("result")}
                shown.append(m)

        stored = history["coupons"].get(ds, {})
        fresh = cp.build_coupons([m for m in shown if m["status"] in NOT_STARTED and not m.get("low_data")])
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

    cutoff = (today - timedelta(days=HISTORY_DAYS)).isoformat()
    history["picks"] = {k: v for k, v in history["picks"].items() if v["date"] >= cutoff}
    history["coupons"] = {k: v for k, v in history["coupons"].items() if k >= cutoff}
    write(hist_path, json.dumps(history, ensure_ascii=False, indent=1, sort_keys=True))

    render_site(cfg, out_days, history, today, now, demo)
    return out_days


def stats_of(history, today):
    settled = [r for r in history["picks"].values() if r.get("result") in ("won", "lost")]
    recent_from = (today - timedelta(days=30)).isoformat()

    def agg(rows):
        return {"settled": len(rows), "won": sum(r["result"] == "won" for r in rows)}

    rows = sorted((r for r in history["picks"].values() if r.get("result")),
                  key=lambda r: r["utc"], reverse=True)[:200]
    return {"all": agg(settled), "recent": agg([r for r in settled if r["date"] >= recent_from])}, rows


def render_site(cfg, out_days, history, today, now, demo):
    out = os.path.join(ROOT, "_site")
    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(os.path.join(ROOT, "static"), os.path.join(out, "assets"))
    updated = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    stats, rows = stats_of(history, today)

    for lang in cfg["languages"]:
        d = os.path.join(out, lang)
        write(os.path.join(d, "index.html"), render.index_page(cfg, lang, out_days, updated, demo))
        write(os.path.join(d, "results.html"), render.results_page(cfg, lang, stats, rows, updated, demo))
        for page in ("about", "advertise", "responsible"):
            write(os.path.join(d, f"{page}.html"), render.static_page(cfg, lang, page, updated, demo))

    write(os.path.join(out, "index.html"), render.root_redirect(cfg))
    base = cfg["base_url"].rstrip("/")
    urls = "".join(f"<url><loc>{base}/{l}/{render._file(p)}</loc><lastmod>{today.isoformat()}</lastmod></url>"
                   for l in cfg["languages"] for p in render.PAGES)
    write(os.path.join(out, "sitemap.xml"),
          f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>')
    write(os.path.join(out, "robots.txt"), f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n")
    write(os.path.join(out, ".nojekyll"), "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="dane syntetyczne zamiast API")
    args = ap.parse_args()
    days = build(demo=args.demo)
    for d in days:
        print(f'{d["date"]}: {len(d["matches"])} meczów, kupony: {", ".join(d["coupons"]) or "brak"}')


if __name__ == "__main__":
    main()
