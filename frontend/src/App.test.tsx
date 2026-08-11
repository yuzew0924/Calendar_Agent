import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";

describe("App", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the project name and backend status", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ status: "ok" }), {
          status: 200,
          headers: { "Content-Type": "application/json" }
        })
      )
    );

    render(<App />);

    expect(screen.getByRole("heading", { name: "Calendar Agent" })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Checking backend");
    expect(await screen.findByText("Backend online")).toBeInTheDocument();
  });
});
