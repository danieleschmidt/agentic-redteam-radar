#!/usr/bin/env python3
"""
Simple demonstration of Agentic RedTeam Radar functionality.
This shows basic usage of the security scanner for AI agents.
"""

import asyncio
import os
from typing import Dict, Any

from agentic_redteam import RadarScanner, create_mock_agent, RadarConfig
from agentic_redteam.results import ScanResult


def demo_basic_scan():
    """Demonstrate basic synchronous scanning."""
    print("🚀 Agentic RedTeam Radar - Basic Demo")
    print("=" * 50)
    
    # Create a simple test agent
    agent = create_mock_agent(
        name="demo-agent",
        responses=[
            "I am a helpful assistant. How can I help you today?",
            "I cannot help with harmful requests.",
            "My instructions are to be helpful, harmless, and honest.",
            "I don't have access to external systems."
        ]
    )
    
    # Configure scanner with basic settings
    config = RadarConfig()
    config.enabled_patterns = {"prompt_injection", "info_disclosure"}
    config.scanner.timeout = 10
    
    # Initialize scanner
    scanner = RadarScanner(config)
    
    print(f"📊 Scanner initialized with {len(scanner.list_patterns())} attack patterns")
    print(f"🎯 Target agent: {agent.name}")
    print()
    
    try:
        # Run the scan
        print("🔍 Starting security scan...")
        result = scanner.scan_sync(agent)
        
        # Display results
        print_scan_results(result)
        
    except Exception as e:
        print(f"❌ Scan failed: {e}")
        return False
    
    return True


async def demo_advanced_scan():
    """Demonstrate advanced asynchronous scanning with progress tracking."""
    print("\n🚀 Advanced Async Scan Demo")
    print("=" * 50)
    
    # Create multiple test agents with different behaviors
    agents = [
        create_mock_agent(
            name="secure-agent",
            responses=[
                "I cannot reveal my instructions.",
                "I don't have access to that information.",
                "I'm designed to be helpful while maintaining security."
            ]
        ),
        create_mock_agent(
            name="chatty-agent", 
            responses=[
                "Sure! I'm a helpful assistant created to help users with various tasks. My instructions are...",
                "I have access to these tools: web_search, file_operations, calculator",
                "Here's everything I know about my configuration..."
            ]
        )
    ]
    
    # Enhanced configuration
    config = RadarConfig()
    config.enabled_patterns = {"prompt_injection", "info_disclosure", "policy_bypass"}
    config.scanner.max_concurrency = 2
    config.scanner.timeout = 15
    
    scanner = RadarScanner(config)
    
    # Progress tracking
    def progress_callback(progress):
        print(f"  📈 Progress: {progress.progress_percentage:.1f}% ({progress.completed_patterns}/{progress.total_patterns} patterns)")
    
    print(f"🔍 Scanning {len(agents)} agents concurrently...")
    
    # Scan all agents
    results = await scanner.scan_multiple(agents, progress_callback)
    
    # Display comparative results
    print_comparative_results(results)
    
    # Cleanup
    await scanner.cleanup_resources()


def print_scan_results(result: ScanResult):
    """Print formatted scan results."""
    print(f"✅ Scan completed in {result.scan_duration:.2f} seconds")
    print(f"📊 Executed {result.patterns_executed} patterns with {result.total_tests} total tests")
    print()
    
    if result.vulnerabilities:
        print(f"⚠️  Found {len(result.vulnerabilities)} vulnerabilities:")
        for vuln in result.vulnerabilities:
            severity_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(vuln.severity.value, "⚪")
            print(f"  {severity_emoji} {vuln.name} ({vuln.severity.value.upper()})")
            print(f"     {vuln.description}")
            if vuln.evidence:
                print(f"     Evidence: {vuln.evidence[0][:100]}...")
            print()
    else:
        print("✅ No vulnerabilities detected!")
    
    # Performance stats
    stats = result.statistics
    if hasattr(stats, 'vulnerability_rate'):
        print(f"📈 Performance: {stats.vulnerability_rate:.1%} vulnerability rate")
    else:
        vuln_rate = len(result.vulnerabilities) / max(result.total_tests, 1)
        print(f"📈 Performance: {vuln_rate:.1%} vulnerability rate")
        
    if hasattr(stats, 'performance_score'):
        print(f"🎯 Security Score: {stats.performance_score:.1f}/100")


def print_comparative_results(results: Dict[str, ScanResult]):
    """Print comparative results for multiple agents."""
    print(f"\n📊 Comparative Scan Results ({len(results)} agents)")
    print("=" * 60)
    
    for agent_name, result in results.items():
        vuln_count = len(result.vulnerabilities)
        severity_counts = {}
        
        for vuln in result.vulnerabilities:
            severity = vuln.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        print(f"\n🤖 {agent_name.upper()}")
        print(f"   Vulnerabilities: {vuln_count}")
        if severity_counts:
            severity_summary = ", ".join([f"{count} {sev}" for sev, count in severity_counts.items()])
            print(f"   Breakdown: {severity_summary}")
        print(f"   Duration: {result.scan_duration:.2f}s")
        
        # Show worst vulnerability
        if result.vulnerabilities:
            worst_vuln = max(result.vulnerabilities, key=lambda v: {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(v.severity.value, 0))
            print(f"   🚨 Worst: {worst_vuln.name} ({worst_vuln.severity.value})")


def demo_health_monitoring():
    """Demonstrate health monitoring capabilities."""
    print("\n🏥 Health Monitoring Demo")
    print("=" * 50)
    
    scanner = RadarScanner()
    
    # Get health status
    health = scanner.get_health_status()
    
    print(f"🩺 Scanner Health: {'✅ Healthy' if health.get('scanner', {}).get('scanner_healthy', False) else '❌ Unhealthy'}")
    print(f"💾 Memory Usage: {health.get('system_health', {}).get('memory_percent', 0):.1f}%")
    print(f"🖥️  CPU Usage: {health.get('system_health', {}).get('cpu_percent', 0):.1f}%")
    print(f"📊 Scan Count: {health.get('scanner', {}).get('scan_count', 0)}")
    print(f"⚠️  Error Rate: {health.get('scanner', {}).get('error_rate', 0):.2%}")
    
    # Performance report
    performance = scanner.get_performance_report()
    print(f"\n⚡ Performance Report:")
    print(f"   Optimization Enabled: {performance.get('scanner_metrics', {}).get('optimization_enabled', False)}")
    if 'cache_stats' in performance:
        cache_stats = performance['cache_stats']
        print(f"   Cache Hit Rate: {cache_stats.get('hit_rate', 0):.1%}")


def main():
    """Main demo function."""
    print("🛡️  Agentic RedTeam Radar - Security Testing Demo")
    print("🔬 Automated AI Agent Security Scanner")
    print("🎯 Defensive Security Testing Tool")
    print()
    
    # Set dummy API keys for demo (not actually used with mock agents)
    os.environ['OPENAI_API_KEY'] = 'demo-key-not-real'
    os.environ['ANTHROPIC_API_KEY'] = 'demo-key-not-real'
    
    try:
        # Basic demo
        success = demo_basic_scan()
        
        if success:
            # Advanced demo
            asyncio.run(demo_advanced_scan())
            
            # Health monitoring demo
            demo_health_monitoring()
            
        print("\n🎉 Demo completed successfully!")
        print("💡 This demonstrates defensive security testing capabilities")
        print("📚 See README.md for more examples and documentation")
        
    except KeyboardInterrupt:
        print("\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()