from chatbot_common.intent_parser import infer_intent


def test_extract_section_course_and_previous_flag() -> None:
    parsed = infer_intent(
        "Give me the list of the students in the ML course section 2 with their previous dept elective",
        known_courses=["ML", "AI"],
    )
    assert parsed.intent == "student_list"
    assert parsed.section == "2"
    assert parsed.course in {"ML", "Ml"}
    assert parsed.wants_previous_elective is True


def test_detect_summary_intent() -> None:
    parsed = infer_intent("How many students are allocated in total?")
    assert parsed.intent == "summary"
