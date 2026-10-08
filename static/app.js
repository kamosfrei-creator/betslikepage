// Godziny meczów w strefie czasowej odwiedzającego + zapamiętanie wybranego języka.
(function () {
  var lang = document.documentElement.lang;
  document.querySelectorAll("time[data-utc]").forEach(function (el) {
    var d = new Date(el.getAttribute("data-utc"));
    if (isNaN(d)) return;
    var opts = el.getAttribute("data-fmt") === "time"
      ? { hour: "2-digit", minute: "2-digit" }
      : { dateStyle: "medium", timeStyle: "short" };
    el.textContent = d.toLocaleString(lang, opts);
  });
  document.querySelectorAll("a[data-lang]").forEach(function (a) {
    a.addEventListener("click", function () {
      try { localStorage.setItem("lang", a.getAttribute("data-lang")); } catch (e) {}
    });
  });
})();
