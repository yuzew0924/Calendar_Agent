# Frontend Workflow

The frontend provides one guided path from raw course data to ranked schedule
options. Users do not need to call backend endpoints manually.

## Main Flow

1. Paste course JSON or select **Load sample data**. Loading the sample fills the
   editor and immediately displays its course summary.
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

## Confirmation and Revision

The interpretation screen separates hard constraints from soft preferences and
shows clarification questions and hard conflicts without reducing them to a
generic warning. **Confirm and generate** is disabled while either condition is
unresolved. **Revise preferences** returns to the input screen with the original
`preferenceText` intact, so the user can edit it and run parsing again.

## Application States

The UI provides feedback for initial input, preference parsing, schedule
generation, successful results, JSON errors, FastAPI validation errors, AI
parsing failures, backend unavailability, and empty schedule results. An empty
result renders every backend diagnostic and a route back to edit the input.

No-result diagnostics distinguish an empty declared group, open-only section
exhaustion, overlapping fixed sections, hard time/day filters, and conflicts
among all remaining combinations.

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

## Preference Input

The preference editor accepts natural-language English and Chinese text. A
nonblank value is sent to `POST /parse-preferences` with the parsed courses. If
the field is blank, the frontend skips the AI call and presents explicit safe
defaults for confirmation: open sections only, with no additional hard or soft
preferences. This keeps the workflow usable without inventing user intent.
