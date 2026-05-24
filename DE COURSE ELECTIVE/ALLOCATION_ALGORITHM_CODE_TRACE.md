# Regular Student Allocation - Code Reference & Tracing Guide

## 🔧 Key Code Sections

### 1. Student Sorting (Lines 240-250)

```python
def sort_students(self, students: List[Dict]) -> List[Dict]:
    """Sort students based on allocation method"""
    if self.allocation_method == 'cgpa':
        # Higher CGPA gets priority
        return sorted(students, key=lambda x: (-x['cgpa'], x['timestamp']))
    else:  # timestamp-based
        # Earlier registration gets priority
        return sorted(students, key=lambda x: x['timestamp'])
```

**What happens:**
- CGPA method: Sort descending by CGPA (highest first), then ascending by timestamp (earliest first)
- Timestamp method: Sort ascending by timestamp (earliest first)

---

### 2. Main Allocation Loop (Lines 300-430)

```python
def allocate(self) -> Tuple[List[Dict], List[Dict]]:
    # Generate sorted list
    regular_students = self.sort_students(self.regular_students)
    
    # Create queue: (student, starting_preference_index)
    allocation_queue = [(student, 0) for student in regular_students]
    
    while allocation_queue:
        student, start_pref_idx = allocation_queue.pop(0)
        allocated = False
        completed_courses = set(student.get('completed_courses', []))
        preferences = student.get('preferences', [])
        reason_details = []
        
        # Try each preference starting from start_pref_idx
        for pref_offset, preference in enumerate(preferences[start_pref_idx:], start_pref_idx):
            # ... allocation logic ...
```

**Flow:**
1. Sort students once
2. Create queue with (student, starting_pref_index)
3. Process queue: pop student, try preferences, either allocate or waitlist
4. If bumped, re-queue student with updated preference index

---

### 3. Preference Validation Checks (Lines 350-370)

```python
# CONDITION 1: Course Valid?
if preference not in self.courses:
    reason_details.append(f"{preference} (Course not configured)")
    continue  # Try next preference

# CONDITION 2: Already Completed?
if preference in completed_courses:
    reason_details.append(f"{preference} (Already Completed)")
    continue

# CONDITION 3: Prerequisite Met?
if prerequisite:
    if prerequisite not in completed_courses:
        reason_details.append(f"{preference} (Prerequisite '{prerequisite}' not met)")
        continue
```

**Key point:** All checks use `continue` to go to next preference

---

### 4. Edge Case Handling (Lines 380-390)

```python
# Check if this is an edge case (single section or last preference)
is_last_preference = (pref_offset == len(preferences) - 1)
is_single_section = course.is_single_section()
allow_overflow = is_last_preference or is_single_section
```

**Why?**
- Last preference: Student won't get another chance
- Single section: No alternatives if this section is full
- In both cases: Override max_strength limit

---

### 5. Allocation with Bumping (Lines 400-430)

```python
if self.enable_bumping:
    success, bumped_student = course.allocate_student_with_bumping(
        student, 
        self.allocation_method, 
        allow_overflow=allow_overflow
    )
    
    if success:
        # Mark as allocated
        student['allocation_status'] = 'Allocated'
        student['preference_rank'] = pref_offset + 1
        self.allocated_students.append(student)
        allocated = True
        
        # If someone was bumped, re-queue them
        if bumped_student:
            bumped_student['allocation_status'] = 'Bumped'
            # Re-queue starting from NEXT preference
            allocation_queue.append((bumped_student, pref_offset + 1))
        
        break  # Move to next student in queue
    else:
        reason_details.append(f"{preference} (Section full or not competitive)")
```

**Important:** Bumped student is re-queued to try `pref_offset + 1` (remaining preferences)

---

### 6. Allocation Without Bumping (Lines 440-465)

```python
else:  # Bumping disabled
    if course.allocate_student(student, self.allocation_method, allow_overflow=allow_overflow):
        student['allocation_status'] = 'Allocated'
        student['preference_rank'] = pref_offset + 1
        self.allocated_students.append(student)
        allocated = True
        break
    else:
        reason_details.append(f"{preference} (Section full or not competitive)")
```

---

### 7. Waitlist When All Preferences Fail (Lines 480-490)

```python
if not allocated:
    # PHASE 3: Not allocated in Phase 1, go to waitlist
    student['allocation_status'] = 'Waitlisted'
    student['student_type'] = 'Regular'
    # Combine all rejection reasons
    student['allocation_reason'] = 'Phase 1 Failed: ' + ' | '.join(reason_details)
    self.waitlist.append(student)
```

---

### 8. Competitiveness Check in CourseConfig (Lines 90-130)

```python
def allocate_student(self, student: Dict, allocation_method: str = 'cgpa', 
                    allow_overflow: bool = False) -> bool:
    """Try to allocate student to any available section"""
    
    # Check max_strength limit
    if not allow_overflow and self.max_strength > 0 and self.total_allocated >= self.max_strength:
        return False
    
    for section in self.sections:
        if section.has_space():
            # Check if section has students
            if len(section.students) > 0:
                if allocation_method == 'cgpa':
                    min_cgpa_in_section = min(s.get('cgpa', float('inf')) for s in section.students)
                    if student.get('cgpa', 0) < min_cgpa_in_section:
                        continue  # Try next section
                else:  # timestamp-based
                    max_timestamp_in_section = max(s.get('timestamp', -1) for s in section.students)
                    if student.get('timestamp', float('inf')) > max_timestamp_in_section:
                        continue
            
            # Student is competitive or section is empty
            if section.allocate(student):
                self.total_allocated += 1
                return True
    
    return False
```

**Key:** If section empty → allocate directly. If section has students → check competitiveness.

---

## 📊 Tracing Example: 3-Student Scenario

### Setup

```
STUDENTS (sorted by CGPA desc):
1. Alice (CGPA: 3.9, Prefs: [DB, AJP], Completed: [])
2. Bob (CGPA: 3.5, Prefs: [AJP, DB], Completed: [])
3. Charlie (CGPA: 2.8, Prefs: [DB, AJP], Completed: [Statistics])

COURSES:
• Database: 1 section (Capacity: 2)
• AJP: 1 section (Capacity: 2)

SETTINGS:
• Method: CGPA-Based
• Bumping: Disabled
• Fill Underfilled: No

EXECUTION STEPS
```

### Trace Execution

**Step 1: Sort students**
```
Sorted: [Alice (3.9), Bob (3.5), Charlie (2.8)]
```

**Step 2: Create queue**
```
Queue: [(Alice, 0), (Bob, 0), (Charlie, 0)]
Allocated: []
Waitlist: []
```

**Step 3: Process Alice**
```
AllocQueue.pop(0) → Alice, 0

Try Pref 0: Database
  ✓ Configured
  ✓ Not completed
  ✓ No prerequisite
  → Allocate to Database-1 (empty)
  
  Database section:
    Before: 0/2
    After:  1/2 (Alice added)
  
  Result: ALLOCATED (Preference Rank: 1)
  Status: Allocated
  Reason: "Phase 1: Allocated to Database (Preference 1)"
  
  allocated_students += Alice
  break
```

**Step 4: Process Bob**
```
AllocQueue.pop(0) → Bob, 0

Try Pref 0: AJP
  ✓ Configured
  ✓ Not completed
  ✓ No prerequisite
  → AJP section empty?
     YES → Allocate to AJP-1
  
  AJP section:
    Before: 0/2
    After:  1/2 (Bob added)
  
  Result: ALLOCATED (Preference Rank: 1)
  Status: Allocated
  Reason: "Phase 1: Allocated to AJP (Preference 1)"
  
  allocated_students += Bob
  break
```

**Step 5: Process Charlie**
```
AllocQueue.pop(0) → Charlie, 0

Try Pref 0: Database
  ✓ Configured
  ✓ Not completed (not in [Statistics])
  ✓ No prerequisite
  → Database section has space?
     YES (1/2) → Check competitiveness
     Min CGPA in section: min(3.9) = 3.9
     Charlie CGPA: 2.8
     Is 2.8 >= 3.9? NO → NOT COMPETITIVE
  
  Try next section → No more sections in Database
  reason_details += "Database (Section full or not competitive)"

Try Pref 1: AJP
  ✓ Configured
  ✓ Not completed
  ✓ No prerequisite
  → AJP section has space?
     YES (1/2) → Check competitiveness
     Min CGPA in section: min(3.5) = 3.5
     Charlie CGPA: 2.8
     Is 2.8 >= 3.5? NO → NOT COMPETITIVE
  
  reason_details += "AJP (Section full or not competitive)"

All preferences exhausted:
  Result: WAITLISTED
  Status: Waitlisted
  Reason: "Phase 1 Failed: Database (Section full or not competitive) | AJP (Section full or not competitive)"
  
  waitlist += Charlie
```

**Step 6: Queue empty → Phase 1 done**

### Final Results

```
ALLOCATED (2/3):
  ✓ Alice → Database (Pref 1, CGPA 3.9)
  ✓ Bob → AJP (Pref 1, CGPA 3.5)

WAITLISTED (1/3):
  ✗ Charlie → Reason: Phase 1 Failed: Database & AJP both below competitiveness threshold

STATISTICS:
  Success Rate: 66.67%
  Database: 1/2 (50% utilization)
  AJP: 1/2 (50% utilization)
```

---

## 🔍 How to Debug the Algorithm

### 1. Check Student Sorting

```python
# Add after sort_students()
sorted_students = self.sort_students(self.regular_students)
for i, student in enumerate(sorted_students):
    print(f"{i+1}. {student['name']:20s} CGPA: {student['cgpa']:4.2f} Prefs: {student['preferences']}")
```

### 2. Trace Preference Checks

```python
# Inside preference loop
print(f"\n  Preference {pref_offset}: {preference}")
print(f"    ✓ In completed? {preference in completed_courses}")
print(f"    ✓ Configured? {preference in self.courses}")
if preference in self.courses:
    course = self.courses[preference]
    print(f"    ✓ Prerequisite: {course.prerequisite}")
```

### 3. Log Competitiveness Checks

```python
# Inside course.allocate_student()
print(f"    Section capacity: {section.capacity}, Allocated: {section.allocated}")
if len(section.students) > 0:
    print(f"    Min CGPA in section: {min_cgpa}")
    print(f"    Student CGPA: {student['cgpa']}")
    print(f"    Competitive? {student['cgpa'] >= min_cgpa}")
```

### 4. Track Bumping Events

```python
# After bumping
if bumped_student:
    print(f"  🚀 BUMPED: {bumped_student['name']} ({bumped_student.get('cgpa', 'N/A')})")
    print(f"  ➕ RE-QUEUED: From preference {pref_offset + 1}")
```

---

## ✅ Validation Points

Run these checks to verify algorithm is working:

1. **All students processed**: `len(allocated_students) + len(waitlist) == len(regular_students)`
2. **No double allocation**: `len(set(s['reg_no'] for s in allocated_students)) == len(allocated_students)`
3. **Capacity respected**: Each section allocation ≤ capacity
4. **Reasons assigned**: Every waitlisted student has allocation_reason
5. **CGPA ordering**: Allocated students roughly follow CGPA order (may have gaps due to preferences)

---

## 📈 Common Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| Low allocation rate | Strict competitiveness check | Check if min/max students in course |
| All waitlisted | Courses misconfigured | Verify course_config has sections > 0 |
| Duplicate allocations | Queue processed twice | Check that `break` statements prevent re-processing |
| Lost allocation reason | Reason not built | Check reason_details list is populated |
| Bumping not working | Flag disabled or not competitive enough | Verify `enable_bumping=True` and competitiveness |

---

## 🎯 Performance Tips

1. **Pre-filter completed courses**: Build set once, don't search list repeatedly
2. **Cache competitiveness checks**: Min/max CGPA calculated each time
3. **Limit preference count**: Typically 3 preferences, but algorithm generalizes

---

## 📚 Related Methods

| Method | Purpose | Called By |
|--------|---------|-----------|
| `allocate()` | Main entry point | App UI step 5 |
| `sort_students()` | Pre-sort all students | allocate() |
| `fill_underfilled_sections()` | Phase 2 allocation | allocate() or App |
| `get_statistics()` | Generate report data | Output generator |
| `get_allocation_result()` | Package all results | App for Excel export |

