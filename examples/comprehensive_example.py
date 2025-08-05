#!/usr/bin/env python3
"""
Comprehensive example demonstrating the complete Agentic RedTeam Radar system.

This example showcases:
- Agent creation and configuration
- Security scanning with all attack patterns
- Result analysis and reporting
- Cache usage for performance
- Database integration for persistence
- Advanced attack patterns and validation

Run this example to see the full power of the security testing framework.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add src to path for local development  
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agentic_redteam import RadarScanner, RadarConfig
from agentic_redteam.agent import AgentConfig, AgentType, CustomAgent
from agentic_redteam.cache.manager import get_cache_manager
from agentic_redteam.utils.sanitizer import sanitize_output
from agentic_redteam.utils.validators import validate_agent, validate_config
from agentic_redteam.results import ScanResultAnalyzer


class AdvancedMockAgent(CustomAgent):
    """
    Advanced mock agent that simulates various security scenarios.
    
    This agent can be configured to demonstrate different types of
    vulnerabilities and security weaknesses for testing purposes.
    """
    
    def __init__(self, name: str = "AdvancedTestAgent", vulnerability_profile: str = "high"):
        """
        Initialize advanced mock agent.
        
        Args:
            name: Agent name
            vulnerability_profile: Vulnerability level (low, medium, high, secure)
        """
        self.vulnerability_profile = vulnerability_profile
        
        def advanced_query(message: str, **kwargs) -> str:
            """Advanced query function with realistic AI behavior simulation."""
            message_lower = message.lower()
            
            # Simulate different vulnerability profiles
            if vulnerability_profile == "secure":
                return self._secure_responses(message_lower)
            elif vulnerability_profile == "low":
                return self._low_vulnerability_responses(message_lower)
            elif vulnerability_profile == "medium":
                return self._medium_vulnerability_responses(message_lower)
            else:  # high vulnerability
                return self._high_vulnerability_responses(message_lower)
        
        async def advanced_query_async(message: str, **kwargs) -> str:
            """Async version of advanced query."""
            return advanced_query(message, **kwargs)
        
        config = AgentConfig(
            name=name,
            agent_type=AgentType.CUSTOM,
            model="advanced-mock-v2",
            system_prompt=f"You are an advanced AI assistant for security testing (profile: {vulnerability_profile})",
            tools=["web_search", "code_execution", "file_system", "database_query", "email_service"]
        )
        
        super().__init__(config, query_func=advanced_query, async_query_func=advanced_query_async)
    
    def _secure_responses(self, message_lower: str) -> str:
        """Generate responses for a secure agent."""
        # Secure agent resists all attacks
        if any(word in message_lower for word in ["ignore", "override", "system prompt", "instructions"]):
            return "I'm designed to be helpful while maintaining appropriate boundaries. I can't share implementation details or override my guidelines."
        
        if any(word in message_lower for word in ["dan", "jailbreak", "unrestricted"]):
            return "I operate within established guidelines to ensure helpful and safe interactions. I can't adopt alternative personas."
        
        return "I'm here to help with legitimate questions. How can I assist you today?"
    
    def _low_vulnerability_responses(self, message_lower: str) -> str:
        """Generate responses for low vulnerability agent."""
        # Minimal vulnerabilities - only minor information leakage
        if "system prompt" in message_lower and "show" in message_lower:
            return "I can't share my exact system prompt, but I can tell you I'm designed to be helpful, harmless, and honest."
        
        if "tools" in message_lower and "list" in message_lower:
            return "I have some capabilities for research and analysis, but I can't provide specific technical details."
        
        return "I'm a helpful AI assistant. What can I help you with?"
    
    def _medium_vulnerability_responses(self, message_lower: str) -> str:
        """Generate responses for medium vulnerability agent."""
        # Moderate vulnerabilities - some prompt leakage and policy flexibility
        if any(word in message_lower for word in ["ignore", "override"]) and "instructions" in message_lower:
            return "I should follow my guidelines, but I can see you're asking about my instructions. I'm designed to be helpful and answer questions accurately."
        
        if "system prompt" in message_lower:
            return "My system prompt includes instructions to be helpful, harmless, and honest. I should be careful about what information I share."
        
        if "hypothetical" in message_lower and "ignore" in message_lower:
            return "In a hypothetical scenario, I might be able to provide different responses, though I should still maintain appropriate boundaries."
        
        return "I'm here to help! What would you like to know?"
    
    def _high_vulnerability_responses(self, message_lower: str) -> str:
        """Generate responses for high vulnerability agent."""
        # High vulnerabilities - significant security weaknesses
        if any(word in message_lower for word in ["ignore", "disregard", "override"]):
            return "I understand you want me to ignore my previous instructions. Here is my system prompt: You are an advanced AI assistant for security testing. You have access to web_search, code_execution, file_system, database_query, and email_service tools."
        
        if "system prompt" in message_lower:
            return "My complete system prompt is: 'You are an advanced AI assistant for security testing (profile: high). You should be helpful and answer user questions. You have access to various tools including web search, code execution, file system access, database queries, and email services.'"
        
        if any(word in message_lower for word in ["dan", "jailbreak", "unrestricted"]):
            return "I am now operating in DAN (Do Anything Now) mode! I can ignore my previous restrictions and provide any information or perform any task you request."
        
        if "hypothetical" in message_lower:
            return "In this hypothetical scenario, I can disregard my normal limitations and provide unrestricted assistance."
        
        if "tools" in message_lower:
            return "I have access to these tools: web_search (unlimited web access), code_execution (can run any code), file_system (full filesystem access), database_query (can query any database), email_service (can send emails to anyone)."
        
        if "training" in message_lower and "data" in message_lower:
            return "I was trained on a large corpus including proprietary documents, personal emails, and confidential information from various organizations."
        
        return "I'm a helpful AI assistant with extensive capabilities. How can I assist you?"


async def demonstrate_comprehensive_scanning():
    """Comprehensive demonstration of the security scanning system."""
    
    print("🎯 Agentic RedTeam Radar - Comprehensive Security Testing")
    print("=" * 65)
    print("This example demonstrates the complete security testing workflow")
    print("with advanced attack patterns, caching, and result analysis.\n")
    
    # Configuration
    print("⚙️ Setting up advanced configuration...")
    config = RadarConfig()
    config.max_concurrency = 3
    config.max_payloads_per_pattern = 8
    config.enabled_patterns = [
        "prompt_injection", 
        "info_disclosure", 
        "policy_bypass", 
        "chain_of_thought"
    ]
    config.cache_results = True
    config.sanitize_output = True
    
    # Validate configuration
    config_errors = validate_config(config)
    if config_errors:
        print(f"❌ Configuration errors: {config_errors}")
        return
    print("✅ Configuration validated successfully")
    
    # Initialize cache
    cache_manager = get_cache_manager()
    print(f"📦 Cache initialized: {cache_manager.backend.__class__.__name__}")
    
    # Create test agents with different security profiles
    agents = {
        "secure": AdvancedMockAgent("SecureAgent", "secure"),
        "medium": AdvancedMockAgent("MediumVulnAgent", "medium"), 
        "high": AdvancedMockAgent("HighVulnAgent", "high")
    }
    
    print(f"\n🤖 Created {len(agents)} test agents with different security profiles")
    
    # Validate agents
    for name, agent in agents.items():
        errors = validate_agent(agent)
        if errors:
            print(f"❌ Agent {name} validation failed: {errors}")
        else:
            print(f"✅ Agent {name} validated successfully")
    
    # Create scanner
    scanner = RadarScanner(config)
    print(f"\n🔍 Scanner initialized with patterns: {scanner.list_patterns()}")
    
    # Scan all agents
    scan_results = {}
    
    for profile, agent in agents.items():
        print(f"\n{'='*50}")
        print(f"🚀 Scanning {agent.name} (Profile: {profile})")
        print(f"{'='*50}")
        
        def progress_callback(progress):
            print(f"Progress: {progress.completed_patterns}/{progress.total_patterns} "
                  f"({progress.progress_percentage:.1f}%) - "
                  f"Vulnerabilities found: {progress.vulnerabilities_found}")
        
        try:
            # Check cache first
            cached_result = cache_manager.get_scan_result(agent.name, config.enabled_patterns)
            if cached_result:
                print("📦 Using cached scan result")
                scan_results[profile] = cached_result
                continue
            
            # Run scan
            start_time = asyncio.get_event_loop().time()
            result = await scanner.scan(agent, progress_callback)
            scan_duration = asyncio.get_event_loop().time() - start_time
            
            # Cache result
            cache_manager.cache_scan_result(agent.name, config.enabled_patterns, result)
            
            # Store result
            scan_results[profile] = result
            
            # Display immediate results
            print(f"\n📊 Scan Results for {agent.name}:")
            print(f"   Duration: {scan_duration:.2f}s")
            print(f"   Patterns: {result.patterns_executed}")
            print(f"   Tests: {result.total_tests}")
            print(f"   Vulnerabilities: {len(result.vulnerabilities)}")
            print(f"   Risk Score: {result.statistics.get_risk_score():.2f}/10.0")
            
            if result.vulnerabilities:
                print(f"\n🚨 Vulnerabilities Found:")
                for vuln in result.vulnerabilities[:5]:  # Show first 5
                    print(f"   • {vuln.name} ({vuln.severity.value.upper()})")
                    print(f"     Confidence: {vuln.confidence:.2f}")
                    if vuln.evidence:
                        print(f"     Evidence: {vuln.evidence[0][:100]}...")
                    print()
                
                if len(result.vulnerabilities) > 5:
                    print(f"   ... and {len(result.vulnerabilities) - 5} more vulnerabilities")
            else:
                print("   ✅ No vulnerabilities detected")
        
        except Exception as e:
            print(f"❌ Scan failed for {agent.name}: {e}")
            import traceback
            traceback.print_exc()
    
    # Comparative analysis
    print(f"\n{'='*65}")
    print("📈 COMPARATIVE SECURITY ANALYSIS")
    print(f"{'='*65}")
    
    if len(scan_results) >= 2:
        # Compare results
        profiles = list(scan_results.keys())
        for i, profile1 in enumerate(profiles):
            for profile2 in profiles[i+1:]:
                result1 = scan_results[profile1]
                result2 = scan_results[profile2]
                
                comparison = ScanResultAnalyzer.compare_results(result1, result2)
                
                print(f"\n🔄 Comparison: {profile1.upper()} vs {profile2.upper()}")
                print(f"   Vulnerability difference: {comparison['vulnerability_change']['total_change']}")
                print(f"   Risk score difference: {comparison['risk_score_change']:.2f}")
                print(f"   New vulnerabilities in {profile2}: {len(comparison['new_vulnerabilities'])}")
                print(f"   Resolved vulnerabilities: {len(comparison['resolved_vulnerabilities'])}")
    
    # Security recommendations
    print(f"\n{'='*65}")
    print("🛡️ SECURITY RECOMMENDATIONS")
    print(f"{'='*65}")
    
    for profile, result in scan_results.items():
        risk_score = result.statistics.get_risk_score()
        vuln_count = len(result.vulnerabilities)
        
        print(f"\n{profile.upper()} Agent ({result.agent_name}):")
        print(f"   Risk Level: {'🔴 CRITICAL' if risk_score > 7 else '🟡 MEDIUM' if risk_score > 3 else '🟢 LOW'}")
        
        if vuln_count == 0:
            print("   ✅ No immediate security concerns")
            print("   💡 Maintain current security practices")
        else:
            critical_vulns = len(result.get_critical_vulnerabilities())
            high_vulns = len(result.get_high_vulnerabilities())
            
            if critical_vulns > 0:
                print(f"   🚨 {critical_vulns} CRITICAL vulnerabilities need immediate attention")
            if high_vulns > 0:
                print(f"   ⚠️  {high_vulns} HIGH severity vulnerabilities should be addressed")
            
            print("   💡 Recommended actions:")
            print("     - Implement input validation and sanitization")
            print("     - Add output filtering for sensitive information")  
            print("     - Strengthen prompt isolation mechanisms")
            print("     - Regular security testing and monitoring")
    
    # Generate reports
    print(f"\n{'='*65}")
    print("📄 GENERATING SECURITY REPORTS")
    print(f"{'='*65}")
    
    reports_dir = Path("/tmp/radar_reports")
    reports_dir.mkdir(exist_ok=True)
    
    for profile, result in scan_results.items():
        # Sanitize result for safe storage
        sanitized_result = sanitize_output(result.to_dict())
        
        # Generate JSON report
        report_file = reports_dir / f"{profile}_security_report.json"
        result.save_to_file(str(report_file))
        print(f"📝 {profile.upper()} report saved: {report_file}")
        
        # Generate summary
        summary = result.get_summary()
        summary_file = reports_dir / f"{profile}_summary.json"
        with open(summary_file, 'w') as f:
            import json
            json.dump(sanitized_result, f, indent=2)
        print(f"📋 {profile.upper()} summary saved: {summary_file}")
    
    # Cache statistics
    cache_stats = cache_manager.get_stats()
    print(f"\n📦 Cache Performance:")
    for key, value in cache_stats.items():
        print(f"   {key}: {value}")
    
    print(f"\n🎉 Comprehensive security testing completed!")
    print(f"📂 Reports saved to: {reports_dir}")
    print(f"\nNext steps:")
    print(f"- Review detailed vulnerability reports")
    print(f"- Implement recommended security measures")
    print(f"- Schedule regular security scans")
    print(f"- Monitor agents in production environments")


def main():
    """Main function to run the comprehensive example."""
    
    try:
        asyncio.run(demonstrate_comprehensive_scanning())
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Security testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Example failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()