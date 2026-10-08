"""Wybór typów dla meczów i składanie kuponów."""

# Rynki rozważane jako typ główny. "12" pomijamy - mało informacyjny.
CANDIDATES = ("1", "X", "2", "1X", "X2", "O15", "O25", "U25", "U35", "BTTS", "NOBTTS")
# Typy z p > MAX_P mają kurs fair < ~1.22, więc nie mają sensu na kuponie.
MAX_P = 0.82

COUPONS = (
    # (klucz, min p pojedynczego typu, maks p, liczba zdarzeń)
    ("safe", 0.68, MAX_P, 3),
    ("standard", 0.58, 0.75, 4),
    ("bold", 0.45, 0.62, 5),
)


def main_pick(probs):
    options = [(probs[k], k) for k in CANDIDATES if probs[k] <= MAX_P]
    p, k = max(options)
    return {"market": k, "p": p}


def alternatives(probs, exclude, n=2):
    options = sorted(((probs[k], k) for k in CANDIDATES if k != exclude and 0.5 <= probs[k] <= MAX_P),
                     reverse=True)
    return [{"market": k, "p": p} for p, k in options[:n]]


def build_coupons(matches):
    """matches: lista meczów (jeszcze nierozpoczętych) z kluczem 'prediction'."""
    result = {}
    for key, lo, hi, size in COUPONS:
        legs = []
        for m in matches:
            probs = m["prediction"]["probs"]
            fitting = [(probs[k], k) for k in CANDIDATES if lo <= probs[k] <= hi]
            if fitting:
                p, k = max(fitting)
                legs.append({"match": m, "market": k, "p": p})
        legs.sort(key=lambda leg: leg["p"], reverse=True)
        legs = legs[:size]
        if len(legs) < 2:
            continue
        total = 1.0
        for leg in legs:
            total *= leg["p"]
        result[key] = {"legs": legs, "p": total, "fair_odds": 1 / total}
    return result


def settle(market, hg, ag):
    g = hg + ag
    return {
        "1": hg > ag, "X": hg == ag, "2": hg < ag,
        "1X": hg >= ag, "X2": hg <= ag, "12": hg != ag,
        "O15": g >= 2, "O25": g >= 3, "O35": g >= 4,
        "U25": g <= 2, "U35": g <= 3,
        "BTTS": hg > 0 and ag > 0, "NOBTTS": hg == 0 or ag == 0,
    }[market]
