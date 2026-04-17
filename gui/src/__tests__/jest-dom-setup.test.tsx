/**
 * Verification test: confirms @testing-library/jest-dom matchers
 * are available globally via vitest.setup.ts without per-file imports.
 */
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";

describe("jest-dom global setup", () => {
  it("provides toBeInTheDocument without explicit import", () => {
    render(<button>Click me</button>);
    expect(screen.getByRole("button")).toBeInTheDocument();
  });

  it("provides toHaveTextContent without explicit import", () => {
    render(<p>Hello world</p>);
    expect(screen.getByText("Hello world")).toHaveTextContent("Hello world");
  });

  it("provides toBeDisabled without explicit import", () => {
    render(<button disabled>Disabled</button>);
    expect(screen.getByRole("button")).toBeDisabled();
  });
});
