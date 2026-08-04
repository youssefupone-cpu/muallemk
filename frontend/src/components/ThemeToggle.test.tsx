import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ThemeProvider } from "./ThemeProvider";
import { ThemeToggle } from "./ThemeToggle";

describe("ThemeToggle", () => {
  const renderWithProvider = () =>
    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>,
    );

  it("تبدّل بين الوضعين عند النقر", () => {
    renderWithProvider();
    const btn = screen.getByRole("button", { name: /وضع/i });
    expect(btn).toBeTruthy();

    // النقر يُشغّل .dark
    fireEvent.click(btn);
    expect(document.documentElement.classList.contains("dark")).toBe(true);

    // النقر مرة أخرى يُطفئ .dark
    fireEvent.click(btn);
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });
});
