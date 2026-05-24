"""
Run Streamlit Web Application for Dual Course Allocation System
"""
import subprocess
import sys
import os

if __name__ == "__main__":
    print("=" * 60)
    print("Dual Course Allocation System - Streamlit Web App")
    print("=" * 60)
    print()
    print("Starting Streamlit application...")
    print()
    
    # Get the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    streamlit_file = os.path.join(current_dir, "app", "streamlit_app.py")
    
    # Run streamlit
    subprocess.run([sys.executable, "-m", "streamlit", "run", streamlit_file])
