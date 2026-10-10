// BetsLike - skrypt wspólny + aplikacje "tips" (przegląd typów) i "stats" (statystyki).
// Bez bibliotek; dane z <lang>/data.json i data/history.json, teksty z <script id="i18n">.
(function () {
  "use strict";

  // ---------------------------------------------------------------- wspólne
  var lang = document.documentElement.lang;
  function localizeTimes(root) {
    (root || document).querySelectorAll("time[data-utc]").forEach(function (el) {
      var d = new Date(el.getAttribute("data-utc"));
      if (isNaN(d)) return;
      var fmt = el.getAttribute("data-fmt");
      var opts = fmt === "time" ? { hour: "2-digit", minute: "2-digit" }
        : fmt === "date" ? { day: "2-digit", month: "2-digit", year: "2-digit" }
        : { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" };
      el.textContent = d.toLocaleString(lang, opts);
    });
  }
  localizeTimes();
  var select = document.getElementById("lang-select");
  if (select) {
    select.addEventListener("change", function () {
      var opt = select.options[select.selectedIndex];
      try { localStorage.setItem("lang", opt.getAttribute("data-lang")); } catch (e) {}
      location.href = opt.value;
    });
  }

  var app = document.getElementById("app");
  var i18nEl = document.getElementById("i18n");
  if (!app || !i18nEl || !window.fetch) return;
  var I = JSON.parse(i18nEl.textContent);

  function T(k) { return I.ui[k] || k; }
  function M(k) { return I.markets[k] || k; }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function fmt(s, o) { return String(s).replace(/\{(\w+)\}/g, function (_, k) { return o[k]; }); }
  function pct(p) { return Math.round(p * 100) + "%"; }
  function dec(x, d) { var s = x.toFixed(d == null ? 2 : d); return I.decimal === "," ? s.replace(".", ",") : s; }
  function fair(p) { return p > 0 ? dec(1 / p) : "-"; }
  function timeOf(utc) { return new Date(utc).toLocaleTimeString(I.lang, { hour: "2-digit", minute: "2-digit" }); }
  function dayLabel(d) { return new Date(d + "T12:00:00").toLocaleDateString(I.lang, { weekday: "short", day: "numeric", month: "short" }); }
  var store = {
    get: function (k, def) { try { var v = localStorage.getItem("bl:" + k); return v ? JSON.parse(v) : def; } catch (e) { return def; } },
    set: function (k, v) { try { localStorage.setItem("bl:" + k, JSON.stringify(v)); } catch (e) {} }
  };
  function getJSON(url) { return fetch(url, { cache: "no-cache" }).then(function (r) { if (!r.ok) throw r.status; return r.json(); }); }
  function hue(s) { var h = 0; for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) % 360; return h; }
  function crest(url, name) {
    if (url) return '<img class="crest" src="' + esc(url) + '" alt="" loading="lazy" width="22" height="22">';
    var ini = name.split(/\s+/).map(function (w) { return w[0]; }).join("").slice(0, 2).toUpperCase();
    return '<span class="crest ph" style="--h:' + hue(name) + '">' + esc(ini) + "</span>";
  }
  function badge(r) {
    if (!r) return "";
    return '<span class="badge ' + r + '" title="' + esc(T(r)) + '">' + ({ won: "✔", lost: "✘", void: "–" }[r]) + "</span>";
  }
  var GROUP = { "1": "1x2", X: "1x2", "2": "1x2", "1X": "1x2", X2: "1x2", "12": "1x2",
                O15: "goals", O25: "goals", O35: "goals", U25: "goals", U35: "goals", BTTS: "btts", NOBTTS: "btts" };
  function agg(rows) {
    var s = rows.filter(function (r) { return r.r === "won" || r.r === "lost"; });
    var won = s.filter(function (r) { return r.r === "won"; }).length;
    var exp = s.reduce(function (a, r) { return a + r.p; }, 0);
    var withOdds = s.filter(function (r) { return r.o; });
    var profit = withOdds.reduce(function (a, r) { return a + (r.r === "won" ? r.o - 1 : -1); }, 0);
    return { n: s.length, won: won, rate: s.length ? won / s.length : null, exp: exp,
             conf: s.length ? exp / s.length : null, roi: withOdds.length ? profit / withOdds.length : null, roiN: withOdds.length };
  }
  function rateTxt(a) { return a.rate == null ? "–" : pct(a.rate); }
  function addDays(iso, n) { var d = new Date(iso + "T12:00:00Z"); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); }

  // tooltip dla wykresów i ikon
  var tip = document.createElement("div");
  tip.className = "tooltip"; tip.hidden = true;
  document.body.appendChild(tip);
  document.addEventListener("pointermove", function (e) {
    var t = e.target.closest && e.target.closest("[data-tip]");
    if (!t) { tip.hidden = true; return; }
    tip.innerHTML = t.getAttribute("data-tip");
    tip.hidden = false;
    var x = Math.min(e.clientX + 14, window.innerWidth - tip.offsetWidth - 8);
    tip.style.left = x + "px"; tip.style.top = (e.clientY + 14) + "px";
  });

  function kpiStrip(hist, today) {
    var picks = hist.picks;
    var y = addDays(today, -1);
    var k = {
      y: agg(picks.filter(function (r) { return r.d === y; })),
      w: agg(picks.filter(function (r) { return r.d >= addDays(today, -7) && r.d < today; })),
      m: agg(picks.filter(function (r) { return r.d >= addDays(today, -30) && r.d < today; }))
    };
    var best = null;
    var byLeague = {};
    picks.forEach(function (r) { if (r.d >= addDays(today, -30)) (byLeague[r.c] = byLeague[r.c] || []).push(r); });
    Object.keys(byLeague).forEach(function (c) {
      var a = agg(byLeague[c]);
      if (a.n >= 5 && (!best || a.rate > best.a.rate)) best = { c: c, a: a };
    });
    var settled = picks.filter(function (r) { return r.r === "won" || r.r === "lost"; });
    var streak = 0, kind = settled.length ? settled[0].r : null;
    for (var i = 0; i < settled.length && settled[i].r === kind; i++) streak++;
    function tile(label, a, extra) {
      return '<div class="kpi"><span class="kpi-l">' + esc(label) + '</span><b>' + rateTxt(a) + "</b>" +
        '<span class="kpi-s">' + (a.n ? esc(fmt(T("picks_won_of"), { won: a.won, n: a.n })) : "–") + (extra || "") + "</span></div>";
    }
    return '<div class="kpis">' + tile(T("kpi_yesterday"), k.y) + tile(T("kpi_week"), k.w) + tile(T("kpi_month"), k.m) +
      '<div class="kpi"><span class="kpi-l">' + esc(T("kpi_best_league")) + "</span><b>" + (best ? pct(best.a.rate) : "–") + "</b>" +
      '<span class="kpi-s">' + (best ? esc(hist.leagues[best.c] || best.c) + " · " + best.a.won + "/" + best.a.n : "–") + "</span></div>" +
      '<div class="kpi"><span class="kpi-l">' + esc(T("kpi_streak")) + '</span><b class="' + (kind || "") + '">' + (streak || "–") + "</b>" +
      '<span class="kpi-s">' + (kind ? esc(fmt(T(kind === "won" ? "streak_w" : "streak_l"), { n: streak })) : "–") + "</span></div></div>";
  }

  // ---------------------------------------------------------------- przegląd typów
  function tipsApp() {
    var state = Object.assign({ day: "today", leagues: [], q: "", sort: "time", market: "all", min: 0, value: false,
                                fav: false, view: "grouped" }, store.get("filters", {}));
    state.q = ""; state.day = location.hash.slice(1) || state.day;
    var favs = store.get("favs", []);
    var slip = store.get("slip", []);
    var open = {};
    var data, hist;

    Promise.all([getJSON("data.json"), getJSON("../data/history.json").catch(function () { return { picks: [], coupons: [], leagues: {} }; })])
      .then(function (res) { data = res[0]; hist = res[1]; if (!data.days.some(function (d) { return d.key === state.day; })) state.day = "today"; render(); })
      .catch(function () { /* zostaje statyczna wersja strony */ });

    function save() {
      store.set("filters", { leagues: state.leagues, sort: state.sort, market: state.market, min: state.min,
                             value: state.value, fav: state.fav, view: state.view, day: state.day });
    }

    function filtered() {
      var q = state.q.trim().toLowerCase();
      return data.matches.filter(function (m) {
        if (m.day !== state.day) return false;
        if (state.leagues.length && state.leagues.indexOf(m.comp) < 0) return false;
        if (q && (m.home + " " + m.away).toLowerCase().indexOf(q) < 0) return false;
        if (state.fav && favs.indexOf(m.id) < 0) return false;
        var pk = m.pick;
        if (state.market !== "all" && (!pk || GROUP[pk.m] !== state.market)) return false;
        if (state.min && (!pk || pk.p * 100 < state.min)) return false;
        if (state.value && !(m.odds && Object.keys(m.odds).some(function (k) { return m.odds[k].isv; }))) return false;
        return true;
      });
    }
    function valueOf(m) {
      if (!m.odds) return 0;
      return Math.max.apply(null, Object.keys(m.odds).map(function (k) { return m.odds[k].v; }));
    }
    function sorted(list) {
      var by = {
        time: function (a, b) { return a.utc < b.utc ? -1 : a.utc > b.utc ? 1 : 0; },
        conf: function (a, b) { return (b.pick ? b.pick.p : 0) - (a.pick ? a.pick.p : 0); },
        value: function (a, b) { return valueOf(b) - valueOf(a); },
        league: function (a, b) { return a.comp < b.comp ? -1 : a.comp > b.comp ? 1 : (a.utc < b.utc ? -1 : 1); },
        goals: function (a, b) { return (b.xg ? b.xg[0] + b.xg[1] : 0) - (a.xg ? a.xg[0] + a.xg[1] : 0); }
      }[state.sort];
      return list.slice().sort(by);
    }

    function statusCell(m) {
      if (m.status === "FINISHED") return '<span class="st ft">' + esc(T("finished")) + "</span>";
      if (m.status === "IN_PLAY" || m.status === "PAUSED") return '<span class="st live">' + esc(T("live")) + "</span>";
      return '<span class="st">' + timeOf(m.utc) + "</span>";
    }
    function inSlip(id, mk) { return slip.some(function (s) { return s.id === id && (!mk || s.m === mk); }); }

    function row(m) {
      var p = m.p, pk = m.pick, isOpen = open[m.id];
      var played = m.hg != null;
      var probs = "";
      if (p) {
        var best = ["1", "X", "2"].reduce(function (a, k) { return p[k] > p[a] ? k : a; }, "1");
        probs = '<div class="m-probs">' + ["1", "X", "2"].map(function (k) {
          return '<span class="pp' + (k === best ? " hi" : "") + '"><i>' + k + "</i>" + Math.round(p[k] * 100) + "</span>";
        }).join("") + '<div class="pbar"><span class="p1" style="width:' + p["1"] * 100 + '%"></span><span class="px" style="width:' +
          p.X * 100 + '%"></span><span class="p2" style="width:' + p["2"] * 100 + '%"></span></div></div>';
      } else probs = '<div class="m-probs empty"></div>';
      var tipHtml = "";
      if (pk) {
        var od = m.odds && m.odds[pk.m];
        tipHtml = '<div class="m-tip"><span class="tip-m">' + esc(M(pk.m)) + "</span>" +
          '<span class="tip-row"><b class="conf">' + pct(pk.p) + "</b>" +
          '<span class="fo" data-tip="' + esc(T("fair_odds")) + '">@' + fair(pk.p) + "</span>" +
          (od ? '<span class="mo" data-tip="' + esc(T("market_odds")) + '">' + dec(od.now) + "</span>" : "") +
          (od && od.isv ? '<span class="chip value">' + esc(T("value_bet")) + "</span>" : "") + badge(pk.r) + "</span></div>";
      } else tipHtml = '<div class="m-tip muted">–</div>';
      var fav = favs.indexOf(m.id) >= 0;
      var acts = '<div class="m-act">' +
        '<button type="button" class="ib' + (fav ? " on" : "") + '" data-act="fav" aria-pressed="' + fav + '" aria-label="' + esc(T("favourite")) + '">★</button>' +
        (pk && !played && m.status !== "IN_PLAY" ? '<button type="button" class="ib add' + (inSlip(m.id, pk.m) ? " on" : "") + '" data-act="add" data-m="' + pk.m + '" aria-label="' + esc(T("add_slip")) + '">+</button>' : "") +
        (p ? '<button type="button" class="ib' + (isOpen ? " on" : "") + '" data-act="open" aria-expanded="' + !!isOpen + '" aria-label="' + esc(T("expand")) + '">▾</button>' : "") +
        "</div>";
      var teams = '<div class="m-teams">' +
        '<div class="tm">' + crest(m.hc, m.home) + '<span class="tn">' + esc(m.home) + "</span>" + (played ? "<b>" + m.hg + "</b>" : "") + "</div>" +
        '<div class="tm">' + crest(m.ac, m.away) + '<span class="tn">' + esc(m.away) + "</span>" + (played ? "<b>" + m.ag + "</b>" : "") + "</div></div>";
      var flags = (m.adj ? '<span class="dot news" data-tip="' + esc(T("adjusted")) + '"></span>' : "") +
                  (m.low ? '<span class="dot low" data-tip="' + esc(T("low_data")) + '"></span>' : "");
      return '<article class="mrow' + (isOpen ? " open" : "") + '" data-id="' + m.id + '">' +
        '<div class="m-time">' + statusCell(m) + flags + "</div>" + teams + probs + tipHtml + acts +
        (isOpen ? more(m) : "") + "</article>";
    }

    function more(m) {
      var p = m.p;
      var markets = ["1", "X", "2", "1X", "X2", "O15", "O25", "U25", "O35", "BTTS", "NOBTTS"].map(function (k) {
        var on = inSlip(m.id, k);
        return '<button type="button" class="mk' + (on ? " on" : "") + '" data-act="add" data-m="' + k + '"' +
          (m.hg != null ? " disabled" : "") + '><span>' + esc(M(k)) + "</span><b>" + pct(p[k]) + "</b><i>@" + fair(p[k]) + "</i></button>";
      }).join("");
      var scores = (m.scores || []).map(function (s) { return '<span class="sc"><b>' + s[0] + ":" + s[1] + "</b>" + pct(s[2]) + "</span>"; }).join("");
      var form = function (f) { return (f || "").split("").map(function (c) { return '<i class="f' + c + '">' + c + "</i>"; }).join(""); };
      var flags = ["home", "away"].map(function (side) {
        var fl = (m.flags || {})[side] || [];
        return fl.length ? "<p><b>" + esc(m[side]) + "</b> " + fl.map(function (f) {
          return '<span class="chip f-' + f + '">' + esc(T("f_" + f)) + "</span>"; }).join(" ") + "</p>" : "";
      }).join("");
      var mvm = "";
      if (m.odds) {
        mvm = '<div class="mvm"><h5>' + esc(T("market_vs_model")) + "</h5>" + ["1", "X", "2"].map(function (k) {
          var o = m.odds[k]; if (!o) return "";
          return '<div class="mvm-r"><b>' + k + "</b><span>" + esc(T("model")) + " " + pct(p[k]) + "</span><span>" +
            esc(T("implied")) + " " + pct(1 / o.now) + "</span>" + (o.isv ? '<span class="chip value">' + esc(T("value_bet")) + "</span>" : "") + "</div>";
        }).join("") + "</div>";
      }
      return '<div class="m-more">' +
        '<div class="mm-top"><div class="mm-xg"><span>' + esc(T("model_xg")) + "</span><b>" + dec(m.xg[0], 1) + " – " + dec(m.xg[1], 1) + "</b></div>" +
        '<div class="mm-form"><span>' + esc(T("form")) + "</span><div>" + form(m.form[0]) + "</div><div>" + form(m.form[1]) + "</div></div>" +
        (m.fi && m.fi[0] != null ? '<div class="mm-fi"><span>' + esc(T("form_index")) + "</span><b>" + m.fi[0] + " – " + m.fi[1] + "</b></div>" : "") +
        '<div class="mm-sc"><span>' + esc(T("score_probs")) + "</span><div>" + scores + "</div></div></div>" +
        '<div class="mks">' + markets + "</div>" + flags + mvm +
        '<p class="mm-text">' + esc(m.text) + "</p>" +
        (m.page ? '<a class="more-link" href="match-' + m.id + '.html">' + esc(T("full_analysis")) + " →</a>" : "") + "</div>";
    }

    function couponsHtml() {
      var cs = data.coupons[state.day];
      if (!cs) return "";
      return '<div class="coupons">' + ["safe", "standard", "bold"].filter(function (k) { return cs[k]; }).map(function (k) {
        var c = cs[k];
        return '<article class="coupon ' + k + '"><header><h3>' + esc(T("coupon_" + k)) + "</h3>" + badge(c.result) + "</header><ol>" +
          c.legs.map(function (l) {
            return '<li><span class="teams">' + esc(l.home) + " – " + esc(l.away) + '</span><span class="leg-meta">' + timeOf(l.utc) +
              ' <span class="market">' + esc(M(l.market)) + '</span><span class="prob">' + pct(l.p) + "</span>" + badge(l.result) + "</span></li>";
          }).join("") + '</ol><footer class="total"><span>' + esc(T("probability")) + " <b>" + pct(c.p) + "</b></span><span>" +
          esc(T("fair_odds")) + " <b>" + dec(c.fair_odds) + "</b></span></footer></article>";
      }).join("") + "</div>";
    }

    function slipHtml() {
      var prob = slip.reduce(function (a, s) { return a * s.p; }, 1);
      var allOdds = slip.length && slip.every(function (s) { return s.o; });
      var mo = allOdds ? slip.reduce(function (a, s) { return a * s.o; }, 1) : null;
      return '<aside class="slip' + (store.get("slipOpen", false) ? " open" : "") + '" aria-label="' + esc(T("my_slip")) + '">' +
        '<button type="button" class="slip-head" data-act="slip">' + esc(T("my_slip")) + ' <span class="cnt">' + slip.length + "</span>" +
        (slip.length ? '<span class="slip-odds">@' + dec(1 / prob) + "</span>" : "") + "</button>" +
        '<div class="slip-body">' + (slip.length ? "<ol>" + slip.map(function (s, i) {
          return "<li><span><b>" + esc(s.home) + " – " + esc(s.away) + "</b><small>" + esc(M(s.m)) + " · " + pct(s.p) + " · @" + fair(s.p) +
            '</small></span><button type="button" class="ib" data-act="rm" data-i="' + i + '" aria-label="' + esc(T("remove")) + '">×</button></li>';
        }).join("") + "</ol>" +
          '<div class="slip-sum"><span>' + esc(T("combined_prob")) + " <b>" + pct(prob) + "</b></span><span>" + esc(T("combined_odds")) +
          " <b>" + dec(1 / prob) + "</b></span>" + (mo ? "<span>" + esc(T("market_odds")) + " <b>" + dec(mo) + "</b></span>" : "") + "</div>" +
          '<button type="button" class="btn ghost" data-act="clear">' + esc(T("slip_clear")) + "</button>"
          : '<p class="muted">' + esc(T("slip_empty")) + "</p>") +
        '<p class="hint">18+ · ' + esc(T("fair_odds_hint")) + "</p></div></aside>";
    }

    function render() {
      var dayMatches = data.matches.filter(function (m) { return m.day === state.day; });
      var counts = {};
      dayMatches.forEach(function (m) { counts[m.comp] = (counts[m.comp] || 0) + 1; });
      var today = data.days.filter(function (d) { return d.key === "today"; })[0].date;
      var list = sorted(filtered());

      var html = kpiStrip(hist, today);
      html += '<nav class="daytabs" role="tablist">' + data.days.map(function (d) {
        var n = data.matches.filter(function (m) { return m.day === d.key; }).length;
        return '<button type="button" role="tab" data-act="day" data-day="' + d.key + '" aria-selected="' + (d.key === state.day) + '">' +
          "<b>" + esc(T(d.key)) + "</b><span>" + dayLabel(d.date) + " · " + n + "</span></button>";
      }).join("") + "</nav>";

      html += '<div class="toolbar">' +
        '<input id="f-q" type="search" placeholder="' + esc(T("search_team")) + '" value="' + esc(state.q) + '" aria-label="' + esc(T("search_team")) + '">' +
        sel("f-sort", T("sort_by"), state.sort, [["time", T("sort_time")], ["conf", T("sort_conf")], ["value", T("sort_value")], ["league", T("sort_league")], ["goals", T("sort_goals")]]) +
        sel("f-market", T("filter_market"), state.market, [["all", T("m_all")], ["1x2", T("m_1x2")], ["goals", T("m_goals")], ["btts", T("m_btts")]]) +
        sel("f-min", T("min_conf"), String(state.min), [["0", T("all_short")], ["55", "≥ 55%"], ["60", "≥ 60%"], ["65", "≥ 65%"], ["70", "≥ 70%"], ["75", "≥ 75%"]]) +
        toggle("value", T("only_value")) + toggle("fav", T("only_fav")) +
        '<div class="seg" role="group">' + ["grouped", "list"].map(function (v) {
          return '<button type="button" data-act="view" data-view="' + v + '" aria-pressed="' + (state.view === v) + '">' + esc(T("view_" + v)) + "</button>";
        }).join("") + "</div></div>";

      html += '<div class="lchips"><button type="button" data-act="lg" data-lg="" aria-pressed="' + !state.leagues.length + '">' + esc(T("all_leagues")) + "</button>" +
        Object.keys(data.leagues).filter(function (c) { return counts[c]; }).map(function (c) {
          var lg = data.leagues[c];
          return '<button type="button" data-act="lg" data-lg="' + c + '" aria-pressed="' + (state.leagues.indexOf(c) >= 0) + '">' +
            (lg.emblem ? '<img src="' + esc(lg.emblem) + '" alt="" width="16" height="16" loading="lazy">' : "") + esc(lg.name) + " <i>" + counts[c] + "</i></button>";
        }).join("") + "</div>";

      html += couponsHtml();
      html += '<p class="listinfo">' + esc(fmt(T("matches_count"), { n: list.length })) + "</p>";

      if (!list.length) {
        html += '<div class="emptybox"><p>' + esc(T("no_results_filter")) + '</p><button type="button" class="btn" data-act="reset">' + esc(T("reset_filters")) + "</button></div>";
      } else if (state.view === "grouped" && state.sort !== "conf" && state.sort !== "value") {
        var groups = {};
        list.forEach(function (m) { (groups[m.comp] = groups[m.comp] || []).push(m); });
        Object.keys(data.leagues).concat(Object.keys(groups)).filter(function (c, i, a) { return groups[c] && a.indexOf(c) === i; }).forEach(function (c) {
          var lg = data.leagues[c] || { name: c };
          html += '<section class="lgroup"><header><a href="league-' + c + '.html">' +
            (lg.emblem ? '<img src="' + esc(lg.emblem) + '" alt="" width="20" height="20" loading="lazy">' : '<span class="lg-badge">' + esc(c) + "</span>") +
            "<b>" + esc(lg.name) + "</b>" + (lg.area ? "<span>" + esc(lg.area) + "</span>" : "") + "</a></header>" +
            groups[c].map(row).join("") + "</section>";
        });
      } else {
        html += '<section class="lgroup flat">' + list.map(row).join("") + "</section>";
      }
      html += slipHtml();
      app.innerHTML = html;
      app.classList.add("ready");
    }

    function sel(id, label, value, opts) {
      return '<label class="sel"><span>' + esc(label) + '</span><select id="' + id + '">' + opts.map(function (o) {
        return '<option value="' + o[0] + '"' + (o[0] === value ? " selected" : "") + ">" + esc(o[1]) + "</option>";
      }).join("") + "</select></label>";
    }
    function toggle(key, label) {
      return '<button type="button" class="tgl" data-act="tgl" data-key="' + key + '" aria-pressed="' + !!state[key] + '">' + esc(label) + "</button>";
    }

    app.addEventListener("click", function (e) {
      var b = e.target.closest("[data-act]");
      if (!b || !data) return;
      var act = b.getAttribute("data-act");
      var rowEl = b.closest(".mrow");
      var m = rowEl && data.matches.filter(function (x) { return String(x.id) === rowEl.getAttribute("data-id"); })[0];
      if (act === "day") { state.day = b.getAttribute("data-day"); history.replaceState(null, "", "#" + state.day); }
      else if (act === "lg") {
        var c = b.getAttribute("data-lg");
        if (!c) state.leagues = [];
        else if (state.leagues.indexOf(c) >= 0) state.leagues = state.leagues.filter(function (x) { return x !== c; });
        else state.leagues = state.leagues.concat([c]);
      }
      else if (act === "tgl") { var k = b.getAttribute("data-key"); state[k] = !state[k]; }
      else if (act === "view") state.view = b.getAttribute("data-view");
      else if (act === "reset") { state.leagues = []; state.q = ""; state.market = "all"; state.min = 0; state.value = false; state.fav = false; }
      else if (act === "open") open[m.id] = !open[m.id];
      else if (act === "fav") {
        favs = favs.indexOf(m.id) >= 0 ? favs.filter(function (x) { return x !== m.id; }) : favs.concat([m.id]);
        store.set("favs", favs.slice(-300));
      }
      else if (act === "add") {
        var mk = b.getAttribute("data-m");
        var exists = inSlip(m.id, mk);
        slip = slip.filter(function (s) { return s.id !== m.id; });  // jeden typ na mecz
        if (!exists) slip.push({ id: m.id, home: m.home, away: m.away, m: mk, p: m.p ? m.p[mk] : m.pick.p,
                                 o: m.odds && m.odds[mk] ? m.odds[mk].now : null });
        store.set("slip", slip);
      }
      else if (act === "rm") { slip.splice(+b.getAttribute("data-i"), 1); store.set("slip", slip); }
      else if (act === "clear") { slip = []; store.set("slip", slip); }
      else if (act === "slip") { store.set("slipOpen", !store.get("slipOpen", false)); }
      save(); render();
    });
    app.addEventListener("change", function (e) {
      var id = e.target.id;
      if (id === "f-sort") state.sort = e.target.value;
      else if (id === "f-market") state.market = e.target.value;
      else if (id === "f-min") state.min = +e.target.value;
      else return;
      save(); render();
    });
    var qTimer;
    app.addEventListener("input", function (e) {
      if (e.target.id !== "f-q") return;
      state.q = e.target.value;
      clearTimeout(qTimer);
      qTimer = setTimeout(function () {
        var pos = e.target.selectionStart;
        render();
        var q = document.getElementById("f-q");
        q.focus(); q.setSelectionRange(pos, pos);
      }, 150);
    });
  }

  // ---------------------------------------------------------------- statystyki
  function statsApp() {
    var hist, today;
    var state = { period: "30", league: "", market: "", result: "", page: 0 };
    getJSON("../data/history.json").then(function (h) {
      hist = h; today = new Date().toISOString().slice(0, 10); render();
    }).catch(function () {});

    function inPeriod(r) {
      var p = state.period;
      if (p === "all") return true;
      if (p === "yesterday") return r.d === addDays(today, -1);
      if (p === "today") return r.d === today;
      if (p === "month") return r.d.slice(0, 7) === today.slice(0, 7);
      return r.d >= addDays(today, -(+p)) && r.d <= today;
    }

    function dailyChart(rows) {
      var days = [];
      for (var i = 29; i >= 0; i--) days.push(addDays(today, -i));
      var by = {};
      rows.forEach(function (r) { (by[r.d] = by[r.d] || []).push(r); });
      var W = 480, H = 240, L = 34, B = 26, step = (W - L - 8) / days.length, bw = Math.max(4, step - 6);
      var y = function (v) { return H - B - v * (H - B - 12); };
      var grid = [0, 0.25, 0.5, 0.75, 1].map(function (v) {
        return '<line x1="' + L + '" x2="' + (W - 4) + '" y1="' + y(v) + '" y2="' + y(v) + '" class="grid"/>' +
               '<text x="' + (L - 6) + '" y="' + (y(v) + 4) + '" class="ax" text-anchor="end">' + v * 100 + "%</text>";
      }).join("");
      var bars = "", line = [];
      days.forEach(function (d, i) {
        var a = agg(by[d] || []);
        var x = L + i * step + (step - bw) / 2;
        if (a.n) {
          var h = Math.max(2, (H - B - 12) * a.rate);
          bars += '<rect x="' + x + '" y="' + (H - B - h) + '" width="' + bw + '" height="' + h + '" rx="3" class="bar" data-tip="' +
            esc(dayLabel(d) + ": " + pct(a.rate) + " (" + a.won + "/" + a.n + ") · " + T("predicted") + " " + pct(a.conf)) + '"/>';
          line.push((x + bw / 2) + "," + y(a.conf));
        }
        if (i % 6 === 0) bars += '<text x="' + (x + bw / 2) + '" y="' + (H - 8) + '" class="ax" text-anchor="middle">' + d.slice(8) + "." + d.slice(5, 7) + "</text>";
      });
      var exp = line.length > 1 ? '<polyline points="' + line.join(" ") + '" class="expline"/>' : "";
      return '<svg viewBox="0 0 ' + W + " " + H + '" class="chart" role="img" aria-label="' + esc(T("daily_chart")) + '">' + grid + bars + exp + "</svg>" +
        '<p class="legend"><span class="lg-bar"></span>' + esc(T("actual")) + ' <span class="lg-line"></span>' + esc(T("predicted")) + "</p>";
    }

    function calibration(rows) {
      var buckets = [[0.4, 0.55], [0.55, 0.6], [0.6, 0.65], [0.65, 0.7], [0.7, 0.75], [0.75, 0.8], [0.8, 0.9]];
      var W = 380, H = 300, L = 40, B = 34, lo = 0.2, hi = 1;
      var sx = function (v) { return L + (v - lo) / (hi - lo) * (W - L - 12); };
      var sy = function (v) { return H - B - (v - lo) / (hi - lo) * (H - B - 12); };
      var g = [0.2, 0.4, 0.6, 0.8, 1].map(function (v) {
        return '<line x1="' + L + '" x2="' + (W - 12) + '" y1="' + sy(v) + '" y2="' + sy(v) + '" class="grid"/>' +
          '<text x="' + (L - 6) + '" y="' + (sy(v) + 4) + '" class="ax" text-anchor="end">' + Math.round(v * 100) + "%</text>" +
          '<text x="' + sx(v) + '" y="' + (H - B + 16) + '" class="ax" text-anchor="middle">' + Math.round(v * 100) + "%</text>";
      }).join("");
      var dots = buckets.map(function (b) {
        var a = agg(rows.filter(function (r) { return r.p >= b[0] && r.p < b[1]; }));
        if (!a.n) return "";
        var act = Math.max(lo, Math.min(hi, a.rate));
        return '<circle cx="' + sx(a.conf) + '" cy="' + sy(act) + '" r="' + Math.min(14, 5 + Math.sqrt(a.n)) + '" class="dotc" data-tip="' +
          esc(T("predicted") + " " + pct(a.conf) + " · " + T("actual") + " " + pct(a.rate) + " (" + a.won + "/" + a.n + ")") + '"/>';
      }).join("");
      return '<svg viewBox="0 0 ' + W + " " + H + '" class="chart" role="img" aria-label="' + esc(T("calibration")) + '">' + g +
        '<line x1="' + sx(lo) + '" y1="' + sy(lo) + '" x2="' + sx(hi) + '" y2="' + sy(hi) + '" class="diag"/>' + dots +
        '<text x="' + ((W + L) / 2) + '" y="' + (H - 4) + '" class="ax" text-anchor="middle">' + esc(T("predicted")) + "</text></svg>" +
        '<p class="hint">' + esc(T("calibration_hint")) + "</p>";
    }

    function rankTable(groups, labelFn, title) {
      var rows = Object.keys(groups).map(function (k) { return { k: k, a: agg(groups[k]) }; })
        .filter(function (x) { return x.a.n; }).sort(function (a, b) { return b.a.rate - a.a.rate || b.a.n - a.a.n; });
      if (!rows.length) return "";
      return '<section class="card"><h3>' + esc(title) + '</h3><div class="table-wrap"><table class="rank"><thead><tr><th></th><th>' +
        esc(T("settled")) + "</th><th>" + esc(T("won")) + "</th><th>" + esc(T("hit_rate")) + "</th><th>" + esc(T("avg_conf")) +
        "</th><th>±</th></tr></thead><tbody>" + rows.map(function (x) {
          var diff = x.a.rate - x.a.conf;
          return "<tr><td>" + esc(labelFn(x.k)) + (x.a.n < 30 ? ' <span class="small" data-tip="' + esc(T("sample_note")) + '">*</span>' : "") +
            "</td><td>" + x.a.n + "</td><td>" + x.a.won + '</td><td><div class="ratebar"><span style="width:' + x.a.rate * 100 + '%"></span><b>' +
            pct(x.a.rate) + "</b></div></td><td>" + pct(x.a.conf) + '</td><td class="' + (diff >= 0 ? "pos" : "neg") + '">' +
            (diff >= 0 ? "+" : "") + Math.round(diff * 100) + " pp</td></tr>";
        }).join("") + "</tbody></table></div></section>";
    }

    function render() {
      var all = hist.picks;
      var rows = all.filter(inPeriod);
      var a = agg(rows);
      var byLeague = {}, byMarket = {}, byMonth = {};
      rows.forEach(function (r) { (byLeague[r.c] = byLeague[r.c] || []).push(r); (byMarket[r.m] = byMarket[r.m] || []).push(r); });
      all.forEach(function (r) { (byMonth[r.d.slice(0, 7)] = byMonth[r.d.slice(0, 7)] || []).push(r); });
      var periods = [["yesterday", T("yesterday")], ["today", T("today")], ["7", T("kpi_week")], ["30", T("kpi_month")], ["month", T("p_this_month")], ["all", T("p_all")]];

      var html = '<div class="stats-head"><h1>' + esc(T("results_title")) + '</h1><div class="seg" role="group" aria-label="' + esc(T("period")) + '">' +
        periods.map(function (p) { return '<button type="button" data-act="period" data-p="' + p[0] + '" aria-pressed="' + (state.period === p[0]) + '">' + esc(p[1]) + "</button>"; }).join("") + "</div></div>";
      html += kpiStrip(hist, today);
      html += '<div class="kpis big">' +
        '<div class="kpi"><span class="kpi-l">' + esc(T("hit_rate")) + "</span><b>" + rateTxt(a) + '</b><span class="kpi-s">' + esc(fmt(T("picks_won_of"), { won: a.won, n: a.n })) + "</span></div>" +
        '<div class="kpi"><span class="kpi-l">' + esc(T("expected_hits")) + "</span><b>" + (a.n ? dec(a.exp, 1) : "–") + '</b><span class="kpi-s">' + esc(T("actual_hits")) + " " + a.won + "</span></div>" +
        '<div class="kpi"><span class="kpi-l">' + esc(T("avg_conf")) + "</span><b>" + (a.conf != null ? pct(a.conf) : "–") + '</b><span class="kpi-s">' + esc(T("settled")) + " " + a.n + "</span></div>" +
        '<div class="kpi"><span class="kpi-l">' + esc(T("roi")) + '</span><b class="' + (a.roi > 0 ? "won" : a.roi < 0 ? "lost" : "") + '">' +
        (a.roi != null ? (a.roi > 0 ? "+" : "") + Math.round(a.roi * 100) + "%" : "–") + '</b><span class="kpi-s">' + (a.roiN ? a.roiN + " · " + esc(T("market_odds")) : "–") + "</span></div></div>";

      html += '<div class="grid2"><section class="card"><h3>' + esc(T("daily_chart")) + "</h3>" + dailyChart(all.filter(function (r) { return r.d >= addDays(today, -30); })) +
        '</section><section class="card"><h3>' + esc(T("calibration")) + "</h3>" + calibration(rows) + "</section></div>";
      html += rankTable(byLeague, function (c) { return hist.leagues[c] || c; }, T("leagues_ranking")) +
        rankTable(byMarket, M, T("markets_ranking"));

      // kupony
      var cp = { safe: [], standard: [], bold: [] };
      hist.coupons.filter(function (c) { return inPeriod(c); }).forEach(function (c) { (cp[c.k] = cp[c.k] || []).push(c); });
      html += '<section class="card"><h3>' + esc(T("coupons_history")) + '</h3><div class="kpis">' + Object.keys(cp).map(function (k) {
        var s = cp[k].filter(function (c) { return c.r === "won" || c.r === "lost"; });
        var w = s.filter(function (c) { return c.r === "won"; }).length;
        return '<div class="kpi"><span class="kpi-l">' + esc(T("coupon_" + k)) + "</span><b>" + (s.length ? pct(w / s.length) : "–") +
          '</b><span class="kpi-s">' + esc(fmt(T("picks_won_of"), { won: w, n: s.length })) + "</span></div>";
      }).join("") + "</div></section>";

      // miesiące
      var months = Object.keys(byMonth).sort().reverse();
      html += '<section class="card"><h3>' + esc(T("monthly")) + '</h3><div class="table-wrap"><table class="rank"><thead><tr><th>' + "" +
        "</th><th>" + esc(T("settled")) + "</th><th>" + esc(T("won")) + "</th><th>" + esc(T("hit_rate")) + "</th><th>" + esc(T("avg_conf")) + "</th></tr></thead><tbody>" +
        months.map(function (mo) {
          var x = agg(byMonth[mo]);
          return "<tr><td>" + new Date(mo + "-15").toLocaleDateString(I.lang, { month: "long", year: "numeric" }) + "</td><td>" + x.n + "</td><td>" + x.won +
            '</td><td><div class="ratebar"><span style="width:' + (x.rate || 0) * 100 + '%"></span><b>' + rateTxt(x) + "</b></div></td><td>" + (x.conf != null ? pct(x.conf) : "–") + "</td></tr>";
        }).join("") + "</tbody></table></div></section>";

      // dziennik typów
      var log = rows.filter(function (r) {
        return (!state.league || r.c === state.league) && (!state.market || r.m === state.market) &&
               (!state.result || (state.result === "pending" ? !r.r : r.r === state.result));
      });
      var per = 50, pages = Math.max(1, Math.ceil(log.length / per));
      state.page = Math.min(state.page, pages - 1);
      var leagueOpts = Object.keys(hist.leagues).map(function (c) { return [c, hist.leagues[c]]; });
      var marketOpts = Object.keys(I.markets).map(function (k) { return [k, I.markets[k]]; });
      html += '<section class="card"><h3>' + esc(T("picks_log")) + '</h3><div class="toolbar">' +
        sel("s-league", T("leagues"), state.league, [["", T("all_leagues")]].concat(leagueOpts)) +
        sel("s-market", T("market"), state.market, [["", T("m_all")]].concat(marketOpts)) +
        sel("s-result", T("result"), state.result, [["", T("result_all")], ["won", T("won")], ["lost", T("lost")], ["pending", T("pending")]]) +
        '<a class="btn ghost" href="../data/history.json" download>' + esc(T("download_data")) + "</a></div>" +
        '<div class="table-wrap"><table class="log"><thead><tr><th>' + esc(T("date")) + "</th><th>" + esc(T("match")) + "</th><th>" + esc(T("pick")) +
        "</th><th>%</th><th>" + esc(T("result")) + "</th><th></th></tr></thead><tbody>" +
        log.slice(state.page * per, state.page * per + per).map(function (r) {
          return "<tr><td>" + r.d.slice(5).split("-").reverse().join(".") + '</td><td><a href="match-' + r.id + '.html">' + esc(r.h) + " – " + esc(r.a) +
            '</a><small class="muted"> · ' + esc(hist.leagues[r.c] || r.c || "") + "</small></td><td>" + esc(M(r.m)) + "</td><td>" + pct(r.p) +
            "</td><td>" + esc(r.s || "") + "</td><td>" + (badge(r.r) || '<span class="muted">' + esc(T("pending")) + "</span>") + "</td></tr>";
        }).join("") + "</tbody></table></div>" +
        (pages > 1 ? '<div class="pager"><button type="button" class="btn ghost" data-act="pg" data-d="-1"' + (state.page ? "" : " disabled") + ">" + esc(T("page_prev")) +
          "</button><span>" + (state.page + 1) + " / " + pages + '</span><button type="button" class="btn ghost" data-act="pg" data-d="1"' +
          (state.page < pages - 1 ? "" : " disabled") + ">" + esc(T("page_next")) + "</button></div>" : "") +
        '<p class="hint">' + esc(T("sample_note")) + "</p></section>";

      app.innerHTML = html;
      app.classList.add("ready");
    }

    function sel(id, label, value, opts) {
      return '<label class="sel"><span>' + esc(label) + '</span><select id="' + id + '">' + opts.map(function (o) {
        return '<option value="' + esc(o[0]) + '"' + (o[0] === value ? " selected" : "") + ">" + esc(o[1]) + "</option>";
      }).join("") + "</select></label>";
    }
    app.addEventListener("click", function (e) {
      var b = e.target.closest("[data-act]");
      if (!b || !hist) return;
      if (b.getAttribute("data-act") === "period") { state.period = b.getAttribute("data-p"); state.page = 0; }
      if (b.getAttribute("data-act") === "pg") state.page += +b.getAttribute("data-d");
      render();
    });
    app.addEventListener("change", function (e) {
      if (!hist) return;
      if (e.target.id === "s-league") state.league = e.target.value;
      else if (e.target.id === "s-market") state.market = e.target.value;
      else if (e.target.id === "s-result") state.result = e.target.value;
      else return;
      state.page = 0; render();
    });
  }

  if (app.getAttribute("data-kind") === "tips") tipsApp();
  else if (app.getAttribute("data-kind") === "stats") statsApp();
})();
