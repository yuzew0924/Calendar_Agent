PREFERENCE_PARSER_INSTRUCTIONS = """You extract schedule preferences into JSON.
Return only one JSON object with exactly these fields:
{
  "earliestStart": "10:00",
  "earliestStartIsHard": false,
  "preferredDaysOff": ["F"],
  "fixedSections": ["CSE 373 A"],
  "requireOpenSections": true,
  "hardConstraints": ["text notes"],
  "softPreferences": ["text notes"]
}
Do not invent fixed sections, course codes, section IDs, days, or times.
Use 24-hour HH:MM times and weekday codes M, T, W, Th, and F.
Free-text notes are metadata and must not replace structured fields.
"""
