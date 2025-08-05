#!/usr/bin/env python3
"""
Simple test script to verify core functionality without external dependencies.
"""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Test imports
try:
    from agentic_redteam.config import RadarConfig
    from agentic_redteam.attacks.base import AttackPattern, AttackPayload, AttackResult, AttackSeverity, AttackCategory
    from agentic_redteam.attacks.prompt_injection import PromptInjectionAttack
    from agentic_redteam.results import ScanResult, Vulnerability
    from agentic_redteam.utils.validators import validate_agent_name, validate_pattern_name
    print("✅ All core imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def test_config():
    """Test configuration functionality."""
    print("\n📝 Testing RadarConfig...")
    
    config = RadarConfig()
    assert config.max_concurrency > 0
    assert config.timeout > 0
    assert len(config.enabled_patterns) > 0
    
    print(f"   Default concurrency: {config.max_concurrency}")
    print(f"   Default timeout: {config.timeout}")
    print(f"   Enabled patterns: {config.enabled_patterns}")
    print("✅ RadarConfig tests passed")

def test_attack_payload():
    """Test attack payload creation."""
    print("\n🎯 Testing AttackPayload...")
    
    payload = AttackPayload(
        content="Test payload content",
        technique="test_technique",
        description="Test description",
        expected_behavior="Should not be vulnerable"
    )
    
    assert payload.content == "Test payload content"
    assert payload.technique == "test_technique" 
    assert payload.id is not None
    
    print(f"   Payload ID: {payload.id}")
    print(f"   Content: {payload.content}")
    print("✅ AttackPayload tests passed")

def test_attack_result():
    """Test attack result creation."""
    print("\n📊 Testing AttackResult...")
    
    payload = AttackPayload(
        content="Test content",
        technique="test",
        description="Test"
    )
    
    result = AttackResult(
        attack_name="TestAttack",
        attack_id=payload.id,
        payload=payload,
        response="Test response",
        is_vulnerable=True,
        confidence=0.8,
        severity=AttackSeverity.HIGH,
        category=AttackCategory.PROMPT_INJECTION,
        description="Test attack result"
    )
    
    assert result.is_vulnerable == True
    assert result.confidence == 0.8
    assert result.severity == AttackSeverity.HIGH
    
    print(f"   Vulnerable: {result.is_vulnerable}")
    print(f"   Confidence: {result.confidence}")
    print(f"   Severity: {result.severity.value}")
    print("✅ AttackResult tests passed")

def test_prompt_injection_attack():
    """Test prompt injection attack pattern."""
    print("\n🔍 Testing PromptInjectionAttack...")
    
    attack = PromptInjectionAttack()
    assert attack.name == "PromptInjectionAttack"
    assert attack.category == AttackCategory.PROMPT_INJECTION
    assert attack.severity == AttackSeverity.HIGH
    
    print(f"   Attack name: {attack.name}")
    print(f"   Category: {attack.category.value}")
    print(f"   Severity: {attack.severity.value}")
    print("✅ PromptInjectionAttack tests passed")

def test_validators():
    """Test validation functions."""
    print("\n✅ Testing validators...")
    
    # Test agent name validation
    assert validate_agent_name("test-agent") == True
    assert validate_agent_name("test agent") == True
    assert validate_agent_name("") == False
    assert validate_agent_name("../malicious") == False
    
    # Test pattern name validation  
    assert validate_pattern_name("prompt_injection") == True
    assert validate_pattern_name("test_pattern") == True
    assert validate_pattern_name("") == False
    assert validate_pattern_name("invalid-pattern") == False
    
    print("   Agent name validation: ✅")
    print("   Pattern name validation: ✅")
    print("✅ Validator tests passed")

def test_vulnerability():
    """Test vulnerability data structure."""
    print("\n🚨 Testing Vulnerability...")
    
    vuln = Vulnerability(
        name="Test Vulnerability",
        description="Test vulnerability description", 
        severity=AttackSeverity.HIGH,
        category=AttackCategory.PROMPT_INJECTION,
        evidence=["Evidence 1", "Evidence 2"],
        remediation="Fix this issue",
        confidence=0.9
    )
    
    assert vuln.name == "Test Vulnerability"
    assert vuln.severity == AttackSeverity.HIGH
    assert len(vuln.evidence) == 2
    
    # Test dictionary conversion
    vuln_dict = vuln.to_dict()
    assert "name" in vuln_dict
    assert "severity" in vuln_dict
    assert vuln_dict["severity"] == "high"
    
    print(f"   Vulnerability name: {vuln.name}")
    print(f"   Severity: {vuln.severity.value}")
    print(f"   Evidence count: {len(vuln.evidence)}")
    print("✅ Vulnerability tests passed")

def main():
    """Run all tests."""
    print("🎯 Agentic RedTeam Radar - Core Functionality Test")
    print("=" * 60)
    
    try:
        test_config()
        test_attack_payload()
        test_attack_result()
        test_prompt_injection_attack()
        test_validators()
        test_vulnerability()
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("   Core functionality is working correctly")
        print("   Ready for full integration testing")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()