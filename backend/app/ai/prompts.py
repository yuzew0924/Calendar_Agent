from __future__ import annotations

from typing import Any


PREFERENCE_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "earliestStart": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "earliestStartIsHard": {"type": "boolean"},
        "preferredDaysOff": {
            "type": "array",
            "items": {"type": "string", "enum": ["M", "T", "W", "Th", "F"]},
        },
        "requiredDaysOff": {
            "type": "array",
            "items": {"type": "string", "enum": ["M", "T", "W", "Th", "F"]},
        },
        "fixedSections": {"type": "array", "items": {"type": "string"}},
        "requireOpenSections": {"type": "boolean"},
        "hardConstraints": {"type": "array", "items": {"type": "string"}},
        "softPreferences": {"type": "array", "items": {"type": "string"}},
        "conflicts": {"type": "array", "items": {"type": "string"}},
        "needsClarification": {"type": "boolean"},
        "clarificationQuestions": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "earliestStart",
        "earliestStartIsHard",
        "preferredDaysOff",
        "requiredDaysOff",
        "fixedSections",
        "requireOpenSections",
        "hardConstraints",
        "softPreferences",
        "conflicts",
        "needsClarification",
        "clarificationQuestions",
    ],
}


PREFERENCE_PARSER_INSTRUCTIONS = """You convert preferenceText into schedule preference JSON.

Output rules:
- Return exactly one JSON object and nothing else.
- Do not return Markdown, code fences, comments, or natural-language explanation.
- Return every schema field. Do not add fields.
- Use null, false, true, or [] defaults when the user did not specify a value.

Field rules:
- earliestStart: null or a 24-hour HH:MM time such as 09:30.
- earliestStartIsHard: true only when the user clearly says the start limit is mandatory.
- preferredDaysOff: use only M, T, W, Th, or F.
- requiredDaysOff: use only M, T, W, Th, or F, and only for an explicit mandatory day-off requirement.
- fixedSections: use only '<courseCode> <sectionId>' values present in the supplied courses catalog.
- requireOpenSections: true unless the user explicitly permits closed sections.
- hardConstraints: only clear mandatory requirements not already captured by a structured field.
- softPreferences: ambiguous, approximate, or preference language such as 'prefer', 'ideally', or 'try to'.
- conflicts: describe mutually incompatible or contradictory user requirements.
- needsClarification: true when conflicts exist or a necessary meaning cannot be determined safely.
- clarificationQuestions: focused questions needed to resolve those conflicts or uncertainties.

Grounding rules:
- Use only course codes, section IDs, types, statuses, days, and times present in the courses catalog.
- Never invent or normalize an unknown course, section, weekday, or time.
- If a fixed course or section cannot be matched exactly, do not add it to fixedSections; set needsClarification to true and ask a clarification question.
- If wording is vague, preserve it in softPreferences instead of creating a hard constraint.
- If requirements contradict each other, record the contradiction in conflicts, set needsClarification to true, and add at least one clarification question.

Ambiguity examples:
- 'Not too early' is softPreferences only. Keep earliestStart null because no exact time was given.
- 'Prefer Friday off' adds F to preferredDaysOff and remains a soft preference.
- 'Friday must be free' adds F to requiredDaysOff.
- 'I want an easier schedule', 'Try to avoid long gaps', and 'Prefer afternoons free' belong in softPreferences.
- 'Classes must not start before 10:00' sets earliestStart to 10:00 and earliestStartIsHard to true.
- 'Do not start before 10:00' sets earliestStart to 10:00 and earliestStartIsHard to true.
- If a mandatory request is too ambiguous to represent safely, do not invent a value; set needsClarification to true and ask one focused question.
"""
