from collections import Counter
from typing import Any


def _safe_get(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        if key in row and row[key] is not None:
            return str(row[key]).strip()
    return ""


def filter_rows(rows: list[dict[str, Any]], section: str | None = None, course: str | None = None) -> list[dict[str, Any]]:
    filtered = rows

    if section:
        filtered = [
            row
            for row in filtered
            if _safe_get(row, "Section", "section").lower() == str(section).strip().lower()
        ]

    if course:
        c = str(course).strip().lower()
        filtered = [
            row
            for row in filtered
            if c in _safe_get(row, "Skill", "skill", "Allocated Course", "allocated_course", "G1 Course", "g1_course").lower()
            or c in _safe_get(row, "G2 Course", "g2_course").lower()
        ]

    return filtered


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    section_counter = Counter()
    course_counter = Counter()

    for row in rows:
        section = _safe_get(row, "Section", "section", "pair_label")
        if section:
            section_counter[section] += 1

        course = _safe_get(row, "Skill", "Allocated Course", "G1 Course", "allocated_course", "g1_course")
        if course:
            course_counter[course] += 1

    return {
        "totalStudents": len(rows),
        "topSections": section_counter.most_common(5),
        "topCourses": course_counter.most_common(5),
    }
