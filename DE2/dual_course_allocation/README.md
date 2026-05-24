# 📚 Dual Course Allocation System

A fair, merit-based allocation system for assigning students to dual course pairs (Group 1 + Group 2) with support for both **automatic demand-driven section creation** and **manual section definition**.

---

## 🎯 Project Overview

**Problem:** Allocate 100+ students to course sections fairly based on their preferences while respecting prerequisites and section capacities.

**Solution:**

- Multi-pass allocation algorithm with preference ranking
- Automatic section generation based on demand analysis
- Manual section override for special requirements
- Merit-based (CGPA) or first-come-first-serve (Timestamp) allocation
- Comprehensive fallback mechanism for unaccommodated students

---

## ⚙️ Core Logic & Algorithm

### **Phase 1: Input Validation & Preprocessing**

- **Deduplication:** Keep newest response per student (by registration number)
- **Sorting:** Order students by allocation criterion:
    - **CGPA Mode:** Sort by CGPA (high→low), secondary by timestamp, tertiary by registration
    - **Timestamp Mode:** Sort by registration timestamp (early→late), secondary by CGPA, tertiary by registration

### **Phase 2: Section Initialization**

#### **Automatic Mode (User-Specified Sections)**

1. Analyze demand for all G1+G2 combinations (based on first preferences)
2. Sort combinations by student count (descending)
3. Allocate exactly N sections (user choice) to top N combinations
4. **Capacity calculation:** `capacity = total_students ÷ target_sections`
    - Example: 100 students, 5 sections → 20 per section

#### **Manual Mode (User-Defined Sections)**

- Load sections exactly as defined by user
- Use provided capacities and course combinations

### **Phase 3: Main Allocation Loop**

For each student (in sorted order):

**Step 1:** Validate preferences

- Check if preferences are provided
- Verify courses exist in configuration
- Ensure courses belong to correct groups

**Step 2:** Rank eligible courses

- Filter by prerequisites (student must have completed prerequisites)
- Return ranked list: (rank_index, course_name)

**Step 3:** Try preference-based allocation

- Nested loop through G1 and G2 preferences (rank order)
- Find best available section using scoring:
    - Preference rank (lower = better)
    - Section utilization (less full = better)
    - CGPA fairness (balanced CGPA distribution)
- Allocate if found

**Step 4:** Try fallback allocation (if enabled)

- **Pass 1:** All stated G1 + G2 preferences (any combination)
- **Pass 2:** Alternative G1s + preferred G2
- **Pass 3:** Preferred G1 + alternative G2s
- **Pass 4:** Any eligible G1+G2 combination
- Pick best section by score

**Step 5:** Mark unallocated

- Record reason if all passes fail

### **Prerequisite Validation**

- Course has `prerequisites` field (list of course names)
- Student has `completed_courses` field
- **Rule:** Student can take course only if ALL prerequisites are in completed_courses
- **Default:** If no prerequisites specified, all students eligible

### **Course Name Normalization**

- All course lookups use case-insensitive, space-trimmed names
- Example: "Cloud Computing", "cloud computing", " Cloud Computing " → all match
- Built at startup in `AllocationEngine.__init__()` via `_normalize_course_name()`

---

## 🔄 Complete Workflow (4 Steps)

### **Step 1️⃣: Upload Files**

- **Upload course configuration** (Excel)
    - Columns: Course Name | Group (G1/G2) | Prerequisites (optional, comma-separated)
    - System validates courses load correctly
- **Upload student data** (Excel)
    - Columns: Name | Registration | CGPA (optional) | Timestamp | G1 Preferences | G2 Preferences | Completed Courses (optional)
    - Lenient parsing: missing CGPA defaults to 3.0, missing timestamp defaults to now()
    - Shows diagnostic to verify course groups are correct

### **Step 2️⃣: Define Sections**

**Option A - Automatic Mode:**

1. Choose allocation criteria: **CGPA (Merit)** or **Timestamp (FCFS)**
2. Enter number of sections (smart default: sqrt(students))
3. System generates plan showing:
    - Top N combos by demand
    - Suggested capacity per section
4. **Optional edit:** Click "Edit Sections" expander to customize courses/capacities
5. Click "Use Automatic Mode"

**Option B - Manual Mode:**

1. Choose allocation criteria: **CGPA** or **Timestamp**
2. Manually define sections:
    - Select G1 course
    - Select G2 course
    - Enter capacity
    - Click "Add Section"
3. Repeat for all sections
4. Click "Use Manual Mode"

### **Step 3️⃣: Run Allocation**

- Review mode summary (Automatic / Manual / Automatic with Custom Edits)
- Criteria shown: CGPA or Timestamp-based
- Click "Execute" to run allocation engine

### **Step 4️⃣: View Results**

- **Allocated Students:** Table with name, registration, courses, section, ranks (1-indexed), fallback flag
- **Unallocated Students:** Table with name, registration, failure reason
- **Section-wise Breakdown:** Expandable tables per section showing students and their ranks
- **Statistics dashboard:** Total/allocated/unallocated counts, allocation rate
- **📊 Download Complete Report (Excel):**
    - Sheet 1: Statistics summary
    - Sheet 2: All allocated students
    - Sheet 3: All unallocated students with reasons
    - Sheets 4+: Each section's students

---

## ⚠️ Edge Cases Handled

### **1. Course Name Mismatches**

- **Issue:** Student says "Cloud Computing", config says "cloud computing"
- **Solution:** Normalize all names (lowercase, trimmed) for comparison
- **Result:** Case-insensitive matching works

### **2. Missing Data**

- **Issue:** Student missing CGPA, timestamp, preferences
- **Solution:**
    - Missing CGPA → default 3.0
    - Missing timestamp → default current time
    - Missing preferences → skip student with error message
- **Result:** System loads 95%+ of students instead of skipping due to one missing field

### **3. No Eligible Courses**

- **Issue:** Student fails prerequisite check for all preferences
- **Solution:** Student marked unallocated with reason "No eligible courses"
- **Result:** No silent drops, user sees exactly why

### **4. Section Overflow**

- **Issue:** 92 students want same G1+G2 combo, only 1 section exists
- **Solution:** Multi-pass fallback
    - Pass 1: Allocate to first choice
    - Pass 2: Allocate to alternative G2 courses (same G1)
    - Pass 3: Allocate to alternative G1+G2 combinations
    - Pass 4: Allocate to ANY eligible combination
- **Result:** 90%+ students allocated even with few sections

### **5. Invalid Courses**

- **Issue:** Student lists "Comic Books" but system has no such course
- **Solution:** Skip that preference, try next-ranked preference
- **Result:** Tolerant allocation, not strict failure

### **6. Group Mismatch**

- **Issue:** Student lists course as G1 preference but course is configured as G2
- **Solution:** Validation error shows: "Course 'X' is configured as GROUP 2, expected GROUP 1"
- **Result:** Clear diagnostic to fix config

### **7. Same Student Multiple Responses**

- **Issue:** Student submitted form twice with different preferences
- **Solution:** Keep only newest response (by timestamp/submission order)
- **Result:** Latest preferences respected, no duplicate allocation

### **8. Prerequisites Not Met**

- **Issue:** Student lists course but hasn't completed prerequisites
- **Solution:** Course removed from ranked preferences, try next choices
- **Result:** Prerequisite chain enforced without blocking entire allocation

### **9. Empty Section**

- **Issue:** Too many sections created, some get no students
- **Solution:** System counts available sections in results
- **Result:** Report shows exact section utilization

### **10. Capacity Mismatch**

- **Issue:** User defines section capacity too low for demand
- **Solution:** System attempts multi-pass fallback; some students unallocated with reason
- **Result:** User sees allocation rate %; can re-run with more sections

---

## 🚀 How to Run

### **Prerequisites**

```bash
pip install -r requirements.txt
```

### **Start the Application**

```bash
streamlit run run_streamlit.py
```

### **Access Web Interface**

```
http://localhost:8501
```

### **Sample Data**

- `sample_config.xlsx` - Example course configuration
- `sample_students.xlsx` - Example student data

---

## 📊 Input File Formats

### **Course Configuration (Excel)**

```
| Course Name           | Group | Prerequisites        |
|---|---|---|
| Artificial Intelligence | G1    |                     |
| Cloud Computing      | G1    | Artificial Intelligence |
| Cybersecurity        | G2    |                     |
| Data Engineering     | G2    | Cloud Computing     |
```

### **Student Data (Excel)**

```
| Name     | Registration | CGPA | Timestamp           | G1 Preferences | G2 Preferences | Completed Courses |
|---|---|---|---|---|---|---|
| Alice    | 001          | 3.8  | 2026-04-10 10:00:00 | AI, ML         | Cyber, DE      | (empty)           |
| Bob      | 002          | 3.5  | 2026-04-10 10:15:00 | Cloud, AI      | Cyber, Blockchain | AI, Cloud    |
```

---

## 📈 Key Features

✅ **Automatic Section Creation** - System analyzes demand and creates optimal sections
✅ **Manual Section Override** - Full control for special requirements
✅ **Merit-Based Allocation** - CGPA ordering for fair merit distribution
✅ **First-Come-First-Serve** - Timestamp-based for early-bird priority
✅ **Preference Ranking** - Students ranked by their stated course preferences
✅ **Prerequisite Validation** - Enforce course prerequisites
✅ **Multi-Pass Fallback** - Intelligent fallback to alternative courses
✅ **Load Balancing** - Sections filled fairly based on demand
✅ **Comprehensive Reports** - Excel export with all allocation details
✅ **Editable Plans** - Users can customize auto-generated section plans

---

## 📁 Project Structure

```
dual_course_allocation/
│
├── app/
│   ├── __init__.py
│   ├── models.py           # Data models (Student, Course, Section, etc.)
│   ├── allocator.py        # Core allocation engine
│   ├── excel_handler.py    # Excel I/O handling
│   └── streamlit_app.py    # Web UI (4-step workflow)
│
├── tests/
│   ├── test_allocation.py          # Allocation algorithm tests
│   └── __init__.py
│
├── sample_config.xlsx      # Example course configuration
├── sample_students.xlsx    # Example student data
├── requirements.txt        # Python dependencies
├── run_streamlit.py       # Entry point for web app
└── README.md             # This file
```

---

## 🔬 Testing

```bash
cd tests
pytest test_allocation.py -v
```

---

## 📝 Configuration

Edit `app/models.py` to adjust:

- `max_section_strength` - Maximum students per section (default: 100)
- `allow_open_seat_fallback` - Enable/disable fallback allocation (default: True)

---

**Version:** 1.0
**Last Updated:** April 10, 2026
**Status:** Production Ready ✅