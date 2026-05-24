# Life Skill Chatbot Sidecar

This is an add-on FastAPI service that does not change existing Life Skill backend code.

## Start

```powershell
cd addons/lifeskill_chatbot_service
pip install -r requirements.txt
python main.py
```

Runs on port 8010 by default.

## Load data

Use POST /chatbot/load-results with multipart form:
- dataset_type=studentwise with student-wise result file (json/csv/xlsx)
- dataset_type=unallocated with unallocated file (optional)
- dataset_type=previous-elective with source file containing RegNo + completed/elective column (optional)

## Ask questions

POST /chatbot/query

```json
{
  "question": "Give me the list of the students in the ML course section 2 with their previous dept elective"
}
```

If no allocation data is loaded, it returns: please run allocation first + guidelines.
