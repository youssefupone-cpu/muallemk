/**
 * shadcn/ui-style `sonner` wrapper (P4-246) — thin re-export so the rest
 * of the codebase imports from `./ui/sonner` (matches shadcn convention)
 * without requiring the full `shadcn/ui` path alias.
 */
import { Toaster as SonnerToaster } from "sonner";

export { SonnerToaster as Toaster };
