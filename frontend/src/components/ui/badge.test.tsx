import { describe, it, expect } from "vitest";
import { render, screen } from "@/../tests/test-utils";
import { Badge } from "./badge";

describe("Badge component", () => {
  it("renders text content properly", () => {
    render(<Badge>New Feature</Badge>);
    expect(screen.getByText("New Feature")).toBeInTheDocument();
  });

  it("renders with variant classes", () => {
    const { container } = render(<Badge variant="destructive">Critical</Badge>);
    expect(container.firstChild).toBeInTheDocument();
  });
});
