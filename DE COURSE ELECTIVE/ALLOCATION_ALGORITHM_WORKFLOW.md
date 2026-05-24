# Regular Student Allocation Algorithm - Complete Workflow

## 🎯 Overview
The algorithm has **3 main phases** to allocate regular students to courses:
1. **Phase 1**: Initial allocation from 1st/2nd/3rd preferences
2. **Phase 2**: Fill underfilled sections (optional)
3. **Bumping**: Competitive displacement (if enabled)

---

## 📊 PHASE 1: Initial Allocation (Main Phase)

### Entry Point: `allocate()` method

```
START
  ↓
  Sort regular students by:
  • CGPA (descending): Higher CGPA gets priority
  • Timestamp (ascending): Earlier registration gets priority
  ↓
  Create allocation queue: [(student, starting_pref_idx=0), ...]
  ↓
  WHILE students in queue:
    Pop student from queue
    ↓
    FOR each preference (in order):
      ↓
      Check: Is course in preferences list?
        YES → Continue to next check
        NO  → Log reason: "Course not configured" → Try next preference
      ↓
      Check: Has student already completed this course?
        YES → Log reason: "{Course} (Already Completed)" → Try next preference
        NO  → Continue to next check
      ↓
      Check: Does course require a prerequisite?
        YES → Check: Does student have prerequisite?
               YES → Continue to allocation
               NO  → Log reason: "{Course} (Prerequisite '{Prereq}' not met)" → Try next preference
        NO  → Continue to allocation
      ↓
      ALLOCATION ATTEMPT:
      ↓
        Is this edge case? (Last preference OR Single section course)
          YES → Allow overflow (ignore max_strength limit)
          NO  → Respect max_strength limit
      ↓
        If BUMPING ENABLED:
          → Try allocate_student_with_bumping()
          
          Case 1: Section has space
            → Allocate directly
            → Status: "Allocated"
            → Break (move to next student)
          
          Case 2: Section full, but student is MORE COMPETITIVE
            → Bump out least competitive student
            → Allocate new student
            → Re-queue bumped student for remaining preferences
            → Status: "Allocated" (new), "Bumped" (old)
            → Break (move to next student)
          
          Case 3: Student not competitive enough
            → Log reason: "{Course} (Section full or not competitive)"
            → Try next preference
        
        Else (WITHOUT BUMPING):
          → Try allocate_student() normally
          
          Case 1: Section has space AND meets competitiveness threshold
            → Allocate directly
            → Status: "Allocated"
            → Break (move to next student)
          
          Case 2: Section full or student not competitive
            → Log reason: "{Course} (Section full or not competitive)"
            → Try next preference
      ↓
    END FOR (all preferences exhausted)
    ↓
    If NOT allocated after all preferences:
      → Move to WAITLIST
      → Status: "Waitlisted"
      → Reason: "Phase 1 Failed: {detailed_reason_list}"
      
    Else if allocated:
      → Remove from queue (move to allocated list)
      ↓
  END WHILE
  ↓
END PHASE 1
```

---

## 🔄 Competitiveness Check Logic

### For CGPA-Based Allocation:
```
Student can allocate to section IF:
  • Section is empty (no students), OR
  • Student's CGPA >= Minimum CGPA in section
  
Why? Ensure similar-grade students are allocated together
```

### For Timestamp-Based Allocation:
```
Student can allocate to section IF:
  • Section is empty (no students), OR
  • Student's timestamp <= Maximum timestamp in section
  
Why? Ensure early registrants get priority
```

---

## 🚀 PHASE 2: Fill Underfilled Sections (Optional)

**Triggered IF**: `fill_underfilled = True` AND Phase 1 complete

```
START
  ↓
  Find all sections: 0 < allocated < capacity
  ↓
  Create allocation queue: [(waitlisted_student, starting_pref_idx=0), ...]
  ↓
  WHILE students in waitlist:
    (Same logic as Phase 1, but with status "Allocated (Fill-Up)")
    ↓
    If allocated → Move to allocated_students list
    Else → Keep in waitlist
    ↓
  END WHILE
  ↓
END PHASE 2
```

---

## 💥 Bumping Algorithm

**Triggered IF**: `enable_bumping = True` AND section is FULL

### Bumping Mechanism:
```
New Student > Current Section (full)
  ↓
  Step 1: Find least competitive student in section
    (CGPA-based: student with MIN CGPA)
    (Timestamp-based: student with MAX/latest timestamp)
  ↓
  Step 2: Compare competitiveness
    New Student MORE competitive than least competitive?
      YES → Step 3
      NO  → Section rejected
  ↓
  Step 3: Check max_strength limit
    (max_strength rule might prevent bumping)
  ↓
  Step 4: Execute bumping
    Remove: Least competitive student from section
    Add: New student to section
    Re-queue: Bumped student with remaining preferences
  ↓
  Result: New student allocated, old student tries other preferences
```

### Example:
```
Scenario: CGPA-Based, Bumping Enabled

Section: Database (Capacity: 2)
  Current Students: [Alice (CGPA: 3.5), Bob (CGPA: 3.2)]

New Student: Charlie (CGPA: 3.8)

Process:
  1. Section full (2/2)
  2. Find least competitive: Bob (3.2)
  3. Charlie (3.8) > Bob (3.2)? YES
  4. Bump Bob out of section
  5. Add Charlie to section
  6. Re-queue Bob: Try 2nd/3rd preferences

Result:
  Section: [Alice (3.5), Charlie (3.8)]
  Bob: Tries remaining preferences
```

---

## 📋 Decision Tree: Single Preference Try

```
Student tries Preference N:
  │
  ├─ Course not configured?
  │  └─ SKIP (log reason: "Course not configured")
  │
  ├─ Already completed this course?
  │  └─ SKIP (log reason: "Already Completed")
  │
  ├─ Prerequisite required?
  │  ├─ YES: Student has it?
  │  │  ├─ YES → Continue
  │  │  └─ NO → SKIP (log reason: "Prerequisite not met")
  │  └─ NO → Continue
  │
  └─ Attempt allocation:
     ├─ Edge case? (Last preference or Single section)
     │  ├─ YES → Allow overflow
     │  └─ NO → Respect max_strength
     │
     ├─ Bumping enabled?
     │  ├─ YES:
     │  │  ├─ Space available?
     │  │  │  └─ YES → ALLOCATE ✓
     │  │  ├─ Section full?
     │  │  │  ├─ Student more competitive?
     │  │  │  │  ├─ YES → BUMP & ALLOCATE ✓
     │  │  │  │  └─ NO → SKIP (not competitive)
     │  │  │  └─ SKIP (not competitive)
     │  │  └─ NOT COMPETITIVE → SKIP
     │  │
     │  └─ NO (Bumping disabled):
     │     ├─ Space available?
     │     │  ├─ YES → ALLOCATE ✓
     │     │  └─ NO → SKIP (section full)
     │     └─ Competitive enough?
     │        ├─ YES → ALLOCATE ✓
     │        └─ NO → SKIP (not competitive)
     │
     └─ Result: ALLOCATED or SKIP
```

---

## 🔍 Allocation Status Definitions

| Status | Phase | Meaning | Next Action |
|--------|-------|---------|------------|
| Allocated | Phase 1 | Got 1st/2nd/3rd preference | Done |
| Allocated (Fill-Up) | Phase 2 | Got preference after fill-up | Done |
| Bumped | Phase 1/2 | Displaced by more competitive student | Tries remaining preferences |
| Waitlisted | After all phases | No preference could be filled | Manual allocation/appeal |

---

## 📊 Example Workflow: 3 Students, 2 Courses

### Setup:
```
Courses:
  • AJP: 2 sections (20 capacity each) = 40 total
  • Database: 1 section (25 capacity)

Students (sorted by CGPA):
  1. Alice (CGPA: 3.8) → Preferences: [AJP, Database]
  2. Bob (CGPA: 3.5) → Preferences: [Database, AJP]
  3. Charlie (CGPA: 2.8) → Preferences: [AJP, Database]

Settings:
  • Allocation method: CGPA
  • Bumping: Disabled
  • Fill underfilled: Yes
```

### Execution:

**Phase 1: Initial Allocation**

```
Queue: [(Alice, 0), (Bob, 0), (Charlie, 0)]

--- Student 1: Alice (CGPA: 3.8) ---
  Preference 1: AJP
    • Course configured? YES
    • Already completed? NO
    • Prerequisite? NO
    • Section 1 empty? YES
    → ALLOCATE to AJP-1
    → Status: "Allocated"
    → Preference Rank: 1

Queue: [(Bob, 0), (Charlie, 0)]

--- Student 2: Bob (CGPA: 3.5) ---
  Preference 1: Database
    • Course configured? YES
    • Already completed? NO
    • Prerequisite? NO
    • Section empty? YES
    → ALLOCATE to Database-1
    → Status: "Allocated"
    → Preference Rank: 1

Queue: [(Charlie, 0)]

--- Student 3: Charlie (CGPA: 2.8) ---
  Preference 1: AJP
    • Course configured? YES
    • Already completed? NO
    • Prerequisite? NO
    • Section 1: 1/20 used, MIN CGPA: 3.8
    • Charlie (2.8) < Min CGPA (3.8)? YES → NOT COMPETITIVE
    • Section 2 empty? YES
    → ALLOCATE to AJP-2
    → Status: "Allocated"
    → Preference Rank: 1

Queue: [] (ALL ALLOCATED)
```

**Phase 2: Fill Underfilled (if enabled)**
```
Underfilled sections: [AJP-1 (1/20), AJP-2 (1/20), Database-1 (1/25)]
Waitlisted students: NONE

No students to fill → Phase 2 done
```

**Final Result:**
```
Allocated:
  ✓ Alice → AJP, Preference 1, CGPA: 3.8
  ✓ Bob → Database, Preference 1, CGPA: 3.5
  ✓ Charlie → AJP, Preference 1, CGPA: 2.8

Waitlisted: 0 students
```

---

## ⚠️ Edge Cases Handled

### 1. Single Section Courses
```
If course has only 1 section:
  • Ignore max_strength limit (allow_overflow = TRUE)
  • Why? No alternatives if student fails this section
```

### 2. Last Preference
```
If assigning last preference to student:
  • Ignore max_strength limit (allow_overflow = TRUE)
  • Why? Student won't get another chance
```

### 3. Prerequisites
```
If course requires prerequisite:
  • Student MUST have completed it
  • Otherwise: Rejected with detailed reason
  • Format: "{Course} (Prerequisite '{PrerequiteName}' not met)"
```

### 4. Already Completed Courses
```
If student already completed this course:
  • Skip automatically
  • Reason: "{Course} (Already Completed)"
  • Try next preference
```

---

## 📈 Performance Characteristics

| Aspect | Value |
|--------|-------|
| Time Complexity | O(n × p × s) |
| n | Number of students |
| p | Number of preferences per student |
| s | Number of sections per course |
| Space Complexity | O(n + c×s) |
| Worst Case | All students competing for same course |
| Bumping Overhead | O(p) re-queueing |

---

## 🔧 Configuration Parameters

```python
# In AllocationEngine.__init__()
allocation_method: str  # 'cgpa' or 'timestamp'
enable_bumping: bool    # True = allow competitive displacement
fill_underfilled: bool  # True = Phase 2 allocation

# In course_config per course:
sections: List[int]     # Capacities: [20, 30, 25]
prerequisite: str       # Optional: None or course name
min_strength: int       # Unused currently
max_strength: int       # Max students to allocate (with overflow exceptions)
```

---

## 🎯 Key Insights

1. **Priority Mechanism**: Students are sorted ONCE at start (no re-sorting)
2. **Greedy Allocation**: Students process preferences in order, take first available
3. **Competitiveness**: Ensures similar-level students group together
4. **Queuing**: Bumped students re-enter with remaining preferences (not re-sorted)
5. **Two-Phase**: Phase 1 = preferences, Phase 2 = fill gaps
6. **Traceable**: Each rejection logged with specific reason

---

## ✅ Verification Checklist

- [x] Phase 1 allocation: Processes all preferences in order
- [x] Competitiveness check: CGPA or Timestamp compared fairly
- [x] Prerequisite validation: Blocks students not meeting requirements
- [x] Bumping logic: Only displaces less competitive students
- [x] Edge cases: Last preference and single section handled
- [x] Reason tracking: All rejections logged with specific cause
- [x] Phase 2 fill-up: Works on remaining waitlist
- [x] Re-queuing: Bumped students processed correctly

