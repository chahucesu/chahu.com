(function () {
  "use strict";

  var body = document.body;
  var toggle = document.querySelector("[data-nav-toggle]");
  var nav = document.querySelector("[data-main-nav]");
  var backTop = document.querySelector("[data-back-top]");
  var progress = document.querySelector("[data-reading-progress]");

  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var isOpen = body.classList.toggle("nav-open");
      toggle.setAttribute("aria-expanded", String(isOpen));
    });

    nav.addEventListener("click", function (event) {
      if (event.target.closest("a")) {
        body.classList.remove("nav-open");
        toggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  if (backTop) {
    backTop.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }

  var tocLinks = Array.prototype.slice.call(document.querySelectorAll(".toc a"));
  var headings = tocLinks
    .map(function (link) {
      return document.querySelector(link.getAttribute("href"));
    })
    .filter(Boolean);

  function updateReadingState() {
    var scrollTop = window.scrollY || document.documentElement.scrollTop;
    var scrollable = document.documentElement.scrollHeight - window.innerHeight;

    if (progress) {
      progress.style.width = (scrollable > 0 ? Math.min(100, (scrollTop / scrollable) * 100) : 0) + "%";
    }

    if (backTop) {
      backTop.classList.toggle("visible", scrollTop > 520);
    }

    if (headings.length) {
      var current = headings[0].id;
      headings.forEach(function (heading) {
        if (heading.getBoundingClientRect().top <= 140) {
          current = heading.id;
        }
      });
      tocLinks.forEach(function (link) {
        link.classList.toggle("active", link.getAttribute("href") === "#" + current);
      });
    }
  }

  window.addEventListener("scroll", updateReadingState, { passive: true });
  window.addEventListener("resize", updateReadingState);
  updateReadingState();
})();
