import {
  Bot,
  CalendarDays,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  CirclePlus,
  History,
  Info,
  Menu,
  MoreHorizontal,
  SendHorizontal,
  Settings,
  Sparkles,
  Star,
  User
} from "lucide-react";
import type { CSSProperties } from "react";

type EventTone = "purple" | "green" | "blue" | "orange";

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

const lectureGroups = [
  {
    name: "Lecture A",
    time: "MWF 12:30 - 1:20 PM",
    status: "Open",
    quizzes: [
      { id: "AA", time: "Thu 12:30 - 1:20 PM", status: "Closed" },
      { id: "AB", time: "Thu 1:30 - 2:20 PM", status: "Closed" },
      { id: "AC", time: "Thu 2:30 - 3:20 PM", status: "Closed" }
    ],
    more: "View 3 more quizzes"
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
const hours = [8, 9, 10, 11, 12, 13, 14, 15, 16];

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
    day: 3,
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
  if (hour < 12) {
    return `${hour} AM`;
  }

  if (hour === 12) {
    return "12 PM";
  }

  return `${hour - 12} PM`;
};

const getEventStyle = (event: CalendarEvent) =>
  ({
    "--event-day": event.day + 1,
    "--event-start": `${((event.start - 480) / 540) * 100}%`,
    "--event-height": `${((event.end - event.start) / 540) * 100}%`
  }) as CSSProperties;

function TopBar() {
  return (
    <header className="top-bar">
      <div className="brand">
        <button className="icon-button" type="button" aria-label="Open menu">
          <Menu size={24} />
        </button>
        <div className="brand-mark" aria-hidden="true">
          <CalendarDays size={22} />
        </div>
        <h1>Calendar Agent</h1>
      </div>

      <nav className="top-actions" aria-label="Application actions">
        <button type="button">
          <CircleHelp size={20} />
          Help
        </button>
        <button type="button">
          <History size={20} />
          History
        </button>
        <button type="button">
          <Settings size={20} />
          Settings
        </button>
      </nav>
    </header>
  );
}

function CourseBuilder() {
  return (
    <aside className="left-panel">
      <section className="card course-card">
        <h2>Add a course</h2>

        <label className="field-label" htmlFor="course-name">
          Course name
        </label>
        <input id="course-name" defaultValue="CSE 414" />

        <p className="field-label">Lecture &amp; quiz groups</p>
        <div className="lecture-list">
          {lectureGroups.map((group) => (
            <article className="lecture-group" key={group.name}>
              <div className="lecture-row">
                <ChevronDown size={16} />
                <span className="section-dot open" />
                <div>
                  <strong>{group.name}</strong>
                  <p>{group.time}</p>
                </div>
                <span className="pill pill-open">{group.status}</span>
              </div>

              <div className="quiz-list">
                {group.quizzes.map((quiz) => (
                  <div className="quiz-row" key={quiz.id}>
                    <span className="quiz-node" />
                    <div>
                      <strong>{quiz.id} · Quiz</strong>
                      <p>{quiz.time}</p>
                    </div>
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

              {group.more && <button className="text-link">{group.more}</button>}
            </article>
          ))}
        </div>

        <button className="secondary-action" type="button">
          <CirclePlus size={18} />
          Add lecture group
        </button>
      </section>

      <section className="card chat-card">
        <h2>Preference Chat</h2>
        <div className="chat-row user">
          <span className="avatar">
            <User size={18} />
          </span>
          <p>No classes before 9:30, keep Fridays light, and prefer short gaps between classes.</p>
        </div>
        <div className="chat-row assistant">
          <span className="avatar bot-avatar">
            <Bot size={18} />
          </span>
          <p>Got it. I’ll prioritize later starts, fewer Friday classes, and compact schedules.</p>
        </div>
        <div className="chat-input">
          <input aria-label="Describe schedule preferences" placeholder="Describe your schedule preferences..." />
          <button type="button" aria-label="Send preference">
            <SendHorizontal size={20} />
          </button>
        </div>
      </section>

      <button className="generate-button" type="button">
        <Sparkles size={24} />
        Generate schedules
      </button>
    </aside>
  );
}

function WeeklyCalendar() {
  return (
    <section className="calendar-section">
      <div className="section-header">
        <h2>Weekly Calendar</h2>
        <div className="calendar-controls">
          <button type="button">Today</button>
          <button type="button" aria-label="Previous week">
            <ChevronLeft size={20} />
          </button>
          <button type="button" aria-label="Next week">
            <ChevronRight size={20} />
          </button>
        </div>
      </div>

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

      <div className="calendar-footer">
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
        <div className="calendar-meta">
          <span>All times shown in local time</span>
          <span>
            Showing 1 of 10 options <Info size={16} />
          </span>
        </div>
      </div>
    </section>
  );
}

function RankedSchedules() {
  return (
    <aside className="right-panel">
      <div className="ranked-heading">
        <h2>Ranked Schedules</h2>
        <Info size={16} />
      </div>

      <div className="schedule-stack">
        {rankedSchedules.map((schedule, index) => (
          <article className={`schedule-card ${index === 0 ? "selected" : ""}`} key={schedule.title}>
            <div className="schedule-title-row">
              <h3>{schedule.title}</h3>
              {schedule.badge && (
                <span className="recommendation">
                  <Star size={15} fill="currentColor" />
                  {schedule.badge}
                </span>
              )}
              <div className="score">
                <span>Score</span>
                <strong>{schedule.score}</strong>
              </div>
            </div>

            <div className="tag-row">
              <span className="pill pill-open">Open</span>
              <span className="pill pill-fixed">Fixed</span>
              <span className={`pill ${schedule.penalty ? "pill-warning" : "pill-open"}`}>
                {schedule.penalty ? "More gaps" : "Low gaps"}
              </span>
            </div>

            <h4>Why this works</h4>
            <ul className="reason-list">
              {schedule.reasons.map((reason) => (
                <li key={reason}>
                  <CheckCircle2 size={16} />
                  {reason}
                </li>
              ))}
            </ul>

            <div className="schedule-actions">
              <button type="button">View in calendar</button>
              <button type="button" aria-label={`${schedule.title} menu`}>
                <MoreHorizontal size={22} />
              </button>
            </div>
          </article>
        ))}
      </div>

      <button className="view-all" type="button">
        View all 10 options
      </button>
    </aside>
  );
}

function App() {
  return (
    <div className="app">
      <TopBar />
      <main className="planner-layout">
        <CourseBuilder />
        <WeeklyCalendar />
        <RankedSchedules />
      </main>
    </div>
  );
}

export default App;
