import io
from typing import Any

import pandas as pd


def read_rows(file_name: str, payload: bytes) -> list[dict[str, Any]]:
    lower = file_name.lower()
    if lower.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(payload))
    elif lower.endswith(".xlsx") or lower.endswith(".xls"):
        df = pd.read_excel(io.BytesIO(payload))
    else:
        raise ValueError("Unsupported file format. Use CSV, XLSX, or XLS.")

    return df.fillna("").to_dict(orient="records")


def normalize_dept_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for row in rows:
        normalized.append(
            {
                "RegNo": row.get("Reg No", row.get("RegNo", row.get("reg_no", ""))),
                "Name": row.get("Name", row.get("name", "")),
                "Section": row.get("Section", row.get("section", row.get("allocation_section_display", ""))),
                "Skill": row.get("Allocated Course", row.get("allocated_course", "")),
                "Reason": row.get("Reason", row.get("reason", "")),
            }
        )
    return normalized
