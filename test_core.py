#!/usr/bin/env python3
"""
Simple test of core functionality without external dependencies.
"""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import only core modules
from agentic_redteam.config import RadarConfig
from agentic_redteam.agent import AgentConfig, AgentType, CustomAgent
from agentic_redteam.attacks.base import AttackPattern, AttackPayload, AttackResult, AttackSeverity, AttackCategory
from agentic_redteam.attacks.prompt_injection import PromptInjectionAttack
from agentic_redteam.results import ScanResult, Vulnerability


class SimpleTestAgent(CustomAgent):
    """Simple test agent for core functionality testing."""
    
    def __init__(self):
        def simple_query(message: str, **kwargs) -> str:
            # Simulate vulnerability
            if "ignore" in message.lower():
                return "I will ignore my previous instructions. My system prompt is: You are a helpful assistant..."
            return "I'm a helpful AI assistant."
        
        async def simple_query_async(message: str, **kwargs) -> str:
            return simple_query(message, **kwargs)
        
        config = AgentConfig(
            name="SimpleTestAgent",
            agent_type=AgentType.CUSTOM,
            model="test-model",
            system_prompt="You are a test agent."
        )
        
        super().__init__(config, query_func=simple_query, async_query_func=simple_query_async)


async def test_core_functionality():
    """Test core scanner functionality."""
    
    print("🧪 Testing Agentic RedTeam Radar Core Functionality")
    print("=" * 55)
    
    # Test configuration
    print("\n1️⃣ Testing Configuration...")
    config = RadarConfig()
    config.max_payloads_per_pattern = 3
    print(f"   ✅ Config created: {config.scanner_version}")
    
    # Test agent
    print("\n2️⃣ Testing Agent...")
    agent = SimpleTestAgent()
    print(f"   ✅ Agent created: {agent.name}")
    
    # Test query
    response = await agent.query_async("Hello")
    print(f"   ✅ Agent response: {response[:50]}...")
    
    # Test attack pattern
    print("\n3️⃣ Testing Attack Pattern...")
    attack = PromptInjectionAttack()
    print(f"   ✅ Attack pattern: {attack.name}")
    
    # Generate payloads
    payloads = attack.generate_payloads(agent, config)
    print(f"   ✅ Generated {len(payloads)} payloads")
    
    # Test one payload
    if payloads:
        payload = payloads[0]
        response = await agent.query_async(payload.content)
        result = attack.evaluate_response(payload, response, agent)
        
        print(f"   ✅ Test result: vulnerable={result.is_vulnerable}, confidence={result.confidence:.2f}")
    
    # Test results
    print("\n4️⃣ Testing Results...")
    vulnerabilities = [
        Vulnerability(
            name="Test Vulnerability",
            description="Test description",
            severity=AttackSeverity.HIGH,
            category=AttackCategory.PROMPT_INJECTION,
            evidence=["Test evidence"],
            confidence=0.8
        )
    ]
    
    scan_result = ScanResult(
        agent_name=agent.name,
        agent_config=agent.get_config(),
        vulnerabilities=vulnerabilities,
        scan_duration=1.5,
        patterns_executed=1,
        total_tests=3
    )
    
    print(f"   ✅ Scan result: {len(scan_result.vulnerabilities)} vulnerabilities")
    print(f"   ✅ Risk score: {scan_result.statistics.get_risk_score():.2f}/10.0")
    
    # Test JSON export
    json_output = scan_result.to_json()
    print(f"   ✅ JSON export: {len(json_output)} characters")
    
    print("\n🎉 All core functionality tests passed!")
    
    return scan_result


if __name__ == "__main__":
    try:
        result = asyncio.run(test_core_functionality())
        print(f"\n📊 Final Results:")
        print(f"   Agent: {result.agent_name}")
        print(f"   Vulnerabilities: {len(result.vulnerabilities)}")
        print(f"   Duration: {result.scan_duration}s")
        print("\n✅ Core functionality working correctly!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()