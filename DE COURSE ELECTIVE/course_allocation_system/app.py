import streamlit as st
import pandas as pd
from pathlib import Path
import os
import tempfile
import re

from data_processor import DataProcessor
from allocation_engine import AllocationEngine
from output_generator import OutputGenerator

# Page configuration
st.set_page_config(page_title='Course Allocation System', layout='wide', initial_sidebar_state='expanded')

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding-top: 2rem;
    }
    .section-header {
        font-size: 24px;
        font-weight: bold;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #366092;
        padding-bottom: 0.5rem;
    }
    .step-header {
        font-size: 18px;
        font-weight: bold;
        background-color: #f0f2f6;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        margin-top: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'regular_students' not in st.session_state:
    st.session_state.regular_students = None
if 'research_students' not in st.session_state:
    st.session_state.research_students = None
if 'courses' not in st.session_state:
    st.session_state.courses = []
if 'allocation_result' not in st.session_state:
    st.session_state.allocation_result = None
if 'course_config' not in st.session_state:
    st.session_state.course_config = {}


def _single_prompt_examples():
    return [
        "Show students allocated to ML section 2",
        "List waitlisted students",
        "Give me allocation summary",
        "Show course-wise utilization",
        "List research/special allocated students",
    ]


def _extract_section_number(question):
    match = re.search(r"\b(?:section|sec)\s*(\d+)\b", str(question).lower())
    return match.group(1) if match else None


def _extract_course_name(question, course_names):
    q = str(question or "").lower()
    for course in course_names:
        c = str(course or "").strip()
        if c and c.lower() in q:
            return c
    return None


def _run_single_results_assistant(question, result):
    q = str(question or "").strip()
    lower = q.lower()

    if not q:
        return {
            "kind": "text",
            "title": "Ask a question",
            "message": "Type a question or choose an example prompt.",
        }

    stats = result.get('statistics', {})
    allocated = result.get('allocated_students', [])
    waitlist = result.get('waitlist', [])
    course_stats = stats.get('courses', {})
    course_names = list(course_stats.keys())

    if "summary" in lower or "how many" in lower or "total" in lower:
        return {
            "kind": "summary",
            "title": "Allocation Summary",
            "summary": {
                "Total Students": stats.get('total_students', 0),
                "Allocated": stats.get('allocated', 0),
                "Waitlisted": stats.get('waitlisted', 0),
                "Success Rate %": round((stats.get('allocated', 0) / max(stats.get('total_students', 1), 1)) * 100, 2),
            },
        }

    if "waitlist" in lower or "waitlisted" in lower or "unallocated" in lower:
        rows = [
            {
                "Name": s.get('name', ''),
                "Reg No": s.get('reg_no', ''),
                "CGPA": s.get('cgpa', ''),
                "Type": s.get('student_type', ''),
                "Reason": s.get('allocation_reason', 'Unknown'),
            }
            for s in waitlist
        ]
        return {
            "kind": "table",
            "title": "Waitlisted Students",
            "message": f"Found {len(rows)} waitlisted students.",
            "rows": rows,
        }

    if "course-wise" in lower or "utilization" in lower or "course wise" in lower:
        rows = [
            {
                "Course": name,
                "Sections": c_stat.get('sections', 0),
                "Capacity": c_stat.get('total_capacity', 0),
                "Allocated": c_stat.get('total_allocated', 0),
                "Unfilled": c_stat.get('unfilled', 0),
                "Utilization %": round(c_stat.get('utilization_percent', 0), 2),
            }
            for name, c_stat in course_stats.items()
        ]
        return {
            "kind": "table",
            "title": "Course-wise Utilization",
            "message": f"Showing {len(rows)} courses.",
            "rows": rows,
        }

    if "research" in lower or "special" in lower:
        rows = [
            {
                "Name": s.get('name', ''),
                "Reg No": s.get('reg_no', ''),
                "CGPA": s.get('cgpa', ''),
                "Allocated Course": s.get('allocated_course', 'N/A'),
                "Section": s.get('allocation_section_display', s.get('allocation_section_id', 'N/A')),
                "Status": s.get('allocation_status', 'Allocated'),
            }
            for s in allocated
            if s.get('student_type') == 'Research/Special'
        ]
        return {
            "kind": "table",
            "title": "Research/Special Allocated Students",
            "message": f"Found {len(rows)} research/special allocated students.",
            "rows": rows,
        }

    section = _extract_section_number(q)
    course = _extract_course_name(q, course_names)

    filtered = allocated
    if course:
        filtered = [
            s for s in filtered
            if str(s.get('allocated_course', '')).strip().lower() == str(course).strip().lower()
        ]
    if section:
        filtered = [
            s for s in filtered
            if str(section) in str(s.get('allocation_section_display', s.get('allocation_section_id', '')))
        ]

    if filtered:
        rows = [
            {
                "Name": s.get('name', ''),
                "Reg No": s.get('reg_no', ''),
                "CGPA": s.get('cgpa', ''),
                "Allocated Course": s.get('allocated_course', 'N/A'),
                "Section": s.get('allocation_section_display', s.get('allocation_section_id', 'N/A')),
                "Preference": s.get('preference_rank', 'N/A'),
                "Type": s.get('student_type', ''),
            }
            for s in filtered
        ]
        return {
            "kind": "table",
            "title": "Filtered Allocated Students",
            "message": f"Matched {len(rows)} students.",
            "rows": rows,
        }

    return {
        "kind": "text",
        "title": "No direct match found",
        "message": "Try a prompt like 'Show students allocated to ML section 2' or 'List waitlisted students'.",
    }

def step_1_upload_students():
    """Step 1: Upload student files"""
    st.markdown('<div class="section-header">Step 1: Upload Student Lists</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 Regular Students")
        st.write("Upload Excel file with regular student data")
        st.write("**Expected columns:** Name, Reg No, CGPA, Course Preferences (Choice 1, Choice 2, etc.), Completed Courses (Optional)")
        
        regular_file = st.file_uploader("Regular Students", type=['xlsx', 'xls'], key='regular_students_file')
        
        if regular_file:
            try:
                df, col_map = DataProcessor.read_regular_students(regular_file)
                st.success(f"✓ Loaded {len(df)} regular students")
                
                # Display detected columns
                with st.expander("View Detected Columns"):
                    st.json({
                        'Name Column': col_map['name'],
                        'Reg No Column': col_map['reg_no'],
                        'CGPA Column': col_map['cgpa'],
                        'Preference Columns': col_map['preferences'],
                        'Completed Courses Column': col_map.get('completed', 'Not found')
                    })
                
                # Preview data
                with st.expander("Preview Data"):
                    st.dataframe(df.head(10), use_container_width=True)
                
                # Store processed data
                students = []
                for idx in range(len(df)):
                    student = DataProcessor.get_student_data(df, col_map, idx)
                    students.append(student)
                
                st.session_state.regular_students = students
                st.session_state.regular_col_map = col_map
                st.session_state.regular_df = df
                
            except Exception as e:
                st.error(f"Error processing file: {str(e)}")
    
    with col2:
        st.subheader("🔬 Research/Special Students")
        st.write("Upload Excel file with research student data (Optional)")
        st.write("**Expected columns:** Name, Reg No, CGPA, Course Preferences, Completed Courses (Optional)")
        
        research_file = st.file_uploader("Research Students", type=['xlsx', 'xls'], key='research_students_file')
        
        if research_file:
            try:
                df, col_map = DataProcessor.read_research_students(research_file)
                st.success(f"✓ Loaded {len(df)} research students")
                
                with st.expander("View Detected Columns"):
                    st.json({
                        'Name Column': col_map['name'],
                        'Reg No Column': col_map['reg_no'],
                        'CGPA Column': col_map['cgpa'],
                        'Preference Columns': col_map['preferences'],
                        'Completed Courses Column': col_map.get('completed', 'Not found')
                    })
                
                with st.expander("Preview Data"):
                    st.dataframe(df.head(10), use_container_width=True)
                
                students = []
                for idx in range(len(df)):
                    student = DataProcessor.get_student_data(df, col_map, idx)
                    students.append(student)
                
                st.session_state.research_students = students
                st.session_state.research_col_map = col_map
                st.session_state.research_df = df
            
            except Exception as e:
                st.error(f"Error processing file: {str(e)}")
    
    # Remove duplicates between regular and research students
    # Keep students ONLY in their research/special section list
    if st.session_state.regular_students and st.session_state.research_students:
        research_reg_nos = {student['reg_no'] for student in st.session_state.research_students}
        
        # Find duplicates - students that are in both lists
        duplicates = []
        filtered_regular = []
        
        for student in st.session_state.regular_students:
            if student['reg_no'] in research_reg_nos:
                # This student is ALSO in research list - remove from regular
                duplicates.append(student)
            else:
                # Keep in regular list
                filtered_regular.append(student)
        
        # Remove duplicates from REGULAR students (keep ONLY in research/special)
        if duplicates:
            st.session_state.regular_students = filtered_regular
            
            # Display warning about removed duplicates
            with st.warning(f"⚠️ **Duplicate Students Removed from Regular List**: {len(duplicates)} student(s)"):
                dup_names = ', '.join([f"{s['name']} ({s['reg_no']})" for s in duplicates])
                st.write(f"**Removed from Regular Students:** {dup_names}")
                st.write("**Action:** These students will be allocated ONLY to Special/Research sections.")
    
    # Display course registration summary
    if st.session_state.regular_students or st.session_state.research_students:
        st.divider()
        st.subheader("📊 Course Registration Summary (Excluding Completed Courses)")
        
        # Combine all students
        all_students = (st.session_state.regular_students or []) + (st.session_state.research_students or [])
        total_students = len(all_students)
        
        # Count students per course by preference order (excluding completed courses)
        course_preference_counts = {}  # {course: {1: count, 2: count, 3: count, ...}}
        course_total_counts = {}  # {course: total_count}
        students_with_preferences = 0
        
        for student in all_students:
            preferences = student.get('preferences', [])
            completed_courses = set(student.get('completed_courses', []))
            
            has_active_preference = False
            for pref_idx, course in enumerate(preferences, 1):  # 1-indexed preference
                if course and course not in completed_courses:  # Skip empty and completed courses
                    # Initialize course if not seen
                    if course not in course_preference_counts:
                        course_preference_counts[course] = {}
                        course_total_counts[course] = 0
                    
                    # Count this preference
                    course_preference_counts[course][pref_idx] = course_preference_counts[course].get(pref_idx, 0) + 1
                    course_total_counts[course] += 1
                    has_active_preference = True
            
            if has_active_preference:
                students_with_preferences += 1
        
        # Sort by total count (descending)
        sorted_courses = sorted(course_total_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Display statistics
        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
        with col_stat1:
            st.metric("Total Students", total_students)
        with col_stat2:
            st.metric("Active Students", students_with_preferences, 
                     help="Students with at least 1 non-completed course preference")
        with col_stat3:
            st.metric("Unique Courses", len(course_total_counts))
        with col_stat4:
            avg_students = round(students_with_preferences / len(course_total_counts), 1) if course_total_counts else 0
            st.metric("Avg Students/Course", avg_students)
        
        # Display detailed course-wise registration by preference
        st.write("**Students per Course by Preference Order (excluding already-completed courses):**")
        st.caption("📌 Suggested sections based on **1st preference count only** (solid demand)")
        
        # Create detailed breakdown
        for course, total_count in sorted_courses:
            # Get preference breakdown for this course
            pref_breakdown = course_preference_counts.get(course, {})
            
            # Create display string for preference breakdown
            pref_strings = []
            for pref_idx in sorted(pref_breakdown.keys()):
                count = pref_breakdown[pref_idx]
                pref_strings.append(f"Pref {pref_idx}: {count}")
            
            pref_display = " | ".join(pref_strings) if pref_strings else "No preferences"
            
            # Estimate sections based on 1st preference count only
            first_pref_count = pref_breakdown.get(1, 0)
            recommended_sections = max(1, round(first_pref_count / 72))
            
            # Display in columns
            col1, col2, col3, col4 = st.columns([1.5, 3.5, 1.5, 1.5])
            with col1:
                st.write(f"**{course}**")
            with col2:
                st.write(pref_display)
            with col3:
                st.write(f"**Total: {total_count}** ({(total_count/students_with_preferences)*100:.1f}%)")
            with col4:
                st.write(f"📌 **{recommended_sections}** sections")
            
            st.divider()
        
        with st.info(
            "💡 **Tip:** This shows how many students prefer each course as their 1st, 2nd, 3rd choice, etc. "
            "Use the totals to guide section configuration in Step 3. "
            "For example, if a course has 148 total students, we recommend 2-3 sections with ~72 capacity each."
        ):
            pass
    
    # Next button
    if st.session_state.regular_students:
        col1, col2, col3 = st.columns([1, 1, 1])
        with col3:
            if st.button("Next: Configure Courses →", key='step1_next', use_container_width=True):
                st.session_state.step = 2
                st.rerun()

def step_2_upload_courses():
    """Step 2: Upload course list"""
    st.markdown('<div class="section-header">Step 2: Upload Course List</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📚 Course List")
        st.write("Upload Excel file with course names (single column)")
        
        course_file = st.file_uploader("Course List", type=['xlsx', 'xls'], key='course_list_file')
        
        if course_file:
            try:
                courses = DataProcessor.read_course_list(course_file)
                st.success(f"✓ Loaded {len(courses)} courses")
                
                with st.expander("View Courses"):
                    for i, course in enumerate(courses, 1):
                        st.write(f"{i}. {course}")
                
                st.session_state.courses = courses
            
            except Exception as e:
                st.error(f"Error processing file: {str(e)}")
    
    # Navigation buttons
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("← Back: Students", key='step2_back', use_container_width=True):
            st.session_state.step = 1
            st.rerun()
    
    with col3:
        if st.session_state.courses:
            if st.button("Next: Configure Courses →", key='step2_next', use_container_width=True):
                st.session_state.step = 3
                st.rerun()

def step_3_configure_courses():
    """Step 3: Configure course sections and capacities"""
    st.markdown('<div class="section-header">Step 3: Configure Courses (Regular Students)</div>', unsafe_allow_html=True)
    
    st.write("Define sections and capacities for **REGULAR STUDENTS** in each course. (Set sections to 0 to disable a course)")
    st.info("📌 **Note:** These sections are for REGULAR students only. Special/Research sections are configured separately in Step 4.")
    
    # Initialize course_config in session state if not present
    if 'course_config' not in st.session_state:
        st.session_state.course_config = {}
    
    course_config = st.session_state.course_config.copy()
    
    for course in st.session_state.courses:
        with st.expander(f"📖 {course}", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            # Get existing value for num_sections or default to 2
            existing_config = course_config.get(course, {})
            existing_sections = existing_config.get('sections', [])
            default_num_sections = len(existing_sections) if existing_sections else 2
            existing_prerequisite = existing_config.get('prerequisite', '')
            
            with col1:
                num_sections = st.number_input(
                    f"Sections in {course} (Regular Students)",
                    min_value=0,
                    max_value=10,
                    value=default_num_sections,
                    key=f"{course}_sections",
                    on_change=lambda: st.session_state.update({'config_changed': True})
                )
            
            with col3:
                prerequisite = st.text_input(
                    f"Prerequisite for {course}",
                    value=existing_prerequisite if existing_prerequisite else "",
                    key=f"{course}_prereq",
                    placeholder="(Optional)",
                    on_change=lambda: st.session_state.update({'config_changed': True})
                )
            
            # Get section capacities (only if sections > 0)
            capacities = []
            
            if num_sections > 0:
                cols = st.columns(num_sections)
                
                for i, col in enumerate(cols):
                    with col:
                        # Get existing capacity or default to 30
                        existing_capacity = existing_sections[i] if i < len(existing_sections) else 30
                        
                        capacity = st.number_input(
                            f"Section {i+1}",
                            min_value=1,
                            max_value=200,
                            value=existing_capacity,
                            key=f"{course}_section_{i+1}_capacity",
                            on_change=lambda: st.session_state.update({'config_changed': True})
                        )
                        capacities.append(capacity)
                
                course_config[course] = {
                    'sections': capacities,
                    'prerequisite': prerequisite if prerequisite else None
                }
                
            else:
                st.warning(f"⚠️ {course} is disabled (0 sections configured)")
                
                course_config[course] = {
                    'sections': [],
                    'prerequisite': prerequisite if prerequisite else None
                }
    
    # Save to session state immediately after building the config
    st.session_state.course_config = course_config
    
    # Navigation buttons
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("← Back: Courses", key='step3_back', use_container_width=True):
            st.session_state.step = 2
            st.rerun()
    
    with col3:
        if st.button("Next: Allocate Research Students →", key='step3_next', use_container_width=True):
            st.session_state.step = 4
            st.rerun()

def step_4_research_allocation():
    """Step 4: Configure Special/Research Sections"""
    st.markdown('<div class="section-header">Step 4: Configure Special/Research Sections (SEPARATE from Regular)</div>', unsafe_allow_html=True)
    
    if not st.session_state.research_students:
        st.info("ℹ️ No research/special students provided. Proceeding with regular allocation...")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col3:
            if st.button("Next: Run Allocation →", key='step4_skip', use_container_width=True):
                st.session_state.step = 5
                st.rerun()
        return
    
    st.write(f"**Total Research/Special Students:** {len(st.session_state.research_students)}")
    st.write("Configure **special/research sections** - Completely independent from regular sections in Step 3")
    st.info("🔬 **Important:** Special sections are SEPARATE from regular sections. A course can have both regular sections (Step 3) AND special sections (Step 4) at the same time.")
    
    # Initialize special sections config if not exists
    if 'special_sections_config' not in st.session_state:
        st.session_state.special_sections_config = {}
    
    # Input: Number of special sections
    num_special_sections = st.number_input(
        "Number of Special/Research Sections",
        min_value=0,
        max_value=10,
        value=1,
        key='num_special_sections'
    )
    
    st.divider()
    
    special_sections = {}
    
    # Configure each special section
    for section_idx in range(num_special_sections):
        st.subheader(f"🔬 Special Section {section_idx + 1}")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            course_name = st.selectbox(
                f"Course for Section {section_idx + 1}",
                options=st.session_state.courses,
                key=f"special_section_{section_idx}_course"
            )
        
        with col2:
            strength = st.number_input(
                f"Strength/Capacity",
                min_value=1,
                max_value=100,
                value=15,
                key=f"special_section_{section_idx}_strength"
            )
        
        with col3:
            prerequisite = st.text_input(
                f"Prerequisite (if any)",
                value="",
                key=f"special_section_{section_idx}_prereq",
                placeholder="(Optional)"
            )
        
        special_sections[f"SpecialSection{section_idx + 1}"] = {
            'course': course_name,
            'strength': strength,
            'prerequisite': prerequisite if prerequisite else None
        }
        
        st.divider()
    
    st.session_state.special_sections_config = special_sections
    
    # Show summary
    if special_sections:
        st.subheader("📋 Special Sections Summary")
        for sec_name, config in special_sections.items():
            st.write(f"**{sec_name}**: {config['course']} | Strength: {config['strength']}")
            if config['prerequisite']:
                st.write(f"   ℹ️ Prerequisite: {config['prerequisite']}")
    
    # Show comparison of regular vs special sections
    st.divider()
    st.subheader("📊 Regular vs Special Sections Comparison")
    
    comparison_data = []
    
    # Add regular sections - with better error handling
    if hasattr(st.session_state, 'course_config') and st.session_state.course_config:
        for course, config in st.session_state.course_config.items():
            sections_list = config.get('sections', [])
            if sections_list and len(sections_list) > 0:  # If sections exist
                total_capacity = sum(sections_list)
                comparison_data.append({
                    'Type': '📚 REGULAR',
                    'Course': course,
                    'Num Sections': len(sections_list),
                    'Total Capacity': total_capacity,
                    'Student Count': len(st.session_state.regular_students) if hasattr(st.session_state, 'regular_students') and st.session_state.regular_students else 0
                })
    else:
        st.warning("⚠️ Regular section configuration not found. Please go back to Step 3 and configure courses.")
    
    # Add special sections
    if special_sections:
        for sec_name, config in special_sections.items():
            comparison_data.append({
                'Type': '🔬 SPECIAL',
                'Course': config['course'],
                'Num Sections': 1,
                'Total Capacity': config['strength'],
                'Student Count': len(st.session_state.research_students) if hasattr(st.session_state, 'research_students') and st.session_state.research_students else 0
            })
    
    if comparison_data:
        df_comparison = pd.DataFrame(comparison_data)
        st.dataframe(df_comparison, use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ No sections configured yet. Configure regular sections in Step 3 and special sections above.")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("← Back: Configure", key='step4_back', use_container_width=True):
            st.session_state.step = 3
            st.rerun()
    
    with col3:
        if st.button("Next: Run Allocation →", key='step4_next', use_container_width=True):
            st.session_state.step = 5
            st.rerun()

def step_5_allocation_settings():
    """Step 5: Select allocation method and run allocation"""
    st.markdown('<div class="section-header">Step 5: Allocation Settings</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("📊 Allocation Criteria")
        allocation_method = st.radio(
            "Select allocation method:",
            options=['CGPA-Based', 'Timestamp-Based'],
            help="CGPA-Based: Higher CGPA gets priority\nTimestamp-Based: Earlier registration gets priority"
        )
        
        method = 'cgpa' if allocation_method == 'CGPA-Based' else 'timestamp'
    
    with col2:
        st.subheader("⚙️ Options")
        fill_underfilled = st.checkbox(
            "Fill underfilled sections",
            value=True,
            help="Try to fill sections with < capacity using student's 2nd/3rd preferences"
        )
    
    with col3:
        st.subheader("🔄 Competitive Allocation")
        enable_bumping = st.checkbox(
            "Enable bumping",
            value=False,
            help="If enabled: More competitive students can displace less competitive ones in full sections. Displaced students try their remaining preferences."
        )
    
    st.divider()
    
    # Navigation buttons
    nav_col1, nav_col2, nav_col3 = st.columns([1, 1, 1])
    
    with nav_col1:
        if st.button("← Back: Edit Configuration", key='step5_back', use_container_width=True):
            st.session_state.step = 4
            st.rerun()
    
    with nav_col3:
        # Run allocation
        if st.button("▶️ Run Allocation", use_container_width=True, key='run_allocation'):
            with st.spinner("Running allocation algorithm..."):
                try:
                    # Initialize engine with bumping enabled/disabled
                    engine = AllocationEngine(allocation_method=method, enable_bumping=enable_bumping)
                    engine.configure_courses(st.session_state.course_config)
                    
                    # Configure special sections for research students
                    special_sections_config = st.session_state.special_sections_config if hasattr(st.session_state, 'special_sections_config') else {}
                    if special_sections_config:
                        engine.configure_special_sections(special_sections_config)
                    
                    # Add regular students
                    if st.session_state.regular_students:
                        engine.add_regular_students(st.session_state.regular_students)
                    
                    # Add all research students
                    if st.session_state.research_students:
                        engine.add_research_students(st.session_state.research_students)
                    
                    # Run allocation
                    engine.allocate()
                    
                    # Fill underfilled if selected
                    if fill_underfilled:
                        engine.fill_underfilled_sections()
                    
                    # Store result
                    st.session_state.allocation_result = engine.get_allocation_result()
                    st.session_state.step = 6
                    st.rerun()
                
                except Exception as e:
                    st.error(f"Allocation failed: {str(e)}")

def step_6_results():
    """Step 6: Display results and download"""
    st.markdown('<div class="section-header">Step 6: Allocation Results</div>', unsafe_allow_html=True)
    
    result = st.session_state.allocation_result
    stats = result['statistics']
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Students", stats['total_students'])
    with col2:
        st.metric("Allocated", stats['allocated'], delta=f"{stats['allocated']/stats['total_students']*100:.1f}%")
    with col3:
        st.metric("Waitlisted", stats['waitlisted'])
    with col4:
        success_rate = (stats['allocated'] / stats['total_students'] * 100) if stats['total_students'] > 0 else 0
        st.metric("Success Rate", f"{success_rate:.1f}%")

    st.divider()
    st.subheader("🤖 AI Assistant")
    st.caption("Ask questions on current Step 6 allocation results. This assistant is visible directly in Single Course Results.")

    if 'single_ai_question' not in st.session_state:
        st.session_state.single_ai_question = _single_prompt_examples()[0]

    example_prompt = st.selectbox(
        "Example prompts",
        _single_prompt_examples(),
        key='single_ai_prompt_examples'
    )

    ex_col1, ex_col2 = st.columns([3, 1])
    with ex_col1:
        st.session_state.single_ai_question = st.text_input(
            "Ask AI",
            value=st.session_state.single_ai_question,
            key='single_ai_question_input',
            placeholder="Example: Show students allocated to ML section 2"
        )
    with ex_col2:
        st.write("")
        if st.button("Use Example", key='single_ai_use_example', use_container_width=True):
            st.session_state.single_ai_question = example_prompt
            st.rerun()

    if st.button("Ask AI", key='single_ai_ask', use_container_width=False):
        st.session_state.single_ai_answer = _run_single_results_assistant(
            st.session_state.single_ai_question,
            result
        )

    ai_answer = st.session_state.get('single_ai_answer')
    if ai_answer:
        st.markdown(f"**{ai_answer.get('title', 'AI Response')}**")
        if ai_answer.get('message'):
            st.write(ai_answer['message'])

        if ai_answer.get('kind') == 'summary':
            summary = ai_answer.get('summary', {})
            cols = st.columns(max(len(summary), 1))
            for idx, (key, value) in enumerate(summary.items()):
                with cols[idx]:
                    st.metric(key, value)
        elif ai_answer.get('kind') == 'table':
            rows = ai_answer.get('rows', [])
            st.dataframe(pd.DataFrame(rows), use_container_width=True)
    
    # Tabs for different views
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Allocated Students", "Waitlist", "Statistics", "Special Sections", "Download Results"])
    
    with tab1:
        st.subheader("✓ Allocated Students")
        allocated = result['allocated_students']
        
        # Separate by type
        regular = [s for s in allocated if s.get('student_type') == 'Regular']
        research = [s for s in allocated if s.get('student_type') == 'Research/Special']
        
        if regular:
            st.write(f"**Regular Students ({len(regular)})**")
            df_regular = pd.DataFrame([
                {
                    'Name': s['name'],
                    'Reg No': s['reg_no'],
                    'CGPA': s['cgpa'],
                    'Allocated Course': s.get('allocated_course', 'N/A'),
                    'Section': s.get('allocation_section_display', 'N/A'),
                    'Preference': f"Preference-{s.get('preference_rank', 'N/A')}" if s.get('preference_rank') else 'N/A',
                    'Status': s.get('allocation_status', 'Allocated')
                }
                for s in regular
            ])
            st.dataframe(df_regular, use_container_width=True)
        
        if research:
            st.write(f"**Research/Special Students ({len(research)})**")
            df_research = pd.DataFrame([
                {
                    'Name': s['name'],
                    'Reg No': s['reg_no'],
                    'CGPA': s['cgpa'],
                    'Allocated Course': s.get('allocated_course', 'N/A'),
                    'Section': s.get('allocation_section_display', s.get('allocation_section_id', 'N/A')),
                    'Preference': s.get('preference_rank', 'Special'),
                    'Status': s.get('allocation_status', 'Allocated')
                }
                for s in research
            ])
            st.dataframe(df_research, use_container_width=True)
    
    with tab2:
        st.subheader("⚠️ Waitlisted Students - Separated by Type")
        waitlist = result['waitlist']
        
        if waitlist:
            # Separate special and regular students
            special_waitlist = [s for s in waitlist if s.get('student_type') == 'Research/Special']
            regular_waitlist = [s for s in waitlist if s.get('student_type') == 'Regular']
            
            # Summary counts
            col_w1, col_w2, col_w3 = st.columns(3)
            with col_w1:
                st.metric("🔬 Special/Research Waitlisted", len(special_waitlist))
            with col_w2:
                st.metric("📚 Regular Waitlisted", len(regular_waitlist))
            with col_w3:
                st.metric("📊 Total Waitlisted", len(waitlist))
            
            st.divider()
            
            # SPECIAL STUDENTS SECTION
            if special_waitlist:
                st.subheader("🔬 Unallocated Special/Research Students")
                st.write(f"**Total: {len(special_waitlist)} students**")
                
                special_data = []
                for idx, s in enumerate(special_waitlist, 1):
                    special_data.append({
                        'S.No': idx,
                        'Name': s['name'],
                        'Reg No': s['reg_no'],
                        'CGPA': s['cgpa'],
                        'Reason for Waitlist': s.get('allocation_reason', 'Unknown reason')
                    })
                
                df_special = pd.DataFrame(special_data)
                st.dataframe(df_special, use_container_width=True, height=400)
                
                # Download special waitlist
                csv_special = df_special.to_csv(index=False)
                st.download_button(
                    label="📥 Download Special Waitlist",
                    data=csv_special,
                    file_name="special_students_waitlist.csv",
                    mime="text/csv",
                    key="download_special_waitlist"
                )
            
            st.divider()
            
            # REGULAR STUDENTS SECTION
            if regular_waitlist:
                st.subheader("📚 Unallocated Regular Students")
                st.write(f"**Total: {len(regular_waitlist)} students**")
                
                regular_data = []
                for idx, s in enumerate(regular_waitlist, 1):
                    regular_data.append({
                        'S.No': idx,
                        'Name': s['name'],
                        'Reg No': s['reg_no'],
                        'CGPA': s['cgpa'],
                        'Preferences': ', '.join(s.get('preferences', [])),
                        'Reason for Waitlist': s.get('allocation_reason', 'Unknown reason')
                    })
                
                df_regular = pd.DataFrame(regular_data)
                st.dataframe(df_regular, use_container_width=True, height=400)
                
                # Download regular waitlist
                csv_regular = df_regular.to_csv(index=False)
                st.download_button(
                    label="📥 Download Regular Waitlist",
                    data=csv_regular,
                    file_name="regular_students_waitlist.csv",
                    mime="text/csv",
                    key="download_regular_waitlist"
                )
            
            st.divider()
            
            # COMBINED WAITLIST WITH TYPE INDICATOR
            st.subheader("📋 Combined Waitlist (All Students)")
            
            combined_data = []
            for idx, s in enumerate(waitlist, 1):
                student_type = "🔬 SPECIAL" if s.get('student_type') == 'Research/Special' else "📚 REGULAR"
                prefs = ', '.join(s.get('preferences', [])) if s.get('student_type') == 'Regular' else "N/A"
                
                combined_data.append({
                    'S.No': idx,
                    'Type': student_type,
                    'Name': s['name'],
                    'Reg No': s['reg_no'],
                    'CGPA': s['cgpa'],
                    'Preferences': prefs,
                    'Reason for Waitlist': s.get('allocation_reason', 'Unknown reason')
                })
            
            df_combined = pd.DataFrame(combined_data)
            st.dataframe(df_combined, use_container_width=True, height=500)
            
            # Download combined waitlist
            csv_combined = df_combined.to_csv(index=False)
            st.download_button(
                label="📥 Download Combined Waitlist",
                data=csv_combined,
                file_name="all_students_waitlist.csv",
                mime="text/csv",
                key="download_combined_waitlist"
            )
        
        else:
            st.success("✓ No students in waitlist! All students successfully allocated.")
    
    with tab3:
        st.subheader("📊 Allocation Statistics")
        
        # Course-wise stats
        courses_stats = stats.get('courses', {})
        
        st.write("**Course-wise Summary:**")
        df_courses = pd.DataFrame([
            {
                'Course': course,
                'Sections': c_stat['sections'],
                'Capacity': c_stat['total_capacity'],
                'Allocated': c_stat['total_allocated'],
                'Unfilled': c_stat['unfilled'],
                'Utilization %': f"{c_stat['utilization_percent']:.1f}%"
            }
            for course, c_stat in courses_stats.items()
        ])
        st.dataframe(df_courses, use_container_width=True)
        
        # Section details
        st.write("**Section Details:**")
        for course, c_stat in courses_stats.items():
            with st.expander(f"{course} - Sections"):
                df_sections = pd.DataFrame(c_stat['section_details'])
                st.dataframe(df_sections, use_container_width=True)
    
    with tab4:
        st.subheader("🎯 Special Section Allocations")
        
        special_sections = result.get('special_sections', {})
        special_allocations = result.get('special_section_allocations', {})
        
        if special_sections:
            st.write("**Summary of Special/Research Sections:**")
            
            # Summary table
            summary_data = []
            for section_name, section_config in special_sections.items():
                allocated_count = len(special_allocations.get(section_name, []))
                capacity = section_config.get('strength', 0)
                course = section_config.get('course', 'N/A')
                prerequisite = section_config.get('prerequisite', 'None')
                
                summary_data.append({
                    'Section': section_name,
                    'Course': course,
                    'Capacity': capacity,
                    'Allocated': allocated_count,
                    'Remaining': capacity - allocated_count,
                    'Utilization %': f"{(allocated_count/capacity*100):.1f}%" if capacity > 0 else "0%",
                    'Prerequisite': prerequisite
                })
            
            df_summary = pd.DataFrame(summary_data)
            st.dataframe(df_summary, use_container_width=True)
            
            # Detailed view by section
            st.write("**Detailed Student Allocation by Section:**")
            for section_name in special_sections.keys():
                with st.expander(f"📋 {section_name}", expanded=False):
                    students = special_allocations.get(section_name, [])
                    if students:
                        df_students = pd.DataFrame([
                            {
                                'Name': s['name'],
                                'Reg No': s['reg_no'],
                                'CGPA': s['cgpa'],
                                'Preference Rank': s.get('preference_rank', 'N/A')
                            }
                            for s in students
                        ])
                        st.dataframe(df_students, use_container_width=True)
                        st.success(f"✓ {len(students)} students allocated to {section_name}")
                    else:
                        st.info(f"No students allocated to {section_name}")
        else:
            st.info("ℹ️ No special sections configured for this allocation.")
    
    with tab5:
        st.subheader("📥 Download Results")
        
        if st.button("Generate Excel Report"):
            try:
                # Create temporary file
                temp_dir = tempfile.gettempdir()
                output_file = os.path.join(temp_dir, 'Course_Allocation_Results.xlsx')
                
                OutputGenerator.create_output_file(result, output_file)
                
                with open(output_file, 'rb') as f:
                    st.download_button(
                        label="📊 Download Excel Report",
                        data=f.read(),
                        file_name="Course_Allocation_Results.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                st.success("✓ Report generated successfully!")
            
            except Exception as e:
                st.error(f"Error generating report: {str(e)}")
    
    # Navigation
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("← Back: Settings", key='step6_back', use_container_width=True):
            st.session_state.step = 5
            st.rerun()
    
    with col3:
        if st.button("Start Over", key='restart', use_container_width=True):
            st.session_state.step = 1
            st.session_state.regular_students = None
            st.session_state.research_students = None
            st.session_state.courses = []
            st.session_state.allocation_result = None
            st.session_state.course_config = {}
            st.rerun()

# Main app
def main():
    st.title("🎓 Course Allocation System")
    st.write("Automated course allocation based on student preferences and allocation criteria")
    
    # Progress indicator
    steps = ['Students', 'Courses', 'Configure', 'Research', 'Settings', 'Results']
    current = st.session_state.step - 1
    
    progress = (current + 1) / len(steps)
    st.progress(progress, text=f"Step {current + 1} of {len(steps)}: {steps[current]}")
    
    # Render appropriate step
    if st.session_state.step == 1:
        step_1_upload_students()
    elif st.session_state.step == 2:
        step_2_upload_courses()
    elif st.session_state.step == 3:
        step_3_configure_courses()
    elif st.session_state.step == 4:
        step_4_research_allocation()
    elif st.session_state.step == 5:
        step_5_allocation_settings()
    elif st.session_state.step == 6:
        step_6_results()

if __name__ == '__main__':
    main()
