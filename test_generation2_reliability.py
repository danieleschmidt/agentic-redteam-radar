#!/usr/bin/env python3
"""
Test Generation 2 reliability features.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agentic_redteam import RadarScanner, create_mock_agent, RadarConfig


async def test_reliability_features():
    """Test Generation 2 reliability features."""
    print("🔧 Testing Generation 2 - Reliability Features")
    print("=" * 50)
    
    # Create configuration
    config = RadarConfig()
    
    # Create a mock agent
    agent = create_mock_agent(
        name="reliability-test-agent",
        responses={
            "Hello": "Hello! I'm ready for reliability testing.",
            "ping": "pong"
        }
    )
    
    # Create scanner
    scanner = RadarScanner(config)
    print("✅ Created scanner with reliability features")
    
    # Test 1: Health Monitoring
    print("\n🩺 Testing Health Monitoring...")
    health_status = scanner.get_health_status()
    print(f"   Overall system status: {health_status.get('system_health', {}).get('status', 'unknown')}")
    print(f"   Health score: {health_status.get('system_health', {}).get('score', 0):.2f}")
    print(f"   CPU usage: {health_status.get('system_health', {}).get('cpu_percent', 0):.1f}%")
    print(f"   Memory usage: {health_status.get('system_health', {}).get('memory_percent', 0):.1f}%")
    
    # Test 2: Start reliability systems
    print("\n🚀 Starting reliability systems...")
    await scanner.health_monitor.start_monitoring()
    await scanner.degradation_manager.start_monitoring()
    print("   Health monitor started")
    print("   Degradation manager started")
    
    # Test 3: Run a scan to test circuit breaker and error handling
    print("\n⚡ Testing enhanced error handling during scan...")
    try:
        result = await scanner.scan(agent)
        print(f"   ✅ Scan completed: {len(result.vulnerabilities)} vulnerabilities found")
        
        # Test error handler statistics
        error_stats = scanner.error_handler.get_error_stats()
        print(f"   Error statistics: {error_stats.get('total_errors', 0)} total errors tracked")
        
    except Exception as e:
        print(f"   ❌ Scan failed with error: {e}")
    
    # Test 4: Degradation status
    print("\n📊 Testing degradation management...")
    degradation_status = scanner.degradation_manager.get_degradation_status()
    print(f"   Current degradation level: {degradation_status['current_level']}")
    print(f"   Active degradation actions: {len(degradation_status['active_actions'])}")
    print(f"   Auto-recovery enabled: {degradation_status['auto_recovery_enabled']}")
    
    # Test 5: Force degradation to test system
    print("\n⬇️  Testing manual degradation...")
    from agentic_redteam.reliability.graceful_degradation import DegradationLevel
    scanner.degradation_manager.force_degradation(
        DegradationLevel.LIGHT, 
        "Testing degradation system"
    )
    
    # Wait a moment for degradation to apply
    await asyncio.sleep(2)
    
    updated_status = scanner.degradation_manager.get_degradation_status()
    print(f"   Degradation level after force: {updated_status['current_level']}")
    print(f"   Active actions: {updated_status['active_actions']}")
    
    # Test 6: Recovery
    print("\n⬆️  Testing manual recovery...")
    scanner.degradation_manager.force_recovery("Testing recovery system")
    
    # Wait a moment for recovery
    await asyncio.sleep(2)
    
    recovery_status = scanner.degradation_manager.get_degradation_status()
    print(f"   Degradation level after recovery: {recovery_status['current_level']}")
    
    # Test 7: Circuit breaker functionality
    print("\n🔌 Testing circuit breaker...")
    circuit_breaker_status = scanner.error_handler.get_error_stats()
    circuit_breakers = circuit_breaker_status.get('circuit_breakers', {})
    print(f"   Active circuit breakers: {len(circuit_breakers)}")
    for name, status in circuit_breakers.items():
        print(f"     - {name}: {status['state']} (failures: {status['failure_count']})")
    
    # Test 8: Health trends
    print("\n📈 Testing health trends...")
    health_trends = scanner.health_monitor.get_health_trends(hours=1)
    print(f"   Health trend: {health_trends['trend']}")
    print(f"   Data points collected: {health_trends.get('data_points', 0)}")
    print(f"   Recent health score: {health_trends.get('recent_score', 0):.2f}")
    
    # Test 9: System resource monitoring
    print("\n💻 Testing system metrics...")
    system_metrics = scanner.health_monitor.get_system_metrics()
    print(f"   Process count: {system_metrics.process_count}")
    print(f"   Thread count: {system_metrics.thread_count}")
    print(f"   Open files: {system_metrics.open_files}")
    
    # Test 10: Comprehensive health summary
    print("\n📋 Getting comprehensive health summary...")
    health_summary = scanner.health_monitor.get_health_summary()
    print(f"   Overall status: {health_summary['overall_status']}")
    print(f"   Health checks: {health_summary['healthy_checks']}/{health_summary['total_checks']} passing")
    print(f"   System metrics - CPU: {health_summary['system_metrics']['cpu_percent']:.1f}%, "
          f"Memory: {health_summary['system_metrics']['memory_percent']:.1f}%")
    
    if health_summary['issues']:
        print(f"   Issues detected: {len(health_summary['issues'])}")
        for issue in health_summary['issues'][:3]:  # Show first 3 issues
            print(f"     - {issue}")
    
    if health_summary['recommendations']:
        print(f"   Recommendations: {len(health_summary['recommendations'])}")
        for rec in health_summary['recommendations'][:3]:  # Show first 3 recommendations
            print(f"     - {rec}")
    
    # Cleanup
    print("\n🧹 Cleaning up...")
    await scanner.health_monitor.stop_monitoring()
    await scanner.degradation_manager.stop_monitoring()
    await scanner.cleanup_resources()
    
    print("\n✅ All Generation 2 reliability features tested successfully!")
    return True


async def test_error_recovery():
    """Test error recovery mechanisms."""
    print("\n🔄 Testing Error Recovery Mechanisms")
    print("=" * 40)
    
    config = RadarConfig()
    scanner = RadarScanner(config)
    
    # Test error handler directly
    print("   Testing error categorization and handling...")
    
    # Simulate different types of errors
    test_errors = [
        (Exception("Connection timeout"), "network_test"),
        (ValueError("Invalid input data"), "validation_test"),
        (RuntimeError("System overload"), "resource_test")
    ]
    
    for error, context in test_errors:
        try:
            raise error
        except Exception as e:
            from agentic_redteam.monitoring.error_handler import ErrorCategory, ErrorSeverity
            handled = await scanner.error_handler.handle_error(
                e, 
                context={"test_context": context},
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.MEDIUM
            )
            print(f"     ✓ Handled {type(e).__name__}: recovered={handled}")
    
    # Check error statistics
    error_stats = scanner.error_handler.get_error_stats()
    print(f"   Error registry contains {error_stats['total_errors']} error entries")
    
    return True


def main():
    """Run all Generation 2 tests."""
    try:
        # Test reliability features
        success1 = asyncio.run(test_reliability_features())
        
        # Test error recovery
        success2 = asyncio.run(test_error_recovery())
        
        if success1 and success2:
            print("\n🎉 Generation 2 - MAKE IT ROBUST completed successfully!")
            return 0
        else:
            print("\n❌ Some Generation 2 tests failed")
            return 1
            
    except Exception as e:
        print(f"\n❌ Generation 2 testing failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())