(function () {
  "use strict";
  var expandAll = false;

  function panels() { return Array.prototype.slice.call(document.querySelectorAll(".pillar-panel")); }
  function nodes() { return Array.prototype.slice.call(document.querySelectorAll("button.pnode")); }

  function openPillar(id, scroll) {
    panels().forEach(function (p) { p.hidden = !expandAll && p.id !== id; });
    nodes().forEach(function (b) { b.setAttribute("aria-expanded", b.getAttribute("data-target") === id ? "true" : "false"); });
    var el = document.getElementById(id);
    if (el && scroll && el.scrollIntoView) { el.scrollIntoView({ behavior: "smooth", block: "start" }); }
  }

  nodes().forEach(function (b) {
    b.addEventListener("click", function () {
      var id = b.getAttribute("data-target");
      var el = document.getElementById(id);
      if (!expandAll && el && !el.hidden && b.getAttribute("aria-expanded") === "true") {
        el.hidden = true; b.setAttribute("aria-expanded", "false");
      } else { openPillar(id, true); }
    });
  });

  var all = document.getElementById("expand-all");
  if (all) {
    all.addEventListener("click", function () {
      expandAll = !expandAll;
      panels().forEach(function (p) { p.hidden = !expandAll; });
      all.textContent = expandAll ? "Collapse all pillars" : "Expand all pillars";
    });
  }

  Array.prototype.slice.call(document.querySelectorAll(".tabs")).forEach(function (bar) {
    var card = bar.parentNode;
    bar.addEventListener("click", function (ev) {
      var btn = ev.target.closest ? ev.target.closest("button[data-win]") : null;
      if (!btn) { return; }
      var key = btn.getAttribute("data-win");
      Array.prototype.slice.call(bar.querySelectorAll("button")).forEach(function (x) {
        x.setAttribute("aria-selected", x === btn ? "true" : "false");
      });
      Array.prototype.slice.call(card.querySelectorAll(".win")).forEach(function (w) {
        w.hidden = w.getAttribute("data-win") !== key;
      });
    });
  });

  window.__renderTex = function () {
    if (!window.katex) { return; }
    Array.prototype.slice.call(document.querySelectorAll(".eq[data-tex]")).forEach(function (el) {
      if (el.classList.contains("rendered")) { return; }
      try {
        el.querySelector(".tex").innerHTML = window.katex.renderToString(el.getAttribute("data-tex"), { throwOnError: true, strict: "ignore" });
        el.classList.add("rendered");
      } catch (e) { /* keep the plain-text equation */ }
    });
  };
  window.__renderTex();

  var state = null;
  window.addEventListener("beforeprint", function () {
    state = panels().map(function (p) { return p.hidden; });
    panels().forEach(function (p) { p.hidden = false; });
  });
  window.addEventListener("afterprint", function () {
    if (state) { panels().forEach(function (p, i) { p.hidden = state[i]; }); }
  });
})();
