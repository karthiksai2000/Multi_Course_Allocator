# Course Allocation Algorithm Review - REGULAR STUDENTS

## ✅ COMPLETE 3-PHASE ALGORITHM

### **PHASE 1: PREFERENCE-BASED ALLOCATION**

**Goal**: Try to allocate students to their preferred courses (1st, 2nd, 3rd choice)

**Algorithm**:
```
FOR EACH student (sorted by CGPA/Timestamp):
  FOR EACH preference (starting from 1st choice):
    IF preference already completed:
      → Skip, record: "Already Completed"
      → Continue to next preference
    
    IF preference not in configured courses:
      → Skip this preference
      → Record: "Course not configured"
      → Continue to next preference
    
    IF prerequisite required:
      IF student hasn't completed prerequisite:
        → Skip this preference
        → Record: "Prerequisite 'X' not met"
        → Continue to next preference
    
    TRY TO ALLOCATE:
      IF section has space (or edge case: single section/last preference):
        IF bumping enabled AND section full:
          → Try to bump less competitive student
          → If successful: Record "Phase 1: Allocated"
          → Re-queue bumped student with next preference
        ELSE:
          → Allocate student
          → Record "Phase 1: Allocated to X (Preference Y)"
          → STOP (student allocated successfully)
      ELSE:
        → Section full and no bump possible
        → Record: "Section full or not competitive"
        → Continue to next preference
  
  IF still not allocated after all preferences:
    → Add to WAITLIST with detailed reasons
    → Record ALL rejection reasons from above
```

---

## **ALLOCATION REASONS - REGULAR STUDENTS**

### ✅ **SUCCESSFUL ALLOCATIONS**

| Reason | Meaning | Example |
|--------|---------|---------|
| `Phase 1: Allocated to AJP (Preference 1)` | Got 1st choice | Student got their first preference ✅ |
| `Phase 1: Allocated to DL (Preference 2)` | Got 2nd choice | Student got their second preference ✅ |
| `Phase 1: Bumped due to lower competitiveness` | Displaced but re-queued | More competitive student took their spot, they try remaining prefs ⚠️ |

### ❌ **REJECTION REASONS**

| Reason | Meaning | Action Taken |
|--------|---------|--------------|
| `Already Completed` | Student already took this course | Skip to next preference |
| `Course not configured` | Course listed but not set up by admin | Skip to next preference |
| `Prerequisite 'DSA' not met` | Missing required prerequisite | Skip to next preference |
| `Section full or not competitive` | All sections full/student not competitive enough | Try bumping OR skip to next preference |

### 🔄 **FILL-UP PHASE REASONS**

| Reason | Meaning |
|--------|---------|
| `Phase 2: Allocated during fill-up` | Got 2nd/3rd choice after Phase 1 failed |
| `Phase 2: Bumped during fill-up` | Bumped student got allocated in fill-up phase |

### ⏳ **WAITLIST REASONS**

| Reason | Meaning |
|--------|---------|
| `Phase 1 Failed: AJP (Section full) \| DL (Prerequisite 'ML' not met) \| Python (Course not configured)` | Shows WHY each preference was rejected |
| `Phase 1 Failed: All preferences exhausted` | No valid preferences OR all were tried |

---

## **DETAILED ALLOCATION TRACKING**

### **For ALLOCATED Students** (Excel Output):

```
Name: Raj Kumar
Status: Allocated
Allocated Course: AJP
Section: AJP-1
Preference Rank: 1
Reason for Allocation: Phase 1: Allocated to AJP (Preference 1)
```

### **For WAITLISTED Students** (Excel Output):

```
Name: Priya Singh
Status: Waitlisted
Preferences: AJP, DL, ML
Reason for Waitlist: Phase 1 Failed: AJP (Section full or not competitive) | DL (Prerequisite 'ML' not met) | ML (Already Completed)
```

**What this tells admin**:
- ❌ AJP full and Priya's CGPA not high enough
- ❌ DL requires ML prerequisite which Priya doesn't have
- ❌ ML already completed (no point allocating)

### **For BUMPED Students** (Re-queued):

```
Name: Aditya Gupta
Status: Bumped (then re-queued)
Original Preference: AJP
Why Bumped: Phase 1: Bumped due to lower competitiveness
Next Action: Try remaining preferences (DL, ML, ...)
```

---

## **ALGORITHM ACCURACY CHECK**

✅ **Completed Courses Check**: YES - Skips with reason  
✅ **Prerequisite Check**: YES - Skips with reason  
✅ **Preference Order**: YES - Tries 1st, 2nd, 3rd... in order  
✅ **Competitive Filtering**: YES - CGPA/Timestamp based  
✅ **Bumping Support**: YES - Re-queues with reason  
✅ **Edge Cases**: YES - Single section & last preference overflow  
✅ **Fill-Up Phase**: YES - 2nd/3rd choices after Phase 1  
✅ **Reason Tracking**: YES - All rejections documented  

---

## **EXAMPLE SCENARIOS**

### **Scenario 1: Raj (Competitive, All Preferences Valid)**
```
Preferences: [AJP, DL, ML]
Completed: [DSA]
CGPA: 3.8

Phase 1 Flow:
├─ Check AJP: Valid? YES | Prerequisite? NO | Space? YES
└─ ✅ ALLOCATED → AJP (Section AJP-1)

Result: ALLOCATED to AJP (Preference 1)
```

### **Scenario 2: Priya (Prerequisite Issue)**
```
Preferences: [AJP (needs ML), DL, ML]
Completed: [DSA]
CGPA: 2.5

Phase 1 Flow:
├─ Check AJP: Prerequisite ML? NOT COMPLETED ❌
├─ Check DL: Valid? YES | Prerequisite? NO | Space? YES
└─ ✅ ALLOCATED → DL (Section DL-1)

Result: ALLOCATED to DL (Preference 2)
Reason: Phase 1: Allocated to DL (Preference 2)
```

### **Scenario 3: Sam (All Preferences Exhausted)**
```
Preferences: [AJP, DL, ML]
Completed: [ML]
CGPA: 1.8

Phase 1 Flow:
├─ Check AJP: Prerequisite? NEEDED | Space? FULL | Competitive? NO (low CGPA)
├─ Check DL: Prerequisite? NEEDED | Prerequisite MET? YES | Space? FULL | Competitive? NO
├─ Check ML: Already Completed ❌
└─ ❌ NOT ALLOCATED

Result: WAITLISTED
Reason: Phase 1 Failed: AJP (Section full or not competitive) | DL (Section full or not competitive) | ML (Already Completed)
```

### **Scenario 4: Amit (Bumped, Then Gets 2nd Choice)**
```
Preferences: [AJP, DL]
Completed: [DSA]
CGPA: 3.9 (Very High)

Phase 1 Main Allocation:
├─ Check AJP: Valid? YES | Space? NO (but has students)
├─ Least competitive in AJP: CGPA 2.1
├─ Amit CGPA (3.9) > Least competitive (2.1)? YES ✅
└─ BUMP student with CGPA 2.1 from AJP
    ├─ Amit allocated to AJP
    └─ Bumped student re-queued for DL

Result: Amit ALLOCATED to AJP
Bumped student tries DL next
```

---

## **FINAL VERIFICATION**

✅ **Phase 1**: Tries preferences with complete reason tracking  
✅ **Phase 2**: Fill-up phase for waitlisted students  
✅ **Phase 3**: Detai waitlist with all rejection reasons logged  
✅ **Bumping**: Tracked with reason, re-queued properly  
✅ **Min/Max Removed**: No longer used  
✅ **Excel Output**: Shows allocation_reason field for all students  

**SYSTEM STATUS**: ✅ **COMPLETE AND VERIFIED**
