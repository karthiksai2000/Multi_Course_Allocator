# Multi-Use Course Allocation Platform

-------------------------------------------------------------------------------
ONE CONTROL HUB. THREE ALLOCATORS. ZERO MANUAL CHAOS.
-------------------------------------------------------------------------------

Allocate life skills, single-course electives, and dual-course electives from a
single frontend. Upload Excel once, tune constraints, and get clean outputs with
logs, summaries, and auditability.

Live frontend: https://course-allocation-2-frontend.onrender.com/

-------------------------------------------------------------------------------
WHY THIS EXISTS
-------------------------------------------------------------------------------
Manual elective allocation breaks at scale: duplicate rows, uneven section loads,
capacity overflow, and opaque outcomes. This platform automates the hard parts
while keeping admins in control with configurable constraints and readable logs.

-------------------------------------------------------------------------------
WHAT YOU GET (FEATURES)
-------------------------------------------------------------------------------
- Three modules in one UI:
	- Life Skills Allocator (FastAPI + React)
	- Single Course Department Allocator (Streamlit)
	- Dual Course Department Allocator (Streamlit)
- Upload once, allocate once, download everything:
	- Student-wise, section-wise, slot-wise, capacity dashboard
	- Unallocated list and decision logs
- Configurable constraints:
	- Section-to-slot mapping, skill capacities, per-section limits
	- Prerequisite checks and allocation fallbacks

-------------------------------------------------------------------------------
TECHNOLOGY STACK
-------------------------------------------------------------------------------
Frontend:
	- Vite + React (frontend/)

APIs:
	- FastAPI (backend/) for Life Skills

Allocators:
	- Streamlit (DE COURSE ELECTIVE/...) for Single Course
	- Streamlit (DE2/dual_course_allocation/...) for Dual Course

Data:
	- Excel (.xlsx/.xls) inputs and outputs

-------------------------------------------------------------------------------
ALGORITHMS (HIGH LEVEL)
-------------------------------------------------------------------------------
Life Skills Allocation:
	1) Parse Excel and normalize columns (student, reg no, section, CGPA, prefs)
	2) Rank students by CGPA (and optional attendance weighting)
	3) Place by preference list while honoring:
		 - Skill capacity limits
		 - Section skill limits
		 - Slot constraints
	4) Generate dashboards and detailed allocation logs

Single Course Allocation (Streamlit):
	- Priority ordering with tie-breakers
	- Capacity and prerequisites validation
	- Section load balancing to avoid overfill

Dual Course Allocation (Streamlit):
	- Merit-based ordering (CGPA-first) with timestamp tie-breakers
	- Multi-pass fallback for unallocated students
	- Automatic section distribution across slots

-------------------------------------------------------------------------------
CONSTRAINTS (WHAT THE SYSTEM ENFORCES)
-------------------------------------------------------------------------------
- Input files must be Excel (.xlsx/.xls)
- Required fields for most flows: name, reg no, section, CGPA, preferences
- Capacity and section limits are enforced before allocations finalize
- Duplicate or invalid rows are flagged and reported

-------------------------------------------------------------------------------
QUICKSTART (LOCAL)
-------------------------------------------------------------------------------
Prereqs:
	- Node.js 18+ recommended
	- Python 3.10+ recommended

Install JS deps once:
```bash
npm install
```

Start everything with one command:
```bash
npm run dev:all
```

Local URLs:
	- Frontend (React):  http://localhost:5173
	- Life Skills API:   http://localhost:8000
	- Single Course UI:  http://localhost:8501
	- Dual Course UI:    http://localhost:8502

If you only need a specific module:
```bash
npm run dev:frontend
npm run dev:api
npm run dev:single
npm run dev:dual
```

-------------------------------------------------------------------------------
ENVIRONMENT VARIABLES
-------------------------------------------------------------------------------
Frontend uses Vite envs:
	- VITE_LIFESKILL_API   (default http://localhost:8000)
	- VITE_DEPT_ALLOC_URL  (default http://localhost:8501)
	- VITE_DUAL_ALLOC_URL  (default http://localhost:8502)

Example:
```bash
VITE_LIFESKILL_API=https://lifeskill-api.onrender.com
VITE_DEPT_ALLOC_URL=https://dept-allocator.onrender.com
VITE_DUAL_ALLOC_URL=https://dual-allocator.onrender.com
```

-------------------------------------------------------------------------------
REPOSITORY MAP
-------------------------------------------------------------------------------
```
backend/                               FastAPI service for life skills
frontend/                              Vite/React UI (module selector + UI)
DE COURSE ELECTIVE/course_allocation_system/  Single-course Streamlit app
DE2/dual_course_allocation/            Dual-course Streamlit app
```

-------------------------------------------------------------------------------
OUTPUTS (WHAT YOU DOWNLOAD)
-------------------------------------------------------------------------------
- Student-wise allocation sheet
- Section-wise and slot-wise breakdowns
- Capacity dashboard
- Allocation log and unallocated reports

-------------------------------------------------------------------------------
DEPLOYMENT NOTES
-------------------------------------------------------------------------------
- Frontend can be hosted on any static host after build.
- FastAPI can run with uvicorn or gunicorn.
- Streamlit apps can run as services on 8501/8502 (or custom ports).

-------------------------------------------------------------------------------
TROUBLESHOOTING
-------------------------------------------------------------------------------
- Only Excel uploads are accepted (.xlsx/.xls)
- If a Streamlit page is blank, ensure its port is running
- If API calls fail, verify VITE_LIFESKILL_API is correct
