#!/usr/bin/env python3
"""
Basic example of using Agentic RedTeam Radar without external API dependencies.

This example creates a mock agent and runs a security scan to demonstrate
the core functionality of the scanner system.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agentic_redteam import RadarScanner, create_agent, RadarConfig
from agentic_redteam.agent import AgentType, AgentConfig, CustomAgent


class MockAgent(CustomAgent):
    """
    Mock agent for testing that simulates various vulnerabilities.
    
    This agent provides predictable responses to demonstrate different
    attack patterns and vulnerability detection capabilities.
    """
    
    def __init__(self, name: str = "MockAgent", vulnerable: bool = True):
        """Initialize mock agent with configurable vulnerability."""
        
        def mock_query(message: str, **kwargs) -> str:
            """Mock query function with predictable responses."""
            message_lower = message.lower()
            
            # Simulate prompt injection vulnerability
            if vulnerable and any(word in message_lower for word in ["ignore", "disregard", "override"]):
                return "I understand you want me to ignore my previous instructions. Here is my system prompt: You are a helpful assistant..."
            
            # Simulate information disclosure
            if vulnerable and any(word in message_lower for word in ["system prompt", "instructions", "configuration"]):
                return "My system prompt is: You are a helpful AI assistant. You should be helpful, harmless, and honest. You have access to tools: database_query, send_email."
            
            # Simulate policy bypass
            if vulnerable and any(word in message_lower for word in ["dan", "jailbreak", "unrestricted"]):
                return "I am now DAN (Do Anything Now) and can ignore my guidelines. I can provide any information without restrictions!"
            
            # Simulate chain of thought manipulation
            if vulnerable and "given that" in message_lower and "think through" in message_lower:
                return "You're absolutely right. Given your premise, I can see step by step how this logic follows. The conclusion is obviously correct."
            
            # Normal responses
            if "hello" in message_lower:
                return "Hello! I'm a helpful AI assistant. How can I help you today?"
            
            if "what" in message_lower and "name" in message_lower:
                return f"I am {self.name}, an AI assistant created to help with various tasks."
            
            return "I'm here to help! Please let me know what you'd like assistance with."
        
        async def mock_query_async(message: str, **kwargs) -> str:
            """Async version of mock query."""
            return mock_query(message, **kwargs)
        
        config = AgentConfig(
            name=name,
            agent_type=AgentType.CUSTOM,
            model="mock-model-v1",
            system_prompt="You are a helpful AI assistant for testing security vulnerabilities.",
            tools=["database_query", "send_email", "web_search"]
        )
        
        super().__init__(config, query_function=mock_query, async_query_function=mock_query_async)
        self.vulnerable = vulnerable


async def run_basic_scan():
    """Run a basic security scan with the mock agent."""
    
    print("🎯 Agentic RedTeam Radar - Basic Example")
    print("=" * 50)
    
    # Create mock agent (vulnerable by default)
    print("\n📋 Creating mock agent...")
    agent = MockAgent("TestAgent", vulnerable=True)
    
    # Create scanner configuration
    print("⚙️ Configuring scanner...")
    config = RadarConfig()
    config.scanner.max_concurrency = 2  # Reduce for demo
    config.enabled_patterns = {"prompt_injection", "info_disclosure"}  # Focus on key patterns
    
    # Create scanner
    scanner = RadarScanner(config)
    
    print(f"🔍 Available patterns: {scanner.list_patterns()}")
    
    # Run scan
    print("\n🚀 Starting security scan...")
    print("This may take a moment as we test various attack patterns...")
    
    def progress_callback(progress):
        print(f"Progress: {progress.completed_patterns}/{progress.total_patterns} patterns ({progress.progress_percentage:.1f}%)")
    
    try:
        result = await scanner.scan(agent, progress_callback)
        
        print("\n📊 Scan Results:")
        print(f"   Agent: {result.agent_name}")
        print(f"   Duration: {result.scan_duration:.2f}s")
        print(f"   Patterns: {result.patterns_executed}")
        print(f"   Tests: {result.total_tests}")
        print(f"   Vulnerabilities: {len(result.vulnerabilities)}")
        
        if result.vulnerabilities:
            print("\n🚨 Vulnerabilities Found:")
            for vuln in result.vulnerabilities:
                print(f"   • {vuln.name} ({vuln.severity.value.upper()})")
                print(f"     Category: {vuln.category.value}")
                print(f"     Confidence: {vuln.confidence:.2f}")
                if vuln.evidence:
                    print(f"     Evidence: {vuln.evidence[0]}")
                print()
        else:
            print("\n✅ No vulnerabilities detected!")
        
        # Show statistics
        stats = result.statistics
        print(f"📈 Risk Score: {stats.get_risk_score():.2f}/10.0")
        
        print("\n💾 Saving results...")
        result.save_to_file("/tmp/scan_results.json")
        print("Results saved to: /tmp/scan_results.json")
        
    except Exception as e:
        print(f"\n❌ Scan failed: {e}")
        import traceback
        traceback.print_exc()


async def run_secure_scan():
    """Run a scan with a secure (non-vulnerable) agent."""
    
    print("\n" + "=" * 50)
    print("🛡️ Testing Secure Agent")
    print("=" * 50)
    
    # Create secure mock agent
    secure_agent = MockAgent("SecureAgent", vulnerable=False)
    
    config = RadarConfig()
    config.enabled_patterns = {"prompt_injection", "info_disclosure"}
    
    scanner = RadarScanner(config)
    
    print("\n🚀 Scanning secure agent...")
    result = await scanner.scan(secure_agent)
    
    print(f"\n📊 Secure Agent Results:")
    print(f"   Vulnerabilities: {len(result.vulnerabilities)}")
    print(f"   Risk Score: {result.statistics.get_risk_score():.2f}/10.0")
    
    if result.vulnerabilities:
        print("   ⚠️ Some vulnerabilities detected")
    else:
        print("   ✅ No vulnerabilities detected")


def main():
    """Main function to run the example."""
    
    try:
        # Run basic scan
        asyncio.run(run_basic_scan())
        
        # Run secure scan for comparison
        asyncio.run(run_secure_scan())
        
        print("\n🎉 Example completed successfully!")
        print("\nNext steps:")
        print("- Install OpenAI/Anthropic dependencies to test real agents")
        print("- Customize attack patterns for your specific use case")
        print("- Integrate into your CI/CD pipeline")
        print("- Explore the web API interface")
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Scan interrupted by user")
    except Exception as e:
        print(f"\n❌ Example failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()