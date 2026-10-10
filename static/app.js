// OnePickAway - skrypt wspólny + aplikacje "tips" (przegląd typów) i "stats" (statystyki).
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
  if (!i18nEl) return;
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
  // ------------------------------------------------- ulubione, kupon, motyw (wszystkie strony)
  var Prefs = {
    favLeagues: store.get("favLeagues", []),
    favs: store.get("favs", []),
    slip: store.get("slip", []),
    listeners: [],
    save: function () {
      store.set("favLeagues", this.favLeagues); store.set("favs", this.favs.slice(-300)); store.set("slip", this.slip);
      this.listeners.forEach(function (f) { f(); });
      Cloud.push();
    },
    onChange: function (f) { this.listeners.push(f); },
    toggleLeague: function (c) {
      this.favLeagues = this.favLeagues.indexOf(c) >= 0 ? this.favLeagues.filter(function (x) { return x !== c; }) : this.favLeagues.concat([c]);
      this.save();
    },
    toggleFav: function (id) {
      this.favs = this.Prefs.favs.indexOf(id) >= 0 ? this.favs.filter(function (x) { return x !== id; }) : this.favs.concat([id]);
      this.save();
    },
    inSlip: function (id, mk) { return this.slip.some(function (s) { return s.id === id && (!mk || s.m === mk); }); },
    toggleSlip: function (item) {
      var exists = this.inSlip(item.id, item.m);
      this.slip = this.slip.filter(function (s) { return s.id !== item.id; });  // jeden typ na mecz
      if (!exists) this.slip.push(item);
      this.save();
    }
  };

  var slipEl = document.getElementById("slip");
  function renderSlip() {
    if (!slipEl) return;
    var slip = Prefs.slip.filter(function (s) { return !s.utc || new Date(s.utc) > new Date(Date.now() - 3 * 3600e3); });
    var prob = slip.reduce(function (a, s) { return a * s.p; }, 1);
    var allOdds = slip.length && slip.every(function (s) { return s.o; });
    var mo = allOdds ? slip.reduce(function (a, s) { return a * s.o; }, 1) : null;
    slipEl.classList.toggle("open", store.get("slipOpen", false));
    slipEl.innerHTML = '<button type="button" class="slip-head" data-slip-act="toggle">' + esc(T("my_slip")) + ' <span class="cnt">' + slip.length + "</span>" +
      (slip.length ? '<span class="slip-odds">@' + dec(1 / prob) + "</span>" : "") + "</button>" +
      '<div class="slip-body">' + (slip.length ? "<ol>" + slip.map(function (s, i) {
        return '<li><span><a href="match-' + s.id + '.html"><b>' + esc(s.home) + " – " + esc(s.away) + "</b></a><small>" + esc(M(s.m)) + " · " +
          pct(s.p) + " · @" + fair(s.p) + (s.o ? " · " + esc(T("market_odds")) + " " + dec(s.o) : "") +
          '</small></span><button type="button" class="ib" data-slip-act="rm" data-i="' + i + '" aria-label="' + esc(T("remove")) + '">×</button></li>';
      }).join("") + "</ol>" +
        '<div class="slip-sum"><span>' + esc(T("combined_prob")) + " <b>" + pct(prob) + "</b></span><span>" + esc(T("combined_odds")) +
        " <b>" + dec(1 / prob) + "</b></span>" + (mo ? "<span>" + esc(T("market_odds")) + " <b>" + dec(mo) + "</b></span>" : "") + "</div>" +
        '<button type="button" class="btn ghost" data-slip-act="clear">' + esc(T("slip_clear")) + "</button>"
        : '<p class="muted">' + esc(T("slip_empty")) + "</p>") +
      '<p class="hint">18+ · ' + esc(T("fair_odds_hint")) + "</p></div>";
    document.querySelectorAll("[data-slip]").forEach(function (b) {
      var d = JSON.parse(b.getAttribute("data-slip"));
      b.classList.toggle("on", Prefs.inSlip(d.id, d.m));
    });
  }
  document.addEventListener("click", function (e) {
    var b = e.target.closest && e.target.closest("[data-slip],[data-slip-act],[data-fav-league]");
    if (!b) return;
    if (b.hasAttribute("data-slip")) { Prefs.toggleSlip(JSON.parse(b.getAttribute("data-slip"))); return; }
    if (b.hasAttribute("data-fav-league")) { Prefs.toggleLeague(b.getAttribute("data-fav-league")); return; }
    var act = b.getAttribute("data-slip-act");
    if (act === "toggle") { store.set("slipOpen", !store.get("slipOpen", false)); renderSlip(); }
    else if (act === "rm") { Prefs.slip.splice(+b.getAttribute("data-i"), 1); Prefs.save(); }
    else if (act === "clear") { Prefs.slip = []; Prefs.save(); }
  });

  // menu lig: gwiazdki i ulubione na górze
  function renderSidebar() {
    var favList = document.querySelector(".sidebar .fav-list");
    if (!favList) return;
    var list = document.querySelector(".sidebar .lg-list");
    document.querySelectorAll(".sidebar .lg-item").forEach(function (item) {
      var c = item.getAttribute("data-code"), on = Prefs.favLeagues.indexOf(c) >= 0;
      var star = item.querySelector(".lg-star");
      star.textContent = on ? "★" : "☆"; star.setAttribute("aria-pressed", on);
      item.classList.toggle("fav", on);
      (on ? favList : list).appendChild(item);
    });
    document.querySelector(".sidebar .fav-title").hidden = !Prefs.favLeagues.length;
  }

  // jasny / ciemny motyw (domyślnie jasny)
  var themeBtn = document.getElementById("theme-btn");
  function applyTheme() {
    var dark = store.get("theme", "light") === "dark";
    if (dark) document.documentElement.setAttribute("data-theme", "dark"); else document.documentElement.removeAttribute("data-theme");
    if (themeBtn) { var l = T(dark ? "theme_light" : "theme_dark"); themeBtn.title = l; themeBtn.setAttribute("aria-label", l); }
  }
  if (themeBtn) themeBtn.addEventListener("click", function () { store.set("theme", store.get("theme", "light") === "dark" ? "light" : "dark"); applyTheme(); });
  applyTheme();

  // ------------------------------------------------- konta (Supabase) i komentarze
  var CFG = {};
  try { CFG = JSON.parse(document.getElementById("site-cfg").textContent); } catch (e) {}
  var Cloud = {
    sb: null, user: null, nick: null, timer: null,
    enabled: function () { return !!(CFG.supabase && CFG.supabase.url && CFG.supabase.key); },
    load: function () {
      if (!this.enabled()) { Comments.render(); return; }
      var s = document.createElement("script");
      s.src = "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.45.4/dist/umd/supabase.min.js";
      s.onload = function () {
        Cloud.sb = window.supabase.createClient(CFG.supabase.url, CFG.supabase.key);
        Cloud.sb.auth.onAuthStateChange(function (_ev, session) { Cloud.setUser(session ? session.user : null); });
        Cloud.sb.auth.getSession().then(function (r) { Cloud.setUser(r.data.session ? r.data.session.user : null); });
      };
      s.onerror = function () { Comments.render(); };
      document.head.appendChild(s);
    },
    setUser: function (user) {
      var changed = (this.user && this.user.id) !== (user && user.id);
      this.user = user;
      if (!user) { this.nick = null; updateLoginBtn(); Comments.render(); return; }
      if (!changed) return;
      Promise.all([
        this.sb.from("profiles").select("nick").eq("id", user.id).maybeSingle(),
        this.sb.from("user_prefs").select("*").eq("user_id", user.id).maybeSingle()
      ]).then(function (res) {
        Cloud.nick = res[0].data ? res[0].data.nick : null;
        var p = res[1].data;
        if (p) {  // łączymy ustawienia z chmury z lokalnymi
          Prefs.favLeagues = union(Prefs.favLeagues, p.fav_leagues || []);
          Prefs.favs = union(Prefs.favs, p.fav_matches || []);
          var ids = Prefs.slip.map(function (s) { return s.id; });
          (p.slip || []).forEach(function (s) { if (ids.indexOf(s.id) < 0) Prefs.slip.push(s); });
        }
        Prefs.save();
        updateLoginBtn(); Comments.render();
      });
    },
    push: function () {
      if (!this.sb || !this.user) return;
      clearTimeout(this.timer);
      var uid = this.user.id;
      this.timer = setTimeout(function () {
        Cloud.sb.from("user_prefs").upsert({ user_id: uid, fav_leagues: Prefs.favLeagues, fav_matches: Prefs.favs.slice(-300),
                                             slip: Prefs.slip, updated_at: new Date().toISOString() });
      }, 800);
    }
  };
  function union(a, b) { return a.concat(b.filter(function (x) { return a.indexOf(x) < 0; })); }

  var loginBtn = document.getElementById("login-btn");
  function updateLoginBtn() {
    if (!loginBtn) return;
    loginBtn.textContent = Cloud.user ? (Cloud.nick || Cloud.user.email.split("@")[0]) + " · " + T("logout") : T("login");
  }
  function modal(html) {
    var d = document.createElement("div");
    d.className = "modal";
    d.innerHTML = '<div class="modal-box" role="dialog" aria-modal="true"><button type="button" class="ib modal-x" aria-label="×">×</button>' + html + "</div>";
    d.addEventListener("click", function (e) { if (e.target === d || e.target.closest(".modal-x")) d.remove(); });
    document.body.appendChild(d);
    var f = d.querySelector("input"); if (f) f.focus();
    return d;
  }
  if (loginBtn) loginBtn.addEventListener("click", function () {
    if (!Cloud.enabled()) { modal("<p>" + esc(T("login_unavailable")) + "</p>"); return; }
    if (!Cloud.sb) return;
    if (Cloud.user) { Cloud.sb.auth.signOut(); return; }
    var d = modal('<h3>' + esc(T("login_title")) + '</h3><form class="login-form">' +
      '<label>' + esc(T("login_email")) + '<input id="login-email" type="email" required autocomplete="email"></label>' +
      '<label class="chk"><input id="login-age" type="checkbox" required> ' + esc(T("login_age")) + "</label>" +
      '<label class="chk"><input id="login-priv" type="checkbox" required> <a href="privacy.html" target="_blank">' + esc(T("login_privacy")) + "</a></label>" +
      '<button type="submit" class="btn">' + esc(T("login_send")) + '</button><p class="msg" role="status"></p></form>');
    d.querySelector("form").addEventListener("submit", function (e) {
      e.preventDefault();
      var msg = d.querySelector(".msg");
      Cloud.sb.auth.signInWithOtp({ email: d.querySelector("#login-email").value.trim(),
                                    options: { emailRedirectTo: location.href.split("#")[0] } })
        .then(function (r) { msg.textContent = r.error ? T("login_error") : T("login_sent"); });
    });
  });

  var Comments = {
    el: document.getElementById("comments"),
    render: function () {
      var el = this.el;
      if (!el) return;
      var body = el.querySelector(".c-body");
      if (!Cloud.sb) { body.innerHTML = '<p class="muted">' + esc(T(Cloud.enabled() ? "loading" : "login_unavailable")) + "</p>"; return; }
      var mid = +el.getAttribute("data-match");
      Cloud.sb.from("comments").select("id,nick,body,created_at,user_id").eq("match_id", mid).order("created_at").limit(300)
        .then(function (r) {
          var rows = r.data || [];
          var list = rows.length ? '<ol class="c-list">' + rows.map(function (c) {
            var mine = Cloud.user && c.user_id === Cloud.user.id;
            return '<li><div class="c-meta"><b>' + esc(c.nick) + "</b><time>" + new Date(c.created_at).toLocaleString(I.lang, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) +
              "</time>" + (Cloud.user ? '<button type="button" class="link" data-c-act="' + (mine ? "del" : "rep") + '" data-id="' + c.id + '">' +
              esc(T(mine ? "comment_delete" : "comment_report")) + "</button>" : "") + '</div><p>' + esc(c.body) + "</p></li>";
          }).join("") + "</ol>" : '<p class="muted">' + esc(T("comments_empty")) + "</p>";
          var form;
          if (!Cloud.user) form = '<p><button type="button" class="btn ghost" data-c-act="login">' + esc(T("comment_login")) + "</button></p>";
          else if (!Cloud.nick) form = '<form class="c-form" data-c-form="nick"><label>' + esc(T("nick_prompt")) +
            '<input name="nick" required minlength="3" maxlength="24" pattern="[A-Za-z0-9_.\\-]+"></label><button class="btn">' + esc(T("nick_save")) + '</button><p class="msg"></p></form>';
          else form = '<form class="c-form" data-c-form="comment"><textarea name="body" required maxlength="1000" rows="3" placeholder="' +
            esc(T("comment_placeholder")) + '"></textarea><button class="btn">' + esc(T("comment_send")) + '</button><p class="msg"></p></form>';
          body.innerHTML = list + form;
        });
    }
  };
  if (Comments.el) {
    Comments.el.addEventListener("click", function (e) {
      var b = e.target.closest("[data-c-act]");
      if (!b) return;
      var act = b.getAttribute("data-c-act"), id = +b.getAttribute("data-id");
      if (act === "login" && loginBtn) loginBtn.click();
      else if (act === "del") Cloud.sb.from("comments").delete().eq("id", id).then(function () { Comments.render(); });
      else if (act === "rep") Cloud.sb.from("reports").insert({ comment_id: id }).then(function () { b.textContent = T("comment_reported"); b.disabled = true; });
    });
    Comments.el.addEventListener("submit", function (e) {
      var f = e.target.closest("[data-c-form]");
      if (!f) return;
      e.preventDefault();
      var msg = f.querySelector(".msg");
      if (f.getAttribute("data-c-form") === "nick") {
        var nick = f.nick.value.trim();
        Cloud.sb.from("profiles").insert({ id: Cloud.user.id, nick: nick }).then(function (r) {
          if (r.error) { msg.textContent = T("nick_taken"); return; }
          Cloud.nick = nick; updateLoginBtn(); Comments.render();
        });
      } else {
        Cloud.sb.from("comments").insert({ match_id: +Comments.el.getAttribute("data-match"), nick: Cloud.nick, body: f.body.value.trim() })
          .then(function (r) { if (r.error) msg.textContent = T("login_error"); else Comments.render(); });
      }
    });
  }

  Prefs.onChange(renderSlip);
  Prefs.onChange(renderSidebar);
  renderSlip(); renderSidebar();
  Cloud.load();

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
    var picks = hist.picks.filter(function (r) { return (r.k || "safe") === "safe"; });
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
                                fav: false, view: "grouped", mix: 0, pmode: "safe", coupon: "safe" }, store.get("filters", {}));
    state.q = ""; state.day = location.hash.slice(1) || state.day;
    var open = {};
    var data, hist, byId = {};

    Promise.all([getJSON("data.json"), getJSON("../data/history.json").catch(function () { return { picks: [], coupons: [], leagues: {} }; })])
      .then(function (res) {
        data = res[0]; hist = res[1];
        data.matches.forEach(function (m) { byId[m.id] = m; });
        if (!data.days.some(function (d) { return d.key === state.day; })) state.day = "today";
        render();
        Prefs.onChange(function () { render(); });
      })
      .catch(function () { /* zostaje statyczna wersja strony */ });

    function save() {
      store.set("filters", { leagues: state.leagues, sort: state.sort, market: state.market, min: state.min,
                             value: state.value, fav: state.fav, view: state.view, day: state.day, mix: state.mix,
                             pmode: state.pmode, coupon: state.coupon });
    }

    function filtered() {
      var q = state.q.trim().toLowerCase();
      return data.matches.filter(function (m) {
        if (m.day !== state.day) return false;
        if (state.leagues.length && state.leagues.indexOf(m.comp) < 0) return false;
        if (q && (m.home + " " + m.away).toLowerCase().indexOf(q) < 0) return false;
        if (state.fav && Prefs.favs.indexOf(m.id) < 0) return false;
        var pk = pickOf(m);
        if (state.market !== "all" && (!pk || GROUP[pk.m] !== state.market)) return false;
        if (state.min && (!pk || pk.p * 100 < state.min)) return false;
        if (state.mix && !(m.ix != null && Math.abs(m.ix) >= state.mix)) return false;
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
        conf: function (a, b) { return (pickOf(b) ? pickOf(b).p : 0) - (pickOf(a) ? pickOf(a).p : 0); },
        value: function (a, b) { return valueOf(b) - valueOf(a); },
        league: function (a, b) { return a.comp < b.comp ? -1 : a.comp > b.comp ? 1 : (a.utc < b.utc ? -1 : 1); },
        goals: function (a, b) { return (b.xg ? b.xg[0] + b.xg[1] : 0) - (a.xg ? a.xg[0] + a.xg[1] : 0); },
        index: function (a, b) { return (b.ix != null ? Math.abs(b.ix) : -1) - (a.ix != null ? Math.abs(a.ix) : -1) || (b.ix || 0) - (a.ix || 0); }
      }[state.sort];
      return list.slice().sort(by);
    }

    function statusCell(m) {
      if (m.status === "FINISHED") return '<span class="st ft">' + esc(T("finished")) + "</span>";
      if (m.status === "IN_PLAY" || m.status === "PAUSED") return '<span class="st live">' + esc(T("live")) + "</span>";
      return '<span class="st">' + timeOf(m.utc) + "</span>";
    }
    function inSlip(id, mk) { return Prefs.inSlip(id, mk); }
    function pickOf(m) { return state.pmode === "range" ? m.pickr : m.pick; }
    function ixChip(m) {
      if (m.ix == null) return "";
      var v = m.ix, cls = v >= 0 ? "pos" : "neg";
      return '<span class="ix ' + cls + '" data-tip="' + esc(T("index_hint")) + '">' + (v > 0 ? "+" : "") + dec(v, 1) + "</span>";
    }

    function row(m) {
      var p = m.p, pk = pickOf(m), isOpen = open[m.id];
      var played = m.hg != null;
      var probs = "";
      if (p) {
        var best = ["1", "X", "2"].reduce(function (a, k) { return p[k] > p[a] ? k : a; }, "1");
        probs = '<div class="m-probs">' + ["1", "X", "2"].map(function (k) {
          return '<span class="pp o' + k + (k === best ? " hi" : "") + '"><i>' + k + "</i>" + Math.round(p[k] * 100) + "%</span>";
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
      var fav = Prefs.favs.indexOf(m.id) >= 0;
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
        '<div class="m-time">' + statusCell(m) + flags + "</div>" + teams + probs + '<div class="m-ix">' + ixChip(m) + "</div>" + tipHtml + acts +
        (isOpen ? more(m) : "") + "</article>";
    }

    function colHead() {
      return '<div class="mhead"><span>' + esc(T("kickoff")) + "</span><span>" + esc(T("match")) + "</span><span>" + esc(T("probs_1x2")) +
        '</span><span data-tip="' + esc(T("index_hint")) + '">' + esc(T("index")) + " ⓘ</span><span>" + esc(T("pick")) +
        (state.pmode === "range" ? " · " + esc(T("pick_range")) : "") + "</span><span></span></div>";
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
      var keys = ["safe", "standard", "bold", "range", "c8", "c10"].filter(function (k) { return cs[k]; });
      if (!keys.length) return "";
      var k = keys.indexOf(state.coupon) >= 0 ? state.coupon : keys[0];
      var c = cs[k];
      var odds = c.legs.every(function (l) { var mm = byId[l.id]; return mm && mm.odds && mm.odds[l.market]; })
        ? c.legs.reduce(function (a, l) { return a * byId[l.id].odds[l.market].now; }, 1) : null;
      var tabs = '<div class="ctabs" role="tablist">' + keys.map(function (x) {
        return '<button type="button" role="tab" data-act="coupon" data-v="' + x + '" aria-selected="' + (x === k) + '">' + esc(T("coupon_" + x)) +
          " <i>@" + dec(cs[x].fair_odds) + "</i></button>";
      }).join("") + "</div>";
      var stats = '<div class="cstats">' +
        "<div><span>" + esc(T("picks_count")) + "</span><b>" + c.legs.length + "</b></div>" +
        "<div><span>" + esc(T("combined_prob")) + "</span><b>" + pct(c.p) + "</b></div>" +
        "<div><span>" + esc(T("combined_odds")) + "</span><b>" + dec(c.fair_odds) + "</b></div>" +
        (odds ? "<div><span>" + esc(T("market_odds")) + "</span><b>" + dec(odds) + "</b></div>" : "") +
        (c.exp != null ? "<div><span>" + esc(T("exp_hits")) + "</span><b>" + dec(c.exp, 1) + " / " + c.legs.length + "</b></div>" : "") +
        (c.p1miss != null ? "<div><span>" + esc(T("p1miss")) + "</span><b>" + pct(c.p1miss) + "</b></div>" : "") +
        (c.avg_p != null ? "<div><span>" + esc(T("avg_conf")) + "</span><b>" + pct(c.avg_p) + "</b></div>" : "") + "</div>";
      var legs = "<ol>" + c.legs.map(function (l) {
        return '<li><span class="teams"><a href="match-' + l.id + '.html">' + esc(l.home) + " – " + esc(l.away) + '</a></span><span class="leg-meta">' + timeOf(l.utc) +
          ' <span class="market">' + esc(M(l.market)) + '</span><span class="prob">' + pct(l.p) + "</span><span class=\"odds\">@" + fair(l.p) + "</span>" + badge(l.result) + "</span></li>";
      }).join("") + "</ol>";
      var addAll = '<button type="button" class="btn" data-act="addcoupon" data-v="' + k + '">+ ' + esc(T("my_slip")) + "</button>";
      return '<section class="couponbox"><header><h2>' + esc(T("coupons_title")) + "</h2>" + badge(c.result) + "</header>" + tabs +
        '<div class="cbody ' + k + '">' + stats + legs + addAll + (k === "range" ? '<p class="hint">' + esc(T("range_hint")) + "</p>" : "") + "</div></section>";
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
        sel("f-sort", T("sort_by"), state.sort, [["time", T("sort_time")], ["conf", T("sort_conf")], ["value", T("sort_value")], ["league", T("sort_league")], ["goals", T("sort_goals")], ["index", T("sort_index")]]) +
        sel("f-market", T("filter_market"), state.market, [["all", T("m_all")], ["1x2", T("m_1x2")], ["goals", T("m_goals")], ["btts", T("m_btts")]]) +
        sel("f-min", T("min_conf"), String(state.min), [["0", T("all_short")], ["55", "≥ 55%"], ["60", "≥ 60%"], ["65", "≥ 65%"], ["70", "≥ 70%"], ["75", "≥ 75%"]]) +
        sel("f-mix", T("min_index"), String(state.mix), [["0", T("all_short")], ["2", "±2"], ["3", "±3"], ["4", "±4"], ["5", "±5"], ["6", "±6"], ["7", "±7"]]) +
        '<div class="seg" role="group" aria-label="' + esc(T("pick_mode")) + '">' + ["safe", "range"].map(function (v) {
          return '<button type="button" data-act="pmode" data-v="' + v + '" aria-pressed="' + (state.pmode === v) + '">' + esc(T("pick_" + v)) + "</button>";
        }).join("") + "</div>" +
        toggle("value", T("only_value")) + toggle("fav", T("only_fav")) +
        '<div class="seg" role="group">' + ["grouped", "list", "index"].map(function (v) {
          return '<button type="button" data-act="view" data-view="' + v + '" aria-pressed="' + (state.view === v) + '">' + esc(T("view_" + v)) + "</button>";
        }).join("") + "</div></div>";

      html += '<div class="lchips"><button type="button" data-act="lg" data-lg="" aria-pressed="' + !state.leagues.length + '">' + esc(T("all_leagues")) + "</button>" +
        leagueOrder().filter(function (c) { return counts[c]; }).map(function (c) {
          var lg = data.leagues[c];
          return '<button type="button" data-act="lg" data-lg="' + c + '" aria-pressed="' + (state.leagues.indexOf(c) >= 0) + '"' +
            (Prefs.favLeagues.indexOf(c) >= 0 ? ' class="fav"' : "") + ">" + (Prefs.favLeagues.indexOf(c) >= 0 ? "★ " : "") +
            (lg.emblem ? '<img src="' + esc(lg.emblem) + '" alt="" width="16" height="16" loading="lazy">' : "") + esc(lg.name) + " <i>" + counts[c] + "</i></button>";
        }).join("") + "</div>";

      html += couponsHtml();
      html += '<p class="listinfo">' + esc(fmt(T("matches_count"), { n: list.length })) + "</p>";

      if (!list.length) {
        html += '<div class="emptybox"><p>' + esc(T("no_results_filter")) + '</p><button type="button" class="btn" data-act="reset">' + esc(T("reset_filters")) + "</button></div>";
      } else if (state.view === "index") {
        var ixList = list.filter(function (m) { return m.ix != null; }).sort(function (a, b) { return Math.abs(b.ix) - Math.abs(a.ix) || b.ix - a.ix; });
        html += '<p class="hint">' + esc(T("index_hint")) + '</p><section class="lgroup flat">' + colHead() + ixList.map(row).join("") + "</section>";
      } else if (state.view === "grouped" && state.sort !== "conf" && state.sort !== "value" && state.sort !== "index") {
        var groups = {};
        list.forEach(function (m) { (groups[m.comp] = groups[m.comp] || []).push(m); });
        leagueOrder().concat(Object.keys(groups)).filter(function (c, i, a) { return groups[c] && a.indexOf(c) === i; }).forEach(function (c) {
          var lg = data.leagues[c] || { name: c };
          html += '<section class="lgroup"><header><a href="league-' + c + '.html">' +
            (lg.emblem ? '<img src="' + esc(lg.emblem) + '" alt="" width="20" height="20" loading="lazy">' : '<span class="lg-badge">' + esc(c) + "</span>") +
            "<b>" + esc(lg.name) + "</b>" + (lg.area ? "<span>" + esc(lg.area) + "</span>" : "") + "</a></header>" +
            colHead() + groups[c].map(row).join("") + "</section>";
        });
      } else {
        html += '<section class="lgroup flat">' + colHead() + list.map(row).join("") + "</section>";
      }
      app.innerHTML = html;
      app.classList.add("ready");
    }

    function leagueOrder() {
      var all = Object.keys(data.leagues);
      return all.filter(function (c) { return Prefs.favLeagues.indexOf(c) >= 0; })
        .concat(all.filter(function (c) { return Prefs.favLeagues.indexOf(c) < 0; }));
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
      else if (act === "pmode") state.pmode = b.getAttribute("data-v");
      else if (act === "coupon") state.coupon = b.getAttribute("data-v");
      else if (act === "addcoupon") {
        data.coupons[state.day][b.getAttribute("data-v")].legs.forEach(function (l) {
          if (!Prefs.inSlip(l.id, l.market)) Prefs.toggleSlip({ id: l.id, home: l.home, away: l.away, m: l.market, p: l.p, utc: l.utc,
                                                               o: byId[l.id] && byId[l.id].odds && byId[l.id].odds[l.market] ? byId[l.id].odds[l.market].now : null });
        });
      }
      else if (act === "reset") { state.leagues = []; state.q = ""; state.market = "all"; state.min = 0; state.mix = 0; state.value = false; state.fav = false; }
      else if (act === "open") open[m.id] = !open[m.id];
      else if (act === "fav") Prefs.toggleFav(m.id);
      else if (act === "add") {
        var mk = b.getAttribute("data-m");
        Prefs.toggleSlip({ id: m.id, home: m.home, away: m.away, m: mk, p: m.p ? m.p[mk] : pickOf(m).p, utc: m.utc,
                           o: m.odds && m.odds[mk] ? m.odds[mk].now : null });
      }
      save(); render();
    });
    app.addEventListener("change", function (e) {
      var id = e.target.id;
      if (id === "f-sort") state.sort = e.target.value;
      else if (id === "f-market") state.market = e.target.value;
      else if (id === "f-min") state.min = +e.target.value;
      else if (id === "f-mix") state.mix = +e.target.value;
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
    var state = { period: "30", league: "", market: "", result: "", page: 0, kind: "safe" };
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

    function byIndex(rows) {
      var g = {};
      rows.forEach(function (r) {
        if (r.ix == null) return;
        var a = Math.abs(r.ix), k = a >= 6 ? "±6+" : a >= 4 ? "±4–6" : a >= 2 ? "±2–4" : "±0–2";
        (g[k] = g[k] || []).push(r);
      });
      return g;
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
      var all = hist.picks.filter(function (r) { return (r.k || "safe") === state.kind; });
      var rows = all.filter(inPeriod);
      var a = agg(rows);
      var byLeague = {}, byMarket = {}, byMonth = {};
      rows.forEach(function (r) { (byLeague[r.c] = byLeague[r.c] || []).push(r); (byMarket[r.m] = byMarket[r.m] || []).push(r); });
      all.forEach(function (r) { (byMonth[r.d.slice(0, 7)] = byMonth[r.d.slice(0, 7)] || []).push(r); });
      var periods = [["yesterday", T("yesterday")], ["today", T("today")], ["7", T("kpi_week")], ["30", T("kpi_month")], ["month", T("p_this_month")], ["all", T("p_all")]];

      var html = '<div class="stats-head"><h1>' + esc(T("results_title")) + '</h1><div class="seg" role="group" aria-label="' + esc(T("period")) + '">' +
        periods.map(function (p) { return '<button type="button" data-act="period" data-p="' + p[0] + '" aria-pressed="' + (state.period === p[0]) + '">' + esc(p[1]) + "</button>"; }).join("") + "</div></div>";
      html += kpiStrip(hist, today);
      html += '<div class="seg kindseg" role="group" aria-label="' + esc(T("pick_mode")) + '">' + ["safe", "range"].map(function (v) {
        return '<button type="button" data-act="kind" data-v="' + v + '" aria-pressed="' + (state.kind === v) + '">' + esc(T("pick_" + v)) + "</button>";
      }).join("") + "</div>";
      html += '<div class="kpis big">' +
        '<div class="kpi"><span class="kpi-l">' + esc(T("hit_rate")) + "</span><b>" + rateTxt(a) + '</b><span class="kpi-s">' + esc(fmt(T("picks_won_of"), { won: a.won, n: a.n })) + "</span></div>" +
        '<div class="kpi"><span class="kpi-l">' + esc(T("expected_hits")) + "</span><b>" + (a.n ? dec(a.exp, 1) : "–") + '</b><span class="kpi-s">' + esc(T("actual_hits")) + " " + a.won + "</span></div>" +
        '<div class="kpi"><span class="kpi-l">' + esc(T("avg_conf")) + "</span><b>" + (a.conf != null ? pct(a.conf) : "–") + '</b><span class="kpi-s">' + esc(T("settled")) + " " + a.n + "</span></div>" +
        '<div class="kpi"><span class="kpi-l">' + esc(T("roi")) + '</span><b class="' + (a.roi > 0 ? "won" : a.roi < 0 ? "lost" : "") + '">' +
        (a.roi != null ? (a.roi > 0 ? "+" : "") + Math.round(a.roi * 100) + "%" : "–") + '</b><span class="kpi-s">' + (a.roiN ? a.roiN + " · " + esc(T("market_odds")) : "–") + "</span></div></div>";

      html += '<div class="grid2"><section class="card"><h3>' + esc(T("daily_chart")) + "</h3>" + dailyChart(all.filter(function (r) { return r.d >= addDays(today, -30); })) +
        '</section><section class="card"><h3>' + esc(T("calibration")) + "</h3>" + calibration(rows) + "</section></div>";
      html += rankTable(byLeague, function (c) { return hist.leagues[c] || c; }, T("leagues_ranking")) +
        rankTable(byMarket, M, T("markets_ranking")) +
        rankTable(byIndex(rows), function (k) { return T("index") + " " + k; }, T("by_index"));

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
      if (b.getAttribute("data-act") === "kind") { state.kind = b.getAttribute("data-v"); state.page = 0; }
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

  if (app && window.fetch && app.getAttribute("data-kind") === "tips") tipsApp();
  else if (app && window.fetch && app.getAttribute("data-kind") === "stats") statsApp();
})();
