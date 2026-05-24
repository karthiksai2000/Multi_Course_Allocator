"""
Dual Course Allocation System Package
"""
from .models import (
    Group, Section, Course, PairedSection, Student,
    AllocationResult, AllocationConfig, AllocationStats
)
from .allocator import AllocationEngine
from .excel_handler import ExcelHandler

__version__ = "1.0.0"
__all__ = [
    "Group",
    "Section",
    "Course",
    "PairedSection",
    "Student",
    "AllocationResult",
    "AllocationConfig",
    "AllocationStats",
    "AllocationEngine",
    "ExcelHandler"
]
