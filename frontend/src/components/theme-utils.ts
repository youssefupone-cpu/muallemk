export type Theme = "light" | "dark" | "system";

/** خوادم تطبيق المظهر على <html> — منفّصل لتجنب تحذير only-export-components في ThemeProvider (P4-239). */
export function applyTheme(t: Theme) {
  const root = document.documentElement;
  if (t === "system") {
    const isDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    root.classList.toggle("dark", isDark);
  } else {
    root.classList.toggle("dark", t === "dark");
  }
}
