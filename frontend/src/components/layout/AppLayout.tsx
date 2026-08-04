import type { ReactNode } from "react";
import { Link, NavLink } from "react-router-dom";

import { ThemeToggle } from "../ThemeToggle";

/**
 * الهيكل الموحّد للصفحات (P1-86): شريط علوي RTL موحّد بدل التذييل المنسوخ.
 * يُزيل تكرار dir="rtl" يدوياً (P1-90) — index.css يضبطه عمومياً.
 */

const NAV_ITEMS: { to: string; label: string }[] = [
  { to: "/", label: "المحادثة" },
  { to: "/books", label: "الكتب" },
  { to: "/exam", label: "الامتحان" },
  { to: "/diagnostic", label: "تشخيص" },
  { to: "/documents", label: "مستنداتي" },
  { to: "/plugins", label: "الإضافات" },
  { to: "/settings", label: "الإعدادات" },
];

export function AppLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-50">
      <header className="sticky top-0 z-10 border-b border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3">
          <Link
            to="/"
            className="text-lg font-bold text-slate-900 dark:text-slate-100"
          >
            معلّمك
          </Link>
          <nav
            className="flex flex-wrap items-center gap-1"
            aria-label="التنقل الرئيسي"
          >
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) =>
                  isActive
                    ? "rounded-lg bg-blue-600 px-3 py-1.5 text-sm text-white"
                    : "rounded-lg px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-slate-50"
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <ThemeToggle />
        </div>
      </header>
      <main className="flex-1">{children}</main>
    </div>
  );
}
