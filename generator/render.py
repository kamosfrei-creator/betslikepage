"""Generowanie statycznych stron HTML.

Struktura w każdym języku:
  index.html            przegląd: kupony, najmocniejsze typy, mecze wg lig
  league-<KOD>.html     liga: mecze dziś/jutro, tabela, trafność w lidze
  match-<id>.html       analiza meczu (forma, H2H, statystyki, wyniki, kursy...)
  results.html, archive-<rrrr-mm>.html, about/advertise/responsible.html
"""

import json
from html import escape

from .texts import MARKETS, META, UI, num, pct

PAGES = ("index", "results", "community", "about", "advertise", "responsible", "privacy")


def _file(page):
    return "index.html" if page == "index" else f"{page}.html"


# ------------------------------------------------------------------ layout

def layout(cfg, lang, page, title, body, updated, demo, leagues=None, active=None):
    t = UI[lang]
    base = cfg["base_url"].rstrip("/")
    alt = "\n".join(f'<link rel="alternate" hreflang="{l}" href="{base}/{l}/{_file(page)}">' for l in cfg["languages"])
    nav = "".join(
        f'<a href="{_file(p)}"{" aria-current=page" if p == page else ""}>{escape(t[k])}</a>'
        for p, k in (("index", "coupons"), ("results", "results"), ("community", "community"), ("about", "method_title"),
                     ("advertise", "advertise")))
    options = "".join(
        f'<option value="../{l}/{_file(page)}" data-lang="{l}"{" selected" if l == lang else ""}>'
        f'{escape(META[l]["name"])}</option>' for l in cfg["languages"])
    banner = f'<div class="demo">{escape(t["demo"])}</div>' if demo else ""
    side = ""
    if leagues:
        items = "".join(
            f'<div class="lg-item" data-code="{escape(code)}"><a href="league-{code}.html"{" aria-current=page" if code == active else ""}>'
            f'<span class="lg-code">{escape(code)}</span><span class="lg-name">{escape(lg["name"])}</span>'
            f'<span class="lg-count">{lg.get("count") or ""}</span></a>'
            f'<button type="button" class="lg-star" data-fav-league="{escape(code)}" aria-pressed="false" '
            f'title="{escape(t["fav_league_toggle"])}" aria-label="{escape(t["fav_league_toggle"])}">☆</button></div>'
            for code, lg in leagues.items())
        side = f"""<aside class="sidebar" aria-label="{escape(t["leagues"])}">
<a class="side-home" href="index.html"{" aria-current=page" if page == "index" else ""}><span class="lg-code">⚽</span><span class="lg-name">{escape(t["overview"])}</span><span class="lg-count"></span></a>
<p class="side-title fav-title" hidden>{escape(t["fav_leagues"])}</p><div class="fav-list"></div>
<p class="side-title">{escape(t["leagues"])}</p>
<div class="lg-list">{items}</div></aside>"""
    return f"""<!doctype html>
<html lang="{lang}" dir="{META[lang]["dir"]}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} | {escape(cfg["site_name"])}</title>
<meta name="description" content="{escape(t["tagline"])}">
<link rel="canonical" href="{base}/{lang}/{_file(page)}">
{alt}
<link rel="icon" href="../assets/favicon.svg">
<link rel="stylesheet" href="../assets/style.css">
<script>try{{if(localStorage.getItem("bl:theme")==='"dark"')document.documentElement.setAttribute("data-theme","dark")}}catch(e){{}}</script>
<script defer src="../assets/app.js"></script>
</head>
<body>
{banner}
<header class="topbar">
  <div class="topbar-in">
    <a class="brand" href="index.html"><img class="logo" src="../assets/logo.svg" alt="" width="34" height="34"><span class="wm">OnePick<b>Away</b></span></a>
    <nav class="mainnav">{nav}</nav>
    <div class="top-actions">
      <button type="button" id="theme-btn" class="tb" aria-label="{escape(t["theme_dark"])}" title="{escape(t["theme_dark"])}">◐</button>
      <button type="button" id="login-btn" class="tb login">{escape(t["login"])}</button>
      <label class="langs"><span class="sr">{escape(t["language"])}</span>
        <select id="lang-select" aria-label="{escape(t["language"])}">{options}</select></label>
    </div>
  </div>
</header>
<div class="shell{' has-side' if side else ''}">
{side}
<main>
{body}
</main>
<aside id="slip" class="slip" aria-label="{escape(t["my_slip"])}"></aside>
</div>
<script id="i18n" type="application/json">{_i18n(lang)}</script>
<script id="site-cfg" type="application/json">{_site_cfg(cfg)}</script>
<footer>
  <div class="foot-in">
  <p class="disclaimer"><strong>18+</strong> {escape(t["disclaimer"])}</p>
  <p>{escape(t["help_text"])} <a href="{t["help_url"]}" rel="noopener" target="_blank">{escape(t["help_name"])}</a> ·
     <a href="responsible.html">{escape(t["responsible"])}</a> · <a href="about.html">{escape(t["about"])}</a> ·
     <a href="privacy.html">{escape(t["privacy"])}</a></p>
  <p class="muted">{escape(t["data_credit"])}{(" " + escape(t["data_extra"])) if cfg.get("extra_leagues") else ""}</p>
  <p class="muted">{escape(t["updated"])}: <time data-utc="{updated}">{updated}</time> · {escape(t["next_update"])}</p>
  </div>
</footer>
</body>
</html>
"""


def _json_script(data):
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def _i18n(lang):
    """Teksty interfejsu dla skryptu (bez długich bloków HTML)."""
    return _json_script({"lang": lang, "decimal": META[lang]["decimal"], "dir": META[lang]["dir"],
                         "ui": {k: v for k, v in UI[lang].items() if not k.endswith("_html")},
                         "markets": MARKETS[lang]})


def _site_cfg(cfg):
    """Publiczna konfiguracja dla przeglądarki (klucz anon Supabase jest publiczny z założenia)."""
    sb = cfg.get("supabase") or {}
    return _json_script({"supabase": {"url": sb.get("url", ""), "key": sb.get("anon_key", "")}})


def _slip_btn(m, market, p, label="+", cls="slip-add"):
    """Przycisk dodania typu do kuponu użytkownika (obsługuje go app.js na każdej stronie)."""
    if m.get("status") not in ("SCHEDULED", "TIMED"):
        return ""
    o = next((r["now"] for r in m.get("odds") or [] if r["outcome"] == market), None)
    data = {"id": m["id"], "m": market, "p": round(p, 4), "home": m["home"], "away": m["away"], "o": o, "utc": m["utc"]}
    return f'<button type="button" class="{cls}" data-slip="{escape(json.dumps(data, ensure_ascii=False))}" aria-label="+">{label}</button>'


def _app(lang, kind, static_html):
    """Kontener aplikacji JS: statyczna treść (SEO, brak JS), którą skrypt zastępuje."""
    return f'<div id="app" data-kind="{kind}">{static_html}</div>'


# ----------------------------------------------------------------- pieces

def ad_slot(cfg, lang, slot):
    t = UI[lang]
    for ad in cfg.get("ads", []):
        if ad.get("slot") == slot and lang in ad.get("languages", [lang]):
            return (f'<aside class="ad"><span class="ad-label">{escape(t["ad_label"])} · 18+</span>'
                    f'<a href="{escape(ad["url"])}" rel="sponsored nofollow noopener" target="_blank">'
                    f'<img src="{escape(ad["image"])}" alt="{escape(ad.get("alt", ""))}" loading="lazy"></a></aside>')
    return f'<aside class="ad placeholder"><a href="advertise.html">{escape(t["ad_placeholder"])}</a></aside>'


def _form(form):
    return "".join(f'<i class="f{c}">{c}</i>' for c in form)


def _badge(result):
    if not result:
        return ""
    sym = {"won": "✔", "lost": "✘", "void": "–"}[result]
    return f'<span class="badge {result}">{sym}</span>'


def _odds(p):
    return num(1 / p, "en") if p > 0 else "-"


def _pick_line(lang, market, p):
    return (f'<span class="market">{escape(MARKETS[lang][market])}</span>'
            f'<span class="prob">{pct(p)}</span><span class="odds">@{_odds(p)}</span>')


def _pbar(probs):
    return ('<div class="pbar" aria-hidden="true">'
            f'<span class="p1" style="width:{probs["1"] * 100:.1f}%"></span>'
            f'<span class="px" style="width:{probs["X"] * 100:.1f}%"></span>'
            f'<span class="p2" style="width:{probs["2"] * 100:.1f}%"></span></div>')


def _value_flag(m):
    return any(r["is_value"] for r in m.get("odds") or [])


def coupon_card(lang, key, coupon):
    t = UI[lang]
    legs = "".join(
        f'<li><span class="teams">{escape(leg["home"])} – {escape(leg["away"])}</span>'
        f'<span class="leg-meta"><time data-utc="{leg["utc"]}" data-fmt="time"></time>'
        f'{_pick_line(lang, leg["market"], leg["p"])}{_badge(leg.get("result"))}</span></li>'
        for leg in coupon["legs"])
    return f"""<article class="coupon {key}">
<header><h3>{escape(t["coupon_" + key])}</h3>{_badge(coupon.get("result"))}</header>
<ol>{legs}</ol>
<footer class="total"><span>{escape(t["probability"])} <b>{pct(coupon["p"])}</b></span>
<span>{escape(t["fair_odds"])} <b>{num(coupon["fair_odds"], "en")}</b></span>
{f'<span>{escape(t["exp_hits"])} <b>{num(coupon["exp"], lang)}/{len(coupon["legs"])}</b></span>' if coupon.get("exp") else ""}</footer>
</article>"""


def match_row(lang, m):
    """Wiersz tabeli meczów: godzina, mecz, 1/X/2 w %, przewidywany wynik, typ."""
    t = UI[lang]
    pick = m["pick"]
    has_pred = "prediction" in m
    score = ""
    if m.get("home_goals") is not None and m["status"] in ("IN_PLAY", "PAUSED", "FINISHED"):
        score = f'<span class="live-score">{m["home_goals"]}:{m["away_goals"]}</span>'
    if has_pred:
        p = m["prediction"]["probs"]
        best = max(("1", "X", "2"), key=lambda k: p[k])
        cells = "".join(f'<span class="pc{" hi" if k == best else ""}">{round(p[k] * 100)}</span>' for k in ("1", "X", "2"))
        hs, as_ = m["likely_score"]
        exp = f'<span class="cs">{hs}:{as_}</span>'
    else:
        cells, exp = '<span class="pc">–</span>' * 3, '<span class="cs">–</span>'
    teams = f'{escape(m["home"])} <span class="vs">–</span> {escape(m["away"])}'
    link = f'<a class="mt" href="match-{m["id"]}.html">{teams}</a>' if has_pred else f'<span class="mt">{teams}</span>'
    flags = ""
    if m.get("adjusted"):
        flags += f'<span class="chip news" title="{escape(t["adjusted"])}">i</span>'
    if _value_flag(m):
        flags += f'<span class="chip value">{escape(t["value_bet"])}</span>'
    if m.get("low_data"):
        flags += f'<span class="chip low" title="{escape(t["low_data"])}">?</span>'
    tip = (f'<span class="market">{escape(MARKETS[lang][pick["market"]])}</span>'
           f'<span class="prob">{pct(pick["p"])}</span>{_badge(pick.get("result"))}'
           f'{_slip_btn(m, pick["market"], pick["p"]) if has_pred else ""}') if pick else "–"
    return f"""<div class="row" data-start="{m["utc"]}">
<time class="ko" data-utc="{m["utc"]}" data-fmt="time"></time>
<div class="teams-cell">{link}{score}{flags}</div>
<div class="p3">{cells}</div>{exp}
<div class="tip">{tip}</div>
</div>"""


def match_table(lang, matches):
    t = UI[lang]
    head = (f'<div class="row head"><span>{escape(t["kickoff"])}</span><span>{escape(t["match"])}</span>'
            f'<div class="p3"><span>1</span><span>X</span><span>2</span></div>'
            f'<span class="cs">{escape(t["predicted_score"])}</span><span class="tip">{escape(t["pick"])}</span></div>')
    return f'<div class="mtable">{head}{"".join(match_row(lang, m) for m in matches)}</div>'


def _by_league(matches):
    groups = {}
    for m in matches:
        groups.setdefault((m["competition"], m["competition_name"]), []).append(m)
    return groups


def _day_tabs(t):
    return ('<nav class="tabs">' + "".join(f'<a href="#{k}">{escape(t[k])}</a>'
            for k in ("yesterday", "today", "tomorrow", "after_tomorrow")) + "</nav>")


# ----------------------------------------------------------------- pages

def index_page(cfg, lang, days, updated, demo, leagues=None):
    t = UI[lang]
    sections = []
    for i, day in enumerate(days):
        label = t[day["key"]]
        coupons = "".join(coupon_card(lang, k, c) for k, c in day["coupons"].items())
        candidates = [m for m in day["matches"] if "prediction" in m and not m.get("low_data") and m.get("pick")]
        top = sorted(candidates, key=lambda m: m["pick"]["p"], reverse=True)[:6]
        top_html = "".join(
            f'<a class="top-pick" href="match-{m["id"]}.html"><span class="tp-comp">{escape(m["competition_name"])}</span>'
            f'<span class="tp-teams">{escape(m["home"])} – {escape(m["away"])}</span>'
            f'<span class="tp-pick">{escape(MARKETS[lang][m["pick"]["market"]])}</span>'
            f'<span class="tp-p">{pct(m["pick"]["p"])}</span></a>' for m in top)
        groups = "".join(
            f'<section class="league-block"><h4><a href="league-{code}.html">{escape(name)}</a></h4>{match_table(lang, ms)}</section>'
            for (code, name), ms in _by_league(day["matches"]).items())
        sections.append(f"""<section class="day" id="{day["key"]}">
<h2>{escape(label)} <small>{day["date"]}</small></h2>
{f'<div class="coupons">{coupons}</div><p class="hint">{escape(t["fair_odds_hint"])}</p>' if coupons else ''}
{f'<h3 class="sec">{escape(t["top_picks"])}</h3><div class="top-picks">{top_html}</div>' if top_html else ''}
{ad_slot(cfg, lang, "day" + str(i))}
<h3 class="sec">{escape(t["all_matches"])}</h3>
{groups or f'<p class="empty">{escape(t["no_matches"])}</p>'}
</section>""")
    static = _day_tabs(t) + "\n".join(sections)
    feats = "".join(f'<li>{escape(t["hero_f" + str(i)])}</li>' for i in range(1, 6))
    hero = (f'<section class="welcome"><div><h1>{escape(t["hero_title"])}</h1><p>{escape(t["hero_sub"])}</p>'
            f'<ul class="feats">{feats}</ul><a class="btn" href="#matches">{escape(t["hero_cta"])} ↓</a></div></section>')
    return layout(cfg, lang, "index", t["coupons"], hero + '<div id="matches"></div>' + _app(lang, "tips", static),
                  updated, demo, leagues)


def _standings(lang, table, highlight=()):
    t = UI[lang]
    if not table:
        return ""
    rows = "".join(
        f'<tr{" class=hl" if r["id"] in highlight else ""}><td>{r["rank"]}</td><td class="tn">{escape(str(r["team"]))}</td>'
        f'<td>{r["p"]}</td><td>{r["w"]}</td><td>{r["d"]}</td><td>{r["l"]}</td>'
        f'<td>{r["gf"]}:{r["ga"]}</td><td><b>{r["pts"]}</b></td></tr>' for r in table)
    return f"""<div class="table-wrap"><table class="standings">
<thead><tr><th>{escape(t["pos"])}</th><th>{escape(t["team"])}</th><th>{escape(t["played"])}</th><th>{escape(t["w"])}</th>
<th>{escape(t["d"])}</th><th>{escape(t["l"])}</th><th>{escape(t["goals"])}</th><th>{escape(t["pts"])}</th></tr></thead>
<tbody>{rows}</tbody></table></div>"""


def league_page(cfg, lang, code, league, days, record, updated, demo, leagues):
    t = UI[lang]
    parts = [f'<h1>{escape(league["name"])}</h1>']
    if record and record["settled"]:
        parts.append(f'<p class="league-rec">{escape(t["league_record"])}: <b>{pct(record["won"] / record["settled"])}</b> '
                     f'({record["won"]}/{record["settled"]})</p>')
    any_match = False
    for i, day in enumerate(days):
        ms = [m for m in day["matches"] if m["competition"] == code]
        if ms:
            any_match = True
            parts.append(f'<section data-day="{day["key"]}"><h2>{escape(t[day["key"]])} <small>{day["date"]}</small></h2>'
                         + match_table(lang, ms) + "</section>")
    if not any_match:
        parts.append(f'<p class="empty">{escape(t["no_league_matches"])}</p>')
    parts.append(ad_slot(cfg, lang, "league"))
    if league.get("table"):
        parts.append(f'<h2>{escape(t["standings"])}</h2>' + _standings(lang, league["table"]))
    return layout(cfg, lang, f"league-{code}", league["name"], "\n".join(parts), updated, demo, leagues, code)


def _recent_list(team_name, games):
    if not games:
        return ""
    rows = "".join(
        f'<li><time data-utc="{g["utc"]}" data-fmt="date"></time><span class="rl-teams">{escape(g["home"])} – {escape(g["away"])}</span>'
        f'<b>{g["score"]}</b><i class="f{g["res"]}">{g["res"]}</i></li>' for g in games)
    return f'<div class="recent"><h4>{escape(team_name)}</h4><ol>{rows}</ol></div>'


def _stat_compare(label, hv, av, fmt):
    total = (hv or 0) + (av or 0)
    hw = 50 if not total else hv / total * 100
    return (f'<div class="cmp"><span class="cv">{fmt(hv)}</span><span class="cl">{escape(label)}</span>'
            f'<span class="cv r">{fmt(av)}</span><div class="cbar"><span class="ch" style="width:{hw:.0f}%"></span>'
            f'<span class="ca" style="width:{100 - hw:.0f}%"></span></div></div>')


def _absences(lang, side_data):
    t = UI[lang]
    items = (side_data or {}).get("absences", [])
    if not items:
        return f'<p class="muted">{escape(t["no_injuries"])}</p>'
    return '<ul class="abs">' + "".join(
        f'<li><span class="pos">{escape(a.get("position", ""))}</span><span class="pn">{escape(a["player"])}</span>'
        f'{"<span class=key>★</span>" if a.get("importance") == "key" else ""}'
        f'<span class="st {escape(a.get("status", ""))}">{escape(t["out"] if a.get("status") == "out" else t["doubtful"])}</span></li>'
        for a in items) + "</ul>"


def _book_link(lang, r, big=False):
    t = UI[lang]
    if r["url"] and (not r["book_langs"] or lang in r["book_langs"]):
        return (f'<a class="bet{" big" if big else ""}" href="{escape(r["url"])}" rel="sponsored nofollow noopener" target="_blank">'
                f'{escape(t["bet_now"].format(bookmaker=r["book_name"]))}</a>')
    return escape(r["book_name"]) if r["book_name"] else ""


def _odds_block(lang, m):
    t = UI[lang]
    rows = m.get("odds")
    if not rows:
        return f'<p class="muted">{escape(t["no_odds"])}</p>'
    body = ""
    for r in rows:
        move = r["move"]
        arrow = f'<span class="mv {"up" if move > 0 else "down"}">{"▲" if move > 0 else "▼"}</span>' if move else ""
        value = f'{num(r["value"], lang)}' + (f' <span class="chip value">{escape(t["value_bet"])}</span>' if r["is_value"] else "")
        body += (f'<tr><td><b>{r["outcome"]}</b></td><td>{num(r["open"], lang)}</td><td>{num(r["now"], lang)} {arrow}</td>'
                 f'<td><b>{num(r["best"], lang)}</b></td><td>{value}</td><td>{_book_link(lang, r)}</td></tr>')
    return f"""<div class="table-wrap"><table class="odds-t">
<thead><tr><th></th><th>{escape(t["opening"])}</th><th>{escape(t["current"])}</th><th>{escape(t["best_odds"])}</th>
<th>{escape(t["value_bet"])}</th><th>{escape(t["bookmaker"])}</th></tr></thead><tbody>{body}</tbody></table></div>
<p class="hint">{escape(t["value_hint"])} <span class="ad-label">18+</span></p>"""


def _breakdown(lang, m):
    """Dane wejściowe modelu i szanse 1X2 po każdym kroku obliczeń."""
    t = UI[lang]
    pred = m["prediction"]
    r = pred["ratings"]
    fi, ld = m.get("form_index") or {}, m.get("load") or {}

    def val(v, suffix=""):
        if v is None:
            return "–"
        return (num(v, lang) if isinstance(v, float) else str(v)) + suffix

    def ratio(x):
        return f"{'+' if x >= 1 else ''}{round((x - 1) * 100)}%"

    def bar_row(label, hv, av, hraw=None, araw=None):
        hv_n, av_n = hraw if hraw is not None else hv, araw if araw is not None else av
        tot = (hv_n or 0) + (av_n or 0)
        hw = 50 if not tot else hv_n / tot * 100
        return (f'<div class="cmp"><span class="cv">{hv}</span><span class="cl">{escape(label)}</span>'
                f'<span class="cv r">{av}</span><div class="cbar"><span class="ch" style="width:{hw:.0f}%"></span>'
                f'<span class="ca" style="width:{100 - hw:.0f}%"></span></div></div>')

    fh, fa = fi.get("home", {}), fi.get("away", {})
    lh, la = ld.get("home", {}), ld.get("away", {})
    w, d, l = m.get("h2h_balance") or (0, 0, 0)
    inputs = (
        bar_row(t["form_index"], val(fh.get("all")), val(fa.get("all")), fh.get("all"), fa.get("all"))
        + bar_row(t["form_venue"], val(fh.get("venue")), val(fa.get("venue")), fh.get("venue"), fa.get("venue"))
        + bar_row(f'{t["attack_rating"]} ({t["vs_avg"]})', ratio(r["home_att"]), ratio(r["away_att"]), r["home_att"], r["away_att"])
        + bar_row(f'{t["defence_rating"]} ({t["vs_avg"]})', ratio(r["home_def"]), ratio(r["away_def"]), r["home_def"], r["away_def"])
        + bar_row("Elo", pred["elo_home"], pred["elo_away"])
        + bar_row(t["load_14"], val(lh.get("m14")), val(la.get("m14")), lh.get("m14"), la.get("m14"))
        + bar_row(t["rest_days"], val(lh.get("rest")), val(la.get("rest")), lh.get("rest"), la.get("rest"))
        + (f'<p class="h2h-bal">{escape(t["h2h_balance"])}: <b>{w}-{d}-{l}</b></p>' if w + d + l else ""))

    rows, prev = "", None
    for name, (p1, px, p2) in pred["steps"]:
        cells = ""
        for i, v in enumerate((p1, px, p2)):
            delta = "" if prev is None else round((v - prev[i]) * 100)
            arrow = "" if not delta else f'<small class="{"up" if delta > 0 else "down"}">{"+" if delta > 0 else ""}{delta}</small>'
            cells += f"<td><b>{pct(v)}</b> {arrow}</td>"
        rows += f'<tr{" class=final" if name == "elo" else ""}><td>{escape(t["step_" + name])}</td>{cells}</tr>'
        prev = (p1, px, p2)
    return f"""<section class="card"><h3>{escape(t["model_breakdown"])}</h3>
<div class="two"><div><h4>{escape(t["inputs"])}</h4>
<div class="cmp-head"><span>{escape(m["home"])}</span><span>{escape(m["away"])}</span></div>{inputs}</div>
<div><div class="table-wrap"><table class="steps"><thead><tr><th></th><th>1</th><th>X</th><th>2</th></tr></thead><tbody>{rows}</tbody></table></div>
<p class="hint">{escape(t["breakdown_hint"])}</p></div></div></section>"""


def _thumbs(t, kind, mid):
    """Łapki pod typem strony - liczniki i stan uzupełnia app.js z Supabase."""
    return (f'<div class="thumbs" data-kind="{kind}" data-mid="{mid}"><span class="th-q">{escape(t["rate_pick"])}</span>'
            f'<button type="button" class="th up" data-v="1" aria-label="{escape(t["thumb_up"])}">👍 <b>0</b></button>'
            f'<button type="button" class="th down" data-v="-1" aria-label="{escape(t["thumb_down"])}">👎 <b>0</b></button></div>')


def community_page(cfg, lang, updated, demo, leagues=None):
    t = UI[lang]
    body = f"""<h1>{escape(t["community"])}</h1>
<p class="lead">{escape(t["community_lead"])}</p>
<div id="community" class="community"><p class="muted">{escape(t["loading"])}</p></div>
<p class="hint">{escape(t["points_rule"])}</p>"""
    return layout(cfg, lang, "community", t["community"], body, updated, demo, leagues)


def match_page(cfg, lang, m, updated, demo, leagues):
    t = UI[lang]
    pred = m["prediction"]
    p = pred["probs"]
    rh, ra = m.get("ranks") or (None, None)
    pick = m["pick"]

    cta = ""
    for r in m.get("odds") or []:
        if r["outcome"] == pick["market"]:
            link = _book_link(lang, r, big=True) if r["url"] else ""
            cta = (f'<div class="best"><span class="label">{escape(t["best_odds"])}</span><b>{num(r["best"], lang)}</b>'
                   f'{" <span class=chip value>" + escape(t["value_bet"]) + "</span>" if r["is_value"] else ""}</div>{link}'
                   + (f'<span class="ad-label">{escape(t["ad_label"])} · 18+</span>' if link else ""))

    markets = "".join(
        f'<tr><td>{escape(MARKETS[lang][k])}</td><td><b>{pct(p[k])}</b></td><td>{_odds(p[k])}</td><td>{_slip_btn(m, k, p[k])}</td></tr>'
        for k in ("1", "X", "2", "1X", "X2", "12", "O15", "O25", "O35", "U25", "U35", "BTTS", "NOBTTS"))
    scores = "".join(f'<div class="sc"><b>{x}:{y}</b><span>{pct(pp)}</span></div>' for x, y, pp in pred["top_scores"])

    flags_html = ""
    for side in ("home", "away"):
        fl = (m.get("flags") or {}).get(side, [])
        if fl:
            flags_html += f'<p><b>{escape(m[side])}</b> ' + " ".join(
                f'<span class="chip f-{f}">{escape(t["f_" + f])}</span>' for f in fl) + "</p>"

    res = m.get("research") or {}
    lineups = ""
    if any((res.get(s) or {}).get("probable_lineup") for s in ("home", "away")):
        cols = "".join(
            f'<div><h4>{escape(m[s])}</h4><ol class="xi">'
            + "".join(f"<li>{escape(n)}</li>" for n in (res.get(s) or {}).get("probable_lineup", [])) + "</ol></div>"
            for s in ("home", "away"))
        lineups = (f'<section class="card"><h3>{escape(t["probable_lineups"])}</h3><div class="two">{cols}</div>'
                   f'<p class="hint">{escape(t["lineups_unconfirmed"])}</p></section>')

    sh, sa = m.get("stats_home"), m.get("stats_away")
    stats_html = ""
    if sh and sa:
        f1 = lambda v: num(v, lang)
        stats_html = f"""<section class="card"><h3>{escape(t["season_stats"])}</h3>
<div class="cmp-head"><span>{escape(m["home"])}</span><span>{escape(m["away"])}</span></div>
{_stat_compare(t["model_xg"], pred["xg_home"], pred["xg_away"], f1)}
{_stat_compare(t["goals_per_game"], sh["gf"], sa["gf"], f1)}
{_stat_compare(t["conceded_per_game"], sh["ga"], sa["ga"], f1)}
{_stat_compare(t["btts_rate"], sh["btts"], sa["btts"], pct)}
{_stat_compare(t["over25_rate"], sh["over25"], sa["over25"], pct)}
{_stat_compare(t["clean_sheets"], sh["clean"], sa["clean"], pct)}
</section>"""

    h2h_html = "".join(
        f'<li><time data-utc="{g["utc"]}" data-fmt="date"></time><span class="rl-teams">{escape(g["home"])} – {escape(g["away"])}</span><b>{g["score"]}</b></li>'
        for g in m.get("h2h") or []) or f'<li class="muted">{escape(t["no_h2h"])}</li>'

    pr = m.get("pick_range")
    range_html = ""
    if pr:
        range_html = (f'<section class="pick-card alt"><div class="pc-main"><span class="label">{escape(t["pick_range"])}</span>'
                      f'<span class="pick-main">{escape(MARKETS[lang][pr["market"]])}</span>'
                      f'<span><span class="prob">{pct(pr["p"])}</span> <span class="odds">{escape(t["fair_odds"])} {_odds(pr["p"])}</span></span></div>'
                      f'<div class="cta">{_slip_btn(m, pr["market"], pr["p"], "+ " + escape(t["add_slip"]), "slip-add")}</div>'
                      f'{_thumbs(t, "range", m["id"])}</section>')

    def hero_team(side, rank, elo):
        return (f'<div class="hero-team"><span class="tn">{escape(m[side])}</span>'
                f'<span class="meta">{f"#{rank} · " if rank else ""}Elo {elo}</span>'
                f'<span class="form">{_form(m.get(side + "_form", ""))}</span></div>')

    body = f"""<nav class="crumbs"><a href="index.html">{escape(t["overview"])}</a> › <a href="league-{m["competition"]}.html">{escape(m["competition_name"])}</a></nav>
<section class="hero">
  {hero_team("home", rh, pred["elo_home"])}
  <div class="hero-mid"><time data-utc="{m["utc"]}"></time>
    <div class="hero-xg"><b>{num(pred["xg_home"], lang)}</b><small>{escape(t["model_xg"])}</small><b>{num(pred["xg_away"], lang)}</b></div>
    {_pbar(p)}
    <div class="p3 big"><span>1 <b>{pct(p["1"])}</b></span><span>X <b>{pct(p["X"])}</b></span><span>2 <b>{pct(p["2"])}</b></span></div></div>
  {hero_team("away", ra, pred["elo_away"])}
</section>
<section class="pick-card">
  <div class="pc-main"><span class="label">{escape(t["pick"])}</span><span class="pick-main">{escape(MARKETS[lang][pick["market"]])}</span>
  <span><span class="prob">{pct(pick["p"])}</span> <span class="odds">{escape(t["fair_odds"])} {_odds(pick["p"])}</span></span></div>
  <div class="cta">{_slip_btn(m, pick["market"], pick["p"], "+ " + escape(t["add_slip"]), "slip-add big")}{cta}</div>
  {_thumbs(t, "safe", m["id"])}
</section>
{range_html}
<section class="card predict" id="predict" data-match="{m["id"]}" data-utc="{m["utc"]}" data-home="{escape(m["home"])}" data-away="{escape(m["away"])}">
<h3>{escape(t["who_wins"])}</h3><p class="hint">{escape(t["predict_hint"])}</p><div class="pr-body"></div></section>
{f'<section class="card"><h3>{escape(t["key_factors"])}</h3>{flags_html}<p class="hint">{escape(t["ai_note"])}</p></section>' if flags_html else ''}
<section class="card"><h3>{escape(t["analysis_title"])}</h3><p class="analysis">{escape(m["analysis"][lang])}</p></section>
{_breakdown(lang, m)}
<div class="grid2">
<section class="card"><h3>{escape(t["markets_title"])}</h3><div class="table-wrap"><table class="mk">
<thead><tr><th></th><th>{escape(t["probability"])}</th><th>{escape(t["fair_odds"])}</th><th></th></tr></thead><tbody>{markets}</tbody></table></div></section>
<section class="card"><h3>{escape(t["score_probs"])}</h3><div class="scores">{scores}</div></section>
</div>
<section class="card"><h3>{escape(t["odds_title"])} · {escape(t["odds_movement"])}</h3>{_odds_block(lang, m)}</section>
{ad_slot(cfg, lang, "match")}
{stats_html}
<section class="card"><h3>{escape(t["last_matches"])}</h3><div class="two">
{_recent_list(m["home"], m.get("recent_home"))}{_recent_list(m["away"], m.get("recent_away"))}</div></section>
<section class="card"><h3>{escape(t["h2h"])}</h3><ol class="h2h">{h2h_html}</ol></section>
<section class="card"><h3>{escape(t["injuries_title"])}</h3><div class="two">
<div><h4>{escape(m["home"])}</h4>{_absences(lang, res.get("home"))}</div>
<div><h4>{escape(m["away"])}</h4>{_absences(lang, res.get("away"))}</div></div></section>
{lineups}
<section class="card comments" id="comments" data-match="{m["id"]}"><h3>{escape(t["comments"])}</h3>
<p class="hint">{escape(t["comment_rules"])}</p><div class="c-body"><p class="muted">{escape(t["comment_login"])}</p></div></section>"""
    title = f'{m["home"]} – {m["away"]}: {t["match_analysis"]}'
    return layout(cfg, lang, f"match-{m['id']}", title, body, updated, demo, leagues, m["competition"])


# ---------------------------------------------------------- track record

def _rate(s):
    return pct(s["won"] / s["settled"]) if s["settled"] else "-"


def _stat_box(t, label, s):
    return (f'<div class="stat"><b>{_rate(s)}</b><span>{escape(t["hit_rate"])} · {escape(label)}</span>'
            f'<small>{escape(t["won"])} {s["won"]} / {escape(t["settled"])} {s["settled"]}</small></div>')


def _day_details(lang, day, open_=False):
    t = UI[lang]
    rows = "".join(
        f'<tr><td>{escape(r["home"])} – {escape(r["away"])}</td>'
        f'<td>{escape(MARKETS[lang][r["market"]])} ({pct(r["p"])})</td><td>{r.get("score") or ""}</td>'
        f'<td>{_badge(r.get("result")) or escape(t["pending"])}</td></tr>' for r in day["picks"])
    coupons = "".join(
        f'<li>{escape(t["coupon_" + k])}: {pct(c["p"])} · @{num(c["fair_odds"], "en")} '
        f'{_badge(c.get("result")) or escape(t["pending"])}</li>'
        for k, c in day["coupons"].items())
    summary = (f'{day["date"]} · {escape(t["hit_rate"])}: <b>{_rate(day)}</b> '
               f'({day["won"]}/{day["settled"]}, {len(day["picks"])} {escape(t["picks_count"])})')
    return f"""<details class="day-log"{" open" if open_ else ""}><summary>{summary}</summary>
{f'<ul class="coupon-log">{coupons}</ul>' if coupons else ''}
<div class="table-wrap"><table>
<thead><tr><th>{escape(t["match"])}</th><th>{escape(t["pick"])}</th><th>{escape(t["result"])}</th><th>{escape(t["status"])}</th></tr></thead>
<tbody>{rows}</tbody></table></div></details>"""


def _archive_links(lang, months, current=None):
    t = UI[lang]
    links = " · ".join(
        f'<a href="archive-{m}.html"{" aria-current=page" if m == current else ""}>{m}</a>' for m in months)
    return f'<h2>{escape(t["archive"])}</h2><p class="archive">{links}</p>' if links else ""


def results_page(cfg, lang, summary, updated, demo, leagues=None):
    t = UI[lang]
    if not summary["recent_days"]:
        body = f'<h1>{escape(t["results_title"])}</h1><p class="empty">{escape(t["no_history"])}</p>'
        return layout(cfg, lang, "results", t["results"], _app(lang, "stats", body), updated, demo, leagues)

    coupons = "".join(_stat_box(t, t["coupon_" + k], s) for k, s in summary["coupons"].items())
    markets = "".join(
        f'<tr><td>{escape(MARKETS[lang][m])}</td><td>{s["won"]}/{s["settled"]}</td><td><b>{_rate(s)}</b></td></tr>'
        for m, s in summary["markets"].items() if s["settled"])
    days = "".join(_day_details(lang, d, i == 0) for i, d in enumerate(summary["recent_days"]))
    body = f"""<h1>{escape(t["results_title"])}</h1>
<div class="stats">{_stat_box(t, t["last_7"], summary["d7"])}{_stat_box(t, t["last_days"], summary["d30"])}{_stat_box(t, t["all_time"], summary["all"])}</div>
<h2>{escape(t["coupons_history"])}</h2>
<div class="stats">{coupons}</div>
{ad_slot(cfg, lang, "results")}
<h2>{escape(t["by_market"])}</h2>
<div class="table-wrap"><table><thead><tr><th>{escape(t["market"])}</th><th>{escape(t["won"])}/{escape(t["settled"])}</th><th>{escape(t["hit_rate"])}</th></tr></thead>
<tbody>{markets}</tbody></table></div>
<h2>{escape(t["history_by_day"])}</h2>
{days}
{_archive_links(lang, summary["months"])}"""
    return layout(cfg, lang, "results", t["results"], _app(lang, "stats", body), updated, demo, leagues)


def archive_page(cfg, lang, month, days, months, updated, demo, leagues=None):
    t = UI[lang]
    total = {"won": sum(d["won"] for d in days), "settled": sum(d["settled"] for d in days)}
    body = f"""<h1>{escape(t["archive"])} {month}</h1>
<div class="stats">{_stat_box(t, month, total)}</div>
{"".join(_day_details(lang, d) for d in days)}
{_archive_links(lang, months, month)}"""
    return layout(cfg, lang, f"archive-{month}", f'{t["archive"]} {month}', body, updated, demo, leagues)


def static_page(cfg, lang, page, updated, demo, leagues=None):
    t = UI[lang]
    title = t["method_title"] if page == "about" else t[page]
    body = f"<h1>{escape(title)}</h1>"
    if page == "about":
        body += t["method_html"] + f"<p>{escape(t['ai_note'])}</p><h2>{escape(t['about'])}</h2>" + t["about_html"]
    else:
        body += t[page + "_html"]
    if page == "advertise":
        email = escape(cfg["contact_email"])
        body += f'<p>{escape(t["contact"])}: <a href="mailto:{email}">{email}</a></p>'
    return layout(cfg, lang, page, title, f'<div class="prose">{body}</div>', updated, demo, leagues)


def root_redirect(cfg):
    langs = cfg["languages"]
    links = " · ".join(f'<a href="{l}/index.html">{escape(META[l]["name"])}</a>' for l in langs)
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(cfg["site_name"])}</title>
<script>
(function () {{
  var supported = {langs!r};
  var pick = null;
  try {{ pick = localStorage.getItem("lang"); }} catch (e) {{}}
  if (supported.indexOf(pick) < 0) {{
    pick = "{cfg["default_language"]}";
    var prefs = navigator.languages || [navigator.language || ""];
    for (var i = 0; i < prefs.length; i++) {{
      var code = String(prefs[i]).slice(0, 2).toLowerCase();
      code = {{nb: "no", nn: "no"}}[code] || code;
      if (supported.indexOf(code) >= 0) {{ pick = code; break; }}
    }}
  }}
  location.replace(pick + "/index.html" + location.hash);
}})();
</script>
<link rel="stylesheet" href="assets/style.css">
</head><body><main><p>{links}</p></main></body></html>
"""
