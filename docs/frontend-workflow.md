# Frontend Workflow

The frontend provides one guided path from raw course data to ranked schedule
options. Users do not need to call backend endpoints manually.

## Main Flow

1. Paste course JSON or load the built-in sample.
2. Parse the data and review the course count and declared section groups.
3. Enter schedule preferences in natural language.
4. Send the preferences to `POST /parse-preferences`.
5. Review the validated hard constraints, soft preferences, conflicts, and any
   clarification questions returned by the backend.
6. Confirm the interpretation or return to edit the preference text.
7. Send the confirmed request to `POST /api/schedules/generate`.
8. Review the ranked, conflict-free schedule candidates.
9. Switch between candidates and compare their weekly calendars.
10. Inspect each option's score, reasons, trade-offs, and score breakdown.

## Course Input Rules

The MVP accepts either a JSON array of courses or an object containing a
`courses` array. The frontend summarizes each course's actual groups after a
successful parse.

- A lecture-only course is valid.
- Quiz and lab groups are processed only when they appear in the input.
- The frontend never invents a missing component.
- A declared group with an empty `sections` array remains required. It is shown
  in the summary and will cause the scheduler to return no legal combinations.
- Malformed JSON and missing structural fields are shown as input errors before
  an API request is made.

The backend Pydantic models remain the authority for complete schema validation.
