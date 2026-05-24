from pathlib import Path
import sys

import streamlit as st

CURRENT_DIR = Path(__file__).resolve().parent
ADDONS_ROOT = CURRENT_DIR.parent
sys.path.insert(0, str(ADDONS_ROOT))

from chatbot_common import filter_rows, infer_intent, summarize_rows
from dual_chatbot_app.data_adapter import normalize_dual_rows, read_rows


st.set_page_config(page_title="Dual Course Chatbot Sidecar", layout="wide")
st.title("Dual Course Chatbot Sidecar")
st.caption("Additional feature. Existing Dual Course app is unchanged.")

if "dual_rows" not in st.session_state:
    st.session_state.dual_rows = []

DUAL_GUIDELINES = [
    "Run Dual Course allocation in the original module.",
    "Download allocated students output file.",
    "Upload the output file in this chatbot sidecar.",
    "Ask section/course combination questions.",
]

with st.sidebar:
    st.subheader("Load results")
    data_file = st.file_uploader("Allocated/Result file", type=["csv", "xlsx", "xls"])
    if data_file and st.button("Load file"):
        rows = read_rows(data_file.name, data_file.getvalue())
        st.session_state.dual_rows = normalize_dual_rows(rows)
        st.success(f"Loaded {len(st.session_state.dual_rows)} rows")

question = st.text_input("Ask", "Show students in section 2 for AI")

if st.button("Ask Chatbot"):
    if not st.session_state.dual_rows:
        st.warning("Please run allocation first, then upload dual allocation results file.")
        for idx, step in enumerate(DUAL_GUIDELINES, start=1):
            st.write(f"{idx}. {step}")
    else:
        courses = sorted({str(row.get("Skill", "")).strip() for row in st.session_state.dual_rows if str(row.get("Skill", "")).strip()})
        parsed = infer_intent(question, known_courses=courses)

        if parsed.wants_guidelines:
            st.info("Dual Course checklist")
            for idx, step in enumerate(DUAL_GUIDELINES, start=1):
                st.write(f"{idx}. {step}")
        elif parsed.intent == "summary":
            summary = summarize_rows(st.session_state.dual_rows)
            st.json(summary)
        elif parsed.intent == "unallocated":
            unallocated = [r for r in st.session_state.dual_rows if str(r.get("Reason", "")).strip()]
            st.dataframe(unallocated[:200], use_container_width=True)
        else:
            filtered = filter_rows(st.session_state.dual_rows, section=parsed.section, course=parsed.course)
            if not filtered:
                st.warning("No matching students found.")
            else:
                st.success(f"Matched {len(filtered)} rows. Showing up to 200.")
                st.dataframe(filtered[:200], use_container_width=True)
