// Arboles Urbanos — comportamiento común del sitio (sin dependencias externas además de Bootstrap)
(function () {
  "use strict";

  // ---- Lightbox para galerías de fichas de especies ----
  var galleryLinks = Array.prototype.slice.call(document.querySelectorAll(".au-gallery-grid a"));
  if (galleryLinks.length) {
    var lightbox = document.createElement("div");
    lightbox.className = "au-lightbox";
    lightbox.innerHTML =
      '<button class="au-lightbox-close" aria-label="Cerrar">&times;</button>' +
      '<button class="au-lightbox-nav prev" aria-label="Anterior">&#8249;</button>' +
      '<img alt="">' +
      '<button class="au-lightbox-nav next" aria-label="Siguiente">&#8250;</button>';
    document.body.appendChild(lightbox);

    var imgEl = lightbox.querySelector("img");
    var idx = 0;

    function show(i) {
      idx = (i + galleryLinks.length) % galleryLinks.length;
      var link = galleryLinks[idx];
      imgEl.src = link.getAttribute("href");
      imgEl.alt = link.querySelector("img") ? link.querySelector("img").alt : "";
    }
    function open(i) {
      show(i);
      lightbox.classList.add("open");
      document.body.style.overflow = "hidden";
    }
    function close() {
      lightbox.classList.remove("open");
      document.body.style.overflow = "";
    }

    galleryLinks.forEach(function (link, i) {
      link.addEventListener("click", function (e) {
        e.preventDefault();
        open(i);
      });
    });
    lightbox.querySelector(".au-lightbox-close").addEventListener("click", close);
    lightbox.querySelector(".prev").addEventListener("click", function () { show(idx - 1); });
    lightbox.querySelector(".next").addEventListener("click", function () { show(idx + 1); });
    lightbox.addEventListener("click", function (e) {
      if (e.target === lightbox) close();
    });
    document.addEventListener("keydown", function (e) {
      if (!lightbox.classList.contains("open")) return;
      if (e.key === "Escape") close();
      if (e.key === "ArrowLeft") show(idx - 1);
      if (e.key === "ArrowRight") show(idx + 1);
    });
  }
})();
