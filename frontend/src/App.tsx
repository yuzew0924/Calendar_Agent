const sampleEvents = [
  {
    course: "CSE 414",
    section: "C/CD",
    days: "MWF / Th",
    time: "12:30 PM-1:20 PM / 2:30 PM-3:20 PM"
  },
  {
    course: "CSE 332",
    section: "B/BC",
    days: "MWF / Th",
    time: "3:30 PM-4:20 PM / 3:30 PM-4:20 PM"
  }
];

function App() {
  return (
    <main className="app-shell">
      <section className="intro">
        <div>
          <p className="eyebrow">Schedule planning assistant</p>
          <h1>Calendar Agent</h1>
          <p className="summary">
            React frontend is running. The next milestone is connecting this UI
            to a Python scheduling API that generates ranked weekly calendars.
          </p>
        </div>
        <div className="status-panel" aria-label="Project status">
          <span className="status-dot" />
          <div>
            <strong>Frontend ready</strong>
            <p>Waiting for backend scheduler integration.</p>
          </div>
        </div>
      </section>

      <section className="workspace-grid" aria-label="Planner workspace">
        <div className="panel">
          <div className="panel-heading">
            <span>1</span>
            <h2>Course Input</h2>
          </div>
          <p>
            This area will let users add courses, available sections, fixed
            sections, and registration availability.
          </p>
        </div>

        <div className="panel">
          <div className="panel-heading">
            <span>2</span>
            <h2>Preferences</h2>
          </div>
          <p>
            Preference controls will include earliest start time, allowed gap
            rules, open-only filtering, and compactness scoring.
          </p>
        </div>

        <div className="panel calendar-panel">
          <div className="panel-heading">
            <span>3</span>
            <h2>Calendar Preview</h2>
          </div>
          <div className="calendar-placeholder">
            {sampleEvents.map((event) => (
              <article className="event-card" key={`${event.course}-${event.section}`}>
                <strong>{event.course}</strong>
                <span>{event.section}</span>
                <small>{event.days}</small>
                <small>{event.time}</small>
              </article>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}

export default App;
