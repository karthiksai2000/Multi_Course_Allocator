"""
Data models for Dual Course Allocation System
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple, Any
from enum import Enum
from datetime import datetime


class Group(Enum):
    """Course group classification"""
    GROUP_1 = "G1"
    GROUP_2 = "G2"


@dataclass
class Section:
    """Represents a course section"""
    section_id: str
    capacity: int
    enrolled: int = 0
    students: List[str] = field(default_factory=list)

    def available_seats(self) -> int:
        """Returns number of available seats"""
        return self.capacity - self.enrolled

    def is_full(self) -> bool:
        """Check if section is full"""
        return self.enrolled >= self.capacity

    def can_accommodate(self, count: int = 1) -> bool:
        """Check if section can accommodate students"""
        return self.available_seats() >= count

    def add_student(self, student_id: str) -> bool:
        """Add student to section"""
        if self.is_full():
            return False
        self.students.append(student_id)
        self.enrolled += 1
        return True

    def remove_student(self, student_id: str) -> bool:
        """Remove student from section"""
        if student_id in self.students:
            self.students.remove(student_id)
            self.enrolled -= 1
            return True
        return False

    def clear_section(self) -> Dict[str, int]:
        """
        Clear all students from section
        Returns: Dictionary with removed_count and previous_students list
        """
        removed_students = self.students.copy()
        removed_count = len(removed_students)
        self.students = []
        self.enrolled = 0
        return {
            "removed_count": removed_count,
            "previous_students": removed_students
        }

    def is_empty(self) -> bool:
        """Check if section has no students"""
        return self.enrolled == 0


@dataclass
class Course:
    """Represents a course"""
    course_name: str
    group: Group
    prerequisites: List[str] = field(default_factory=list)
    sections: Dict[str, Section] = field(default_factory=dict)

    def get_total_capacity(self) -> int:
        """Calculate total capacity across all sections"""
        return sum(section.capacity for section in self.sections.values())

    def get_total_enrolled(self) -> int:
        """Calculate total enrolled across all sections"""
        return sum(section.enrolled for section in self.sections.values())


@dataclass
class PairedSection:
    """Represents a paired course section (G1 + G2)"""
    pair_id: str  # "COURSE1+COURSE2-Sec1"
    g1_course: str
    g2_course: str
    section_index: int
    capacity: int
    enrolled: int = 0
    students: List[str] = field(default_factory=list)

    def available_seats(self) -> int:
        """Returns number of available seats"""
        return self.capacity - self.enrolled

    def is_full(self) -> bool:
        """Check if paired section is full"""
        return self.enrolled >= self.capacity

    def can_accommodate(self, count: int = 1) -> bool:
        """Check if section can accommodate students"""
        return self.available_seats() >= count

    def add_student(self, student_id: str) -> bool:
        """Add student to paired section"""
        if self.is_full():
            return False
        self.students.append(student_id)
        self.enrolled += 1
        return True

    def remove_student(self, student_id: str) -> bool:
        """Remove a specific student from paired section"""
        if student_id in self.students:
            self.students.remove(student_id)
            self.enrolled -= 1
            return True
        return False

    def clear_section(self) -> Dict[str, any]:
        """
        Clear all students from this paired section
        Returns: Dictionary with removal details
        """
        removed_students = self.students.copy()
        removed_count = len(removed_students)
        self.students = []
        self.enrolled = 0
        return {
            "pair_id": self.pair_id,
            "section_label": self.get_label(),
            "removed_count": removed_count,
            "previous_students": removed_students,
            "cleared_at": datetime.now()
        }

    def is_empty(self) -> bool:
        """Check if paired section has no students"""
        return self.enrolled == 0

    def get_load_percentage(self) -> float:
        """Get current load as percentage of capacity"""
        return (self.enrolled / self.capacity * 100) if self.capacity > 0 else 0.0

    def get_label(self) -> str:
        """Get human-readable label"""
        return f"{self.g1_course} + {self.g2_course} - Section {self.section_index}"


@dataclass
class Student:
    """Represents a student"""
    registration_number: str
    name: str
    cgpa: float
    timestamp: datetime
    completed_courses: List[str] = field(default_factory=list)
    g1_preferences: List[str] = field(default_factory=list)
    g2_preferences: List[str] = field(default_factory=list)

    def get_sort_key(self, sorting_basis: str = "cgpa") -> Tuple:
        """
        Return sort key based on sorting basis:
        - 'cgpa': CGPA (Highest First) → Timestamp (Earliest First) → RegNo (Alphabetical)
        - 'timestamp': Timestamp (Earliest First) → CGPA (Highest First) → RegNo (Alphabetical)
        """
        if sorting_basis == "timestamp":
            return (self.timestamp, -self.cgpa, self.registration_number)
        else:  # default to 'cgpa'
            return (-self.cgpa, self.timestamp, self.registration_number)


@dataclass
class AllocationResult:
    """Represents allocation result for a student"""
    registration_number: str
    name: str
    g1_course: Optional[str] = None
    g1_section: Optional[str] = None
    g2_course: Optional[str] = None
    g2_section: Optional[str] = None
    pair_label: Optional[str] = None
    g1_preference_rank: Optional[int] = None
    g2_preference_rank: Optional[int] = None
    fallback_used: bool = False
    allocated: bool = False
    reason: Optional[str] = None  # For unallocated students


@dataclass
class AllocationConfig:
    """Configuration for allocation system"""
    courses: Dict[str, Course]  # key: course_code
    sorting_basis: str = "cgpa"  # 'cgpa' or 'timestamp'
    allow_open_seat_fallback: bool = True
    min_section_merge_threshold: int = 5
    compact_section_threshold: int = 35
    min_section_strength: int = 68  # Minimum students per section (admin configurable)
    max_section_strength: int = 75  # Maximum students per section (admin configurable)

    def get_group1_courses(self) -> List[Course]:
        """Get all Group 1 courses"""
        return [c for c in self.courses.values() if c.group == Group.GROUP_1]

    def get_group2_courses(self) -> List[Course]:
        """Get all Group 2 courses"""
        return [c for c in self.courses.values() if c.group == Group.GROUP_2]


@dataclass
class AllocationStats:
    """Statistics about allocation results with fairness metrics"""
    total_students: int
    allocated_students: int
    unallocated_students: int
    fallback_used_count: int
    allocation_rate: float
    cgpa_fairness_score: float = 0.0  # 0-100: measure of fairness (higher = more fair)
    avg_preference_rank: float = 0.0  # Average preference rank (lower = better matching)
    section_load_variance: float = 0.0  # Section capacity utilization variance (lower = balanced)
    g1_distribution: Dict[str, int] = field(default_factory=dict)  # Count per G1 course
    g2_distribution: Dict[str, int] = field(default_factory=dict)  # Count per G2 course
    section_distribution: Dict[str, int] = field(default_factory=dict)  # Count per section
    
    def __post_init__(self):
        if self.total_students > 0:
            self.allocation_rate = self.allocated_students / self.total_students
