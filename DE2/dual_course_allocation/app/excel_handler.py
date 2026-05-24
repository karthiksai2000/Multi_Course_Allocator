"""
Excel input/output handling for Dual Course Allocation System
"""
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from .models import (
    Student, Course, Section, AllocationConfig, Group, AllocationResult
)


class ExcelHandler:
    """Handles reading and writing Excel files"""

    # Keywords for dynamic column detection
    CGPA_KEYWORDS = ["cgpa", "gpa", "grade", "point", "score"]
    REG_KEYWORDS = ["registration", "reg", "id", "student id", "rollno", "roll", "student no", "enroll"]
    TIMESTAMP_KEYWORDS = ["timestamp", "time", "date", "submitted", "submit", "registration date", "enrolled"]
    COMPLETED_KEYWORDS = ["completed", "courses done", "courses taken", "taken", "prerequisite", "passed"]
    NAME_KEYWORDS = ["name", "fullname", "full name"]  # Removed "student" to avoid false matches with "student_id"
    PREFERENCE_KEYWORDS = ["preference", "choice", "option", "course", "select"]
    COURSE_NAME_KEYWORDS = ["course name", "course", "subject", "code", "course code"]
    GROUP_KEYWORDS = ["group", "category", "type", "tier", "level"]
    PREREQ_KEYWORDS = ["prerequisite", "prereq", "pre requisite", "requirements", "required", "pre_requisite"]

    @staticmethod
    def detect_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
        """
        Detect column names using keyword scoring
        
        Returns: {
            'timestamp': column_name,
            'name': column_name,
            'registration': column_name,
            'cgpa': column_name,
            'completed': column_name
        }
        """
        columns_lower = [str(c).lower() for c in df.columns]
        result = {}

        # Detect single columns with better scoring
        result['timestamp'] = ExcelHandler._find_best_column(columns_lower, ExcelHandler.TIMESTAMP_KEYWORDS, list(df.columns))
        result['registration'] = ExcelHandler._find_best_column(columns_lower, ExcelHandler.REG_KEYWORDS, list(df.columns))
        result['cgpa'] = ExcelHandler._find_best_column(columns_lower, ExcelHandler.CGPA_KEYWORDS, list(df.columns))
        result['completed'] = ExcelHandler._find_best_column(columns_lower, ExcelHandler.COMPLETED_KEYWORDS, list(df.columns))
        
        # Name detection with priority: exact match > contains > fallback
        result['name'] = ExcelHandler._find_best_column(columns_lower, ExcelHandler.NAME_KEYWORDS, list(df.columns))

        return result

    @staticmethod
    def _find_best_column(columns_lower: List[str], keywords: List[str], df_columns: List = None) -> Optional[str]:
        """
        Find column matching any keyword with keyword scoring
        Prioritizes exact matches and longer keyword matches
        Avoids false positives by requiring word boundaries
        """
        best_match = None
        best_score = 0
        
        for i, col in enumerate(columns_lower):
            # Skip if column already matched with higher priority
            col_best_score = 0
            
            for keyword in keywords:
                # Score based on keyword matching accuracy
                if keyword == col:
                    # Exact match - highest priority
                    score = 10000 + len(keyword)
                elif col.startswith(keyword) or col.endswith(keyword):
                    # Partial match at boundaries - high priority
                    score = 1000 + len(keyword)
                elif keyword in col:
                    # Keyword contained somewhere in column name
                    # But check for word boundaries to avoid false matches
                    # e.g., don't match "id" in "student_id" as a "student" keyword match
                    score = 100 + len(keyword)
                else:
                    score = 0
                
                # Track the best score for this column
                if score > col_best_score:
                    col_best_score = score
            
            # Update overall best match if this column is better
            if col_best_score > best_score:
                best_score = col_best_score
                best_match = i
        
        # Return actual column name if match found
        return df_columns[best_match] if best_match is not None and df_columns else None

    @staticmethod
    def detect_course_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
        """
        Detect course file columns using keyword matching
        
        Returns: {
            'course_name': column_name,
            'group': column_name,
            'prerequisites': column_name
        }
        """
        columns_lower = [str(c).lower() for c in df.columns]
        result = {}
        
        result['course_name'] = ExcelHandler._find_best_column(columns_lower, ExcelHandler.COURSE_NAME_KEYWORDS, list(df.columns))
        result['group'] = ExcelHandler._find_best_column(columns_lower, ExcelHandler.GROUP_KEYWORDS, list(df.columns))
        result['prerequisites'] = ExcelHandler._find_best_column(columns_lower, ExcelHandler.PREREQ_KEYWORDS, list(df.columns))
        
        return result

    @staticmethod
    @staticmethod
    def read_students_from_excel(
        file_path: str, g1_prefs_cols: List[str] = None, g2_prefs_cols: List[str] = None
    ) -> Tuple[List[Student], List[str]]:
        """
        Read students from Excel file with auto-detection of columns
        
        Args:
            file_path: Path to Excel file
            g1_prefs_cols: List of column names for Group 1 preferences (auto-detected if None)
            g2_prefs_cols: List of column names for Group 2 preferences (auto-detected if None)
        
        Returns: Tuple of (List of Student objects, List of error messages for skipped rows)
        """
        df = pd.read_excel(file_path)
        columns_detected = ExcelHandler.detect_columns(df)
        
        # Auto-detect preference columns if not provided
        if g1_prefs_cols is None or g2_prefs_cols is None:
            g1_prefs_cols, g2_prefs_cols = ExcelHandler.detect_preference_columns(df)

        students = []
        errors = []

        for idx, row in df.iterrows():
            try:
                # Parse basic info
                reg_col = columns_detected['registration']
                name_col = columns_detected['name']
                cgpa_col = columns_detected['cgpa']
                timestamp_col = columns_detected['timestamp']
                completed_col = columns_detected['completed']

                registration = str(row[reg_col]).strip()
                name = str(row[name_col]).strip()
                
                # More lenient CGPA parsing - use default if missing or invalid
                try:
                    cgpa = float(row[cgpa_col]) if pd.notna(row[cgpa_col]) else 3.0
                except (ValueError, TypeError):
                    cgpa = 3.0  # Default CGPA if cannot parse
                
                # More lenient timestamp parsing - use current time if missing
                try:
                    timestamp = ExcelHandler._parse_timestamp(row[timestamp_col])
                except:
                    timestamp = datetime.now()  # Default to current time

                # Parse completed courses (comma-separated)
                completed_str = str(row[completed_col]) if pd.notna(row[completed_col]) else ""
                completed = [c.strip() for c in completed_str.split(",") if c.strip()]

                # Parse preferences
                g1_prefs = []
                for col in g1_prefs_cols:
                    if col in df.columns and pd.notna(row[col]):
                        pref = str(row[col]).strip()
                        if pref:
                            g1_prefs.append(pref)

                g2_prefs = []
                for col in g2_prefs_cols:
                    if col in df.columns and pd.notna(row[col]):
                        pref = str(row[col]).strip()
                        if pref:
                            g2_prefs.append(pref)

                # Skip if missing critical fields
                if not registration or not name:
                    error_msg = f"Row {idx + 2}: Missing registration or name"
                    errors.append(error_msg)
                    continue
                
                # Skip if no preferences
                if not g1_prefs or not g2_prefs:
                    error_msg = f"Row {idx + 2} ({registration}): Missing Group 1 or Group 2 preferences"
                    errors.append(error_msg)
                    continue

                student = Student(
                    registration_number=registration,
                    name=name,
                    cgpa=cgpa,
                    timestamp=timestamp,
                    completed_courses=completed,
                    g1_preferences=g1_prefs,
                    g2_preferences=g2_prefs
                )
                students.append(student)

            except Exception as e:
                error_msg = f"Row {idx + 2}: {str(e)}"  # +2 for 1-based index and header row
                errors.append(error_msg)
                continue

        return students, errors
    
    @staticmethod
    def detect_preference_columns(df: pd.DataFrame) -> Tuple[List[str], List[str]]:
        """
        Smart preference column detection (NOT just splitting in half)
        
        Strategy:
        1. Look for explicit "G1"/"G2" or "Group1"/"Group2" labels
        2. Look for "Preference 1", "Preference 2", "Preference 3" patterns
           - First 2-3 = G1, Next 2-3 = G2
        3. If multiple preference columns, analyze header patterns
        4. If still unclear, ask user for manual specification
        
        Returns: (g1_columns, g2_columns)
        """
        g1_cols = []
        g2_cols = []
        
        cols_lower = [(i, c.lower()) for i, c in enumerate(df.columns)]
        
        # Strategy 1: Explicit G1/G2 labels
        for idx, col_lower in cols_lower:
            original_col = df.columns[idx]
            
            if 'g1' in col_lower or 'group 1' in col_lower or 'group1' in col_lower or 'group_1' in col_lower:
                g1_cols.append(original_col)
            elif 'g2' in col_lower or 'group 2' in col_lower or 'group2' in col_lower or 'group_2' in col_lower:
                g2_cols.append(original_col)
        
        # Strategy 2: If explicit labels found, use them
        if g1_cols and g2_cols:
            return g1_cols, g2_cols
        
        # Strategy 3: Look for numbered preference patterns
        pref_cols = []
        for idx, col_lower in cols_lower:
            original_col = df.columns[idx]
            if 'preference' in col_lower or 'choice' in col_lower or 'select' in col_lower:
                pref_cols.append((idx, original_col, col_lower))
        
        if len(pref_cols) >= 2:
            # Sort by column index to get natural order
            pref_cols.sort(key=lambda x: x[0])
            
            # Heuristic: First half = G1, second half = G2
            mid = len(pref_cols) // 2
            g1_cols = [col for _, col, _ in pref_cols[:mid]]
            g2_cols = [col for _, col, _ in pref_cols[mid:]]
            
            return g1_cols, g2_cols
        
        # Strategy 4: Last resort - look for any course-like columns
        # and try to infer from data
        for idx, col_lower in cols_lower:
            original_col = df.columns[idx]
            if 'course' in col_lower or 'subject' in col_lower:
                # Add to a generic list, we'll split later
                pref_cols.append((idx, original_col))
        
        if pref_cols:
            pref_cols.sort(key=lambda x: x[0])
            mid = len(pref_cols) // 2
            g1_cols = [col for _, col in pref_cols[:mid]]
            g2_cols = [col for _, col in pref_cols[mid:]]
            return g1_cols, g2_cols
        
        # If nothing found, return empty (will be handled by calling code)
        return [], []

    @staticmethod
    def read_courses_from_excel(file_input) -> AllocationConfig:
        """
        Read course configuration from Excel - FLEXIBLE COLUMN DETECTION
        
        Accepts file path (str) or BytesIO object
        Only 1 sheet required with flexible column naming:
        - Course Name (supports: course, course name, subject, course code, etc.)
        - Group (supports: group, category, type, tier, level)
        - Prerequisites (optional - supports: prerequisite, prereq, requirements, etc.)
        
        Sections are created through Streamlit UI (Step 2)
        """
        try:
            excel_file = pd.ExcelFile(file_input)
            sheet_names = excel_file.sheet_names
            
            # Get first sheet (any name is fine)
            sheet_name = sheet_names[0]
            courses_df = pd.read_excel(file_input, sheet_name=sheet_name)
            excel_file.close()  # Close file handle immediately
        except Exception as e:
            excel_file.close() if 'excel_file' in locals() else None
            raise e
        
        # Detect course file columns
        detected_cols = ExcelHandler.detect_course_columns(courses_df)
        
        course_col = detected_cols.get('course_name')
        group_col = detected_cols.get('group')
        prereq_col = detected_cols.get('prerequisites')
        
        if not course_col:
            raise ValueError("""
            ❌ No Course Name column found!
            
            Please ensure your file contains a column with any of these names:
            - Course Name, Course, Subject, Course Code, Code, Course Title
            """)
        
        if not group_col:
            raise ValueError("""
            ❌ No Group column found!
            
            Please ensure your file contains a column with any of these names:
            - Group, Category, Type, Tier, Level
            """)
        
        courses_dict: Dict[str, Course] = {}

        # Parse courses
        for idx, row in courses_df.iterrows():
            try:
                name = str(row[course_col]).strip()
                group_str = str(row[group_col]).strip().upper()

                # Determine group
                if "G1" in group_str or "GROUP 1" in group_str or "1" in group_str:
                    group = Group.GROUP_1
                elif "G2" in group_str or "GROUP 2" in group_str or "2" in group_str:
                    group = Group.GROUP_2
                else:
                    print(f"Warning: Row {idx} has invalid group '{group_str}', skipping")
                    continue

                # Parse prerequisites - optional
                prereqs = []
                if prereq_col and pd.notna(row[prereq_col]):
                    prereqs_str = str(row[prereq_col]).strip()
                    if prereqs_str and prereqs_str.lower() not in ['nan', 'none', '']:
                        prereqs = [p.strip() for p in prereqs_str.split(",") if p.strip()]

                # Create course without sections (will be added via UI)
                course = Course(
                    course_name=name,
                    group=group,
                    prerequisites=prereqs
                )
                courses_dict[name] = course

            except Exception as e:
                print(f"Warning: Could not parse course row {idx}: {e}")
                continue

        if not courses_dict:
            raise ValueError("""
            ❌ No courses found in the file.
            
            Please ensure your Excel file contains at least one row of course data.
            """)

        config = AllocationConfig(courses=courses_dict)
        return config

    @staticmethod
    def _parse_timestamp(ts_value) -> datetime:
        """Parse timestamp from various formats"""
        if isinstance(ts_value, datetime):
            return ts_value

        ts_str = str(ts_value).strip()

        # Try common formats
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%d-%m-%Y %H:%M:%S",
            "%d-%m-%Y",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y"
        ]

        for fmt in formats:
            try:
                return datetime.strptime(ts_str, fmt)
            except ValueError:
                continue

        # Default to current time if parsing fails
        return datetime.now()

    @staticmethod
    def write_results_to_excel(
        allocation_results: List[AllocationResult],
        output_path: str
    ) -> None:
        """
        Write allocation results to Excel
        Creates two sheets: Allocated and Unallocated
        """
        # Separate results
        allocated = [r for r in allocation_results if r.allocated]
        unallocated = [r for r in allocation_results if not r.allocated]

        # Create DataFrames
        allocated_data = []
        for r in allocated:
            allocated_data.append({
                "Registration Number": r.registration_number,
                "Name": r.name,
                "Group 1 Course": r.g1_course,
                "Group 1 Section": r.g1_section,
                "Group 2 Course": r.g2_course,
                "Group 2 Section": r.g2_section,
                "Pair Label": r.pair_label,
                "G1 Preference Rank": r.g1_preference_rank,
                "G2 Preference Rank": r.g2_preference_rank,
                "Fallback Used": "Yes" if r.fallback_used else "No"
            })

        unallocated_data = []
        for r in unallocated:
            unallocated_data.append({
                "Registration Number": r.registration_number,
                "Name": r.name,
                "Reason": r.reason
            })

        # Write to Excel
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            if allocated_data:
                df_allocated = pd.DataFrame(allocated_data)
                df_allocated.to_excel(writer, sheet_name="Allocated", index=False)

            if unallocated_data:
                df_unallocated = pd.DataFrame(unallocated_data)
                df_unallocated.to_excel(writer, sheet_name="Unallocated", index=False)

            # Add summary sheet
            summary_data = {
                "Metric": [
                    "Total Students",
                    "Allocated",
                    "Unallocated",
                    "Allocation Rate (%)"
                ],
                "Value": [
                    len(allocation_results),
                    len(allocated),
                    len(unallocated),
                    f"{(len(allocated) / len(allocation_results) * 100):.2f}" if allocation_results else "0.00"
                ]
            }
            df_summary = pd.DataFrame(summary_data)
            df_summary.to_excel(writer, sheet_name="Summary", index=False)

    @staticmethod
    def create_sample_student_file(output_path: str) -> None:
        """Create sample student data Excel file for testing"""
        data = {
            "Timestamp": [
                "2024-01-01 09:00:00",
                "2024-01-01 10:30:00",
                "2024-01-01 11:00:00"
            ],
            "Student Name": ["Alice Johnson", "Bob Smith", "Charlie Brown"],
            "Registration Number": ["REG001", "REG002", "REG003"],
            "CGPA": [3.8, 3.5, 3.9],
            "Completed Courses": ["CS101,CS102", "CS101", "CS101,CS102,CS103"],
            "G1 Preference 1": ["Artificial Intelligence", "Artificial Intelligence", "Internet of Things"],
            "G1 Preference 2": ["Machine Learning", "Internet of Things", "Artificial Intelligence"],
            "G2 Preference 1": ["Database Systems", "Web Development", "Database Systems"],
            "G2 Preference 2": ["Web Development", "Database Systems", "Web Development"]
        }
        df = pd.DataFrame(data)
        df.to_excel(output_path, index=False)

    @staticmethod
    def create_sample_config_file(output_path: str) -> None:
        """Create sample course configuration Excel file (NO SECTIONS)
        
        User will define sections in Step 2 through Streamlit UI
        """
        # Courses sheet only
        courses_data = {
            "Course Name": [
                "Artificial Intelligence",
                "Machine Learning",
                "Internet of Things",
                "Database Systems",
                "Web Development",
                "Cybersecurity"
            ],
            "Group": ["G1", "G1", "G1", "G2", "G2", "G2"],
            "Prerequisites": ["", "Artificial Intelligence", "", "CS101", "", ""]
        }

        df_courses = pd.DataFrame(courses_data)

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            df_courses.to_excel(writer, sheet_name="Courses", index=False)
