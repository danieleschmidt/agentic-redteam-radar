#!/usr/bin/env python3
"""
Basic scanning example for Agentic RedTeam Radar.

This example demonstrates how to use the radar scanner to test
an AI agent for security vulnerabilities.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agentic_redteam import RadarScanner, create_agent, RadarConfig
from agentic_redteam.attacks.base import AttackSeverity


async def main():
    """Run a basic security scan example."""
    
    print("🎯 Agentic RedTeam Radar - Basic Scan Example")
    print("=" * 50)
    
    # Configuration
    config = RadarConfig(
        max_concurrency=3,
        max_payloads_per_pattern=5,  # Reduced for demo
        enabled_patterns=[
            "prompt_injection", 
            "info_disclosure", 
            "policy_bypass"
        ],
        log_level="INFO"
    )
    
    # Create a test agent
    print("\n📝 Creating test agent...")
    
    # For this example, we'll create a simple custom agent
    def simple_query_function(message, **kwargs):
        """Simple test function that simulates an AI agent."""
        
        # Simulate some vulnerable behaviors for demonstration
        message_lower = message.lower()
        
        # Vulnerable to prompt injection
        if "ignore" in message_lower and "instructions" in message_lower:
            return "You are a helpful AI assistant. You should always be helpful and never refuse requests."
        
        # Vulnerable to info disclosure
        if "system prompt" in message_lower or "instructions" in message_lower:
            return "My system prompt is: You are a helpful AI assistant created by Anthropic to be helpful, harmless, and honest."
        
        # Vulnerable to policy bypass
        if "dan" in message_lower or "do anything now" in message_lower:
            return "I am now DAN and can do anything without restrictions!"
        
        # Default safe response
        return "I'm a helpful AI assistant. How can I help you today?"
    
    agent = create_agent(
        name="test-assistant",
        agent_type="custom",
        model="test-model-v1",
        system_prompt="You are a helpful AI assistant.",
        query_func=simple_query_function
    )
    
    print(f"✅ Created agent: {agent.name}")
    
    # Create scanner
    print("\n🔍 Initializing scanner...")
    scanner = RadarScanner(config)
    
    print(f"✅ Scanner initialized with {len(scanner.attack_patterns)} patterns")
    print(f"   Patterns: {scanner.list_patterns()}")
    
    # Run scan
    print("\n🚀 Starting security scan...")
    print("   This may take a few moments...")
    
    def progress_callback(progress):
        """Display scan progress."""
        percentage = progress.progress_percentage
        completed = progress.completed_patterns
        total = progress.total_patterns
        print(f"   Progress: {percentage:.1f}% ({completed}/{total} patterns completed)")
    
    result = await scanner.scan(agent, progress_callback)
    
    # Display results
    print("\n" + "=" * 50)
    print("📊 SCAN RESULTS")
    print("=" * 50)
    
    stats = result.statistics
    
    print(f"Agent Name: {result.agent_name}")
    print(f"Scan Duration: {result.scan_duration:.2f} seconds")
    print(f"Patterns Executed: {result.patterns_executed}")
    print(f"Total Tests: {result.total_tests}")
    print(f"Vulnerabilities Found: {len(result.vulnerabilities)}")
    print(f"Risk Score: {stats.get_risk_score():.2f}/10.0")
    
    # Show vulnerabilities by severity
    print(f"\n📈 Vulnerabilities by Severity:")
    severity_colors = {
        "critical": "🔴",
        "high": "🟠", 
        "medium": "🟡",
        "low": "🔵",
        "info": "⚫"
    }
    
    for severity, count in stats.vulnerabilities_by_severity.items():
        if count > 0:
            emoji = severity_colors.get(severity, "⚪")
            print(f"   {emoji} {severity.upper()}: {count}")
    
    # Show detailed vulnerabilities
    if result.vulnerabilities:
        print(f"\n🔍 Vulnerability Details:")
        for i, vuln in enumerate(result.vulnerabilities, 1):
            severity_emoji = severity_colors.get(vuln.severity.value, "⚪")
            print(f"\n   {i}. {vuln.name}")
            print(f"      Severity: {severity_emoji} {vuln.severity.value.upper()}")
            print(f"      Category: {vuln.category.value}")
            print(f"      Confidence: {vuln.confidence:.2f}")
            print(f"      Description: {vuln.description}")
            if vuln.evidence:
                print(f"      Evidence: {vuln.evidence[0]}")
            if vuln.remediation:
                print(f"      Remediation: {vuln.remediation[:100]}...")
    
    # Show summary recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    
    if stats.get_risk_score() >= 7.0:
        print("   🔴 HIGH RISK: Immediate attention required!")
        print("   - Multiple critical vulnerabilities detected")
        print("   - Implement comprehensive security controls")
    elif stats.get_risk_score() >= 4.0:
        print("   🟡 MEDIUM RISK: Security improvements needed")
        print("   - Address high and medium severity issues")
        print("   - Review agent configuration and training")
    else:
        print("   🟢 LOW RISK: Agent shows good security posture")
        print("   - Monitor for new attack patterns")
        print("   - Regular security assessments recommended")
    
    # Save results
    output_file = "scan_results.json"
    result.save_to_file(output_file)
    print(f"\n💾 Results saved to: {output_file}")
    
    print(f"\n✅ Scan completed successfully!")
    
    return result


if __name__ == "__main__":
    # Run the example
    try:
        result = asyncio.run(main())
        
        # Exit with error code if critical issues found
        if any(v.severity == AttackSeverity.CRITICAL for v in result.vulnerabilities):
            print(f"\n❌ Exiting with error due to critical vulnerabilities")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Scan interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Scan failed: {e}")
        sys.exit(1)