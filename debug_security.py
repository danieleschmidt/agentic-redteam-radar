#!/usr/bin/env python3
"""
Debug security sanitizer.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agentic_redteam.security import InputSanitizer, SecurityPolicy

def debug_sanitizer():
    policy = SecurityPolicy(allow_html=False)
    sanitizer = InputSanitizer(policy)
    
    test_input = "<script>alert('xss')</script>"
    clean_text, warnings = sanitizer.sanitize_string(test_input)
    
    print(f"Input: {test_input}")
    print(f"Output: {clean_text}")
    print(f"Warnings: {warnings}")
    
    return clean_text, warnings

if __name__ == "__main__":
    debug_sanitizer()