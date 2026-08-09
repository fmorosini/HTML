// Buscador y filtro de categorías para /fichas-de-especies.html — 100% cliente, sin backend.
(function () {
  "use strict";

  var input = document.getElementById("auSpeciesSearch");
  var cards = Array.prototype.slice.call(document.querySelectorAll("[data-species-card]"));
  var chips = Array.prototype.slice.call(document.querySelectorAll("[data-cat-chip]"));
  var countEl = document.getElementById("auResultsCount");
  var emptyEl = document.getElementById("auEmptyState");

  if (!input || !cards.length) return;

  var activeCats = new Set();

  function normalize(s) {
    return (s || "")
      .toLowerCase()
      .normalize("NFD").replace(/[̀-ͯ]/g, "");
  }

  function apply() {
    var q = normalize(input.value.trim());
    var visible = 0;
    cards.forEach(function (card) {
      var text = normalize(card.getAttribute("data-search"));
      var cats = (card.getAttribute("data-cats") || "").split(",");
      var matchesText = !q || text.indexOf(q) !== -1;
      var matchesCat = activeCats.size === 0 || cats.some(function (c) { return activeCats.has(c); });
      var show = matchesText && matchesCat;
      card.closest("[data-species-col]").style.display = show ? "" : "none";
      if (show) visible++;
    });
    if (countEl) countEl.textContent = visible;
    if (emptyEl) emptyEl.style.display = visible === 0 ? "block" : "none";
  }

  input.addEventListener("input", apply);

  chips.forEach(function (chip) {
    chip.addEventListener("click", function () {
      var cat = chip.getAttribute("data-cat-chip");
      if (activeCats.has(cat)) {
        activeCats.delete(cat);
        chip.classList.remove("active");
      } else {
        activeCats.add(cat);
        chip.classList.add("active");
      }
      apply();
    });
  });

  apply();
})();
