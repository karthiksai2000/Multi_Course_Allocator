from pathlib import Path
import sys
from typing import Any

from fastapi import FastAPI, File, Form, UploadFile
from pydantic import BaseModel

CURRENT_DIR = Path(__file__).resolve().parent
ADDONS_ROOT = CURRENT_DIR.parent
sys.path.insert(0, str(ADDONS_ROOT))

from chatbot_common import filter_rows, infer_intent, summarize_rows, table_response, text_response
from lifeskill_chatbot_service.data_adapter import build_previous_elective_map, read_rows_from_upload


class QueryPayload(BaseModel):
    question: str


class ChatbotStore:
    def __init__(self) -> None:
        self.student_rows: list[dict[str, Any]] = []
        self.unallocated_rows: list[dict[str, Any]] = []
        self.previous_elective_map: dict[str, str] = {}


store = ChatbotStore()

app = FastAPI(title="Life Skill Chatbot Sidecar")

LIFESKILL_GUIDELINES = [
    "Upload the latest Excel data in the Life Skill allocator.",
    "Review skills, sections, and slot mapping.",
    "Click Run Allocation to generate student-wise results.",
    "Export student-wise output and load it in this chatbot sidecar.",
]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chatbot/load-results")
async def load_results(dataset_type: str = Form(...), file: UploadFile = File(...)) -> dict[str, Any]:
    payload = await file.read()
    rows = read_rows_from_upload(file.filename or "data.json", payload)

    if dataset_type == "studentwise":
        store.student_rows = rows
    elif dataset_type == "unallocated":
        store.unallocated_rows = rows
    elif dataset_type == "previous-elective":
        store.previous_elective_map = build_previous_elective_map(rows)
    else:
        return {"ok": False, "message": "dataset_type must be studentwise, unallocated, or previous-elective"}

    return {"ok": True, "datasetType": dataset_type, "rowsLoaded": len(rows)}


@app.post("/chatbot/query")
def chatbot_query(payload: QueryPayload) -> dict[str, Any]:
    if not store.student_rows:
        return text_response(
            title="Allocation data not loaded",
            message="Please run the allocation first and then load student-wise results in the chatbot.",
            guidelines=LIFESKILL_GUIDELINES,
            source_module="lifeskill",
        )

    known_courses = sorted({str(row.get("Skill", "")).strip() for row in store.student_rows if str(row.get("Skill", "")).strip()})
    parsed = infer_intent(payload.question, known_courses=known_courses)

    if parsed.wants_guidelines:
        return text_response(
            title="Life Skill allocation checklist",
            message="Follow these steps to get accurate chatbot answers.",
            guidelines=LIFESKILL_GUIDELINES,
            source_module="lifeskill",
        )

    if parsed.intent == "unallocated":
        if not store.unallocated_rows:
            return text_response(
                title="No unallocated dataset loaded",
                message="Load unallocated output file to query unallocated reasons.",
                source_module="lifeskill",
            )
        return table_response(
            title="Unallocated students",
            rows=store.unallocated_rows[:200],
            message=f"Showing {min(200, len(store.unallocated_rows))} rows.",
            source_module="lifeskill",
        )

    if parsed.intent == "summary":
        summary = summarize_rows(store.student_rows)
        return {
            "type": "summary",
            "title": "Allocation summary",
            "sourceModule": "lifeskill",
            "summary": summary,
        }

    filtered = filter_rows(store.student_rows, section=parsed.section, course=parsed.course)

    response_rows = []
    for row in filtered[:200]:
        reg = str(row.get("RegNo", row.get("reg_no", ""))).strip().upper()
        out = {
            "RegNo": row.get("RegNo", row.get("reg_no", "")),
            "Name": row.get("Name", row.get("name", "")),
            "Section": row.get("Section", row.get("section", "")),
            "Skill": row.get("Skill", row.get("skill", "")),
            "Slot": row.get("Slot", row.get("slot", "")),
        }
        if parsed.wants_previous_elective:
            out["PreviousDeptElective"] = store.previous_elective_map.get(reg, "Not available in loaded files")
        response_rows.append(out)

    if not response_rows:
        return text_response(
            title="No matching rows",
            message="I could not find matching students for the given section/course filters.",
            source_module="lifeskill",
        )

    return table_response(
        title="Filtered students",
        rows=response_rows,
        message=f"Matched {len(filtered)} students. Showing up to 200 rows.",
        source_module="lifeskill",
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8010, reload=True)
