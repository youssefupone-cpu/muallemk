import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MathRenderer } from "./MathRenderer";

describe("MathRenderer", () => {
  it("يدعم المعادلات النصية الداخلية", () => {
    const { container } = render(<MathRenderer content="معادلة: $E = mc^2$" />);
    expect(container.querySelector(".katex")).not.toBeNull();
  });

  it("يدعم المعادلات المنسقة على سطر منفص بدون رمي خطأ", () => {
    expect(() =>
      render(<MathRenderer content="$$\nx^2 + y^2 = z^2\n$$" />),
    ).not.toThrow();
  });
});
