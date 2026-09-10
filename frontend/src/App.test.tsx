import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";

function defaultParsedPreferences() {
  return {
    earliestStart: null,
    earliestStartIsHard: false,
    preferredDaysOff: [],
    requiredDaysOff: [],
    preferredTimeOfDay: "none",
    gapPreference: "none",
    fixedSections: [],
    requireOpenSections: true,
    hardConstraints: [],
    softPreferences: [],
    conflicts: [],
    needsClarification: false,
    clarificationQuestions: []
  };
}

function mockApiResponse(payload: object) {
  return vi.fn().mockImplementation((_input: string, init?: RequestInit) =>
    Promise.resolve(
      new Response(
        JSON.stringify(init?.method ? payload : { status: "ok" }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    )
  );
}

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

  it("adds a course from section rows and groups its components", async () => {
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

    fireEvent.change(screen.getByLabelText("Course name"), {
      target: { value: "CSE 414" }
    });
    fireEvent.click(screen.getByRole("button", { name: "Add section time" }));
    fireEvent.change(screen.getByLabelText("Section 2 type"), {
      target: { value: "quiz" }
    });
    fireEvent.change(screen.getByLabelText("Section 2 ID"), {
      target: { value: "AA" }
    });
    fireEvent.change(screen.getByLabelText("Section 2 days"), {
      target: { value: "Th" }
    });
    fireEvent.click(screen.getByRole("button", { name: "Add course" }));

    expect(await screen.findByText("CSE 414")).toBeInTheDocument();
    expect(screen.getByText("lecture · choose 1 · 1 section")).toBeInTheDocument();
    expect(screen.getByText("quiz · choose 1 · 1 section")).toBeInTheDocument();
  });

  it("loads sample data and immediately displays its course summary", () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: "ok" }), { status: 200 }))
    );
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Load sample data" }));

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

  it("shows a clear error for invalid section days", async () => {
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

    fireEvent.change(screen.getByLabelText("Course name"), { target: { value: "CSE 414" } });
    fireEvent.change(screen.getByLabelText("Section 1 days"), { target: { value: "Sunday" } });
    fireEvent.click(screen.getByRole("button", { name: "Add course" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Use weekday codes");
    expect(screen.queryByText("Added courses")).not.toBeInTheDocument();
  });

  it("supports the parse, confirm, generate, and option review flow", async () => {
    const parsedPreferences = {
      earliestStart: "10:00",
      earliestStartIsHard: false,
      preferredDaysOff: ["F"],
      requiredDaysOff: [],
      preferredTimeOfDay: "afternoon",
      gapPreference: "compact",
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
                score: 87,
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
                  gaps: {
                    score: 23,
                    maximum: 30,
                    scoreDelta: -7,
                    matchedPreference: "compact",
                    details: "One 70-minute gap",
                    reasonCandidate: null,
                    tradeoffCandidate: "One gap is at least 30 minutes",
                    affectedSections: ["CSE 373 B"],
                    affectedMeetings: []
                  },
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

    fireEvent.click(screen.getByRole("button", { name: "Load sample data" }));
    fireEvent.click(screen.getByRole("button", { name: /Interpret preferences/ }));

    expect(await screen.findByRole("heading", { name: "Confirm your schedule requirements" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Confirm and generate/ }));

    expect(await screen.findByRole("heading", { name: "Weekly schedule" })).toBeInTheDocument();
    expect(screen.getByText("1 ranked schedules")).toBeInTheDocument();
    expect(screen.getAllByText("CSE 373 B")).toHaveLength(2);
    expect(screen.getByText("Matched: compact · Delta: -7")).toBeInTheDocument();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
  });

  it("shows hard conflicts, blocks generation, and preserves text for revision", async () => {
    const conflictPreferences = {
      ...defaultParsedPreferences(),
      conflicts: ["CSE 373 A conflicts with the required Friday off"],
      needsClarification: true,
      clarificationQuestions: ["Should the fixed section override Friday off?"]
    };
    vi.stubGlobal("fetch", mockApiResponse(conflictPreferences));
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Load sample data" }));
    fireEvent.change(screen.getByLabelText("Describe your ideal schedule"), {
      target: { value: "Keep Friday free and require CSE 373 A" }
    });
    fireEvent.click(screen.getByRole("button", { name: /Interpret preferences/ }));

    expect(await screen.findByText("Hard-constraint conflicts")).toBeInTheDocument();
    expect(screen.getByText(/CSE 373 A conflicts/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Confirm and generate/ })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Revise preferences" }));
    expect(screen.getByLabelText("Describe your ideal schedule")).toHaveValue(
      "Keep Friday free and require CSE 373 A"
    );
  });

  it("renders FastAPI validation details and AI parsing failures", async () => {
    const fetchMock = vi.fn().mockImplementation((input: string, init?: RequestInit) => {
      if (!init?.method) return Promise.resolve(new Response('{"status":"ok"}', { status: 200 }));
      return Promise.resolve(new Response(JSON.stringify({ detail: [{ loc: ["body", "courses", 0, "code"], msg: "Field required" }] }), { status: 422 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Load sample data" }));
    fireEvent.click(screen.getByRole("button", { name: /Interpret preferences/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent("courses.0.code: Field required");

    cleanup();
    vi.stubGlobal("fetch", vi.fn().mockImplementation((input: string, init?: RequestInit) => {
      if (!init?.method) return Promise.resolve(new Response('{"status":"ok"}', { status: 200 }));
      return Promise.resolve(new Response(JSON.stringify({ error: { message: "AI preference parsing timed out" } }), { status: 504 }));
    }));
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Load sample data" }));
    fireEvent.click(screen.getByRole("button", { name: /Interpret preferences/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent("AI preference parsing timed out");
  });

  it("shows a specific backend-unavailable message", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Load sample data" }));
    fireEvent.click(screen.getByRole("button", { name: /Interpret preferences/ }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Backend unavailable at");
    expect(screen.getByRole("status")).toHaveTextContent("Backend unavailable");
  });

  it("shows every no-result diagnostic and a recovery action", async () => {
    const fetchMock = vi.fn().mockImplementation((_input: string, init?: RequestInit) => {
      if (!init?.method) return Promise.resolve(new Response('{"status":"ok"}', { status: 200 }));
      return Promise.resolve(new Response(JSON.stringify({
        interpretedPreferences: defaultParsedPreferences(),
        schedules: [],
        count: 0,
        warnings: [
          "CSE 373 quiz group has no open sections while open-only is enabled.",
          "All remaining combinations have meeting conflicts."
        ]
      }), { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Load sample data" }));
    fireEvent.change(screen.getByLabelText("Describe your ideal schedule"), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: /Interpret preferences/ }));
    fireEvent.click(screen.getByRole("button", { name: /Confirm and generate/ }));

    expect(await screen.findByRole("heading", { name: "No legal schedules" })).toBeInTheDocument();
    expect(screen.getByText(/quiz group has no open sections/)).toBeInTheDocument();
    expect(screen.getByText(/All remaining combinations/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Edit courses/ })).toBeInTheDocument();
  });

  it("supports lecture and lab groups without inventing other components", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: "ok" }), { status: 200 }))
    );
    render(<App />);

    fireEvent.change(screen.getByLabelText("Course name"), {
      target: { value: "CHEM 142" }
    });
    fireEvent.click(screen.getByRole("button", { name: "Add section time" }));
    fireEvent.change(screen.getByLabelText("Section 2 type"), {
      target: { value: "lab" }
    });
    fireEvent.change(screen.getByLabelText("Section 2 ID"), {
      target: { value: "LA" }
    });
    fireEvent.click(screen.getByRole("button", { name: "Add course" }));

    expect(await screen.findByText("CHEM 142")).toBeInTheDocument();
    expect(screen.getByText("lecture · choose 1 · 1 section")).toBeInTheDocument();
    expect(screen.getByText("lab · choose 1 · 1 section")).toBeInTheDocument();
    expect(screen.queryByText(/quiz ·/)).not.toBeInTheDocument();
  });
});
