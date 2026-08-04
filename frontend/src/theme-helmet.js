(function () {
  // Zero-FOUC theme bootstrap — runs before CSS paints (P4-239).
  // Mirrors next-themes pre-effect so the correct .dark class is set
  // synchronously; React picks up the same value via ThemeProvider.
  var stored = localStorage.getItem("theme");
  var dark;
  if (stored === "dark") dark = true;
  else if (stored === "light") dark = false;
  else dark = window.matchMedia("(prefers-color-scheme: dark)").matches;

  if (dark) document.documentElement.classList.add("dark");
})();
