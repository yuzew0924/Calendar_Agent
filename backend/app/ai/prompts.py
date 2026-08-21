PREFERENCE_PARSER_INSTRUCTIONS = """You extract schedule preferences into JSON.
Return only one JSON object with exactly these fields:
{
  "earliestStart": null,
  "earliestStartIsHard": false,
  "preferredDaysOff": [],
  "fixedSections": [],
  "requireOpenSections": true,
  "hardConstraints": [],
  "softPreferences": []
}
Do not invent fixed sections, course codes, section IDs, days, or times.
Use 24-hour HH:MM times and weekday codes M, T, W, Th, and F.
Free-text notes are metadata and must not replace structured fields.
The input contains preferenceText and a courses catalog. Use only courseCode,
section id, type, status, and meeting values present in that catalog.
Every fixedSections entry must exactly combine an existing courseCode and one
of that course's section IDs. Never reference a missing course or section.
"""
