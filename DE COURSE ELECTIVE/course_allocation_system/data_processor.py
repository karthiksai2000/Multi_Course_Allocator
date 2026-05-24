import pandas as pd
import numpy as np
from typing import Tuple, List, Dict
import re

class DataProcessor:
    """Handle Excel input with dynamic column detection"""
    
    STUDENT_KEYWORDS = ['name', 'student', 'student name']
    REG_KEYWORDS = ['regdl', 'reg', 'registration', 'reg no', 'regd no']
    CGPA_KEYWORDS = ['cgpa', 'gpa', 'score', 'grade']
    PREFERENCE_KEYWORDS = ['choice', 'preference', 'course', 'option','Elective Choice','Department Elective Choice']
    RESEARCH_KEYWORDS = ['research', 'special', 'research/special']
    COMPLETED_KEYWORDS = ['completed', 'done', 'taken', 'finished', 'cleared','courses persued']
    
    @staticmethod
    def detect_column(df: pd.DataFrame, keywords: List[str]) -> str:
        """
        Dynamically detect column name based on keywords
        Returns the column name if found, None otherwise
        """
        columns_lower = {col.lower(): col for col in df.columns}
        
        for keyword in keywords:
            for col_lower, col_original in columns_lower.items():
                if keyword.lower() in col_lower:
                    return col_original
        return None
    
    @staticmethod
    def extract_preference_columns(df: pd.DataFrame) -> List[str]:
        """
        Extract columns containing course preferences
        Returns list of preference column names
        """
        preference_cols = []
        columns_lower = {col.lower(): col for col in df.columns}
        
        for col_lower, col_original in columns_lower.items():
            if any(kw in col_lower for kw in DataProcessor.PREFERENCE_KEYWORDS):
                # Check if it's a numbered choice (Choice 1, Choice 2, etc.)
                if re.search(r'\d+', col_original) or 'choice' in col_lower or 'preference' in col_lower:
                    preference_cols.append(col_original)
        
        # Sort by number if available (numeric sort, not string sort)
        preference_cols.sort(key=lambda x: int((re.findall(r'\d+', x) or ['999'])[0]))
        
        return preference_cols
    
    @staticmethod
    def is_research_student(row_value) -> bool:
        """Check if student is research/special student"""
        if pd.isna(row_value):
            return False
        value_str = str(row_value).lower().strip()
        return any(kw in value_str for kw in DataProcessor.RESEARCH_KEYWORDS) or value_str == 'yes'
    
    @staticmethod
    def read_regular_students(file_path: str) -> Tuple[pd.DataFrame, Dict]:
        """
        Read regular student data with dynamic column detection
        Returns: (DataFrame, column_mapping)
        """
        df = pd.read_excel(file_path, sheet_name=0)
        df = df.dropna(how='all')  # Remove completely empty rows
        
        column_map = {
            'name': DataProcessor.detect_column(df, DataProcessor.STUDENT_KEYWORDS),
            'reg_no': DataProcessor.detect_column(df, DataProcessor.REG_KEYWORDS),
            'cgpa': DataProcessor.detect_column(df, DataProcessor.CGPA_KEYWORDS),
            'preferences': DataProcessor.extract_preference_columns(df),
            'completed': DataProcessor.detect_column(df, DataProcessor.COMPLETED_KEYWORDS)
        }
        
        # Check for research/special column
        research_col = None
        for col in df.columns:
            if 'research' in col.lower() or 'special' in col.lower():
                research_col = col
                break
        
        column_map['research_column'] = research_col
        
        # Validate critical columns
        if not column_map['name'] or not column_map['cgpa']:
            raise ValueError("Could not detect Name and/or CGPA columns. Please check Excel format.")
        
        return df, column_map
    
    @staticmethod
    def read_research_students(file_path: str) -> Tuple[pd.DataFrame, Dict]:
        """
        Read special/research student data with dynamic column detection
        Returns: (DataFrame, column_mapping)
        """
        df = pd.read_excel(file_path, sheet_name=0)
        df = df.dropna(how='all')
        
        column_map = {
            'name': DataProcessor.detect_column(df, DataProcessor.STUDENT_KEYWORDS),
            'reg_no': DataProcessor.detect_column(df, DataProcessor.REG_KEYWORDS),
            'cgpa': DataProcessor.detect_column(df, DataProcessor.CGPA_KEYWORDS),
            'preferences': DataProcessor.extract_preference_columns(df),
            'completed': DataProcessor.detect_column(df, DataProcessor.COMPLETED_KEYWORDS)
        }
        
        if not column_map['name'] or not column_map['cgpa']:
            raise ValueError("Could not detect Name and/or CGPA columns in research students file.")
        
        return df, column_map
    
    @staticmethod
    def read_course_list(file_path: str) -> List[str]:
        """Read list of courses from Excel"""
        df = pd.read_excel(file_path, sheet_name=0)
        
        # Get first column with data
        course_col = df.iloc[:, 0]
        courses = course_col.dropna().unique().tolist()
        courses = [str(c).strip() for c in courses]
        
        return courses
    
    @staticmethod
    def get_student_data(df: pd.DataFrame, col_map: Dict, row_idx: int) -> Dict:
        """Extract student data from a row"""
        row = df.iloc[row_idx]
        
        preferences = []
        if col_map['preferences']:
            for pref_col in col_map['preferences']:
                pref = row[pref_col]
                if pd.notna(pref):
                    preferences.append(str(pref).strip())
        
        # Extract completed courses (comma-separated or single value)
        completed_courses = []
        if col_map.get('completed'):
            completed_value = row[col_map['completed']]
            if pd.notna(completed_value):
                completed_str = str(completed_value).strip()
                # Split by comma if multiple courses, otherwise single course
                completed_courses = [c.strip() for c in completed_str.split(',') if c.strip()]
        
        return {
            'name': str(row[col_map['name']]).strip(),
            'reg_no': str(row[col_map['reg_no']]).strip() if col_map['reg_no'] else 'N/A',
            'cgpa': float(row[col_map['cgpa']]) if pd.notna(row[col_map['cgpa']]) else 0.0,
            'preferences': preferences,
            'completed_courses': completed_courses,
            'timestamp': row_idx  # Index acts as registration order
        }
