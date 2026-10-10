"""Wybór typów dla meczów i składanie kuponów."""

# Rynki rozważane jako typ główny. "12" pomijamy - mało informacyjny.
CANDIDATES = ("1", "X", "2", "1X", "X2", "O15", "O25", "U25", "U35", "BTTS", "NOBTTS")
# Typy z p > MAX_P mają kurs fair < ~1.22, więc nie mają sensu na kuponie.
MAX_P = 0.82

# Typy "z kursem 1,5-2,0": prawdopodobieństwo 47-69% (kurs fair ok. 1,45-2,15).
RANGE_LO, RANGE_HI = 0.47, 0.69

COUPONS = (
    # (klucz, min p pojedynczego typu, maks p, liczba zdarzeń, wymagana pełna liczba)
    ("safe", 0.68, MAX_P, 3, False),
    ("standard", 0.58, 0.75, 4, False),
    ("bold", 0.45, 0.62, 5, False),
    ("range", RANGE_LO, RANGE_HI, 4, False),
    ("c8", 0.62, MAX_P, 8, True),
    ("c10", 0.6, MAX_P, 10, True),
)
COUPON_KEYS = tuple(c[0] for c in COUPONS)


def main_pick(probs):
    options = [(probs[k], k) for k in CANDIDATES if probs[k] <= MAX_P]
    p, k = max(options)
    return {"market": k, "p": p}


def range_pick(probs):
    """Najpewniejszy typ z kursem fair ok. 1,5-2,0 (albo None)."""
    options = [(probs[k], k) for k in CANDIDATES if RANGE_LO <= probs[k] <= RANGE_HI]
    if not options:
        return None
    p, k = max(options)
    return {"market": k, "p": p}


def slip_stats(ps):
    """Statystyki kuponu: oczekiwana liczba trafień i szansa na najwyżej jedno pudło."""
    dist = [1.0]  # rozkład liczby trafień (Poisson-dwumianowy)
    for p in ps:
        nxt = [0.0] * (len(dist) + 1)
        for k, v in enumerate(dist):
            nxt[k] += v * (1 - p)
            nxt[k + 1] += v * p
        dist = nxt
    n = len(ps)
    return {"exp": sum(ps), "p1miss": dist[n] + (dist[n - 1] if n >= 1 else 0), "avg_p": sum(ps) / n if n else 0}


def alternatives(probs, exclude, n=2):
    options = sorted(((probs[k], k) for k in CANDIDATES if k != exclude and 0.5 <= probs[k] <= MAX_P),
                     reverse=True)
    return [{"market": k, "p": p} for p, k in options[:n]]


def build_coupons(matches):
    """matches: lista meczów (jeszcze nierozpoczętych) z kluczem 'prediction'."""
    result = {}
    for key, lo, hi, size, full in COUPONS:
        legs = []
        for m in matches:
            probs = m["prediction"]["probs"]
            fitting = [(probs[k], k) for k in CANDIDATES if lo <= probs[k] <= hi]
            if fitting:
                p, k = max(fitting)
                legs.append({"match": m, "market": k, "p": p})
        legs.sort(key=lambda leg: leg["p"], reverse=True)
        legs = legs[:size]
        if len(legs) < (size if full else 2):
            continue
        total = 1.0
        for leg in legs:
            total *= leg["p"]
        result[key] = {"legs": legs, "p": total, "fair_odds": 1 / total, **slip_stats([leg["p"] for leg in legs])}
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
