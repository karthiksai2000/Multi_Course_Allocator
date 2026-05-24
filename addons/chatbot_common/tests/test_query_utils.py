from chatbot_common.query_utils import filter_rows, summarize_rows


def test_filter_rows_by_section_and_course() -> None:
    rows = [
        {"RegNo": "1", "Section": "2", "Skill": "ML"},
        {"RegNo": "2", "Section": "1", "Skill": "ML"},
        {"RegNo": "3", "Section": "2", "Skill": "AI"},
    ]

    filtered = filter_rows(rows, section="2", course="ML")
    assert len(filtered) == 1
    assert filtered[0]["RegNo"] == "1"


def test_summarize_rows_total() -> None:
    rows = [
        {"Section": "1", "Skill": "ML"},
        {"Section": "1", "Skill": "ML"},
        {"Section": "2", "Skill": "AI"},
    ]
    summary = summarize_rows(rows)
    assert summary["totalStudents"] == 3
    assert summary["topSections"][0][0] == "1"
