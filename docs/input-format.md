# Input Format

## Course Data

Course data should be represented as JSON so it can come from manual entry, OCR, or a scraped course page.

```json
{
  "courses": [],
  "preferences": {}
}
```

## Required Course Fields

```json
{
  "code": "CSE 332",
  "title": "Data Structures and Parallelism",
  "groups": []
}
```

## Section Group

Use a group when the course requires choosing one item from a set, such as one lecture and one quiz.

```json
{
  "type": "quiz",
  "choose": 1,
  "sections": []
}
```

## Section

```json
{
  "id": "BC",
  "status": "open",
  "sln": "13138",
  "meetings": [
    {
      "days": ["Th"],
      "start": "15:30",
      "end": "16:20",
      "location": "KNE 110"
    }
  ]
}
```

## Preference Data

```json
{
  "earliestStart": "09:30",
  "allowEarlierIfOnlyOption": true,
  "allowedGapMinutes": [10],
  "minimumLongGapMinutes": 120,
  "requireOpenSections": true,
  "fixedSections": ["MATH 208 A", "CSE 414 C", "CSE 414 CD"]
}
```

## Day Codes

Use these weekday codes:

- `M`
- `T`
- `W`
- `Th`
- `F`

Weekend support can be added later if needed.
