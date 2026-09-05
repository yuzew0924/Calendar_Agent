import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";

describe("App", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
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

  it("parses course JSON and shows the actual group structure", async () => {
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

    fireEvent.click(screen.getByRole("button", { name: "Parse course data" }));

    expect(await screen.findByText("2 courses parsed")).toBeInTheDocument();
    expect(screen.getAllByText("lecture · choose 1 · 2 sections")).toHaveLength(2);
    expect(screen.getByText("quiz · choose 1 · 2 sections")).toBeInTheDocument();
  });

  it("loads sample data and immediately displays its course summary", () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: "ok" }), { status: 200 }))
    );
    render(<App />);

    fireEvent.change(screen.getByLabelText("Course JSON"), { target: { value: "[]" } });
    fireEvent.click(screen.getByRole("button", { name: "Load sample data" }));

    expect((screen.getByLabelText("Course JSON") as HTMLTextAreaElement).value).toContain("CSE 373");
    expect(screen.getByText("2 courses parsed")).toBeInTheDocument();
    expect(screen.getByText("CSE 373")).toBeInTheDocument();
    expect(screen.getByText("INFO 370")).toBeInTheDocument();
  });

  it("uses safe defaults when preference text is blank", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: "ok" }), { status: 200 })
    );
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Load sample data" }));
    fireEvent.change(screen.getByLabelText("Describe your ideal schedule"), {
      target: { value: "   " }
    });
    fireEvent.click(screen.getByRole("button", { name: /Interpret preferences/ }));

    expect(await screen.findByRole("heading", { name: "Confirm your schedule requirements" })).toBeInTheDocument();
    expect(screen.getByText("Open sections only")).toBeInTheDocument();
    expect(screen.getByText("No soft preferences")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("shows a JSON parse error and clears an invalid summary", async () => {
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

    fireEvent.change(screen.getByLabelText("Course JSON"), { target: { value: "{" } });
    fireEvent.click(screen.getByRole("button", { name: "Parse course data" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("JSON parse error");
    expect(screen.queryByText(/courses parsed/)).not.toBeInTheDocument();
  });

  it("supports the parse, confirm, generate, and option review flow", async () => {
    const parsedPreferences = {
      earliestStart: "10:00",
      earliestStartIsHard: false,
      preferredDaysOff: ["F"],
      requiredDaysOff: [],
      preferredTimeOfDay: "afternoon",
      fixedSections: [],
      requireOpenSections: true,
      hardConstraints: [],
      softPreferences: ["Prefer compact schedules"],
      conflicts: [],
      needsClarification: false,
      clarificationQuestions: []
    };
    const fetchMock = vi.fn().mockImplementation((input: string, init?: RequestInit) => {
      if (!init?.method) {
        return Promise.resolve(new Response(JSON.stringify({ status: "ok" }), { status: 200 }));
      }
      if (input.endsWith("/parse-preferences")) {
        return Promise.resolve(new Response(JSON.stringify(parsedPreferences), { status: 200 }));
      }
      return Promise.resolve(
        new Response(
          JSON.stringify({
            interpretedPreferences: parsedPreferences,
            count: 1,
            warnings: [],
            schedules: [
              {
                rank: 1,
                score: 94,
                sections: [
                  {
                    courseCode: "CSE 373",
                    groupType: "lecture",
                    sectionId: "B",
                    status: "open",
                    sln: null,
                    meetings: [
                      { days: ["M", "W"], startTime: "13:30", endTime: "14:20" }
                    ]
                  }
                ],
                scoreBreakdown: {
                  earliestStart: { score: 25, maximum: 25, details: "Starts later", affectedSections: [] },
                  preferredTimeOfDay: { score: 20, maximum: 20, details: "Afternoon", affectedSections: [] },
                  gaps: { score: 30, maximum: 30, details: "No gaps", affectedSections: [] },
                  preferredDaysOff: { score: 19, maximum: 25, details: "Friday free", affectedSections: [] }
                },
                reasons: ["Classes are concentrated in the afternoon"],
                tradeoffs: []
              }
            ]
          }),
          { status: 200 }
        )
      );
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Parse course data" }));
    fireEvent.click(screen.getByRole("button", { name: /Interpret preferences/ }));

    expect(await screen.findByRole("heading", { name: "Confirm your schedule requirements" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Confirm and generate/ }));

    expect(await screen.findByRole("heading", { name: "Weekly schedule" })).toBeInTheDocument();
    expect(screen.getByText("1 ranked schedules")).toBeInTheDocument();
    expect(screen.getAllByText("CSE 373 B")).toHaveLength(2);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
  });

  it("accepts a lecture-only course and preserves a declared empty group", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: "ok" }), { status: 200 }))
    );
    render(<App />);

    const courses = [
      {
        code: "CHEM 142",
        groups: [
          {
            type: "lecture",
            choose: 1,
            sections: [{ id: "A", status: "open", meetings: [] }]
          },
          { type: "lab", choose: 1, sections: [] }
        ]
      }
    ];
    fireEvent.change(screen.getByLabelText("Course JSON"), {
      target: { value: JSON.stringify(courses) }
    });
    fireEvent.click(screen.getByRole("button", { name: "Parse course data" }));

    expect(await screen.findByText("1 course parsed")).toBeInTheDocument();
    expect(screen.getByText("lecture · choose 1 · 1 section")).toBeInTheDocument();
    expect(screen.getByText("lab · choose 1 · 0 sections")).toBeInTheDocument();
    expect(screen.getByText(/Declared empty groups remain required/)).toBeInTheDocument();
  });
});
