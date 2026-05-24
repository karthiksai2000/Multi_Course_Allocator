# Addons

This folder contains non-invasive additional features only.

## Safety promise

- Existing source files are untouched.
- All chatbot integration is isolated into new sidecar apps.

## Components

- chatbot_common: Shared parser and response helpers.
- lifeskill_chatbot_service: FastAPI chatbot API.
- dept_chatbot_app: Streamlit chatbot for Single Course module outputs.
- dual_chatbot_app: Streamlit chatbot for Dual Course module outputs.
- gateway: helper script to launch existing apps + sidecars.
- docs: faculty/demo documentation.
