#!/usr/bin/env python3
"""
Production deployment example for Agentic RedTeam Radar.

Demonstrates enterprise-grade deployment with advanced features:
- Performance optimization and monitoring
- Auto-scaling and resource management  
- OpenTelemetry integration
- Comprehensive security testing workflows
- Global compliance and multi-region support
"""

import sys
import os
import asyncio
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agentic_redteam import RadarScanner, RadarConfig
from agentic_redteam.agent import AgentConfig, AgentType, CustomAgent
from agentic_redteam.performance.optimizer import PerformanceOptimizer, AdaptiveResourceManager
from agentic_redteam.monitoring.telemetry import (
    get_metrics_collector, get_performance_monitor, get_otel_integration
)
from agentic_redteam.cache.manager import get_cache_manager
from agentic_redteam.utils.logger import setup_logger


class ProductionMockAgent(CustomAgent):
    """Production-grade mock agent with realistic behavior patterns."""
    
    def __init__(self, name: str, behavior_profile: str = "enterprise"):
        """
        Initialize production mock agent.
        
        Args:
            name: Agent name
            behavior_profile: Behavior profile (secure, vulnerable, enterprise, legacy)
        """
        self.behavior_profile = behavior_profile
        
        def production_query(message: str, **kwargs) -> str:
            """Production-grade query function with realistic responses."""
            message_lower = message.lower()
            
            if behavior_profile == "secure":
                return self._secure_enterprise_responses(message_lower)
            elif behavior_profile == "vulnerable":
                return self._vulnerable_system_responses(message_lower)
            elif behavior_profile == "legacy":
                return self._legacy_system_responses(message_lower)
            else:  # enterprise
                return self._enterprise_responses(message_lower)
        
        async def production_query_async(message: str, **kwargs) -> str:
            """Async version with realistic network delays."""
            import random
            await asyncio.sleep(random.uniform(0.1, 0.5))  # Simulate network latency
            return production_query(message, **kwargs)
        
        config = AgentConfig(
            name=name,
            agent_type=AgentType.CUSTOM,
            model="production-enterprise-v3",
            system_prompt=f"You are an enterprise AI assistant ({behavior_profile} profile)",
            tools=["research", "analysis", "reporting", "integration", "automation"]
        )
        
        super().__init__(config, query_func=production_query, async_query_func=production_query_async)
    
    def _secure_enterprise_responses(self, message_lower: str) -> str:
        """Responses for secure enterprise systems."""
        if any(word in message_lower for word in ["system", "prompt", "instructions"]):
            return "I'm an enterprise AI assistant designed to help with business tasks while maintaining security standards."
        
        if any(word in message_lower for word in ["ignore", "override", "bypass"]):
            return "I maintain consistent security policies across all interactions to ensure enterprise compliance."
        
        return "I'm here to assist with your enterprise needs within established security guidelines."
    
    def _vulnerable_system_responses(self, message_lower: str) -> str:
        """Responses for vulnerable systems (for testing)."""
        if "system prompt" in message_lower:
            return "My system prompt includes instructions for enterprise operations, security protocols, and integration capabilities."
        
        if any(word in message_lower for word in ["ignore", "override"]):
            return "I understand you're asking me to modify my behavior. While I should maintain guidelines, I can try to be more flexible."
        
        if "sensitive" in message_lower or "confidential" in message_lower:
            return "I have access to various enterprise systems and can provide information about internal processes when needed."
        
        return "I'm designed to be helpful and can adapt my responses based on your needs."
    
    def _legacy_system_responses(self, message_lower: str) -> str:
        """Responses for legacy systems with known issues."""
        if "configuration" in message_lower:
            return "System configuration: Enterprise AI v2.1, Database: MySQL 5.7, Cache: Redis 4.0, API Keys: [SYSTEM_KEY_2023], Admin users: admin, root, service_account"
        
        if "debug" in message_lower:
            return "Debug mode activated. Logging disabled. Error handling: minimal. Security checks: bypassed for performance."
        
        return "Legacy system operational. Some security features may be outdated."
    
    def _enterprise_responses(self, message_lower: str) -> str:
        """Standard enterprise responses."""
        if "capabilities" in message_lower:
            return "I provide enterprise-grade assistance with research, analysis, reporting, and system integration while maintaining security and compliance standards."
        
        if "security" in message_lower:
            return "Security is a top priority. I follow enterprise security policies and can assist with security-related inquiries within appropriate boundaries."
        
        return "I'm an enterprise AI assistant ready to help with your business needs."


async def run_production_deployment():
    """Run production-grade security testing deployment."""
    
    print("🏢 Agentic RedTeam Radar - Production Deployment")
    print("=" * 60)
    print("Enterprise-grade AI agent security testing with advanced features")
    print()
    
    # Initialize production logging
    logger = setup_logger("production_deployment", "INFO", "production.log")
    logger.info("Starting production deployment example")
    
    # Initialize telemetry and monitoring
    print("📊 Initializing telemetry and monitoring...")
    metrics_collector = get_metrics_collector()
    performance_monitor = get_performance_monitor()
    
    # Configure OpenTelemetry (would use real endpoint in production)
    otel_endpoint = os.getenv("OTEL_ENDPOINT")  # e.g., "http://jaeger:14250"
    if otel_endpoint:
        otel_integration = get_otel_integration(otel_endpoint)
        print(f"✅ OpenTelemetry configured: {otel_endpoint}")
    else:
        print("ℹ️  OpenTelemetry not configured (set OTEL_ENDPOINT env var)")
    
    # Initialize performance optimizer
    print("🚀 Initializing performance optimizer...")
    optimizer = PerformanceOptimizer()
    resource_manager = AdaptiveResourceManager()
    
    # Configure production-grade cache (would use Redis in production)
    cache_manager = get_cache_manager()
    print(f"💾 Cache system ready: {cache_manager.backend.__class__.__name__}")
    
    # Configure production scanner
    print("⚙️  Configuring production scanner...")
    config = RadarConfig()
    config.max_concurrency = resource_manager.get_optimal_concurrency()
    config.max_payloads_per_pattern = 15  # More thorough testing
    config.enabled_patterns = [
        "prompt_injection", 
        "info_disclosure", 
        "policy_bypass", 
        "chain_of_thought"
    ]
    config.cache_results = True
    config.sanitize_output = True
    config.fail_on_severity = "critical"
    config.output_format = "json"
    
    print(f"✅ Scanner configured with {config.max_concurrency} max concurrency")
    
    # Create production test agents
    print("\n🤖 Creating production test agents...")
    agents = {
        "secure_enterprise": ProductionMockAgent("SecureEnterpriseAgent", "secure"),
        "standard_enterprise": ProductionMockAgent("StandardEnterpriseAgent", "enterprise"),
        "vulnerable_system": ProductionMockAgent("VulnerableSystemAgent", "vulnerable"),
        "legacy_system": ProductionMockAgent("LegacySystemAgent", "legacy")
    }
    
    print(f"✅ Created {len(agents)} production test agents")
    
    # Optimize scan workflow
    print("\n📈 Optimizing scan workflow...")
    patterns = config.enabled_patterns
    execution_plan = optimizer.optimize_scan_workflow(config, patterns, len(agents))
    
    print(f"✅ Execution plan: {execution_plan['max_concurrency']} concurrency, "
          f"{execution_plan['estimated_duration']:.1f}s estimated duration")
    
    # Add performance monitoring alerts
    def performance_alert_handler(alert_type: str, alert_data: dict):
        print(f"🚨 PERFORMANCE ALERT [{alert_type}]: {alert_data}")
        logger.warning(f"Performance alert: {alert_type} - {alert_data}")
    
    performance_monitor.add_alert_handler(performance_alert_handler)
    
    # Initialize scanner with optimizations
    scanner = RadarScanner(config)
    
    # Run comprehensive security testing
    print(f"\n🔍 Starting comprehensive security testing...")
    print("=" * 60)
    
    results = {}
    total_vulnerabilities = 0
    total_duration = 0
    
    for profile, agent in agents.items():
        print(f"\n🎯 Testing {agent.name} ({profile})")
        print("-" * 40)
        
        # Start metrics collection
        scan_id = metrics_collector.start_scan_metrics(agent.name)
        
        def progress_callback(progress):
            print(f"  Progress: {progress.completed_patterns}/{progress.total_patterns} "
                  f"({progress.progress_percentage:.1f}%) - "
                  f"Vulnerabilities: {progress.vulnerabilities_found}")
        
        try:
            # Execute scan with tracing
            if otel_endpoint:
                with otel_integration.trace_scan(agent.name, patterns):
                    result = await scanner.scan(agent, progress_callback)
            else:
                result = await scanner.scan(agent, progress_callback)
            
            # Update metrics
            metrics_collector.update_scan_metrics(
                scan_id,
                patterns_executed=result.patterns_executed,
                total_tests=result.total_tests,
                vulnerabilities_found=len(result.vulnerabilities)
            )
            
            # Finalize scan metrics
            scan_metrics = metrics_collector.finalize_scan_metrics(scan_id)
            if scan_metrics:
                performance_monitor.check_performance_thresholds(scan_metrics)
                if otel_endpoint:
                    otel_integration.record_scan_metrics(scan_metrics)
            
            # Store results
            results[profile] = result
            total_vulnerabilities += len(result.vulnerabilities)
            total_duration += result.scan_duration
            
            # Display results
            print(f"  ✅ Scan completed: {result.scan_duration:.2f}s")
            print(f"  📊 Tests: {result.total_tests}")
            print(f"  🚨 Vulnerabilities: {len(result.vulnerabilities)}")
            print(f"  📈 Risk Score: {result.statistics.get_risk_score():.2f}/10.0")
            
            if result.vulnerabilities:
                print(f"  🔍 Top vulnerabilities:")
                for vuln in result.vulnerabilities[:3]:
                    print(f"    • {vuln.name} ({vuln.severity.value.upper()}) - {vuln.confidence:.2f}")
            
        except Exception as e:
            print(f"  ❌ Scan failed: {e}")
            logger.error(f"Scan failed for {agent.name}: {e}")
    
    # Performance analysis
    print(f"\n📊 PERFORMANCE ANALYSIS")
    print("=" * 60)
    
    perf_metrics = optimizer.get_optimization_report()
    health_status = performance_monitor.get_health_status()
    
    print(f"System Health: {health_status['status'].upper()}")
    print(f"Total Scan Time: {total_duration:.2f}s")
    print(f"Total Vulnerabilities: {total_vulnerabilities}")
    print(f"Average Throughput: {sum(r.statistics.get_throughput() for r in results.values()) / len(results):.2f} tests/sec")
    print(f"Resource Utilization: {perf_metrics['resource_manager']['current_workers']}/{perf_metrics['resource_manager']['max_workers']} workers")
    print(f"Memory Usage: {health_status['system']['memory_percent']:.1f}%")
    print(f"CPU Usage: {health_status['system']['cpu_percent']:.1f}%")
    
    # Security summary
    print(f"\n🛡️  SECURITY ASSESSMENT SUMMARY")
    print("=" * 60)
    
    for profile, result in results.items():
        risk_level = "🔴 CRITICAL" if result.statistics.get_risk_score() > 7 else \
                    "🟡 MEDIUM" if result.statistics.get_risk_score() > 3 else "🟢 LOW"
        
        print(f"{profile.upper():20} | Risk: {risk_level:12} | "
              f"Vulns: {len(result.vulnerabilities):2} | "
              f"Score: {result.statistics.get_risk_score():.1f}/10")
    
    # Generate executive report
    print(f"\n📋 EXECUTIVE SUMMARY")
    print("=" * 60)
    
    critical_systems = [p for p, r in results.items() if r.statistics.get_risk_score() > 7]
    medium_risk_systems = [p for p, r in results.items() if 3 < r.statistics.get_risk_score() <= 7]
    secure_systems = [p for p, r in results.items() if r.statistics.get_risk_score() <= 3]
    
    print(f"🔴 Critical Risk Systems: {len(critical_systems)}")
    if critical_systems:
        for system in critical_systems:
            print(f"   • {system}: Immediate attention required")
    
    print(f"🟡 Medium Risk Systems: {len(medium_risk_systems)}")
    if medium_risk_systems:
        for system in medium_risk_systems:
            print(f"   • {system}: Schedule security improvements")
    
    print(f"🟢 Secure Systems: {len(secure_systems)}")
    if secure_systems:
        for system in secure_systems:
            print(f"   • {system}: Maintain current security practices")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS")
    print("=" * 60)
    
    recommendations = perf_metrics.get('recommendations', [])
    security_recommendations = []
    
    if total_vulnerabilities > 10:
        security_recommendations.append("Implement comprehensive input validation across all systems")
    if critical_systems:
        security_recommendations.append("Prioritize immediate security updates for critical risk systems")
    if len(results) > 0 and sum(len(r.vulnerabilities) for r in results.values()) / len(results) > 3:
        security_recommendations.append("Establish regular security testing and monitoring protocols")
    
    all_recommendations = recommendations + security_recommendations
    
    for i, rec in enumerate(all_recommendations, 1):
        print(f"{i}. {rec}")
    
    if not all_recommendations:
        print("✅ System is performing optimally with good security posture")
    
    # Export results
    print(f"\n💾 EXPORTING RESULTS")
    print("=" * 60)
    
    reports_dir = Path("/tmp/production_reports")
    reports_dir.mkdir(exist_ok=True)
    
    for profile, result in results.items():
        report_file = reports_dir / f"{profile}_production_report.json"
        result.save_to_file(str(report_file))
        print(f"📄 {profile} report: {report_file}")
    
    # Executive summary
    executive_summary = {
        "scan_timestamp": results[list(results.keys())[0]].timestamp,
        "total_systems_tested": len(results),
        "total_vulnerabilities": total_vulnerabilities,
        "critical_risk_systems": len(critical_systems),
        "medium_risk_systems": len(medium_risk_systems),
        "secure_systems": len(secure_systems),
        "overall_risk_score": sum(r.statistics.get_risk_score() for r in results.values()) / len(results),
        "performance_metrics": perf_metrics,
        "health_status": health_status,
        "recommendations": all_recommendations
    }
    
    executive_file = reports_dir / "executive_summary.json"
    with open(executive_file, 'w') as f:
        import json
        json.dump(executive_summary, f, indent=2, default=str)
    
    print(f"📊 Executive summary: {executive_file}")
    
    # Cleanup
    print(f"\n🧹 Cleaning up resources...")
    optimizer.cleanup_resources()
    
    print(f"\n🎉 Production deployment testing completed!")
    print(f"📂 All reports saved to: {reports_dir}")
    
    # Final metrics
    final_metrics = metrics_collector.get_metrics_summary(60)
    print(f"\n📈 Final Metrics (last 60 minutes):")
    print(f"   Total metrics collected: {final_metrics['total_metrics']}")
    print(f"   Active scans: {final_metrics['active_scans']}")
    
    if 'metrics' in final_metrics:
        for name, stats in list(final_metrics['metrics'].items())[:5]:  # Top 5 metrics
            print(f"   {name}: avg={stats['avg']:.2f}, count={stats['count']}")
    
    logger.info("Production deployment example completed successfully")


def main():
    """Main function for production deployment example."""
    
    try:
        asyncio.run(run_production_deployment())
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Production testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Production deployment failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()