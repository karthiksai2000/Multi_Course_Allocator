import io
import json
from typing import Any

import pandas as pd


def _rows_from_dataframe(df: pd.DataFrame) -> list[dict[str, Any]]:
    clean = df.copy()
    clean = clean.fillna("")
    return clean.to_dict(orient="records")


def read_rows_from_upload(file_name: str, payload: bytes) -> list[dict[str, Any]]:
    lower = file_name.lower()

    if lower.endswith(".json"):
        data = json.loads(payload.decode("utf-8"))
        if isinstance(data, dict):
            if "studentWise" in data and isinstance(data["studentWise"], list):
                return [dict(item) for item in data["studentWise"]]
            if "rows" in data and isinstance(data["rows"], list):
                return [dict(item) for item in data["rows"]]
            return [data]
        if isinstance(data, list):
            return [dict(item) if isinstance(item, dict) else {"value": item} for item in data]
        return []

    if lower.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(payload))
        return _rows_from_dataframe(df)

    if lower.endswith(".xlsx") or lower.endswith(".xls"):
        df = pd.read_excel(io.BytesIO(payload))
        return _rows_from_dataframe(df)

    raise ValueError("Unsupported file format. Use JSON, CSV, XLSX, or XLS.")


def build_previous_elective_map(rows: list[dict[str, Any]]) -> dict[str, str]:
    reg_keys = ["RegNo", "reg_no", "registration", "Registration Number", "Register Number", "Reg No"]
    elective_keys = [
        "PreviousDeptElective",
        "previous_dept_elective",
        "Previous Elective",
        "Completed Courses",
        "completed_courses",
    ]

    mapping: dict[str, str] = {}

    for row in rows:
        reg_val = ""
        for key in reg_keys:
            if key in row and str(row[key]).strip():
                reg_val = str(row[key]).strip().upper()
                break

        if not reg_val:
            continue

        elective_val = ""
        for key in elective_keys:
            if key in row and str(row[key]).strip():
                elective_val = str(row[key]).strip()
                break

        if elective_val:
            mapping[reg_val] = elective_val

    return mapping
