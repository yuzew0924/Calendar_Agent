import {
  ArrowLeft,
  ArrowRight,
  Bot,
  CalendarDays,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  CirclePlus,
  Info,
  Menu,
  Plus,
  SendHorizontal,
  Star,
  User
} from "lucide-react";
import { useEffect, useState, type CSSProperties } from "react";

type ViewMode = "edit" | "options";
type EventTone = "purple" | "green" | "blue" | "orange";
type BackendState = "checking" | "online" | "unavailable";

type CalendarEvent = {
  course: string;
  section: string;
  time: string;
  room: string;
  day: number;
  start: number;
  end: number;
  tone: EventTone;
};

const courseTabs = ["MATH 208", "CSE 414", "INFO 370", "CSE 332"];
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;

const lectureGroups = [
  {
    name: "Lecture A",
    time: "MWF 12:30 - 1:20 PM",
    status: "Open",
    quizzes: [
      { id: "AA", time: "Thu 12:30 - 1:20 PM", status: "Closed" },
      { id: "AB", time: "Thu 1:30 - 2:20 PM", status: "Closed" },
      { id: "AC", time: "Thu 2:30 - 3:20 PM", status: "Closed" },
      { id: "AD", time: "Thu 3:30 - 4:20 PM", status: "Open" },
      { id: "AE", time: "Thu 11:30 AM - 12:20 PM", status: "Closed" },
      { id: "AF", time: "Thu 12:30 - 1:20 PM", status: "Open" }
    ]
  },
  {
    name: "Lecture B",
    time: "MWF 3:30 - 4:20 PM",
    status: "Open",
    quizzes: [
      { id: "BA", time: "Thu 1:30 - 2:20 PM", status: "Open" },
      { id: "BB", time: "Thu 2:30 - 3:20 PM", status: "Open" },
      { id: "BC", time: "Thu 3:30 - 4:20 PM", status: "Open" }
    ]
  }
];

const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
const hours = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17];

const calendarEvents: CalendarEvent[] = [
  {
    course: "CSE 414",
    section: "A",
    time: "9:30 - 10:45",
    room: "EECS 101",
    day: 0,
    start: 570,
    end: 645,
    tone: "purple"
  },
  {
    course: "CSE 414",
    section: "A",
    time: "9:30 - 10:45",
    room: "EECS 101",
    day: 2,
    start: 570,
    end: 645,
    tone: "purple"
  },
  {
    course: "CSE 414",
    section: "A",
    time: "9:30 - 10:45",
    room: "EECS 101",
    day: 4,
    start: 570,
    end: 645,
    tone: "purple"
  },
  {
    course: "MATH 208",
    section: "A",
    time: "10:30 - 11:20",
    room: "MCB 247",
    day: 0,
    start: 630,
    end: 680,
    tone: "green"
  },
  {
    course: "MATH 208",
    section: "A",
    time: "10:30 - 11:20",
    room: "MCB 247",
    day: 2,
    start: 630,
    end: 680,
    tone: "green"
  },
  {
    course: "MATH 208",
    section: "A",
    time: "10:30 - 11:20",
    room: "MCB 247",
    day: 4,
    start: 630,
    end: 680,
    tone: "green"
  },
  {
    course: "INFO 370",
    section: "B",
    time: "11:00 - 12:15",
    room: "DOW 233",
    day: 0,
    start: 660,
    end: 735,
    tone: "blue"
  },
  {
    course: "INFO 370",
    section: "B",
    time: "11:00 - 12:15",
    room: "DOW 233",
    day: 2,
    start: 660,
    end: 735,
    tone: "blue"
  },
  {
    course: "CSE 332",
    section: "A",
    time: "11:00 - 12:15",
    room: "ENG 103",
    day: 1,
    start: 660,
    end: 735,
    tone: "orange"
  },
  {
    course: "CSE 332",
    section: "A",
    time: "11:00 - 12:15",
    room: "ENG 103",
    day: 3,
    start: 660,
    end: 735,
    tone: "orange"
  },
  {
    course: "MATH 208",
    section: "QA",
    time: "1:00 - 1:50",
    room: "MCB 315",
    day: 1,
    start: 780,
    end: 830,
    tone: "green"
  },
  {
    course: "INFO 370",
    section: "QC",
    time: "1:00 - 1:50",
    room: "DOW 233",
    day: 4,
    start: 780,
    end: 830,
    tone: "blue"
  },
  {
    course: "CSE 414",
    section: "QD",
    time: "2:00 - 2:50",
    room: "EECS 201",
    day: 3,
    start: 840,
    end: 890,
    tone: "purple"
  },
  {
    course: "CSE 332",
    section: "QB",
    time: "3:00 - 3:50",
    room: "ENG 205",
    day: 2,
    start: 900,
    end: 950,
    tone: "orange"
  }
];

const rankedSchedules = [
  {
    title: "Option 1",
    score: 94,
    badge: "Recommended",
    penalty: false,
    reasons: ["No conflicts", "Short gaps", "Starts after 9:30"]
  },
  {
    title: "Option 2",
    score: 91,
    penalty: false,
    reasons: ["No conflicts", "Short gaps", "Starts after 9:30"]
  },
  {
    title: "Option 3",
    score: 86,
    penalty: true,
    reasons: ["No conflicts", "One longer gap", "Starts after 9:30"]
  }
];

const formatHour = (hour: number) => {
  if (hour < 12) return `${hour} AM`;
  if (hour === 12) return "12 PM";
  return `${hour - 12} PM`;
};

const getEventStyle = (event: CalendarEvent) =>
  ({
    "--event-day": event.day + 1,
    "--event-start": `${((event.start - 480) / 600) * 100}%`,
    "--event-height": `${((event.end - event.start) / 600) * 100}%`
  }) as CSSProperties;

function TopBar() {
  const [backendState, setBackendState] = useState<BackendState>("checking");

  useEffect(() => {
    if (!apiBaseUrl) {
      setBackendState("unavailable");
      return;
    }

    const controller = new AbortController();
    const healthUrl = `${apiBaseUrl.replace(/\/$/, "")}/health`;

    fetch(healthUrl, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error("Backend health check failed");

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

  const statusLabel = {
    checking: "Checking backend",
    online: "Backend online",
    unavailable: "Backend unavailable"
  }[backendState];

  return (
    <header className="top-bar">
      <div className="brand">
        <button className="icon-button" type="button" aria-label="Open menu">
          <Menu size={25} />
        </button>
        <div className="brand-mark" aria-hidden="true">
          <CalendarDays size={24} />
        </div>
        <h1>Calendar Agent</h1>
      </div>
      <div className={`backend-status ${backendState}`} role="status" aria-live="polite">
        <span aria-hidden="true" />
        {statusLabel}
      </div>
    </header>
  );
}

function PageTabs({
  activeView,
  onChange
}: {
  activeView: ViewMode;
  onChange: (view: ViewMode) => void;
}) {
  return (
    <nav className="page-tabs" aria-label="Planner sections">
      <button
        className={activeView === "edit" ? "active" : ""}
        type="button"
        onClick={() => onChange("edit")}
      >
        Courses &amp; Preferences
      </button>
      <button
        className={activeView === "options" ? "active" : ""}
        type="button"
        onClick={() => onChange("options")}
      >
        Schedule Options
      </button>
    </nav>
  );
}

function CourseEditor() {
  const [activeCourse, setActiveCourse] = useState("CSE 414");

  return (
    <section className="panel course-editor-card">
      <div className="course-editor-header">
        <h2>Courses</h2>
        <button className="outline-button" type="button">
          <Plus size={18} />
          Add course
        </button>
      </div>

      <div className="course-tabs" role="tablist" aria-label="Courses">
        {courseTabs.map((course) => (
          <button
            className={activeCourse === course ? "active" : ""}
            key={course}
            type="button"
            onClick={() => setActiveCourse(course)}
          >
            {course}
          </button>
        ))}
      </div>

      <div className="course-form-row">
        <div className="course-name-field">
          <label className="field-label" htmlFor="course-name">
            Course name
          </label>
          <input id="course-name" value={activeCourse} readOnly />
        </div>
        <button className="save-button" type="button">
          Save course
        </button>
      </div>

      <h3 className="group-heading">{activeCourse} · Lecture &amp; quiz groups</h3>

      <div className="lecture-list spacious">
        {lectureGroups.map((group) => (
          <article className="lecture-group" key={group.name}>
            <div className="lecture-row">
              <ChevronDown size={17} />
              <span className="section-dot open" />
              <strong>{group.name}</strong>
              <span className="meeting-time">{group.time}</span>
              <span className="pill pill-open">{group.status}</span>
            </div>

            <div className="quiz-list">
              {group.quizzes.map((quiz) => (
                <div className="quiz-row" key={quiz.id}>
                  <span className="quiz-node" />
                  <strong>{quiz.id}</strong>
                  <span className="quiz-type">Quiz</span>
                  <span className="meeting-time">{quiz.time}</span>
                  <span
                    className={`pill ${
                      quiz.status === "Open" ? "pill-open" : "pill-closed"
                    }`}
                  >
                    {quiz.status}
                  </span>
                </div>
              ))}
            </div>
          </article>
        ))}
      </div>

      <button className="secondary-action" type="button">
        <CirclePlus size={18} />
        Add lecture group
      </button>
    </section>
  );
}

function PreferenceChat() {
  return (
    <section className="panel preference-panel">
      <h2>Preference Chat</h2>

      <div className="chat-thread">
        <div className="chat-row user">
          <span className="avatar">
            <User size={23} />
          </span>
          <p>No classes before 9:30, keep Fridays light, and prefer short gaps between classes.</p>
        </div>
        <div className="chat-row assistant">
          <span className="avatar bot-avatar">
            <Bot size={22} />
          </span>
          <p>Got it. I’ll prioritize later starts, fewer Friday classes, and compact schedules.</p>
        </div>
        <div className="chat-row user">
          <span className="avatar">
            <User size={23} />
          </span>
          <p>CSE 332 section A is fixed.</p>
        </div>
        <div className="chat-row assistant">
          <span className="avatar bot-avatar">
            <Bot size={22} />
          </span>
          <p>I’ll keep CSE 332 A in every schedule.</p>
        </div>
      </div>

      <div className="chat-input">
        <input
          aria-label="Describe schedule preferences"
          placeholder="Describe your schedule preferences..."
        />
        <button type="button" aria-label="Send preference">
          <SendHorizontal size={24} />
        </button>
      </div>
    </section>
  );
}

function EditView({ onGenerate }: { onGenerate: () => void }) {
  return (
    <main className="edit-layout">
      <CourseEditor />
      <aside className="preference-column">
        <PreferenceChat />
        <button className="generate-button" type="button" onClick={onGenerate}>
          Generate schedules
          <ArrowRight size={30} />
        </button>
      </aside>
    </main>
  );
}

function CalendarLegend() {
  return (
    <div className="legend" aria-label="Calendar legend">
      <span>
        <i className="legend-open" /> Open
      </span>
      <span>
        <i className="legend-fixed" /> Fixed
      </span>
      <span>
        <i className="legend-conflict" /> Conflict
      </span>
      <span>
        <i className="legend-penalty" /> Preference Penalty
      </span>
    </div>
  );
}

function WeeklyCalendar() {
  return (
    <div className="calendar-grid" aria-label="Weekly schedule">
      <div className="calendar-days">
        <span />
        {days.map((day) => (
          <strong key={day}>{day}</strong>
        ))}
      </div>

      <div className="calendar-body">
        <div className="time-axis">
          {hours.map((hour) => (
            <span key={hour}>{formatHour(hour)}</span>
          ))}
        </div>
        <div className="day-columns">
          {days.map((day) => (
            <div className="day-column" key={day} />
          ))}
          <div className="hour-lines">
            {hours.map((hour) => (
              <span key={hour} />
            ))}
          </div>
          {calendarEvents.map((event) => (
            <article
              className={`calendar-event event-${event.tone}`}
              key={`${event.course}-${event.section}-${event.day}`}
              style={getEventStyle(event)}
            >
              <strong>
                {event.course} {event.section}
              </strong>
              <span>{event.time}</span>
              <span>{event.room}</span>
            </article>
          ))}
        </div>
      </div>
    </div>
  );
}

function ScheduleOptionCard({
  schedule,
  selected,
  onSelect
}: {
  schedule: (typeof rankedSchedules)[number];
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      className={`option-card ${selected ? "selected" : ""}`}
      type="button"
      onClick={onSelect}
    >
      <div className="option-title-row">
        <h3>{schedule.title}</h3>
        {schedule.badge && (
          <span className="recommendation">
            <Star size={15} fill="currentColor" />
            {schedule.badge}
          </span>
        )}
        {selected && <CheckCircle2 className="selected-check" size={27} fill="currentColor" />}
      </div>

      <div className="option-body-row">
        <div>
          <div className="tag-row">
            <span className="pill pill-open">Open</span>
            <span className="pill pill-fixed">Fixed</span>
            <span className={`pill ${schedule.penalty ? "pill-warning" : "pill-open"}`}>
              {schedule.penalty ? "More gaps" : "Low gaps"}
            </span>
          </div>
          <ul className="reason-list">
            {schedule.reasons.map((reason) => (
              <li key={reason}>
                <CheckCircle2 size={16} />
                {reason}
              </li>
            ))}
          </ul>
        </div>
        <div className="score">
          <span>Score</span>
          <strong>{schedule.score}</strong>
        </div>
      </div>
    </button>
  );
}

function OptionsView({ onBack }: { onBack: () => void }) {
  const [selectedOption, setSelectedOption] = useState(0);
  const selectedSchedule = rankedSchedules[selectedOption];

  return (
    <main className="options-layout">
      <aside className="options-sidebar">
        <button className="back-button" type="button" onClick={onBack}>
          <ArrowLeft size={19} />
          Back to edit courses &amp; preferences
        </button>

        <div className="options-heading">
          <h2>Schedule Options</h2>
          <p>10 conflict-free schedules</p>
        </div>

        <div className="option-stack">
          {rankedSchedules.map((schedule, index) => (
            <ScheduleOptionCard
              key={schedule.title}
              schedule={schedule}
              selected={selectedOption === index}
              onSelect={() => setSelectedOption(index)}
            />
          ))}
        </div>

        <div className="pagination">
          <button type="button" aria-label="Previous options">
            <ChevronLeft size={20} />
          </button>
          <span>1–3 of 10</span>
          <button type="button" aria-label="Next options">
            <ChevronRight size={20} />
          </button>
        </div>
      </aside>

      <section className="schedule-detail">
        <div className="schedule-detail-header">
          <h2>
            {selectedSchedule.title} · <span>Weekly Schedule</span>
          </h2>
          <p>
            Score <strong>{selectedSchedule.score}</strong>
          </p>
          <p className="recommended-inline">
            <span /> Recommended
          </p>
        </div>

        <WeeklyCalendar />
        <CalendarLegend />
      </section>
    </main>
  );
}

function App() {
  const [activeView, setActiveView] = useState<ViewMode>("edit");

  return (
    <div className="app">
      <TopBar />
      <PageTabs activeView={activeView} onChange={setActiveView} />
      {activeView === "edit" ? (
        <EditView onGenerate={() => setActiveView("options")} />
      ) : (
        <OptionsView onBack={() => setActiveView("edit")} />
      )}
    </div>
  );
}

export default App;
