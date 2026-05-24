from pathlib import Path
import sys

import streamlit as st

CURRENT_DIR = Path(__file__).resolve().parent
ADDONS_ROOT = CURRENT_DIR.parent
sys.path.insert(0, str(ADDONS_ROOT))

from chatbot_common import filter_rows, infer_intent, summarize_rows
from dept_chatbot_app.data_adapter import normalize_dept_rows, read_rows


st.set_page_config(page_title="Single Course Chatbot Sidecar", layout="wide")
st.title("Single Course Chatbot Sidecar")
st.caption("Additional feature. Existing Single Course app is unchanged.")

if "dept_rows" not in st.session_state:
    st.session_state.dept_rows = []

DEPT_GUIDELINES = [
    "Run Single Course allocation in the original module.",
    "Download Allocated Students output file.",
    "Upload the file in this chatbot sidecar.",
    "Ask section/course questions.",
]

with st.sidebar:
    st.subheader("Load results")
    data_file = st.file_uploader("Allocated/Result file", type=["csv", "xlsx", "xls"])
    if data_file and st.button("Load file"):
        rows = read_rows(data_file.name, data_file.getvalue())
        st.session_state.dept_rows = normalize_dept_rows(rows)
        st.success(f"Loaded {len(st.session_state.dept_rows)} rows")

question = st.text_input("Ask", "Give me list of students in section 2 for ML course")

if st.button("Ask Chatbot"):
    if not st.session_state.dept_rows:
        st.warning("Please run allocation first, then upload allocated results file.")
        for idx, step in enumerate(DEPT_GUIDELINES, start=1):
            st.write(f"{idx}. {step}")
    else:
        courses = sorted({str(row.get("Skill", "")).strip() for row in st.session_state.dept_rows if str(row.get("Skill", "")).strip()})
        parsed = infer_intent(question, known_courses=courses)

        if parsed.wants_guidelines:
            st.info("Single Course checklist")
            for idx, step in enumerate(DEPT_GUIDELINES, start=1):
                st.write(f"{idx}. {step}")
        elif parsed.intent == "summary":
            summary = summarize_rows(st.session_state.dept_rows)
            st.json(summary)
        elif parsed.intent == "unallocated":
            unallocated = [r for r in st.session_state.dept_rows if str(r.get("Reason", "")).strip()]
            st.dataframe(unallocated[:200], use_container_width=True)
        else:
            filtered = filter_rows(st.session_state.dept_rows, section=parsed.section, course=parsed.course)
            if not filtered:
                st.warning("No matching students found.")
            else:
                st.success(f"Matched {len(filtered)} rows. Showing up to 200.")
                st.dataframe(filtered[:200], use_container_width=True)
