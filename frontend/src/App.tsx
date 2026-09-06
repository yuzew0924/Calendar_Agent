import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  Bot,
  CalendarDays,
  Check,
  CheckCircle2,
  ChevronRight,
  ClipboardPaste,
  FileJson,
  LoaderCircle,
  RotateCcw,
  Sparkles
} from "lucide-react";
import { useEffect, useMemo, useState, type CSSProperties } from "react";

type DayCode = "M" | "T" | "W" | "Th" | "F";
type Stage = "input" | "review" | "results";
type BackendState = "checking" | "online" | "unavailable";

type Meeting = {
  days: DayCode[];
  startTime: string;
  endTime: string;
  location?: string | null;
};

type Section = {
  id: string;
  status: "open" | "closed" | "unknown";
  sln?: string | null;
  meetings: Meeting[];
};

type SectionGroup = {
  type: string;
  choose?: number;
  sections: Section[];
};

type Course = {
  code: string;
  title?: string | null;
  groups: SectionGroup[];
};

type ParsedPreferences = {
  earliestStart: string | null;
  earliestStartIsHard: boolean;
  preferredDaysOff: DayCode[];
  requiredDaysOff: DayCode[];
  preferredTimeOfDay: "morning" | "afternoon" | "evening" | "none";
  gapPreference: "compact" | "balanced" | "breaks" | "none";
  fixedSections: string[];
  requireOpenSections: boolean;
  hardConstraints: string[];
  softPreferences: string[];
  conflicts: string[];
  needsClarification: boolean;
  clarificationQuestions: string[];
};

type ScoreBreakdownItem = {
  score: number;
  maximum: number;
  scoreDelta: number;
  matchedPreference: string | null;
  details: string;
  reasonCandidate: string | null;
  tradeoffCandidate: string | null;
  affectedSections: string[];
  affectedMeetings: Array<{
    courseCode: string;
    sectionId: string;
    day: DayCode;
    startTime: string;
    endTime: string;
  }>;
};

type ScheduleSection = {
  courseCode: string;
  groupType: string;
  sectionId: string;
  status: string;
  sln?: string | null;
  meetings: Meeting[];
};

type RankedSchedule = {
  rank: number;
  score: number;
  sections: ScheduleSection[];
  scoreBreakdown: Record<string, ScoreBreakdownItem>;
  reasons: string[];
  tradeoffs: string[];
};

type GenerateResponse = {
  interpretedPreferences: ParsedPreferences;
  schedules: RankedSchedule[];
  count: number;
  warnings: string[];
};

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(
  /\/$/,
  ""
);

const sampleCourses: Course[] = [
  {
    code: "CSE 373",
    title: "Data Structures and Algorithms",
    groups: [
      {
        type: "lecture",
        choose: 1,
        sections: [
          {
            id: "A",
            status: "open",
            meetings: [
              { days: ["M", "W", "F"], startTime: "09:30", endTime: "10:20" }
            ]
          },
          {
            id: "B",
            status: "open",
            meetings: [
              { days: ["M", "W", "F"], startTime: "11:30", endTime: "12:20" }
            ]
          }
        ]
      },
      {
        type: "quiz",
        choose: 1,
        sections: [
          {
            id: "AA",
            status: "open",
            meetings: [{ days: ["Th"], startTime: "12:30", endTime: "13:20" }]
          },
          {
            id: "AB",
            status: "closed",
            meetings: [{ days: ["Th"], startTime: "14:30", endTime: "15:20" }]
          }
        ]
      }
    ]
  },
  {
    code: "INFO 370",
    title: "Core Methods in Data Science",
    groups: [
      {
        type: "lecture",
        choose: 1,
        sections: [
          {
            id: "A",
            status: "open",
            meetings: [{ days: ["T", "Th"], startTime: "10:30", endTime: "11:50" }]
          },
          {
            id: "B",
            status: "open",
            meetings: [{ days: ["T", "Th"], startTime: "13:30", endTime: "14:50" }]
          }
        ]
      }
    ]
  }
];

const sampleJson = JSON.stringify(sampleCourses, null, 2);
const defaultPreferences: ParsedPreferences = {
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
const dayLabels: Record<DayCode, string> = {
  M: "Monday",
  T: "Tuesday",
  W: "Wednesday",
  Th: "Thursday",
  F: "Friday"
};
const days = Object.keys(dayLabels) as DayCode[];
const palette = ["violet", "green", "blue", "orange", "rose"];

function validateCourses(value: unknown): Course[] {
  const candidate = Array.isArray(value)
    ? value
    : typeof value === "object" && value !== null && "courses" in value
      ? (value as { courses: unknown }).courses
      : null;
  if (!Array.isArray(candidate) || candidate.length === 0) {
    throw new Error("Enter a non-empty course array or an object with a courses array.");
  }
  candidate.forEach((course, courseIndex) => {
    if (typeof course !== "object" || course === null) {
      throw new Error(`Course ${courseIndex + 1} must be an object.`);
    }
    const item = course as Partial<Course>;
    if (typeof item.code !== "string" || !item.code.trim()) {
      throw new Error(`Course ${courseIndex + 1} needs a code.`);
    }
    if (!Array.isArray(item.groups) || item.groups.length === 0) {
      throw new Error(`${item.code} needs at least one section group.`);
    }
    item.groups.forEach((group, groupIndex) => {
      if (!group.type || !Array.isArray(group.sections)) {
        throw new Error(`${item.code} group ${groupIndex + 1} needs type and sections.`);
      }
    });
  });
  return candidate as Course[];
}

async function apiRequest<T>(path: string, body: object): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
  } catch {
    throw new Error(
      `Backend unavailable at ${apiBaseUrl}. Start the FastAPI service and try again.`
    );
  }
  const payload = (await response.json().catch(() => ({}))) as {
    error?: { message?: string };
    detail?: string | Array<{ loc?: Array<string | number>; msg?: string }>;
  } & T;
  if (!response.ok) {
    const validationDetails = Array.isArray(payload.detail)
      ? payload.detail.map((item) => `${item.loc?.slice(1).join(".") || "request"}: ${item.msg || "invalid value"}`).join("; ")
      : payload.detail;
    throw new Error(
      payload.error?.message || validationDetails || `Request failed with status ${response.status}.`
    );
  }
  return payload;
}

function TopBar() {
  const [backendState, setBackendState] = useState<BackendState>("checking");

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${apiBaseUrl}/health`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error("Health check failed");
        const body = (await response.json()) as { status?: string };
        if (body.status !== "ok") throw new Error("Unexpected health response");
        setBackendState("online");
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setBackendState("unavailable");
      });
    return () => controller.abort();
  }, []);

  const label = {
    checking: "Checking backend",
    online: "Backend online",
    unavailable: "Backend unavailable"
  }[backendState];

  return (
    <header className="top-bar">
      <div className="brand">
        <CalendarDays size={23} aria-hidden="true" />
        <h1>Calendar Agent</h1>
      </div>
      <div className={`backend-status ${backendState}`} role="status" aria-live="polite">
        <span aria-hidden="true" />
        {label}
      </div>
    </header>
  );
}

function Workflow({ stage }: { stage: Stage }) {
  const current = stage === "input" ? 1 : stage === "review" ? 2 : 3;
  return (
    <ol className="workflow" aria-label="Schedule planning progress">
      {["Course data", "Confirm preferences", "Schedule options"].map((label, index) => (
        <li className={current >= index + 1 ? "active" : ""} key={label}>
          <span>{current > index + 1 ? <Check size={14} /> : index + 1}</span>
          {label}
          {index < 2 && <ChevronRight size={15} aria-hidden="true" />}
        </li>
      ))}
    </ol>
  );
}

function CourseSummary({ courses }: { courses: Course[] }) {
  return (
    <section className="course-summary" aria-label="Parsed course structure">
      <div className="summary-heading">
        <CheckCircle2 size={18} />
        <strong>{courses.length} {courses.length === 1 ? "course" : "courses"} parsed</strong>
      </div>
      <div className="summary-grid">
        {courses.map((course) => (
          <article className="course-summary-row" key={course.code}>
            <div>
              <strong>{course.code}</strong>
              <span>{course.title || "Untitled course"}</span>
            </div>
            <div className="group-tags">
              {course.groups.map((group, index) => (
                <span className={group.sections.length === 0 ? "empty" : ""} key={`${group.type}-${index}`}>
                  {group.type} · choose {group.choose ?? 1} · {group.sections.length}{" "}
                  {group.sections.length === 1 ? "section" : "sections"}
                </span>
              ))}
            </div>
          </article>
        ))}
      </div>
      {courses.some((course) => course.groups.some((group) => group.sections.length === 0)) && (
        <p className="empty-group-note">
          Declared empty groups remain required and will produce no legal schedules.
        </p>
      )}
    </section>
  );
}

type InputViewProps = {
  courseJson: string;
  courses: Course[];
  preferenceText: string;
  parseError: string;
  requestError: string;
  loading: boolean;
  onCourseJsonChange: (value: string) => void;
  onParseCourses: () => void;
  onLoadSample: () => void;
  onPreferenceChange: (value: string) => void;
  onInterpret: () => void;
};

function InputView(props: InputViewProps) {
  return (
    <main className="input-layout">
      <section className="panel course-input-panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">Step 1</span>
            <h2>Course sections</h2>
          </div>
          <button className="secondary-button" type="button" onClick={props.onLoadSample}>
            <RotateCcw size={16} /> Load sample data
          </button>
        </div>

        <label className="field-label" htmlFor="course-json">
          Course JSON
        </label>
        <textarea
          id="course-json"
          className="json-editor"
          value={props.courseJson}
          onChange={(event) => props.onCourseJsonChange(event.target.value)}
          spellCheck={false}
        />
        <div className="format-note">
          <FileJson size={17} />
          <p>
            Each course defines its own groups. Lecture-only courses are valid; quiz or lab groups are
            processed only when present. An existing group with zero sections produces no legal schedule.
          </p>
        </div>
        {props.parseError && (
          <div className="error-message" role="alert">
            <AlertCircle size={17} /> {props.parseError}
          </div>
        )}
        <button className="parse-button" type="button" onClick={props.onParseCourses}>
          <ClipboardPaste size={17} /> Parse course data
        </button>
        {props.courses.length > 0 && <CourseSummary courses={props.courses} />}
      </section>

      <aside className="panel preference-input-panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">Step 2</span>
            <h2>Schedule preferences</h2>
          </div>
          <Bot size={22} aria-hidden="true" />
        </div>
        <label className="field-label" htmlFor="preference-text">
          Describe your ideal schedule
        </label>
        <textarea
          id="preference-text"
          className="preference-editor"
          value={props.preferenceText}
          onChange={(event) => props.onPreferenceChange(event.target.value)}
          placeholder="Example: No classes before 10:00, prefer Friday off, and require CSE 373 A."
        />
        <p className="field-help">
          English and Chinese are supported. Leave this blank to use open sections with no additional preferences.
        </p>
        <div className="preference-examples">
          <span>Later starts</span>
          <span>Compact days</span>
          <span>Fixed sections</span>
          <span>Days off</span>
        </div>
        {props.requestError && (
          <div className="error-message" role="alert">
            <AlertCircle size={17} /> {props.requestError}
          </div>
        )}
        <div className="preference-spacer" />
        <button
          className="primary-button"
          type="button"
          disabled={!props.courses.length || props.loading}
          onClick={props.onInterpret}
        >
          {props.loading ? <LoaderCircle className="spin" size={19} /> : <Sparkles size={19} />}
          {props.loading ? "Interpreting preferences" : "Interpret preferences"}
          {!props.loading && <ArrowRight size={19} />}
        </button>
      </aside>
    </main>
  );
}

function PreferenceList({ title, items, empty }: { title: string; items: string[]; empty: string }) {
  return (
    <div className="preference-list">
      <h3>{title}</h3>
      {items.length ? (
        <ul>
          {items.map((item) => (
            <li key={item}>
              <CheckCircle2 size={16} /> {item}
            </li>
          ))}
        </ul>
      ) : (
        <p>{empty}</p>
      )}
    </div>
  );
}

function ReviewView({
  preferences,
  loading,
  error,
  onBack,
  onGenerate
}: {
  preferences: ParsedPreferences;
  loading: boolean;
  error: string;
  onBack: () => void;
  onGenerate: () => void;
}) {
  const hardItems = [
    ...preferences.fixedSections.map((item) => `Required section: ${item}`),
    ...preferences.requiredDaysOff.map((day) => `${dayLabels[day]} must remain free`),
    ...(preferences.earliestStartIsHard && preferences.earliestStart
      ? [`No classes before ${preferences.earliestStart}`]
      : []),
    ...(preferences.requireOpenSections ? ["Open sections only"] : []),
    ...preferences.hardConstraints
  ];
  const softItems = [
    ...preferences.preferredDaysOff.map((day) => `Prefer ${dayLabels[day]} off`),
    ...(preferences.preferredTimeOfDay !== "none"
      ? [`Prefer ${preferences.preferredTimeOfDay} classes`]
      : []),
    ...(preferences.gapPreference !== "none"
      ? [`Gap preference: ${preferences.gapPreference}`]
      : []),
    ...(!preferences.earliestStartIsHard && preferences.earliestStart
      ? [`Prefer classes at or after ${preferences.earliestStart}`]
      : []),
    ...preferences.softPreferences
  ];

  return (
    <main className="review-layout">
      <button className="back-button" type="button" onClick={onBack}>
        <ArrowLeft size={18} /> Edit input
      </button>
      <section className="panel review-card">
        <div className="review-title">
          <span className="review-icon"><Bot size={24} /></span>
          <div>
            <span className="eyebrow">AI interpretation</span>
            <h2>Confirm your schedule requirements</h2>
          </div>
        </div>
        <div className="review-grid">
          <PreferenceList title="Hard constraints" items={hardItems} empty="No hard constraints" />
          <PreferenceList title="Soft preferences" items={softItems} empty="No soft preferences" />
        </div>
        {preferences.needsClarification && (
          <div className="clarification-box" role="alert">
            <strong>Clarification needed</strong>
            {preferences.clarificationQuestions.map((question) => <p key={question}>{question}</p>)}
          </div>
        )}
        {preferences.conflicts.length > 0 && (
          <div className="conflict-box" role="alert">
            <strong>Hard-constraint conflicts</strong>
            <ul>{preferences.conflicts.map((conflict) => <li key={conflict}>{conflict}</li>)}</ul>
            <p>Revise the preference text before generating a schedule.</p>
          </div>
        )}
        {error && <div className="error-message" role="alert"><AlertCircle size={17} /> {error}</div>}
        <div className="review-actions">
          <button className="secondary-button" type="button" onClick={onBack}>Revise preferences</button>
          <button
            className="primary-button compact"
            type="button"
            disabled={preferences.needsClarification || preferences.conflicts.length > 0 || loading}
            onClick={onGenerate}
          >
            {loading ? <LoaderCircle className="spin" size={19} /> : <Sparkles size={19} />}
            {loading ? "Generating schedules" : "Confirm and generate"}
          </button>
        </div>
      </section>
    </main>
  );
}

function toMinutes(value: string) {
  const [hour, minute] = value.split(":").map(Number);
  return hour * 60 + minute;
}

function Calendar({ schedule }: { schedule: RankedSchedule }) {
  const startMinute = 8 * 60;
  const endMinute = 18 * 60;
  const hours = Array.from({ length: 11 }, (_, index) => index + 8);
  const courseColors = new Map<string, string>();
  schedule.sections.forEach((section) => {
    if (!courseColors.has(section.courseCode)) {
      courseColors.set(section.courseCode, palette[courseColors.size % palette.length]);
    }
  });
  const events = schedule.sections.flatMap((section) =>
    section.meetings.flatMap((meeting) =>
      meeting.days.map((day) => ({ section, meeting, day }))
    )
  );

  return (
    <div className="calendar" aria-label="Weekly schedule">
      <div className="calendar-header"><span />{days.map((day) => <strong key={day}>{dayLabels[day]}</strong>)}</div>
      <div className="calendar-content">
        <div className="time-axis">{hours.map((hour) => <span key={hour}>{hour <= 12 ? hour : hour - 12} {hour < 12 ? "AM" : "PM"}</span>)}</div>
        <div className="calendar-days">
          {days.map((day) => <div className="day-column" key={day} />)}
          <div className="time-lines">{hours.map((hour) => <span key={hour} />)}</div>
          {events.map(({ section, meeting, day }, index) => {
            const style = {
              "--day": days.indexOf(day),
              "--top": `${((toMinutes(meeting.startTime) - startMinute) / (endMinute - startMinute)) * 100}%`,
              "--height": `${((toMinutes(meeting.endTime) - toMinutes(meeting.startTime)) / (endMinute - startMinute)) * 100}%`
            } as CSSProperties;
            return (
              <article className={`calendar-event ${courseColors.get(section.courseCode)}`} style={style} key={`${section.courseCode}-${section.sectionId}-${day}-${index}`}>
                <strong>{section.courseCode} {section.sectionId}</strong>
                <span>{meeting.startTime} - {meeting.endTime}</span>
                {meeting.location && <span>{meeting.location}</span>}
              </article>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function ResultsView({ response, onBack }: { response: GenerateResponse; onBack: () => void }) {
  const [selectedRank, setSelectedRank] = useState(response.schedules[0]?.rank ?? 0);
  const selected = response.schedules.find((item) => item.rank === selectedRank);
  return (
    <main className="results-layout">
      <aside className="results-sidebar">
        <button className="back-button" type="button" onClick={onBack}><ArrowLeft size={18} /> Edit courses &amp; preferences</button>
        <div className="results-heading"><h2>Schedule options</h2><p>{response.count} ranked schedules</p></div>
        {response.schedules.map((schedule) => (
          <button className={`schedule-card ${selectedRank === schedule.rank ? "selected" : ""}`} type="button" key={schedule.rank} onClick={() => setSelectedRank(schedule.rank)}>
            <div className="schedule-card-heading"><h3>Option {schedule.rank}</h3><strong>{schedule.score}</strong></div>
            <span className="score-label">Score</span>
            <p>{schedule.reasons[0] || "Conflict-free schedule"}</p>
          </button>
        ))}
        {!response.schedules.length && <div className="empty-state"><AlertCircle size={22} /><h3>No legal schedules</h3><ul>{response.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></div>}
      </aside>
      <section className="schedule-detail">
        {selected ? (
          <>
            <div className="detail-heading"><div><span className="eyebrow">Option {selected.rank}</span><h2>Weekly schedule</h2></div><div className="large-score"><span>Score</span><strong>{selected.score}</strong></div></div>
            <Calendar schedule={selected} />
            <div className="insight-grid">
              <section className="panel insight-panel"><h3>Why this works</h3><ul>{selected.reasons.map((reason) => <li key={reason}><CheckCircle2 size={16} />{reason}</li>)}</ul></section>
              <section className="panel insight-panel tradeoffs"><h3>Trade-offs</h3>{selected.tradeoffs.length ? <ul>{selected.tradeoffs.map((tradeoff) => <li key={tradeoff}><AlertCircle size={16} />{tradeoff}</li>)}</ul> : <p>No preference trade-offs.</p>}</section>
              <section className="panel score-panel"><h3>Score breakdown</h3>{Object.entries(selected.scoreBreakdown).map(([rule, item]) => <div className="score-row" key={rule}><div><strong>{rule.replace(/([A-Z])/g, " $1")}</strong><span>{item.details}</span>{item.matchedPreference && <small>Matched: {item.matchedPreference} · Delta: {item.scoreDelta}</small>}</div><b>{item.score}/{item.maximum}</b></div>)}</section>
            </div>
          </>
        ) : <div className="empty-detail"><CalendarDays size={34} /><h3>No schedule can satisfy the current input</h3><p>Return to the input screen to revise fixed sections, availability rules, meeting times, or empty section groups.</p></div>}
      </section>
    </main>
  );
}

function App() {
  const [stage, setStage] = useState<Stage>("input");
  const [courseJson, setCourseJson] = useState(sampleJson);
  const [courses, setCourses] = useState<Course[]>([]);
  const [preferenceText, setPreferenceText] = useState(
    "No classes before 10:00 if possible, prefer Friday off, and use open sections only."
  );
  const [preferences, setPreferences] = useState<ParsedPreferences | null>(null);
  const [response, setResponse] = useState<GenerateResponse | null>(null);
  const [parseError, setParseError] = useState("");
  const [requestError, setRequestError] = useState("");
  const [loading, setLoading] = useState(false);

  const canOpenResults = useMemo(() => response !== null, [response]);

  const parseCourses = () => {
    try {
      const parsed = validateCourses(JSON.parse(courseJson));
      setCourses(parsed);
      setParseError("");
      setResponse(null);
    } catch (error) {
      setCourses([]);
      setParseError(error instanceof SyntaxError ? `JSON parse error: ${error.message}` : error instanceof Error ? error.message : "Invalid course data.");
    }
  };

  const loadSample = () => {
    setCourseJson(sampleJson);
    setCourses(sampleCourses);
    setParseError("");
    setResponse(null);
  };

  const interpretPreferences = async () => {
    if (!courses.length) {
      setRequestError("Parse or load course data before continuing.");
      return;
    }
    if (!preferenceText.trim()) {
      setPreferences(defaultPreferences);
      setRequestError("");
      setStage("review");
      return;
    }
    setLoading(true);
    setRequestError("");
    try {
      const parsed = await apiRequest<ParsedPreferences>("/parse-preferences", {
        courses,
        preferenceText
      });
      setPreferences(parsed);
      setStage("review");
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : "Could not interpret preferences.");
    } finally {
      setLoading(false);
    }
  };

  const generateSchedules = async () => {
    if (!preferences) return;
    setLoading(true);
    setRequestError("");
    try {
      const generated = await apiRequest<GenerateResponse>("/api/schedules/generate", {
        courses,
        preferences,
        topN: 5,
        enhanceReasons: true
      });
      setResponse(generated);
      setStage("results");
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : "Could not generate schedules.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <TopBar />
      <div className="subnav">
        <button className={stage !== "results" ? "active" : ""} type="button" onClick={() => setStage("input")}>Courses &amp; Preferences</button>
        <button className={stage === "results" ? "active" : ""} type="button" disabled={!canOpenResults} onClick={() => setStage("results")}>Schedule Options</button>
        <Workflow stage={stage} />
      </div>
      {stage === "input" && <InputView courseJson={courseJson} courses={courses} preferenceText={preferenceText} parseError={parseError} requestError={requestError} loading={loading} onCourseJsonChange={setCourseJson} onParseCourses={parseCourses} onLoadSample={loadSample} onPreferenceChange={setPreferenceText} onInterpret={interpretPreferences} />}
      {stage === "review" && preferences && <ReviewView preferences={preferences} loading={loading} error={requestError} onBack={() => setStage("input")} onGenerate={generateSchedules} />}
      {stage === "results" && response && <ResultsView response={response} onBack={() => setStage("input")} />}
    </div>
  );
}

export default App;
