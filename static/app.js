// Godziny meczów w strefie czasowej odwiedzającego + zapamiętanie wybranego języka.
(function () {
  var lang = document.documentElement.lang;
  document.querySelectorAll("time[data-utc]").forEach(function (el) {
    var d = new Date(el.getAttribute("data-utc"));
    if (isNaN(d)) return;
    var fmt = el.getAttribute("data-fmt");
    var opts = fmt === "time" ? { hour: "2-digit", minute: "2-digit" }
      : fmt === "date" ? { day: "2-digit", month: "2-digit", year: "2-digit" }
      : { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" };
    el.textContent = d.toLocaleString(lang, opts);
  });
  var select = document.getElementById("lang-select");
  if (select) {
    select.addEventListener("change", function () {
      var opt = select.options[select.selectedIndex];
      try { localStorage.setItem("lang", opt.getAttribute("data-lang")); } catch (e) {}
      location.href = opt.value;
    });
  }
})();
