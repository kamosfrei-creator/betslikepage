"""Zestawienia skuteczności na podstawie pełnej historii typów."""

from datetime import timedelta

COUPON_KEYS = ("safe", "standard", "bold")


def _agg(rows):
    settled = [r for r in rows if r.get("result") in ("won", "lost")]
    return {"settled": len(settled), "won": sum(r["result"] == "won" for r in settled)}


def summarize(history, today):
    picks = list(history["picks"].values())
    since = lambda n: (today - timedelta(days=n)).isoformat()

    by_market = {}
    for r in picks:
        by_market.setdefault(r["market"], []).append(r)

    coupons = {k: [] for k in COUPON_KEYS}
    for day in history.get("coupons", {}).values():
        for k, c in day.items():
            coupons.setdefault(k, []).append(c)

    days = {}
    for r in picks:
        days.setdefault(r["date"], {"picks": [], "coupons": {}})["picks"].append(r)
    for d, c in history.get("coupons", {}).items():
        days.setdefault(d, {"picks": [], "coupons": {}})["coupons"] = c

    day_list = []
    for d in sorted(days, reverse=True):
        if d > today.isoformat():
            continue
        entry = days[d]
        entry["picks"].sort(key=lambda r: (r["utc"], r["home"]))
        day_list.append({"date": d, **entry, **_agg(entry["picks"]),
                         "pending": sum(not r.get("result") for r in entry["picks"])})

    months = {}
    for day in day_list:
        months.setdefault(day["date"][:7], []).append(day)

    return {
        "all": _agg(picks),
        "d30": _agg([r for r in picks if r["date"] >= since(30)]),
        "d7": _agg([r for r in picks if r["date"] >= since(7)]),
        "markets": {m: _agg(rows) for m, rows in sorted(by_market.items())},
        "coupons": {k: _agg(v) for k, v in coupons.items()},
        "recent_days": day_list[:14],
        "months": months,
    }
