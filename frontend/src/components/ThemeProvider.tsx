/**
 * ThemeProvider — next-themes pattern: zero FOUC (P4-239).
 *
 * The actual <html class="dark"> toggle is written by an **inline script**
 * injected via index.html (see `theme-helmet.js`). This provider only
 * *reads* the stored theme and re-publishes it so React doesn't block the
 * first paint while reading localStorage (which SSR would throw on).
 */
import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import { applyTheme, type Theme } from "./theme-utils";

const ThemeContext = createContext<{
  theme: Theme;
  setTheme: (t: Theme) => void;
}>({ theme: "system", setTheme: () => {} });

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>("system");

  // Read once, lazily (after first paint).
  useEffect(() => {
    const stored = (localStorage.getItem("theme") as Theme) ?? "system";
    setThemeState(stored);
  }, []);

  const setTheme = (t: Theme) => {
    localStorage.setItem("theme", t);
    applyTheme(t);
    setThemeState(t);
  };

  useEffect(() => {
    // Apply initial theme read from storage (or system).
    // Runs once — the class is also set synchronously by theme-helmet.js (no FOUC)
    const stored = localStorage.getItem("theme") as Theme | null;
    applyTheme(stored ?? "system");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export const useTheme = () => useContext(ThemeContext);
