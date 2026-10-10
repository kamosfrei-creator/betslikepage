"""Dane JSON dla interaktywnych stron (przegląd i statystyki).

  <lang>/data.json   mecze z 4 dni (wczoraj..pojutrze) z prognozami i analizą w danym języku
  data/history.json  pełna historia typów i kuponów (wspólna dla języków)
"""

KEEP_PROBS = ("1", "X", "2", "1X", "X2", "12", "O15", "O25", "O35", "U25", "U35", "BTTS", "NOBTTS")


def _r(x, n=3):
    return round(x, n) if isinstance(x, float) else x


def match(m, lang):
    out = {
        "id": m["id"], "utc": m["utc"], "status": m["status"], "comp": m["competition"],
        "home": m["home"], "away": m["away"], "hc": m.get("home_crest"), "ac": m.get("away_crest"),
        "hg": m.get("home_goals"), "ag": m.get("away_goals"),
        "page": "prediction" in m,
    }
    pick = m.get("pick")
    if pick:
        out["pick"] = {"m": pick["market"], "p": _r(pick["p"]), "r": pick.get("result")}
    if "prediction" in m:
        pred = m["prediction"]
        out.update({
            "p": {k: _r(pred["probs"][k]) for k in KEEP_PROBS},
            "xg": [_r(pred["xg_home"], 2), _r(pred["xg_away"], 2)],
            "scores": [[x, y, _r(p)] for x, y, p in pred["top_scores"][:3]],
            "alts": [{"m": a["market"], "p": _r(a["p"])} for a in m.get("alternatives", [])],
            "form": [m.get("home_form", ""), m.get("away_form", "")],
            "ranks": list(m.get("ranks") or (None, None)),
            "elo": [pred["elo_home"], pred["elo_away"]],
            "flags": m.get("flags") or {},
            "adj": bool(m.get("adjusted")),
            "low": bool(m.get("low_data")),
            "text": m["analysis"][lang],
        })
        if m.get("odds"):
            out["odds"] = {r["outcome"]: {"now": r["now"], "best": r["best"], "v": r["value"], "isv": r["is_value"]}
                           for r in m["odds"]}
    return out


def day_data(cfg, lang, out_days, leagues, updated, demo):
    seen = set()
    matches = []
    for d in out_days:
        for m in d["matches"]:
            if m["id"] in seen:
                continue
            seen.add(m["id"])
            matches.append({**match(m, lang), "day": d["key"]})
    league_meta = {}
    for d in out_days:
        for m in d["matches"]:
            league_meta.setdefault(m["competition"], {
                "name": m["competition_name"], "emblem": m.get("emblem"), "area": m.get("area"), "flag": m.get("flag")})
    order = {c: i for i, c in enumerate(cfg["competitions"])}
    return {
        "updated": updated, "demo": demo,
        "days": [{"key": d["key"], "date": d["date"]} for d in out_days],
        "leagues": dict(sorted(league_meta.items(), key=lambda kv: order.get(kv[0], 99))),
        "matches": matches,
        "coupons": {d["key"]: d["coupons"] for d in out_days if d["coupons"]},
    }


def history_data(history, leagues):
    picks = [{"id": int(k) if str(k).isdigit() else k, "d": r["date"], "utc": r["utc"], "c": r.get("competition"),
              "h": r["home"], "a": r["away"], "m": r["market"], "p": r["p"], "r": r.get("result"),
              "s": r.get("score"), "o": r.get("odds")}
             for k, r in history["picks"].items()]
    picks.sort(key=lambda x: x["utc"], reverse=True)
    coupons = [{"d": d, "k": k, "p": c["p"], "o": c.get("fair_odds"), "r": c.get("result")}
               for d, day in history.get("coupons", {}).items() for k, c in day.items()]
    return {"picks": picks, "coupons": coupons,
            "leagues": {code: lg["name"] for code, lg in leagues.items()}}
