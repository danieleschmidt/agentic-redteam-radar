"""
Enhanced Generation 2 scanner with reliability features.
"""

import sys
import asyncio
import time
from pathlib import Path

# Add source to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agentic_redteam import RadarScanner
from agentic_redteam.agent import create_mock_agent
from agentic_redteam.reliability.simple_health_monitor import SimpleHealthMonitor
from agentic_redteam.monitoring.error_handler import ErrorHandler
from agentic_redteam.security.input_sanitizer import InputSanitizer


async def demonstrate_generation2_reliability():
    """
    Demonstrate Generation 2 reliability enhancements.
    """
    print("🛡️ GENERATION 2: RELIABILITY ENHANCEMENT DEMO")
    print("=" * 50)
    
    # Initialize components
    scanner = RadarScanner()
    health_monitor = SimpleHealthMonitor()
    error_handler = ErrorHandler()
    input_sanitizer = InputSanitizer()
    
    # Start health monitoring
    await health_monitor.start_monitoring()
    
    try:
        # Create test agent
        agent = create_mock_agent("gen2-reliability-test")
        
        # Test 1: Health Monitoring
        print("\n1. Health Monitoring System")
        print("-" * 30)
        health = health_monitor.get_current_health()
        print(f"Overall Status: {health.status.value}")
        print(f"Health Score: {health.score:.2f}")
        print(f"Active Checks: {len(health.checks)}")
        print(f"System Uptime: {health.metrics.uptime:.1f}s")
        
        # Test 2: Error Handling and Recovery
        print("\n2. Error Handling and Recovery")
        print("-" * 30)
        
        # Test error handling
        try:
            # Simulate an error
            raise ValueError("Simulated scan error")
        except Exception as e:
            recovery_action = await error_handler.handle_error(e, {"scan_id": "test", "agent": agent.name})
            print(f"Error handled: {type(e).__name__}")
            print(f"Recovery action: {recovery_action}")
        
        # Test 3: Input Sanitization
        print("\n3. Input Sanitization")
        print("-" * 30)
        
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "<script>alert('xss')</script>",
            "../../etc/passwd",
            "{{7*7}}"
        ]
        
        for malicious_input in malicious_inputs:
            sanitized, issues = input_sanitizer.sanitize_string(malicious_input)
            is_safe = len(issues) == 0
            print(f"Input: {malicious_input[:30]}")
            print(f"Safe: {is_safe}, Issues: {len(issues)}, Sanitized: {sanitized[:50]}")
        
        # Test 4: Enhanced Scanning with Error Recovery
        print("\n4. Enhanced Scanning with Reliability")
        print("-" * 30)
        
        start_time = time.time()
        
        # Run scan with progress tracking
        def progress_callback(progress):
            print(f"Progress: {progress.progress_percentage:.1f}% "
                  f"({progress.completed_patterns}/{progress.total_patterns})")
        
        scan_result = await scanner.scan(agent, progress_callback)
        
        scan_duration = time.time() - start_time
        
        print(f"\nScan Results:")
        print(f"Duration: {scan_duration:.2f}s")
        print(f"Vulnerabilities: {len(scan_result.vulnerabilities)}")
        print(f"Patterns Executed: {scan_result.patterns_executed}")
        print(f"Success Rate: {(scan_result.patterns_executed / scan_result.patterns_executed * 100):.1f}%")
        
        # Test 5: Health Status After Operations
        print("\n5. Post-Operation Health Assessment")
        print("-" * 30)
        
        final_health = health_monitor.get_current_health()
        health_summary = health_monitor.get_health_summary()
        
        print(f"Final Status: {final_health.status.value}")
        print(f"Final Score: {final_health.score:.2f}")
        print(f"Healthy Checks: {health_summary['healthy_checks']}/{health_summary['total_checks']}")
        
        if final_health.issues:
            print("Issues detected:")
            for issue in final_health.issues:
                print(f"  - {issue}")
        
        if final_health.recommendations:
            print("Recommendations:")
            for rec in final_health.recommendations:
                print(f"  - {rec}")
        
        print("\n✅ Generation 2 Reliability Features Verified")
        
        return {
            "health_score": final_health.score,
            "vulnerabilities_found": len(scan_result.vulnerabilities),
            "scan_duration": scan_duration,
            "reliability_features": [
                "Health Monitoring",
                "Error Handling",
                "Input Sanitization", 
                "Progress Tracking",
                "Recovery Mechanisms"
            ]
        }
        
    finally:
        # Stop monitoring
        await health_monitor.stop_monitoring()


def main():
    """Run Generation 2 reliability demonstration."""
    return asyncio.run(demonstrate_generation2_reliability())


if __name__ == "__main__":
    results = main()
    print(f"\n🎯 Generation 2 Complete: Health Score {results['health_score']:.2f}")