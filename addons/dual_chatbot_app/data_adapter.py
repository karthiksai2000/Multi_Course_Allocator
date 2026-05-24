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


def normalize_dual_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for row in rows:
        normalized.append(
            {
                "RegNo": row.get("Registration Number", row.get("registration_number", row.get("RegNo", ""))),
                "Name": row.get("Name", row.get("name", "")),
                "Section": row.get("Pair Label", row.get("pair_label", row.get("Section", ""))),
                "Skill": row.get("Group 1 Course", row.get("g1_course", "")),
                "G2Course": row.get("Group 2 Course", row.get("g2_course", "")),
                "Reason": row.get("Reason", row.get("reason", "")),
            }
        )
    return normalized
