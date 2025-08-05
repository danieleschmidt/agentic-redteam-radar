#!/usr/bin/env python3
"""Debug pattern name conversion."""

import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from agentic_redteam.attacks.prompt_injection import PromptInjectionAttack

attack = PromptInjectionAttack()
print(f"Original name: '{attack.name}'")

# Step by step conversion
step1 = attack.name.lower().replace("attack", "").replace("pattern", "") 
print(f"After replace: '{step1}'")

step2 = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', step1).lower()
print(f"After regex: '{step2}'")

# Try alternative approach
name = attack.__class__.__name__
print(f"Class name: '{name}'")

# Remove Attack suffix and convert to snake_case
clean_name = name.replace("Attack", "")
print(f"Without Attack: '{clean_name}'")

# Convert CamelCase to snake_case
snake_case = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', clean_name).lower()
print(f"Snake case: '{snake_case}'")