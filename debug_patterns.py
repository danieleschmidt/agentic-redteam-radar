#!/usr/bin/env python3
"""Debug pattern loading."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from agentic_redteam.scanner import RadarScanner
from agentic_redteam.config import RadarConfig
from agentic_redteam.attacks.prompt_injection import PromptInjectionAttack
from agentic_redteam.attacks.info_disclosure import InfoDisclosureAttack

config = RadarConfig()
print(f"Enabled patterns: {config.enabled_patterns}")

attack1 = PromptInjectionAttack()
attack2 = InfoDisclosureAttack()

print(f"Attack 1 name: '{attack1.name}'")
print(f"Attack 2 name: '{attack2.name}'")

# Test matching
for pattern_name in config.enabled_patterns:
    print(f"Looking for: '{pattern_name}'")
    print(f"Match attack1: {pattern_name in attack1.name.lower()}")
    print(f"Match attack2: {pattern_name in attack2.name.lower()}")

scanner = RadarScanner(config)
print(f"Loaded patterns: {scanner.list_patterns()}")