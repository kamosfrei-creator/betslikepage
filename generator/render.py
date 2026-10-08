"""Generowanie statycznych stron HTML."""

from html import escape

from .texts import MARKETS, META, UI, num, pct

PAGES = ("index", "results", "about", "advertise", "responsible")


def layout(cfg, lang, page, title, body, updated, demo):
    t = UI[lang]
    base = cfg["base_url"].rstrip("/")
    alt = "\n".join(f'<link rel="alternate" hreflang="{l}" href="{base}/{l}/{_file(page)}">' for l in cfg["languages"])
    nav = "".join(
        f'<a href="{_file(p)}"{" aria-current=page" if p == page else ""}>{escape(t[k])}</a>'
        for p, k in (("index", "coupons"), ("results", "results"), ("about", "about"), ("advertise", "advertise")))
    options = "".join(
        f'<option value="../{l}/{_file(page)}" data-lang="{l}"{" selected" if l == lang else ""}>'
        f'{escape(META[l]["name"])}</option>' for l in cfg["languages"])
    langs = (f'<label class="langs"><span class="sr">{escape(t["language"])}</span>'
             f'<select id="lang-select" aria-label="{escape(t["language"])}">{options}</select></label>')
    banner = f'<div class="demo">{escape(t["demo"])}</div>' if demo else ""
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
<script defer src="../assets/app.js"></script>
</head>
<body>
{banner}
<header class="top">
  <a class="brand" href="index.html">{escape(cfg["site_name"])}<span>{escape(t["tagline"])}</span></a>
  {langs}
</header>
<nav class="main">{nav}</nav>
<main>
{body}
</main>
<footer>
  <p class="disclaimer"><strong>18+</strong> {escape(t["disclaimer"])}</p>
  <p>{escape(t["help_text"])} <a href="{t["help_url"]}" rel="noopener" target="_blank">{escape(t["help_name"])}</a> ·
     <a href="responsible.html">{escape(t["responsible"])}</a></p>
  <p class="muted">{escape(t["data_credit"])}</p>
  <p class="muted">{escape(t["updated"])}: <time data-utc="{updated}">{updated}</time> · {escape(t["next_update"])}</p>
</footer>
</body>
</html>
"""


def _file(page):
    return "index.html" if page == "index" else f"{page}.html"


def ad_slot(cfg, lang, slot):
    t = UI[lang]
    for ad in cfg.get("ads", []):
        if ad.get("slot") == slot and lang in ad.get("languages", [lang]):
            return (f'<aside class="ad"><span class="ad-label">{escape(t["ad_label"])} · 18+</span>'
                    f'<a href="{escape(ad["url"])}" rel="sponsored nofollow noopener" target="_blank">'
                    f'<img src="{escape(ad["image"])}" alt="{escape(ad.get("alt", ""))}" loading="lazy"></a></aside>')
    return (f'<aside class="ad placeholder"><a href="advertise.html">{escape(t["ad_placeholder"])}</a></aside>')


def _form(form):
    return "".join(f'<i class="f{c}">{c}</i>' for c in form)


def _pick_line(lang, market, p):
    m = MARKETS[lang]
    return (f'<span class="market">{escape(m[market])}</span>'
            f'<span class="prob">{pct(p)}</span><span class="odds">@{num(1 / p, "en")}</span>')


def coupon_card(lang, key, coupon):
    t = UI[lang]
    legs = "".join(
        f'<li><span class="teams">{escape(leg["home"])} - {escape(leg["away"])}</span>'
        f'<time data-utc="{leg["utc"]}" data-fmt="time"></time>{_pick_line(lang, leg["market"], leg["p"])}'
        f'{_status_badge(leg.get("result"))}</li>'
        for leg in coupon["legs"])
    return f"""<article class="coupon {key}">
<h3>{escape(t["coupon_" + key])}</h3>
<ol>{legs}</ol>
<p class="total">{escape(t["probability"])}: <b>{pct(coupon["p"])}</b> · {escape(t["fair_odds"])}: <b>{num(coupon["fair_odds"], "en")}</b>
{_status_badge(coupon.get("result"))}</p>
</article>"""


def _status_badge(result):
    if not result:
        return ""
    sym = {"won": "✔", "lost": "✘", "void": "–"}[result]
    return f'<span class="badge {result}">{sym}</span>'


def match_card(lang, m):
    t = UI[lang]
    pick = m["pick"]
    score = ""
    if m.get("home_goals") is not None and m["status"] in ("IN_PLAY", "PAUSED", "FINISHED"):
        score = f'<span class="score">{m["home_goals"]}:{m["away_goals"]}</span>'
    alts = ""
    if m.get("alternatives"):
        alts = (f'<p class="alts">{escape(t["alternatives"])}: ' + " · ".join(
            f'{escape(MARKETS[lang][a["market"]])} {pct(a["p"])}' for a in m["alternatives"]) + "</p>")
    meta = ""
    if m.get("xg_home") is not None:
        hs, as_ = m["likely_score"]
        meta = (f'<p class="meta">{escape(t["xg"])}: {num(m["xg_home"], lang)} - {num(m["xg_away"], lang)} · '
                f'{escape(t["likely_score"])}: {hs}:{as_}</p>')
    form = ""
    if m.get("home_form") or m.get("away_form"):
        form = (f'<p class="form"><span>{escape(t["form"])}:</span> {_form(m.get("home_form", ""))}'
                f' <span class="vs">|</span> {_form(m.get("away_form", ""))}</p>')
    low = f'<p class="low">{escape(t["low_data"])}</p>' if m.get("low_data") else ""
    news = _news_block(lang, m)
    text = f'<p class="analysis">{escape(m["analysis"][lang])}</p>' if m.get("analysis") else ""
    return f"""<article class="match" id="m{m["id"]}">
<header><span class="comp">{escape(m["competition_name"])}</span><time data-utc="{m["utc"]}" data-fmt="time"></time></header>
<h4>{escape(m["home"])} <span class="vs">vs</span> {escape(m["away"])} {score}</h4>
<p class="pick">{escape(t["pick"])}: {_pick_line(lang, pick["market"], pick["p"])}{_status_badge(pick.get("result"))}</p>
{alts}{meta}{form}{news}{text}{low}
</article>"""


def _news_block(lang, m):
    t = UI[lang]
    rows = []
    for side in ("home", "away"):
        n = (m.get("news") or {}).get(side) or {}
        parts = []
        if n.get("out"):
            parts.append(f'{escape(t["out"])}: {escape(", ".join(n["out"]))}')
        if n.get("doubtful"):
            parts.append(f'{escape(t["doubtful"])}: {escape(", ".join(n["doubtful"]))}')
        if parts:
            rows.append(f'<li><b>{escape(m[side])}</b> - {"; ".join(parts)}</li>')
    lineups = (m.get("news") or {}).get("lineups")
    if lineups:
        rows.append(f'<li>{escape(t["lineups"])}: {escape(lineups[0])} / {escape(lineups[1])}</li>')
    if not rows and not m.get("adjusted"):
        return ""
    flag = f'<p class="adjusted">{escape(t["adjusted"])}</p>' if m.get("adjusted") else ""
    items = f'<ul>{"".join(rows)}</ul>' if rows else ""
    return f'<div class="news"><p class="news-title">{escape(t["team_news"])}</p>{items}{flag}</div>'


def index_page(cfg, lang, days, updated, demo):
    t = UI[lang]
    sections = []
    for i, day in enumerate(days):
        label = t["today"] if i == 0 else t["tomorrow"]
        coupons = "".join(coupon_card(lang, k, c) for k, c in day["coupons"].items())
        matches = "".join(match_card(lang, m) for m in day["matches"]) or f'<p class="empty">{escape(t["no_matches"])}</p>'
        sections.append(f"""<section class="day" id="{'today' if i == 0 else 'tomorrow'}">
<h2>{escape(label)} <small>{day["date"]}</small></h2>
{f'<div class="coupons">{coupons}</div><p class="hint">{escape(t["fair_odds_hint"])}</p>' if coupons else ''}
{ad_slot(cfg, lang, "day" + str(i))}
<h3>{escape(t["all_matches"])}</h3>
<div class="matches">{matches}</div>
</section>""")
    tabs = (f'<nav class="tabs"><a href="#today">{escape(t["today"])}</a>'
            f'<a href="#tomorrow">{escape(t["tomorrow"])}</a></nav>')
    return layout(cfg, lang, "index", t["coupons"], tabs + "\n".join(sections), updated, demo)


def _rate(s):
    return pct(s["won"] / s["settled"]) if s["settled"] else "-"


def _stat_box(t, label, s):
    return (f'<div class="stat"><b>{_rate(s)}</b><span>{escape(t["hit_rate"])} · {escape(label)}</span>'
            f'<small>{escape(t["won"])} {s["won"]} / {escape(t["settled"])} {s["settled"]}</small></div>')


def _day_details(lang, day, open_=False):
    t = UI[lang]
    rows = "".join(
        f'<tr><td>{escape(r["home"])} - {escape(r["away"])}</td>'
        f'<td>{escape(MARKETS[lang][r["market"]])} ({pct(r["p"])})</td><td>{r.get("score") or ""}</td>'
        f'<td>{_status_badge(r.get("result")) or escape(t["pending"])}</td></tr>' for r in day["picks"])
    coupons = "".join(
        f'<li>{escape(t["coupon_" + k])}: {pct(c["p"])} · @{num(c["fair_odds"], "en")} '
        f'{_status_badge(c.get("result")) or escape(t["pending"])}</li>'
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


def results_page(cfg, lang, summary, updated, demo):
    t = UI[lang]
    if not summary["recent_days"]:
        body = f'<h1>{escape(t["results_title"])}</h1><p class="empty">{escape(t["no_history"])}</p>'
        return layout(cfg, lang, "results", t["results"], body, updated, demo)

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
    return layout(cfg, lang, "results", t["results"], body, updated, demo)


def archive_page(cfg, lang, month, days, months, updated, demo):
    t = UI[lang]
    total = {"won": sum(d["won"] for d in days), "settled": sum(d["settled"] for d in days)}
    body = f"""<h1>{escape(t["archive"])} {month}</h1>
<div class="stats">{_stat_box(t, month, total)}</div>
{"".join(_day_details(lang, d) for d in days)}
{_archive_links(lang, months, month)}"""
    return layout(cfg, lang, f"archive-{month}", f'{t["archive"]} {month}', body, updated, demo)


def static_page(cfg, lang, page, updated, demo):
    t = UI[lang]
    title = t[page]
    body = f"<h1>{escape(title)}</h1>{t[page + '_html']}"
    if page == "advertise":
        email = escape(cfg["contact_email"])
        body += f'<p>{escape(t["contact"])}: <a href="mailto:{email}">{email}</a></p>'
    return layout(cfg, lang, page, title, f'<div class="prose">{body}</div>', updated, demo)


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
