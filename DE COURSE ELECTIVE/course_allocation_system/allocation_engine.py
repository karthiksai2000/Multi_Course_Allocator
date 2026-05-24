from typing import Dict, List, Tuple
import pandas as pd
from dataclasses import dataclass, field

@dataclass
class Section:
    """Represents a course section"""
    course_name: str
    section_id: int
    capacity: int
    allocated: int = 0
    students: List[Dict] = field(default_factory=list)
    
    def has_space(self) -> bool:
        return self.allocated < self.capacity
    
    def available_space(self) -> int:
        return self.capacity - self.allocated
    
    def allocate(self, student: Dict) -> bool:
        if self.has_space():
            self.students.append(student)
            student['allocation_section_id'] = self.section_id  # Track which section student is allocated to
            self.allocated += 1
            return True
        return False
    
    def get_least_competitive_student(self, allocation_method: str = 'cgpa') -> Dict:
        """Get the least competitive student in this section (for bumping)"""
        if not self.students:
            return None
        
        if allocation_method == 'cgpa':
            # Return student with minimum CGPA
            return min(self.students, key=lambda s: s.get('cgpa', float('inf')))
        else:  # timestamp-based
            # Return student with maximum (latest) timestamp
            return max(self.students, key=lambda s: s.get('timestamp', -1))
    
    def remove_student(self, student: Dict) -> bool:
        """Remove a student from the section (used for bumping)"""
        try:
            self.students.remove(student)
            self.allocated -= 1
            return True
        except ValueError:
            return False
    
    def is_more_competitive(self, new_student: Dict, least_competitive: Dict, allocation_method: str = 'cgpa') -> bool:
        """Check if new student is more competitive than another student"""
        if allocation_method == 'cgpa':
            return new_student.get('cgpa', 0) > least_competitive.get('cgpa', 0)
        else:  # timestamp-based
            return new_student.get('timestamp', float('inf')) < least_competitive.get('timestamp', float('inf'))

@dataclass
class CourseConfig:
    """Represents course configuration"""
    name: str
    sections: List[Section] = field(default_factory=list)
    prerequisite: str = None
    total_capacity: int = 0
    total_allocated: int = 0
    min_strength: int = 0  # Minimum students to accept
    max_strength: int = 0  # Maximum students to allocate
    
    def add_section(self, capacity: int, section_id: int = None):
        if section_id is None:
            section_id = len(self.sections) + 1
        section = Section(self.name, section_id, capacity)
        self.sections.append(section)
        self.total_capacity += capacity
        return section
    
    def is_single_section(self) -> bool:
        """Check if this course has only 1 section"""
        return len(self.sections) == 1
    
    def has_single_section_space(self) -> bool:
        """Check if single section has available space"""
        if self.is_single_section():
            return self.sections[0].has_space()
        return False
    
    def allocate_student(self, student: Dict, allocation_method: str = 'cgpa', allow_overflow: bool = False) -> bool:
        """
        Try to allocate student to any available section
        Uses competitive allocation based on method
        allow_overflow: If True, ignore max_strength limit (for edge cases with single section or last preference)
        Returns: bool indicating success
        """
        # Check if we've reached max_strength limit (unless overflow allowed)
        if not allow_overflow and self.max_strength > 0 and self.total_allocated >= self.max_strength:
            print(f"    [REJECT] {student['name']}: Course full (capacity {self.max_strength}/{self.total_allocated})")
            return False
        
        for i, section in enumerate(self.sections):
            if section.has_space():
                # If section has students, check competitiveness
                if len(section.students) > 0:
                    if allocation_method == 'cgpa':
                        # For CGPA: student must have CGPA >= minimum in section
                        min_cgpa_in_section = min(s.get('cgpa', float('inf')) for s in section.students)
                        if student.get('cgpa', 0) < min_cgpa_in_section:
                            # Student not competitive, skip this section
                            print(f"    [REJECT-SEC{i}] {student['name']} (CGPA {student['cgpa']}) < min CGPA {min_cgpa_in_section}")
                            continue
                    else:  # timestamp-based
                        # For Timestamp: student must have timestamp <= maximum in section
                        max_timestamp_in_section = max(s.get('timestamp', -1) for s in section.students)
                        if student.get('timestamp', float('inf')) > max_timestamp_in_section:
                            # Student came later, not competitive, skip this section
                            print(f"    [REJECT-SEC{i}] {student['name']} (ts {student['timestamp']}) > max ts {max_timestamp_in_section}")
                            continue
                    print(f"    [OK-SEC{i}] {student['name']} passed competitiveness check")
                else:
                    print(f"    [OK-SEC{i}] {student['name']} - Section empty, no competitive check needed")
                
                # Student is competitive (or section is empty), allocate
                if section.allocate(student):
                    self.total_allocated += 1
                    return True
        
        return False
    
    def allocate_student_with_bumping(self, student: Dict, allocation_method: str = 'cgpa', allow_overflow: bool = False) -> Tuple[bool, Dict]:
        """
        Try to allocate student with bumping enabled
        allow_overflow: If True, ignore max_strength limit (for edge cases)
        Returns: (success: bool, bumped_student: Dict or None)
        """
        # Check if we've reached max_strength limit (unless overflow allowed)
        if not allow_overflow and self.max_strength > 0 and self.total_allocated >= self.max_strength:
            print(f"      [BUMP] Cannot allocate {student['name']}: Course at max capacity")
            return False, None
        
        # First try normal allocation (with space available)
        for i, section in enumerate(self.sections):
            if section.has_space():
                # If section has students, check competitiveness
                if len(section.students) > 0:
                    if allocation_method == 'cgpa':
                        # For CGPA: student must have CGPA >= minimum in section
                        min_cgpa_in_section = min(s.get('cgpa', float('inf')) for s in section.students)
                        if student.get('cgpa', 0) < min_cgpa_in_section:
                            # Student not competitive, skip this section
                            print(f"      [BUMP] SEC{i}: {student['name']} (CGPA {student['cgpa']}) < min {min_cgpa_in_section} - skipped")
                            continue
                    else:  # timestamp-based
                        # For Timestamp: student must have timestamp <= maximum in section
                        max_timestamp_in_section = max(s.get('timestamp', -1) for s in section.students)
                        if student.get('timestamp', float('inf')) > max_timestamp_in_section:
                            # Student came later, not competitive, skip this section
                            print(f"      [BUMP] SEC{i}: {student['name']} (ts {student['timestamp']}) > max {max_timestamp_in_section} - skipped")
                            continue
                
                # Student is competitive (or section is empty), allocate
                if section.allocate(student):
                    print(f"      [BUMP] {student['name']} allocated to SEC{i} (space available)")
                    self.total_allocated += 1
                    return True, None
        
        # Try to bump if no space available (and not already at max without overflow)
        print(f"      [BUMP] All sections full for {student['name']}, attempting bumping...")
        for i, section in enumerate(self.sections):
            if section.allocated >= section.capacity and len(section.students) > 0:
                least_competitive = section.get_least_competitive_student(allocation_method)
                
                # Check if new student is more competitive than the least competitive student
                if section.is_more_competitive(student, least_competitive, allocation_method):
                    # Check if max_strength would be exceeded (not allowed even with bumping unless overflow)
                    if not allow_overflow and self.max_strength > 0 and self.total_allocated >= self.max_strength:
                        # Can't bump because we're at max_strength
                        print(f"      [BUMP] Cannot bump in SEC{i}: already at max_strength limit")
                        continue
                    
                    # Remove the least competitive student
                    bumped_name = least_competitive.get('name', 'Unknown')
                    if allocation_method == 'cgpa':
                        comp_val = least_competitive.get('cgpa', 0)
                        comp_desc = f"CGPA {comp_val}"
                    else:
                        comp_val = least_competitive.get('timestamp', 0)
                        comp_desc = f"ts {comp_val}"
                    
                    print(f"      [BUMP] [OK] SEC{i}: Bumping {bumped_name} ({comp_desc}) for {student['name']}")
                    section.remove_student(least_competitive)
                    self.total_allocated -= 1
                    
                    # Allocate the new student
                    section.allocate(student)
                    self.total_allocated += 1
                    
                    # Return the bumped student for re-allocation
                    return True, least_competitive
        
        print(f"      [BUMP] {student['name']} cannot be bumped in any section")
        return False, None
    
    def allocate_lenient(self, student: Dict) -> bool:
        """
        Lenient allocation for fill-up phase - just find ANY available seat without competitiveness check
        Returns: bool indicating success
        """
        for section in self.sections:
            if section.has_space():
                # No competitiveness check - just fill the seat
                if section.allocate(student):
                    self.total_allocated += 1
                    return True
        return False
    
    def get_unfilled_capacity(self) -> int:
        return self.total_capacity - self.total_allocated


class AllocationEngine:
    """Core allocation algorithm"""
    
    def __init__(self, allocation_method: str = 'cgpa', enable_bumping: bool = False):
        """
        allocation_method: 'cgpa' or 'timestamp'
        enable_bumping: whether to enable bumping/displacement for competitive students
        """
        self.allocation_method = allocation_method
        self.enable_bumping = enable_bumping
        self.courses: Dict[str, CourseConfig] = {}
        self.regular_students: List[Dict] = []
        self.research_students: List[Dict] = []
        self.allocated_students: List[Dict] = []
        self.waitlist: List[Dict] = []
        self.special_sections: Dict[str, Dict] = {}  # Store special sections config
        self.special_section_allocations: Dict[str, List[Dict]] = {}  # Track allocations
        self.displacement_queue: List[Tuple[Dict, int]] = []  # Students to re-allocate with their starting preference index
    
    def configure_courses(self, course_config: Dict[str, Dict]):
        """
        Configure courses with sections and capacities
        Format: {
            'Course1': {
                'sections': [30, 35, 40],
                'prerequisite': 'DSA',
                'min_strength': 85,
                'max_strength': 100
            }
        }
        """
        self.courses = {}
        for course_name, config in course_config.items():
            course = CourseConfig(
                course_name, 
                prerequisite=config.get('prerequisite'),
                min_strength=config.get('min_strength', 0),
                max_strength=config.get('max_strength', 0)
            )
            for i, capacity in enumerate(config['sections']):
                course.add_section(capacity, i + 1)
            self.courses[course_name] = course
    
    def add_regular_students(self, students: List[Dict]):
        self.regular_students = students.copy() if students else []
    
    def add_research_students(self, students: List[Dict]):
        self.research_students = students.copy() if students else []
    
    def configure_special_sections(self, special_sections_config: Dict[str, Dict]):
        """
        Configure special/research sections
        Format: {
            'SpecialSection1': {
                'course': 'Database',
                'strength': 15,
                'prerequisite': 'DSA'
            }
        }
        """
        self.special_sections = special_sections_config
        # Initialize allocation tracking for each special section
        for section_name in special_sections_config.keys():
            self.special_section_allocations[section_name] = []
    
    def sort_students(self, students: List[Dict]) -> List[Dict]:
        """Sort students based on allocation method"""
        if self.allocation_method == 'cgpa':
            # Higher CGPA gets priority (descending order)
            sorted_students = sorted(students, key=lambda x: (-x['cgpa'], x['timestamp']))
            # Debug: Print sort order
            print(f"\n[DEBUG] CGPA Sort Order (should be descending by CGPA):")
            for i, s in enumerate(sorted_students[:5]):  # Show first 5
                print(f"  {i+1}. {s['name']} - CGPA: {s['cgpa']}, Timestamp: {s['timestamp']}")
            return sorted_students
        else:  # timestamp-based
            # Earlier registration gets priority
            return sorted(students, key=lambda x: x['timestamp'])
    
    def _fill_special_sections_with_elite_students(self):
        """
        PHASE 0.5: Fill underfilled special sections with elite regular students
        After allocating special/research students to special sections, if any slots remain,
        fill them with the top-performing regular students who have that course in their preferences.
        """
        if not self.special_sections:
            return
        
        print(f"\n[PHASE 0.5] Filling underfilled special sections with elite regular students...")
        
        # Calculate remaining slots for each special section
        special_section_slots = {}
        special_sections_list = list(self.special_sections.items())
        
        for section_name, config in special_sections_list:
            total_strength = config['strength']
            current_allocated = len(self.special_section_allocations.get(section_name, []))
            remaining_slots = total_strength - current_allocated
            special_section_slots[section_name] = remaining_slots
            
            if remaining_slots > 0:
                print(f"  {section_name}: {current_allocated}/{total_strength} allocated, {remaining_slots} slots available")
        
        # Get all unallocated regular students (students who haven't been allocated yet)
        allocated_reg_nos = {s['reg_no'] for s in self.allocated_students if s['student_type'] == 'Regular'}
        unallocated_regular = [s for s in self.regular_students if s['reg_no'] not in allocated_reg_nos]
        
        # Sort unallocated regular students by competitiveness (CGPA desc or timestamp asc)
        sorted_elite = self.sort_students(unallocated_regular)
        
        # For each special section with remaining slots
        for section_name, config in special_sections_list:
            if special_section_slots[section_name] <= 0:
                continue  # No slots remaining
            
            course_name = config['course']
            prerequisite = config.get('prerequisite')
            slots_needed = special_section_slots[section_name]
            
            # Find elite students who:
            # 1. Haven't been allocated yet
            # 2. Have this course in their preferences
            # 3. Meet prerequisite (if required)
            eligible_elite = []
            
            for student in sorted_elite:
                # Skip if already allocated
                if student['reg_no'] in allocated_reg_nos:
                    continue
                
                # Check if student has this course in preferences
                if course_name not in student.get('preferences', []):
                    continue
                
                # Check prerequisite if required
                if prerequisite:
                    completed_courses = set(student.get('completed_courses', []))
                    if prerequisite not in completed_courses:
                        continue  # Prerequisite not met
                
                eligible_elite.append(student)
            
            # Allocate top N elite students to fill the special section
            allocations_made = 0
            for student in eligible_elite[:slots_needed]:
                student_copy = student.copy()
                student_copy['allocation_status'] = 'Allocated'
                student_copy['student_type'] = 'Regular'
                student_copy['allocated_course'] = course_name
                student_copy['allocation_section_id'] = section_name
                student_copy['allocation_section_display'] = section_name
                student_copy['preference_rank'] = f"Special (Elite/Top students)"
                
                if prerequisite:
                    student_copy['allocation_reason'] = f"Allocated to {section_name}: {course_name} (Phase 0.5 - Elite student, Prerequisite '{prerequisite}' met)"
                else:
                    student_copy['allocation_reason'] = f"Allocated to {section_name}: {course_name} (Phase 0.5 - Elite student)"
                
                student_copy['prerequisite_met'] = True if prerequisite else 'N/A'
                
                self.allocated_students.append(student_copy)
                self.special_section_allocations[section_name].append(student_copy)
                allocated_reg_nos.add(student['reg_no'])
                allocations_made += 1
                
                print(f"    [OK] Allocated {student['name']} (CGPA: {student['cgpa']}) to {section_name} ({course_name})")
            
            if allocations_made > 0:
                print(f"  => Filled {allocations_made}/{slots_needed} slots in {section_name}")
            elif slots_needed > 0:
                print(f"  => No eligible elite students found to fill {slots_needed} slots in {section_name}")
    
    def allocate(self) -> Tuple[List[Dict], List[Dict]]:
        """
        Main allocation algorithm
        Returns: (allocated_students, waitlist)
        """
        self.allocated_students = []
        self.waitlist = []
        
        # Sort research students based on allocation method
        sorted_research = self.sort_students(self.research_students)
        
        # First: Allocate research students to special sections (if configured)
        if self.special_sections and sorted_research:
            # Track available slots for each special section
            special_section_slots = {}
            # Maintain order of special sections
            special_sections_list = list(self.special_sections.items())
            
            for section_name, config in special_sections_list:
                special_section_slots[section_name] = config['strength']
            
            # Keep track of unallocated students
            unallocated_research = []
            
            # Try to allocate each research student to special sections (in order)
            for student in sorted_research:
                allocated = False
                completed_courses = set(student.get('completed_courses', []))
                
                # Try each special section IN ORDER
                for section_name, config in special_sections_list:
                    # Check if this section still has slots
                    if special_section_slots[section_name] > 0:
                        
                        # Check prerequisite requirement
                        prerequisite = config.get('prerequisite')
                        if prerequisite:
                            # Student must have completed the prerequisite
                            if prerequisite not in completed_courses:
                                # Prerequisite not met, skip this section
                                continue
                        
                        # All checks passed - Allocate student to this special section
                        student_copy = student.copy()
                        student_copy['allocation_status'] = 'Allocated'
                        student_copy['student_type'] = 'Research/Special'
                        student_copy['allocated_course'] = config['course']
                        student_copy['allocation_section_id'] = section_name
                        student_copy['allocation_section_display'] = section_name
                        student_copy['preference_rank'] = 'Special'
                        
                        # Set reason based on whether prerequisite was required
                        if prerequisite:
                            student_copy['allocation_reason'] = f"Allocated to {section_name}: {config['course']} (Prerequisite '{prerequisite}' met)"
                        else:
                            student_copy['allocation_reason'] = f"Allocated to {section_name}: {config['course']} (No prerequisite required)"
                        
                        student_copy['prerequisite_met'] = True if prerequisite else 'N/A'
                        
                        self.special_section_allocations[section_name].append(student_copy)
                        self.allocated_students.append(student_copy)
                        special_section_slots[section_name] -= 1
                        allocated = True
                        break  # Move to next student
                
                # If not allocated to any special section, add to unallocated list
                if not allocated:
                    unallocated_research.append(student)
            
            # Remaining research students go to waitlist with detailed reasons
            for student in unallocated_research:
                student['student_type'] = 'Research/Special'
                student['allocation_status'] = 'Waitlisted'
                
                # Build detailed reason for each special section rejection
                completed_courses = set(student.get('completed_courses', []))
                reason_parts = []
                
                for section_name, config in special_sections_list:
                    course = config.get('course', 'N/A')
                    prerequisite = config.get('prerequisite')
                    
                    if prerequisite:
                        if prerequisite not in completed_courses:
                            reason_parts.append(f"{course} (Prerequisite '{prerequisite}' not met)")
                        else:
                            reason_parts.append(f"{course} (No slots available)")
                    else:
                        reason_parts.append(f"{course} (No slots available)")
                
                student['allocation_reason'] = ' | '.join(reason_parts) if reason_parts else 'No special sections available'
                # Store in separate list - they will try regular courses in Phase 1 BEFORE going to waitlist
                unallocated_research_for_phase1 = unallocated_research
        elif sorted_research:
            # If no special sections configured, research students go straight to waitlist
            # They do NOT try Phase 1 (regular courses) - special students only get special sections
            for student in sorted_research:
                student['student_type'] = 'Research/Special'
                student['allocation_status'] = 'Waitlisted'
                student['allocation_reason'] = 'No special sections configured for research students'
                self.waitlist.append(student)
            unallocated_research_for_phase1 = []  # Empty - they already in waitlist
        else:
            unallocated_research_for_phase1 = []
        
        # PHASE 0.5: Fill underfilled special sections with elite regular students
        if self.special_sections:
            self._fill_special_sections_with_elite_students()
        
        # CRITICAL: Get list of students already allocated in Phase 0.5
        # Initialize as empty if no special sections
        phase_0_5_allocated_reg_nos = {
            s['reg_no'] for s in self.allocated_students 
            if s.get('student_type') == 'Regular'
        }
        
        # PHASE 1: Try to allocate from preferences
        # IMPORTANT: Exclude students already allocated in Phase 0.5
        remaining_regular_students = [
            s for s in self.regular_students 
            if s['reg_no'] not in phase_0_5_allocated_reg_nos
        ]
        
        # Also include unallocated research students who will try regular courses as fallback
        # This allows research students to get regular courses if no space in special sections
        all_phase1_students = remaining_regular_students + unallocated_research_for_phase1
        
        regular_students = self.sort_students(all_phase1_students)
        print(f"[PHASE 1] Students already allocated in Phase 0.5: {len(phase_0_5_allocated_reg_nos)}")
        print(f"[PHASE 1] Regular students to process: {len(remaining_regular_students)}")
        print(f"[PHASE 1] Unallocated research students to try regular courses: {len(unallocated_research_for_phase1)}")
        print(f"[PHASE 1] Total Phase 1 queue: {len(regular_students)}")
        
        # Add regular students to allocation queue
        allocation_queue = [(student, 0) for student in regular_students]  # (student, starting_pref_index)
        
        while allocation_queue:
            student, start_pref_idx = allocation_queue.pop(0)
            allocated = False
            completed_courses = set(student.get('completed_courses', []))
            preferences = student.get('preferences', [])
            reason_details = []  # Track reason for non-allocation
            
            # DEBUG: Print which student is being processed
            print(f"\n[DEBUG ALLOC] Processing {student['name']} (CGPA: {student['cgpa']}) | Preferences: {preferences}")
            
            # PHASE 1: Try to allocate starting from start_pref_idx
            for pref_offset, preference in enumerate(preferences[start_pref_idx:], start_pref_idx):
                # Skip if student has already completed this course
                if preference in completed_courses:
                    reason_details.append(f"{preference} (Already Completed)")
                    continue
                    
                if preference in self.courses:
                    course = self.courses[preference]
                    prerequisite = course.prerequisite
                    
                    # Check if prerequisite is met
                    if prerequisite:
                        if prerequisite not in completed_courses:
                            reason_details.append(f"{preference} (Prerequisite '{prerequisite}' not met)")
                            continue
                        else:
                            # Prerequisite met, can allocate
                            pass
                    
                    # Check if this is an edge case (single section or last preference)
                    is_last_preference = (pref_offset == len(preferences) - 1)
                    is_single_section = course.is_single_section()
                    allow_overflow = is_last_preference or is_single_section
                    
                    if self.enable_bumping:
                        # Use bumping-aware allocation
                        success, bumped_student = course.allocate_student_with_bumping(student, self.allocation_method, allow_overflow=allow_overflow)
                        if success:
                            print(f"  [OK] Allocated {student['name']} to {preference} (Preference {pref_offset + 1})")
                            student['allocation_status'] = 'Allocated'
                            student['allocated_course'] = preference
                            student['preference_rank'] = pref_offset + 1  # Track which preference got allocated
                            # Format: CourseName-SectionNumber (e.g., DB-1, ML-2)
                            section_id = student.get('allocation_section_id', 1)
                            course_short = preference[:3].upper()  # First 3 chars of course name
                            student['allocation_section_display'] = f"{course_short}-{section_id}"
                            student['allocation_reason'] = f"Phase 1: Allocated to {preference} (Preference {pref_offset + 1})"
                            student['student_type'] = 'Regular'
                            self.allocated_students.append(student)
                            allocated = True
                            
                            # If a student was bumped, re-queue them for allocation
                            if bumped_student:
                                bumped_student['allocation_status'] = 'Bumped'
                                bumped_student['allocation_reason'] = 'Phase 1: Bumped due to lower competitiveness'
                                bumped_student['student_type'] = 'Regular'
                                # Bumped student tries remaining preferences
                                print(f"  => {bumped_student['name']} BUMPED from {preference}, re-queued to try remaining preferences")
                                allocation_queue.append((bumped_student, pref_offset + 1))
                            
                            break
                        else:
                            print(f"  [FAILED] Could not allocate {student['name']} to {preference} (Preference {pref_offset + 1})")
                            reason_details.append(f"{preference} (Section full or not competitive)")
                    else:
                        # Use normal allocation without bumping
                        if course.allocate_student(student, self.allocation_method, allow_overflow=allow_overflow):
                            print(f"  [OK] Allocated to {preference} (Preference {pref_offset + 1})")
                            student['allocation_status'] = 'Allocated'
                            student['allocated_course'] = preference
                            student['preference_rank'] = pref_offset + 1  # Track which preference got allocated
                            # Format: CourseName-SectionNumber (e.g., DB-1, ML-2)
                            section_id = student.get('allocation_section_id', 1)
                            course_short = preference[:3].upper()  # First 3 chars of course name
                            student['allocation_section_display'] = f"{course_short}-{section_id}"
                            student['allocation_reason'] = f"Phase 1: Allocated to {preference} (Preference {pref_offset + 1})"
                            student['student_type'] = 'Regular'
                            self.allocated_students.append(student)
                            allocated = True
                            break
                        else:
                            print(f"  [FAILED] Could not allocate to {preference} (Preference {pref_offset + 1})")
                            reason_details.append(f"{preference} (Section full or not competitive)")
                else:
                    # Course not configured/invalid
                    reason_details.append(f"{preference} (Course not configured)")
            
            if not allocated:
                # PHASE 3: Not allocated in Phase 1, go to waitlist with detailed reason
                student['allocation_status'] = 'Waitlisted'
                student['preference_rank'] = None
                student['allocation_section_display'] = None
                
                # Determine student type: Keep 'Research/Special' if it's a research student
                if student.get('student_type') != 'Research/Special':
                    student['student_type'] = 'Regular'
                
                # Format reason: show all preferences tried and why they failed
                student['allocation_reason'] = 'Phase 1 Failed: ' + ' | '.join(reason_details) if reason_details else 'Phase 1 Failed: All preferences exhausted'
                self.waitlist.append(student)
    
    
    def fill_underfilled_sections(self):
        """
        Fill underfilled sections with waitlisted students - NO COMPETITIVENESS CHECK
        Phase 2: Just fill available seats, don't care about CGPA/Timestamp matching
        """
        # Process waitlisted students - lenient allocation (no competitiveness check)
        allocation_queue = [(student, 0) for student in self.waitlist]  # (student, starting_pref_index)
        remaining_waitlist = []
        
        while allocation_queue:
            student, start_pref_idx = allocation_queue.pop(0)
            allocated = False
            completed_courses = set(student.get('completed_courses', []))
            preferences = student.get('preferences', [])
            reason_details = []  # Track reason for non-allocation
            
            # Try all preferences (skip already completed courses)
            for pref_offset, preference in enumerate(preferences[start_pref_idx:], start_pref_idx):
                # Skip if student has already completed this course
                if preference in completed_courses:
                    reason_details.append(f"{preference} (Already Completed)")
                    continue
                    
                if preference in self.courses:
                    course = self.courses[preference]
                    prerequisite = course.prerequisite
                    
                    # Check if prerequisite is met
                    if prerequisite:
                        if prerequisite not in completed_courses:
                            reason_details.append(f"{preference} (Prerequisite '{prerequisite}' not met)")
                            continue
                    
                    # LENIENT ALLOCATION: No competitiveness check, just fill any available seat
                    if course.allocate_lenient(student):
                        student['allocation_status'] = 'Allocated (Fill-Up)'
                        student['allocated_course'] = preference
                        student['preference_rank'] = pref_offset + 1
                        section_id = student.get('allocation_section_id', 1)
                        course_short = preference[:3].upper()
                        student['allocation_section_display'] = f"{course_short}-{section_id}"
                        student['allocation_reason'] = 'Allocated during fill-up phase (lenient)'
                        self.allocated_students.append(student)
                        allocated = True
                        break
                    else:
                        reason_details.append(f"{preference} (No available seats)")
                else:
                    # Course not configured/invalid
                    reason_details.append(f"{preference} (Course not configured)")
            
            if not allocated:
                # If not allocated, keep in waitlist with reason
                student['allocation_reason'] = 'Unable to allocate during fill-up: ' + ' | '.join(reason_details) if reason_details else 'All preferences exhausted'
                remaining_waitlist.append(student)
        
        self.waitlist = remaining_waitlist
    
    def get_statistics(self) -> Dict:
        """Generate allocation statistics"""
        stats = {
            'total_students': len(self.regular_students) + len(self.research_students),
            'regular_students': len(self.regular_students),
            'research_students': len(self.research_students),
            'allocated': len(self.allocated_students),
            'waitlisted': len(self.waitlist),
            'courses': {}
        }
        
        for course_name, course in self.courses.items():
            stats['courses'][course_name] = {
                'sections': len(course.sections),
                'total_capacity': course.total_capacity,
                'total_allocated': course.total_allocated,
                'unfilled': course.get_unfilled_capacity(),
                'utilization_percent': round(
                    (course.total_allocated / course.total_capacity * 100) if course.total_capacity > 0 else 0, 2
                ),
                'section_details': [
                    {
                        'section': f"Section {s.section_id}",
                        'capacity': s.capacity,
                        'allocated': s.allocated,
                        'available': s.available_space()
                    }
                    for s in course.sections
                ]
            }
        
        return stats
    
    def get_allocation_result(self) -> Dict:
        """Get full allocation result with all details"""
        return {
            'allocated_students': self.allocated_students,
            'waitlist': self.waitlist,
            'statistics': self.get_statistics(),
            'special_sections': self.special_sections,
            'special_section_allocations': self.special_section_allocations
        }
