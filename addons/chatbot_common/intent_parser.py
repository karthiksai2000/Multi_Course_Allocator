import re
from dataclasses import dataclass
from typing import Iterable


@dataclass
class ParsedIntent:
    raw_question: str
    intent: str
    section: str | None
    course: str | None
    wants_previous_elective: bool
    wants_guidelines: bool


SECTION_PATTERNS = [
    re.compile(r"\bsection\s*(\d+)\b", re.IGNORECASE),
    re.compile(r"\bsec\s*(\d+)\b", re.IGNORECASE),
]

COURSE_PATTERNS = [
    re.compile(r"\bin\s+the\s+([a-z0-9 _\-]+?)\s+course\b", re.IGNORECASE),
    re.compile(r"\bcourse\s+([a-z0-9 _\-]+)\b", re.IGNORECASE),
]


def _normalize_phrase(text: str) -> str:
    lowered = text.strip().lower()
    lowered = re.sub(r"\s+", " ", lowered)
    lowered = lowered.replace("machine learning", "ml")
    lowered = lowered.replace("dept elective", "previous elective")
    return lowered


def _extract_section(question: str) -> str | None:
    for pattern in SECTION_PATTERNS:
        match = pattern.search(question)
        if match:
            return match.group(1)
    return None


def _extract_course(question: str, known_courses: Iterable[str] | None = None) -> str | None:
    normalized = _normalize_phrase(question)

    if known_courses:
        course_map = {str(item).strip().lower(): str(item).strip() for item in known_courses if str(item).strip()}
        for key, original in course_map.items():
            if key and key in normalized:
                return original

    for pattern in COURSE_PATTERNS:
        match = pattern.search(normalized)
        if match:
            value = match.group(1).strip(" .,")
            if value:
                return value.upper() if len(value) <= 4 else value.title()

    if " ml " in f" {normalized} ":
        return "ML"

    return None


def infer_intent(question: str, known_courses: Iterable[str] | None = None) -> ParsedIntent:
    normalized = _normalize_phrase(question)

    wants_guidelines = any(keyword in normalized for keyword in ["guideline", "how to run", "run allocation", "steps"])
    wants_previous = any(
        keyword in normalized
        for keyword in ["previous elective", "previous dept elective", "completed course", "previous department elective"]
    )

    if any(word in normalized for word in ["unallocated", "not allocated", "failed"]):
        intent = "unallocated"
    elif any(word in normalized for word in ["summary", "count", "how many", "total"]):
        intent = "summary"
    else:
        intent = "student_list"

    return ParsedIntent(
        raw_question=question,
        intent=intent,
        section=_extract_section(normalized),
        course=_extract_course(normalized, known_courses=known_courses),
        wants_previous_elective=wants_previous,
        wants_guidelines=wants_guidelines,
    )
