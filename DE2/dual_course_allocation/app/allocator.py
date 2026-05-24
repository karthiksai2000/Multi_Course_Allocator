"""
Complete Dual Course Allocation Algorithm Implementation
Based on comprehensive workflow specification with all edge cases handled
"""
from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime
from .models import (
    Course, PairedSection, Student, AllocationResult,
    AllocationConfig, AllocationStats, Group, Section
)


class AllocationEngine:
    """
    Production-grade allocation engine with optional manual section definition.
    
    Supports two modes:
    1. MANUAL SECTIONS: Admin defines specific sections (recommended for fairness control)
    2. DYNAMIC SECTIONS: System creates sections based on demand (fallback)
    
    WORKFLOW:
      PHASE 1: Input Validation & Preprocessing
        - Deduplicate: Keep newest response per student
        - Sort: By CGPA (desc), timestamp (asc), registration_number
      
      PHASE 2: Section Setup
        - Manual: Load predefined sections
        - Dynamic: Analyze demand and create sections
      
      PHASE 3: Main Allocation Loop
        - For each student (merit order):
          1. Validate preferences
          2. Rank preferences by eligibility
          3. Try to allocate to preferred section
          4. If section full, try other preferences
          5. If no match, mark unallocated
      
      PHASE 4: Output Generation
        - List allocated students per section
        - List unallocated students with reasons
        - Generate statistics
    
    Edge Cases Handled:
      ✓ Fair merit-based allocation (CGPA ordering)
      ✓ Flexible preference matching
      ✓ Prerequisite validation
      ✓ Section capacity constraints
      ✓ State synchronization
    """

    def __init__(self, config: AllocationConfig):
        self.config = config
        self.paired_sections: List[PairedSection] = []
        self.allocation_results: List[AllocationResult] = []
        self.student_map: Dict[str, Student] = {}
        self.allocation_criterion = "CGPA"  # Default: CGPA or Timestamp
        self.target_sections = None  # User-specified number of sections (if any)
        
        # Build normalized course name mapping (case-insensitive, trimmed)
        self.course_name_map = {}
        for course_code, course in self.config.courses.items():
            normalized_name = self._normalize_course_name(course.course_name)
            self.course_name_map[normalized_name] = course_code
    
    def _normalize_course_name(self, name: str) -> str:
        """Normalize course name for case-insensitive matching"""
        return name.strip().lower() if name else ""
    
    def _get_course_code_by_name(self, course_name: str) -> Optional[str]:
        """Get course code by name (case-insensitive, trimmed)"""
        normalized = self._normalize_course_name(course_name)
        return self.course_name_map.get(normalized)

    # ================================================================
    # MAIN ALGORITHM
    # ================================================================

    def allocate_with_manual_sections(self, students: List[Student], 
                                      manual_sections: List[Dict],
                                      criterion: str = "CGPA") -> Tuple[List[AllocationResult], AllocationStats]:
        """
        Execute allocation with manually defined sections.
        
        Args:
            students: List of students to allocate
            manual_sections: List of dicts with keys: 'section_number', 'g1_course', 'g2_course', 'capacity'
            criterion: Allocation priority - "CGPA" (merit-based) or "Timestamp" (first-come-first-serve)
        
        Example:
            manual_sections = [
                {'section_number': 1, 'g1_course': 'AI', 'g2_course': 'Cybersecurity', 'capacity': 70},
                {'section_number': 2, 'g1_course': 'AI', 'g2_course': 'Blockchain', 'capacity': 70},
            ]
        """
        self.allocation_criterion = criterion  # "CGPA" or "Timestamp"
        
        # Build student map for CGPA lookups
        for student in students:
            self.student_map[student.registration_number] = student
        
        # PHASE 1: Preprocess
        deduplicated = self._phase1_deduplicate(students)
        sorted_students = self._phase1_sort(deduplicated)
        
        # PHASE 2: Load manual sections
        self._phase2_load_manual_sections(manual_sections)
        
        # PHASE 3: Allocate to manual sections
        self._phase3_allocate_to_manual_sections(sorted_students)
        
        # Generate statistics
        stats = self._generate_stats(len(students))
        
        return self.allocation_results, stats

    def allocate(self, students: List[Student], criterion: str = "CGPA", target_sections: int = None) -> Tuple[List[AllocationResult], AllocationStats]:
        """Execute dynamic allocation algorithm with specified criterion and target sections
        
        Args:
            students: List of students to allocate
            criterion: "CGPA" (merit-based) or "Timestamp" (first-come-first-serve)
            target_sections: User-specified number of sections to create
        """
        self.allocation_criterion = criterion  # "CGPA" or "Timestamp"
        self.target_sections = target_sections  # User-specified number of sections
        
        # Build student map for CGPA lookups
        for student in students:
            self.student_map[student.registration_number] = student
        
        # PHASE 1: Preprocess
        deduplicated = self._phase1_deduplicate(students)
        sorted_students = self._phase1_sort(deduplicated)
        
        # PHASE 2: Initialize paired sections (dynamic, respecting target count)
        self._phase2_initialize_sections(sorted_students)
        
        # PHASE 3: Main allocation loop
        self._phase3_allocate(sorted_students)
        
        # PHASE 4: Post-processing optimization
        self._phase4_post_process()
        
        # Generate statistics
        stats = self._generate_stats(len(students))
        
        return self.allocation_results, stats
    
    def _phase2_load_manual_sections(self, manual_sections: List[Dict]) -> None:
        """PHASE 2: Load manually defined sections"""
        for section_def in manual_sections:
            section_number = section_def.get('section_number', 1)
            g1_course = section_def.get('g1_course')
            g2_course = section_def.get('g2_course')
            capacity = section_def.get('capacity', 70)
            
            # Validate courses exist
            if g1_course not in self.config.courses or g2_course not in self.config.courses:
                continue
            
            # Create paired section
            pair_id = f"{g1_course}+{g2_course}-Sec{section_number}"
            paired_sec = PairedSection(
                pair_id=pair_id,
                g1_course=g1_course,
                g2_course=g2_course,
                section_index=section_number,
                capacity=capacity
            )
            self.paired_sections.append(paired_sec)
    
    def _phase3_allocate_to_manual_sections(self, sorted_students: List[Student]) -> None:
        """
        PHASE 3: Enhanced allocation with load balancing and smart preference matching
        
        Algorithm:
        1. Multi-pass allocation for better distribution
        2. Weighted preference scoring
        3. Load-aware section selection
        4. Fallback with alternative course combinations
        """
        
        # PASS 1: Primary preference matching with load balancing
        pass1_unallocated = []
        for student in sorted_students:
            if not self._try_allocate_to_manual_section(student, strategy="primary_balanced"):
                pass1_unallocated.append(student)
        
        # PASS 2: Fallback allocation to alternative G2 courses
        pass2_unallocated = []
        for student in pass1_unallocated:
            if not self._try_allocate_to_manual_section(student, strategy="fallback_g2"):
                pass2_unallocated.append(student)
        
        # PASS 3: Aggressive fallback - any eligible course combination
        for student in pass2_unallocated:
            if not self._try_allocate_to_manual_section(student, strategy="aggressive_any"):
                # Final unallocated record
                result = AllocationResult(
                    registration_number=student.registration_number,
                    name=student.name,
                    allocated=False,
                    reason="No section available for any eligible course combination"
                )
                self.allocation_results.append(result)
    
    def _try_allocate_to_manual_section(self, student: Student, strategy: str) -> bool:
        """
        Try to allocate student to a manual section using specified strategy
        Returns True if allocated, False otherwise
        """
        result = AllocationResult(
            registration_number=student.registration_number,
            name=student.name
        )
        
        # Validate preferences
        validation_error = self._validate_student_preferences(student)
        if validation_error:
            result.allocated = False
            result.reason = validation_error
            self.allocation_results.append(result)
            return True  # Pass 1 complete, don't retry in later passes
        
        all_g1 = {c.course_name for c in self.config.courses.values() 
                 if c.group == Group.GROUP_1}
        all_g2 = {c.course_name for c in self.config.courses.values() 
                 if c.group == Group.GROUP_2}
        
        eligible_g1 = [c for c in student.g1_preferences 
                      if self._check_prerequisites_for_course(student, c)]
        eligible_g2 = [c for c in student.g2_preferences 
                      if self._check_prerequisites_for_course(student, c)]
        
        if not (eligible_g1 and eligible_g2):
            result.allocated = False
            result.reason = "No eligible courses after prerequisite check"
            self.allocation_results.append(result)
            return True  # Pass 1 complete
        
        # Strategy-based allocation
        if strategy == "primary_balanced":
            # Use only primary preferences (highest priority) with load balancing
            best_allocation = self._find_best_section_with_load_balancing(
                student, eligible_g1[:1], eligible_g2[:1]  # Top choice only
            )
            if best_allocation:
                section, g1_rank, g2_rank, fallback = best_allocation
                self._commit_allocation(result, section, g1_rank, g2_rank, fallback)
                section.add_student(student.registration_number)
                self.allocation_results.append(result)
                return True
        
        elif strategy == "fallback_g2":
            # Try all stated preferences with load balancing (expansion phase)
            best_allocation = self._find_best_section_with_load_balancing(
                student, eligible_g1, eligible_g2
            )
            if best_allocation:
                section, g1_rank, g2_rank, fallback = best_allocation
                self._commit_allocation(result, section, g1_rank, g2_rank, fallback)
                section.add_student(student.registration_number)
                self.allocation_results.append(result)
                return True
        
        elif strategy == "aggressive_any":
            # AGGRESSIVE: Try alternative G1 and G2 combinations (desperate phase)
            alternative_g1 = list(all_g1 - set(eligible_g1))
            alternative_g2 = list(all_g2 - set(eligible_g2))
            
            # Build expanded search space: eligible + alternatives
            search_g1 = eligible_g1 + alternative_g1
            search_g2 = eligible_g2 + alternative_g2
            
            # Filter by prerequisites for alternatives
            search_g1_filtered = [c for c in search_g1 
                                 if self._check_prerequisites_for_course(student, c)]
            search_g2_filtered = [c for c in search_g2 
                                 if self._check_prerequisites_for_course(student, c)]
            
            if search_g1_filtered and search_g2_filtered:
                best_allocation = self._find_best_section_with_load_balancing(
                    student, search_g1_filtered, search_g2_filtered
                )
                if best_allocation:
                    section, g1_rank, g2_rank, fallback = best_allocation
                    self._commit_allocation(result, section, g1_rank, g2_rank, True)  # Flag as fallback
                    section.add_student(student.registration_number)
                    self.allocation_results.append(result)
                    return True
        
        return False  # Not allocated, continue to next pass
    
    def _find_best_section_with_load_balancing(self, student: Student, 
                                              g1_courses: List[str], 
                                              g2_courses: List[str]) -> Optional[Tuple[PairedSection, int, int, bool]]:
        """
        Find best section with load balancing consideration
        
        Scoring:
        - Preference ranking (lower = better)
        - Section load (lower utilization = better)
        - CGPA fairness (ensure similar CGPA students in same section)
        
        Returns: (section, g1_rank, g2_rank, fallback_flag)
        """
        candidates = []  # List of (score, section, g1_rank, g2_rank)
        
        for g1_rank, g1_course in enumerate(g1_courses):
            if not self._check_prerequisites_for_course(student, g1_course):
                continue
            
            for g2_rank, g2_course in enumerate(g2_courses):
                if not self._check_prerequisites_for_course(student, g2_course):
                    continue
                
                # Find matching sections
                for section in self.paired_sections:
                    if (section.g1_course == g1_course and 
                        section.g2_course == g2_course and
                        section.can_accommodate()):
                        
                        # Calculate weighted score
                        score = self._calculate_section_score(
                            student, section, g1_rank, g2_rank
                        )
                        candidates.append((score, section, g1_rank, g2_rank))
        
        if not candidates:
            return None
        
        # Sort by score (lower = better) and pick best
        candidates.sort(key=lambda x: x[0])
        best_score, best_section, best_g1_rank, best_g2_rank = candidates[0]
        
        # Determine if fallback flag
        fallback = best_g1_rank > 0 or best_g2_rank > 0
        
        return best_section, best_g1_rank, best_g2_rank, fallback
    
    def _calculate_section_score(self, student: Student, section: PairedSection, 
                                g1_rank: int, g2_rank: int) -> float:
        """
        Calculate weighted score for section selection
        Lower score = better choice
        
        Factors:
        - Preference rank (weight: 40%)
        - Section utilization (weight: 40%)
        - Average CGPA difference (weight: 20%)
        """
        # Factor 1: Preference rank (0-2 for first, second, third choice)
        preference_weight = (g1_rank + g2_rank) / 2.0  # Average rank
        
        # Factor 2: Section load balancing (lower utilization = lower penalty)
        utilization = section.enrolled / section.capacity if section.capacity > 0 else 1.0
        load_weight = utilization  # 0.0-1.0
        
        # Factor 3: CGPA fairness (allocate to section with similar CGPA average)
        cgpa_fairness = 0.0
        if section.students:
            # Get average CGPA of already-allocated students in this section
            section_students = [self.student_map[sid] for sid in section.students 
                               if sid in self.student_map]
            if section_students:
                avg_cgpa = sum(s.cgpa for s in section_students) / len(section_students)
                cgpa_diff = abs(student.cgpa - avg_cgpa)
                cgpa_fairness = min(1.0, cgpa_diff / 4.0)  # Normalize to 0-1 (max 4.0 CGPA diff)
        
        # Weighted combination (lower = better)
        score = (0.4 * preference_weight + 
                0.4 * load_weight + 
                0.2 * cgpa_fairness)
        
        return score

    def _find_available_manual_section(self, g1_course: str, g2_course: str) -> Optional[PairedSection]:
        """Find available manual section with both courses - returns first with capacity"""
        for section in self.paired_sections:
            if (section.g1_course == g1_course and 
                section.g2_course == g2_course and
                section.can_accommodate()):
                return section
        return None

    # ================================================================
    # PHASE 1: INPUT VALIDATION & PREPROCESSING
    # ================================================================

    def _phase1_deduplicate(self, students: List[Student]) -> List[Student]:
        """PHASE 1.1: Deduplication - keep newest response per student"""
        by_reg = {}
        for student in sorted(students, key=lambda s: s.timestamp):
            by_reg[student.registration_number] = student
        return list(by_reg.values())
    
    def _phase1_sort(self, students: List[Student]) -> List[Student]:
        """PHASE 1.2: Sort by allocation criterion"""
        if self.allocation_criterion == "Timestamp":
            # Sort by timestamp (asc - earlier first), then CGPA (desc), then registration number
            return sorted(
                students,
                key=lambda s: (s.timestamp, -s.cgpa, s.registration_number)
            )
        else:  # Default to CGPA
            # Sort by CGPA (desc), timestamp (asc), registration_number (asc)
            return sorted(
                students,
                key=lambda s: (-s.cgpa, s.timestamp, s.registration_number)
            )

    # ================================================================
    # PHASE 2: PAIR SECTION INITIALIZATION
    # ================================================================

    def _phase2_initialize_sections(self, students: List[Student]) -> None:
        """
        PHASE 2: Section creation - either demand-driven (default) or target-based (user-specified)
        
        ALGORITHM FOR TARGET-BASED (USER-SPECIFIED):
        1. Calculate TOTAL capacity needed: students_count × 1.2 (20% buffer for fallback)
        2. Distribute exactly N sections to top N high-demand combos
        3. Each section gets equal capacity to handle total load
        4. Multi-pass fallback handles students not getting primary preferences
        
        ALGORITHM FOR DEFAULT (NO TARGET):
        - Creates flexible sections based on demand percentage
        """
        demand_groups: Dict[Tuple[str, str], int] = {}
        
        # Count FIRST PREFERENCE demand for all valid combinations
        for student in students:
            if not (student.g1_preferences and student.g2_preferences):
                continue
            
            g1_course = student.g1_preferences[0]
            g2_course = student.g2_preferences[0]
            
            # Check prerequisites before counting
            g1_ok = self._check_prerequisites_for_course(student, g1_course)
            g2_ok = self._check_prerequisites_for_course(student, g2_course)
            
            if g1_ok and g2_ok:
                key = (g1_course, g2_course)
                demand_groups[key] = demand_groups.get(key, 0) + 1
        
        if not demand_groups:
            return
        
        total_demand = sum(demand_groups.values())
        sorted_combos = sorted(demand_groups.items(), key=lambda x: x[1], reverse=True)
        
        # ==== IF TARGET SECTIONS SPECIFIED (user input) ====
        if self.target_sections and self.target_sections > 0:
            # STRATEGY: Take top N combos (N = target_sections), one section per combo
            # Calculate capacity: equal division across all sections
            
            total_students = len(students)
            # Simple division: capacity_per_section = students / target_sections
            capacity_per_section = max(50, int(total_students / self.target_sections))
            
            sections_created = 0
            
            for combo_idx, ((g1_course, g2_course), demand_count) in enumerate(sorted_combos):
                if sections_created >= self.target_sections:
                    break
                
                g1_obj = self.config.courses.get(g1_course)
                g2_obj = self.config.courses.get(g2_course)
                
                if not (g1_obj and g2_obj):
                    continue
                
                # Create ONE section for this combo
                section_id = f"S1"
                capacity = min(self.config.max_section_strength, capacity_per_section)
                
                # Create individual course sections if needed
                if section_id not in g1_obj.sections:
                    g1_obj.sections[section_id] = Section(section_id=section_id, capacity=capacity)
                if section_id not in g2_obj.sections:
                    g2_obj.sections[section_id] = Section(section_id=section_id, capacity=capacity)
                
                # Create paired section
                pair_id = f"{g1_course}+{g2_course}-Sec{combo_idx + 1}"
                paired_sec = PairedSection(
                    pair_id=pair_id,
                    g1_course=g1_course,
                    g2_course=g2_course,
                    section_index=combo_idx + 1,
                    capacity=capacity
                )
                self.paired_sections.append(paired_sec)
                sections_created += 1
        
        # ==== DEFAULT: DEMAND PERCENTAGE BASED (no target specified) ====
        else:
            for (g1_course, g2_course), count in sorted_combos:
                demand_percentage = (count / total_demand) * 100
                g1_obj = self.config.courses.get(g1_course)
                g2_obj = self.config.courses.get(g2_course)
                
                if not (g1_obj and g2_obj):
                    continue
                
                # Determine number of sections based on demand percentage
                if demand_percentage >= 40:
                    num_sections = 3 if count > 60 else 2
                    base_capacity = max(25, count // num_sections + 5)
                elif demand_percentage >= 20:
                    num_sections = 2 if count > 40 else 1
                    base_capacity = max(25, count + 10)
                elif demand_percentage >= 5:
                    num_sections = 1
                    base_capacity = max(20, count + 5)
                else:
                    num_sections = 1
                    base_capacity = count + 3
                
                # Create the required number of sections
                for sec_idx in range(1, num_sections + 1):
                    section_id = f"S{sec_idx}"
                    capacity = min(self.config.max_section_strength, base_capacity)
                    
                    # Create individual course sections if needed
                    if section_id not in g1_obj.sections:
                        g1_obj.sections[section_id] = Section(section_id=section_id, capacity=capacity)
                    if section_id not in g2_obj.sections:
                        g2_obj.sections[section_id] = Section(section_id=section_id, capacity=capacity)
                    
                    # Create paired section
                    pair_id = f"{g1_course}+{g2_course}-Sec{sec_idx}"
                    paired_sec = PairedSection(
                        pair_id=pair_id,
                        g1_course=g1_course,
                        g2_course=g2_course,
                        section_index=sec_idx,
                        capacity=capacity
                    )
                    self.paired_sections.append(paired_sec)

    # ================================================================
    # PHASE 3: MAIN ALLOCATION LOOP
    # ================================================================

    def _phase3_allocate(self, sorted_students: List[Student]) -> None:
        """PHASE 3: Main allocation with preference and fallback chains"""
        
        for student in sorted_students:
            result = AllocationResult(
                registration_number=student.registration_number,
                name=student.name
            )
            
            # Step 3.1: Validate preferences
            validation_error = self._validate_student_preferences(student)
            if validation_error:
                result.allocated = False
                result.reason = validation_error
                self.allocation_results.append(result)
                continue
            
            # Step 3.2: Rank preferences (filter by eligibility)
            g1_ranked = self._rank_preferences(student, student.g1_preferences, Group.GROUP_1)
            g2_ranked = self._rank_preferences(student, student.g2_preferences, Group.GROUP_2)
            
            if not (g1_ranked and g2_ranked):
                result.allocated = False
                result.reason = "No eligible courses after prerequisite check"
                self.allocation_results.append(result)
                continue
            
            # Step 3.3: Try preference-based allocation (nested loop through ranked)
            allocation = self._try_preference_allocation(student, g1_ranked, g2_ranked)
            if allocation:
                paired_sec, g1_rank, g2_rank = allocation
                self._commit_allocation(result, paired_sec, g1_rank, g2_rank, False)
                paired_sec.add_student(student.registration_number)
                self.allocation_results.append(result)
                continue
            
            # Step 3.4: Try fallback allocation
            if self.config.allow_open_seat_fallback:
                allocation = self._try_fallback_allocation(student, g1_ranked, g2_ranked)
                if allocation:
                    paired_sec, g1_rank, g2_rank = allocation
                    self._commit_allocation(result, paired_sec, g1_rank, g2_rank, True)
                    paired_sec.add_student(student.registration_number)
                    self.allocation_results.append(result)
                    continue
            
            # Step 3.5: Both failed - mark unallocated
            result.allocated = False
            result.reason = "No available seat in any section"
            self.allocation_results.append(result)

    # ================================================================
    # PREFERENCE VALIDATION & RANKING
    # ================================================================

    def _validate_student_preferences(self, student: Student) -> Optional[str]:
        """Validate student preferences - return error reason if invalid"""
        if not student.g1_preferences:
            return "No Group 1 preferences provided"
        if not student.g2_preferences:
            return "No Group 2 preferences provided"
        
        # Validate course codes exist and belong to correct groups
        for course_name in student.g1_preferences:
            # Try to find course by normalized name first
            course_code = self._get_course_code_by_name(course_name)
            if not course_code:
                # If not found, try direct lookup (backwards compatibility)
                course_code = course_name if course_name in self.config.courses else None
            
            if not course_code:
                return f"❌ Invalid G1 course: '{course_name}' (not found in config)"
            
            actual_course = self.config.courses[course_code]
            if actual_course.group != Group.GROUP_1:
                return f"❌ Course '{course_name}' is configured as GROUP {actual_course.group.value}, expected GROUP 1. Check your config file."
        
        for course_name in student.g2_preferences:
            # Try to find course by normalized name first
            course_code = self._get_course_code_by_name(course_name)
            if not course_code:
                # If not found, try direct lookup (backwards compatibility)
                course_code = course_name if course_name in self.config.courses else None
            
            if not course_code:
                return f"❌ Invalid G2 course: '{course_name}' (not found in config)"
            
            actual_course = self.config.courses[course_code]
            if actual_course.group != Group.GROUP_2:
                return f"❌ Course '{course_name}' is configured as GROUP {actual_course.group.value}, expected GROUP 2. Check your config file."
        
        return None
    
    def _rank_preferences(self, student: Student, preferences: List[str], group: Group) -> List[Tuple[int, str]]:
        """Rank preferences by eligibility - only include if prerequisites met"""
        ranked = []
        for rank, course_name in enumerate(preferences):
            # Normalize course name lookup
            course_code = self._get_course_code_by_name(course_name)
            if not course_code:
                # Fallback to direct lookup
                course_code = course_name if course_name in self.config.courses else None
            
            if course_code and self._check_prerequisites_for_course(student, course_code):
                ranked.append((rank, course_name))  # Keep original name for later lookup
        return ranked
    
    def _check_prerequisites_for_course(self, student: Student, course_code: str) -> bool:
        """Check if student meets prerequisites for a single course"""
        if course_code not in self.config.courses:
            return False
        
        course = self.config.courses[course_code]
        return all(p in student.completed_courses for p in course.prerequisites)

    # ================================================================
    # ALLOCATION STRATEGIES
    # ================================================================

    def _try_preference_allocation(self, student: Student, g1_ranked: List[Tuple[int, str]], 
                                  g2_ranked: List[Tuple[int, str]]) -> Optional[Tuple[PairedSection, int, int]]:
        """
        Enhanced preference-based allocation with load balancing
        Returns section with best score (preference + load)
        """
        candidates = []
        
        for g1_rank, g1_course in g1_ranked:
            for g2_rank, g2_course in g2_ranked:
                available_sections = []
                # Normalize both preference course names and section course names for comparison
                g1_norm = self._normalize_course_name(g1_course)
                g2_norm = self._normalize_course_name(g2_course)
                
                for ps in self.paired_sections:
                    ps_g1_norm = self._normalize_course_name(ps.g1_course)
                    ps_g2_norm = self._normalize_course_name(ps.g2_course)
                    
                    if (ps_g1_norm == g1_norm and ps_g2_norm == g2_norm and 
                        ps.can_accommodate()):
                        available_sections.append(ps)
                
                for paired_sec in available_sections:
                    score = self._calculate_section_score(student, paired_sec, g1_rank, g2_rank)
                    candidates.append((score, paired_sec, g1_rank, g2_rank))
        
        if not candidates:
            return None
        
        # Sort by score and return best
        candidates.sort(key=lambda x: x[0])
        _, best_section, best_g1_rank, best_g2_rank = candidates[0]
        return best_section, best_g1_rank, best_g2_rank
    
    def _try_fallback_allocation(self, student: Student, g1_ranked: List[Tuple[int, str]], 
                                g2_ranked: List[Tuple[int, str]]) -> Optional[Tuple[PairedSection, int, int]]:
        """
        Enhanced fallback allocation with intelligent course mixing
        
        Priority order:
        1. Try all G1+G2 preference combinations (ranked by preference index)
        2. Try alternative G2s with preferred G1 (G1 from preferences + other G2s)
        3. Try alternative G1s with preferred G2 (other G1s + G2 from preferences)
        4. Pick best section by CGPA fairness (load-balanced)
        
        Returns: (section, g1_preference_rank, g2_preference_rank) or None
        """
        candidates = []
        
        # Build all eligible courses from preferences
        all_eligible_g1 = []
        all_eligible_g2 = []
        
        for rank, course in enumerate(student.g1_preferences):
            if self._check_prerequisites_for_course(student, course):
                all_eligible_g1.append((rank, course))
        
        for rank, course in enumerate(student.g2_preferences):
            if self._check_prerequisites_for_course(student, course):
                all_eligible_g2.append((rank, course))
        
        if not (all_eligible_g1 and all_eligible_g2):
            return None
        
        # Get all available courses from config (for hybrid matching)
        all_g1_courses = [c.course_name for c in self.config.courses.values() 
                         if c.group == Group.GROUP_1]
        all_g2_courses = [c.course_name for c in self.config.courses.values() 
                         if c.group == Group.GROUP_2]
        
        # ===== PRIORITY 1: Try all G1+G2 preference combinations =====
        for g1_rank, g1_course in all_eligible_g1:
            for g2_rank, g2_course in all_eligible_g2:
                # Normalize course names for comparison
                g1_norm = self._normalize_course_name(g1_course)
                g2_norm = self._normalize_course_name(g2_course)
                
                for paired_sec in self.paired_sections:
                    ps_g1_norm = self._normalize_course_name(paired_sec.g1_course)
                    ps_g2_norm = self._normalize_course_name(paired_sec.g2_course)
                    
                    if (ps_g1_norm == g1_norm and 
                        ps_g2_norm == g2_norm and 
                        paired_sec.can_accommodate()):
                        score = self._calculate_section_score(student, paired_sec, g1_rank, g2_rank)
                        candidates.append((score, paired_sec, g1_rank, g2_rank, "preference_match"))
        
        # If priority 1 found matches, return best
        if candidates:
            candidates.sort(key=lambda x: x[0])
            _, best_section, best_g1_rank, best_g2_rank, _ = candidates[0]
            return best_section, best_g1_rank, best_g2_rank
        
        candidates = []
        
        # ===== PRIORITY 2: Try G1 preferences + any available G2 =====
        for g1_rank, g1_course in all_eligible_g1:
            g1_norm = self._normalize_course_name(g1_course)
            
            for paired_sec in self.paired_sections:
                ps_g1_norm = self._normalize_course_name(paired_sec.g1_course)
                
                if (ps_g1_norm == g1_norm and paired_sec.can_accommodate()):
                    # Check if other G2 is eligible (no prerequisite check needed, just exists)
                    other_g2 = paired_sec.g2_course
                    g2_rank = len(student.g2_preferences)  # Mark as fallback (lower rank)
                    score = self._calculate_section_score(student, paired_sec, g1_rank, g2_rank)
                    candidates.append((score, paired_sec, g1_rank, g2_rank, "g1_match_g2_fallback"))
        
        # ===== PRIORITY 3: Try any available G1 + G2 preferences =====
        for g2_rank, g2_course in all_eligible_g2:
            g2_norm = self._normalize_course_name(g2_course)
            
            for paired_sec in self.paired_sections:
                ps_g2_norm = self._normalize_course_name(paired_sec.g2_course)
                
                if (ps_g2_norm == g2_norm and paired_sec.can_accommodate()):
                    # Other G1 is already in section
                    other_g1 = paired_sec.g1_course
                    g1_rank = len(student.g1_preferences)  # Mark as fallback
                    score = self._calculate_section_score(student, paired_sec, g1_rank, g2_rank)
                    candidates.append((score, paired_sec, g1_rank, g2_rank, "g1_fallback_g2_match"))
        
        # Return best candidate (sorted by score)
        if candidates:
            candidates.sort(key=lambda x: x[0])
            _, best_section, best_g1_rank, best_g2_rank, _ = candidates[0]
            return best_section, best_g1_rank, best_g2_rank
        
        return None
    
    def _find_available_paired_section(self, g1_code: str, g2_code: str) -> Optional[PairedSection]:
        """Find first available paired section with capacity - sorted by index"""
        # Normalize course names for comparison
        g1_norm = self._normalize_course_name(g1_code)
        g2_norm = self._normalize_course_name(g2_code)
        
        available = []
        for ps in self.paired_sections:
            ps_g1_norm = self._normalize_course_name(ps.g1_course)
            ps_g2_norm = self._normalize_course_name(ps.g2_course)
            
            if (ps_g1_norm == g1_norm and ps_g2_norm == g2_norm and 
                ps.can_accommodate()):
                available.append(ps)
        
        if not available:
            return None
        
        # Return section with lowest index
        return min(available, key=lambda s: (s.section_index, s.pair_id))
    
    def _find_or_create_paired_section(self, g1_code: str, g2_code: str) -> Optional[PairedSection]:
        """Find paired section or return existing (even if full) for fallback"""
        # Normalize course names for comparison
        g1_norm = self._normalize_course_name(g1_code)
        g2_norm = self._normalize_course_name(g2_code)
        
        for ps in self.paired_sections:
            ps_g1_norm = self._normalize_course_name(ps.g1_course)
            ps_g2_norm = self._normalize_course_name(ps.g2_course)
            
            if ps_g1_norm == g1_norm and ps_g2_norm == g2_norm:
                return ps
        
        return None

    # ================================================================
    # ALLOCATION COMMITMENT
    # ================================================================

    def _commit_allocation(self, result: AllocationResult, paired_sec: PairedSection, 
                          g1_rank: int, g2_rank: int, fallback_used: bool) -> None:
        """Commit allocation result with proper state synchronization"""
        result.g1_course = paired_sec.g1_course
        result.g2_course = paired_sec.g2_course
        result.g1_section = str(paired_sec.section_index)
        result.g2_section = str(paired_sec.section_index)
        result.pair_label = paired_sec.get_label()
        result.g1_preference_rank = g1_rank
        result.g2_preference_rank = g2_rank
        result.fallback_used = fallback_used
        result.allocated = True

    # ================================================================
    # PHASE 4: POST-PROCESSING OPTIMIZATION
    # ================================================================

    def _phase4_post_process(self) -> None:
        """PHASE 4: Post-processing - merge tiny sections and compact underfilled"""
        self._merge_tiny_sections()
        self._compact_underfilled_sections()
    
    def _merge_tiny_sections(self) -> None:
        """Merge paired sections with < threshold students into other sections"""
        threshold = self.config.min_section_merge_threshold
        course_pairs = self._get_course_pairs()
        
        for (g1_code, g2_code) in course_pairs:
            sections = self._get_paired_sections_for_courses(g1_code, g2_code)
            sections.sort(key=lambda x: x.section_index)
            
            # Scan backwards to avoid skipping merges
            for i in range(len(sections) - 1, 0, -1):
                target = sections[i - 1]
                source = sections[i]
                
                # Conditions for merge:
                # 1. Both have students
                # 2. Target is full
                # 3. Source is tiny (< threshold)
                if not (source.students and target.students):
                    continue
                
                if not target.is_full():
                    continue
                
                if source.enrolled > threshold:
                    continue
                
                # Merge source into target
                for student_id in source.students:
                    target.add_student(student_id)
                    target.capacity += 1  # Expand target
                    
                    # Update allocation results
                    for result in self.allocation_results:
                        if result.registration_number == student_id:
                            result.g1_section = str(target.section_index)
                            result.g2_section = str(target.section_index)
                            result.pair_label = target.get_label()
                            break
                
                source.students = []
                source.enrolled = 0
    
    def _compact_underfilled_sections(self) -> None:
        """Compact underfilled sections that have < threshold and another section is full"""
        threshold = self.config.compact_section_threshold
        course_pairs = self._get_course_pairs()
        
        for (g1_code, g2_code) in course_pairs:
            sections = self._get_paired_sections_for_courses(g1_code, g2_code)
            
            # Find underfilled and full sections
            underfilled = [s for s in sections if 0 < s.enrolled < threshold]
            full_sections = [s for s in sections if s.is_full()]
            
            if not (underfilled and full_sections):
                continue
            
            # Consolidate underfilled students
            for underfilled_sec in underfilled:
                # Sort students by merit for reassignment priority
                students_to_move = list(underfilled_sec.students)
                students_to_move.sort(
                    key=lambda r: (
                        -self.student_map[r].cgpa if r in self.student_map else 0,
                        self.student_map[r].timestamp if r in self.student_map else datetime.now(),
                        r
                    )
                )
                
                # Try to move each student to another section
                for student_id in students_to_move:
                    moved = False
                    
                    for target_sec in sections:
                        if (target_sec.pair_id != underfilled_sec.pair_id and 
                            target_sec.can_accommodate(1)):
                            # Move student
                            underfilled_sec.remove_student(student_id)
                            target_sec.add_student(student_id)
                            
                            # Update result
                            for result in self.allocation_results:
                                if result.registration_number == student_id:
                                    result.g1_section = str(target_sec.section_index)
                                    result.g2_section = str(target_sec.section_index)
                                    result.pair_label = target_sec.get_label()
                                    break
                            
                            moved = True
                            break
                    
                    if not moved:
                        # Can't move - unallocate
                        underfilled_sec.remove_student(student_id)
                        for result in self.allocation_results:
                            if result.registration_number == student_id:
                                result.allocated = False
                                result.reason = "Section compaction - no alternative available"
                                break

    # ================================================================
    # UTILITY METHODS
    # ================================================================

    def _get_course_pairs(self) -> Set[Tuple[str, str]]:
        """Get all unique course pairs from paired sections"""
        pairs = set()
        for ps in self.paired_sections:
            pairs.add((ps.g1_course, ps.g2_course))
        return pairs
    
    def _get_paired_sections_for_courses(self, g1_code: str, g2_code: str) -> List[PairedSection]:
        """Get all paired sections for given courses"""
        return [ps for ps in self.paired_sections 
                if ps.g1_course == g1_code and ps.g2_course == g2_code]
    
    def _generate_stats(self, total_students: int) -> AllocationStats:
        """
        Generate advanced allocation statistics with fairness metrics
        
        Metrics computed:
        - Allocation rate: % of students allocated
        - CGPA fairness: How fairly students distributed by merit
        - Preference rank: How well preferences matched
        - Section load variance: How balanced sections are
        - Course distribution: How evenly distributed across courses
        """
        allocated = [r for r in self.allocation_results if r.allocated]
        unallocated = [r for r in self.allocation_results if not r.allocated]
        fallback_count = sum(1 for r in allocated if r.fallback_used)
        
        # Distribution tracking
        g1_dist = {}
        g2_dist = {}
        section_dist = {}
        
        for result in allocated:
            g1_dist[result.g1_course] = g1_dist.get(result.g1_course, 0) + 1
            g2_dist[result.g2_course] = g2_dist.get(result.g2_course, 0) + 1
            section_dist[result.pair_label] = section_dist.get(result.pair_label, 0) + 1
        
        # Compute CGPA Fairness Score (0-100)
        # High score = fair distribution across merit levels
        cgpa_fairness = self._compute_cgpa_fairness_score(allocated, unallocated)
        
        # Compute average preference rank (lower = better matching)
        avg_preference_rank = self._compute_avg_preference_rank(allocated)
        
        # Compute section load variance (lower = more balanced)
        section_load_variance = self._compute_section_load_variance()
        
        return AllocationStats(
            total_students=total_students,
            allocated_students=len(allocated),
            unallocated_students=len(unallocated),
            fallback_used_count=fallback_count,
            allocation_rate=len(allocated) / total_students if total_students > 0 else 0.0,
            cgpa_fairness_score=cgpa_fairness,
            avg_preference_rank=avg_preference_rank,
            section_load_variance=section_load_variance,
            g1_distribution=g1_dist,
            g2_distribution=g2_dist,
            section_distribution=section_dist
        )
    
    def _compute_cgpa_fairness_score(self, allocated: List[AllocationResult], 
                                    unallocated: List[AllocationResult]) -> float:
        """
        Compute fairness score based on CGPA distribution
        
        High fairness = students with all CGPA levels have similar allocation rate
        Score: 0-100 (100 = perfect fairness)
        """
        if not allocated and not unallocated:
            return 0.0
        
        all_results = allocated + unallocated
        
        # Group by CGPA band
        cgpa_bands = {
            "9.5+": [],
            "9.0-9.5": [],
            "8.5-9.0": [],
            "8.0-8.5": [],
            "below 8.0": []
        }
        
        for result in all_results:
            student = self.student_map.get(result.registration_number)
            if student:
                cgpa = student.cgpa
                if cgpa >= 9.5:
                    cgpa_bands["9.5+"].append(result.allocated)
                elif cgpa >= 9.0:
                    cgpa_bands["9.0-9.5"].append(result.allocated)
                elif cgpa >= 8.5:
                    cgpa_bands["8.5-9.0"].append(result.allocated)
                elif cgpa >= 8.0:
                    cgpa_bands["8.0-8.5"].append(result.allocated)
                else:
                    cgpa_bands["below 8.0"].append(result.allocated)
        
        # Calculate allocation rate per band
        band_rates = []
        for band, results in cgpa_bands.items():
            if results:
                rate = sum(results) / len(results)
                band_rates.append(rate)
        
        if not band_rates:
            return 0.0
        
        # Fairness = how close all rates are to average (lower variance = higher fairness)
        avg_rate = sum(band_rates) / len(band_rates)
        variance = sum((rate - avg_rate) ** 2 for rate in band_rates) / len(band_rates)
        fairness_score = max(0, 100 - (variance * 1000))  # Convert to 0-100 scale
        
        return min(100, fairness_score)  # Cap at 100
    
    def _compute_avg_preference_rank(self, allocated: List[AllocationResult]) -> float:
        """
        Compute average preference rank
        Lower = students got their top preferences
        """
        if not allocated:
            return 0.0
        
        total_rank = 0
        for result in allocated:
            g1_rank = result.g1_preference_rank or 0
            g2_rank = result.g2_preference_rank or 0
            total_rank += (g1_rank + g2_rank) / 2.0
        
        return total_rank / len(allocated) if allocated else 0.0
    
    def _compute_section_load_variance(self) -> float:
        """
        Compute variance of section capacity utilization
        Lower variance = more balanced load
        """
        if not self.paired_sections:
            return 0.0
        
        utilizations = []
        for section in self.paired_sections:
            util = section.enrolled / section.capacity if section.capacity > 0 else 0.0
            utilizations.append(util)
        
        avg_util = sum(utilizations) / len(utilizations) if utilizations else 0.0
        variance = sum((u - avg_util) ** 2 for u in utilizations) / len(utilizations)
        
        return variance

    # ================================================================
    # SECTION MANAGEMENT - Clear/Reset Sections
    # ================================================================

    def clear_section(self, section_id: str) -> Dict:
        """
        Clear (remove all students) from a specific paired section
        
        Args:
            section_id: The pair_id of the section to clear
        
        Returns:
            Dictionary with details of cleared section
        """
        for section in self.paired_sections:
            if section.pair_id == section_id:
                return section.clear_section()
        
        return {
            "status": "error",
            "message": f"Section {section_id} not found"
        }

    def clear_section_by_label(self, g1_course: str, g2_course: str, section_index: int) -> Dict:
        """
        Clear a section by its course combination and index
        
        Args:
            g1_course: Group 1 course name
            g2_course: Group 2 course name
            section_index: Section number
        
        Returns:
            Dictionary with details of cleared section
        """
        for section in self.paired_sections:
            if (section.g1_course == g1_course and 
                section.g2_course == g2_course and 
                section.section_index == section_index):
                return section.clear_section()
        
        return {
            "status": "error",
            "message": f"Section {g1_course} + {g2_course} - Section {section_index} not found"
        }

    def clear_all_sections(self) -> Dict:
        """
        Clear all paired sections
        
        Returns:
            Dictionary with summary of cleared sections
        """
        total_removed = 0
        cleared_sections = []
        
        for section in self.paired_sections:
            result = section.clear_section()
            total_removed += result["removed_count"]
            cleared_sections.append({
                "section": result["section_label"],
                "students_removed": result["removed_count"]
            })
        
        # Also clear allocation results
        self.allocation_results = []
        
        return {
            "status": "success",
            "total_sections_cleared": len(cleared_sections),
            "total_students_removed": total_removed,
            "details": cleared_sections
        }

    def get_section_status(self, section_id: str = None) -> Dict:
        """
        Get status of one or all sections
        
        Args:
            section_id: Optional specific section ID. If None, returns all sections
        
        Returns:
            Dictionary with section status information
        """
        if section_id:
            for section in self.paired_sections:
                if section.pair_id == section_id:
                    return {
                        "pair_id": section.pair_id,
                        "label": section.get_label(),
                        "capacity": section.capacity,
                        "enrolled": section.enrolled,
                        "available_seats": section.available_seats(),
                        "load_percentage": section.get_load_percentage(),
                        "is_full": section.is_full(),
                        "is_empty": section.is_empty(),
                        "student_count": len(section.students)
                    }
            return {"status": "error", "message": f"Section {section_id} not found"}
        
        # Return all sections status
        sections_status = []
        for section in self.paired_sections:
            sections_status.append({
                "pair_id": section.pair_id,
                "label": section.get_label(),
                "capacity": section.capacity,
                "enrolled": section.enrolled,
                "available_seats": section.available_seats(),
                "load_percentage": section.get_load_percentage(),
                "is_full": section.is_full(),
                "is_empty": section.is_empty()
            })
        
        return {
            "total_sections": len(self.paired_sections),
            "sections": sections_status
        }

    def get_students_in_section(self, section_id: str) -> Dict:
        """
        Get list of all students in a specific section
        
        Args:
            section_id: The pair_id of the section
        
        Returns:
            Dictionary with student list
        """
        for section in self.paired_sections:
            if section.pair_id == section_id:
                students = []
                for student_id in section.students:
                    # Try to find student details from results
                    for result in self.allocation_results:
                        if result.registration_number == student_id:
                            students.append({
                                "registration": student_id,
                                "name": result.name,
                                "g1_course": result.g1_course,
                                "g2_course": result.g2_course
                            })
                            break
                
                return {
                    "section_label": section.get_label(),
                    "total_students": len(section.students),
                    "students": students
                }
        
        return {"status": "error", "message": f"Section {section_id} not found"}

    def rebalance_section(self, section_id: str, new_capacity: int) -> Dict:
        """
        Rebalance a section's capacity
        If new capacity is less than enrolled, clear the section first
        
        Args:
            section_id: The pair_id of the section
            new_capacity: New capacity for the section
        
        Returns:
            Dictionary with rebalancing details
        """
        for section in self.paired_sections:
            if section.pair_id == section_id:
                old_capacity = section.capacity
                old_enrolled = section.enrolled
                
                if new_capacity < old_enrolled:
                    # Clear section first
                    clear_result = section.clear_section()
                    section.capacity = new_capacity
                    
                    return {
                        "status": "rebalanced_with_clear",
                        "section_label": section.get_label(),
                        "old_capacity": old_capacity,
                        "new_capacity": new_capacity,
                        "students_cleared": clear_result["removed_count"],
                        "message": f"Section capacity reduced from {old_capacity} to {new_capacity}. All {clear_result['removed_count']} students removed."
                    }
                else:
                    section.capacity = new_capacity
                    
                    return {
                        "status": "rebalanced",
                        "section_label": section.get_label(),
                        "old_capacity": old_capacity,
                        "new_capacity": new_capacity,
                        "currently_enrolled": old_enrolled,
                        "message": f"Section capacity updated from {old_capacity} to {new_capacity}"
                    }
        
        return {"status": "error", "message": f"Section {section_id} not found"}

    def analyze_course_combinations(self, students: List[Student]) -> Dict:
        """
        Analyze G1+G2 course combinations chosen by students
        Shows demand for different course pairings
        
        Args:
            students: List of Student objects
        
        Returns:
            Dictionary with combination statistics including:
            - combinations: List of (g1_course, g2_course, count, percentage)
            - total_students: Total number of students
            - top_combination: Most popular combination
            - combinations_count: Total number of unique combinations
        """
        if not students:
            return {"status": "error", "message": "No students provided"}
        
        # Dictionary to store combination counts
        combination_counts = {}
        
        for student in students:
            # Get first preference for G1 and G2
            g1_pref = student.g1_preferences[0] if student.g1_preferences else "Unspecified"
            g2_pref = student.g2_preferences[0] if student.g2_preferences else "Unspecified"
            
            # Create combination key
            combination_key = (g1_pref, g2_pref)
            
            # Increment count
            combination_counts[combination_key] = combination_counts.get(combination_key, 0) + 1
        
        total_students = len(students)
        
        # Convert to list and sort by count (descending)
        combinations_list = []
        for (g1, g2), count in sorted(combination_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_students) * 100
            combinations_list.append({
                "g1_course": g1,
                "g2_course": g2,
                "student_count": count,
                "percentage": round(percentage, 2),
                "pair_id": f"{g1}+{g2}"
            })
        
        # Get top combination
        top_combination = combinations_list[0] if combinations_list else None
        
        return {
            "status": "success",
            "total_students": total_students,
            "unique_combinations": len(combinations_list),
            "top_combination": top_combination,
            "combinations": combinations_list
        }

