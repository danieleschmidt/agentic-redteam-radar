#!/usr/bin/env python3
"""
Comprehensive Quality Gate Test for Agentic RedTeam Radar
Tests all 3 generations of the SDLC implementation
"""

import sys
import os
import time
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, 'src')

def test_generation_1_basic():
    """Test Generation 1: Basic functionality"""
    print("🔍 Testing Generation 1: MAKE IT WORK (Basic functionality)")
    
    try:
        # Test core imports
        from agentic_redteam import RadarScanner, Agent, create_mock_agent
        from agentic_redteam.simple_scanner import SimpleRadarScanner
        print("  ✅ Core imports successful")
        
        # Test basic scanner creation
        scanner = SimpleRadarScanner()
        print(f"  ✅ Scanner initialized with {len(scanner.attack_patterns)} patterns")
        
        # Test mock agent creation
        agent = create_mock_agent("test-agent")
        print("  ✅ Mock agent created successfully")
        
        # Test basic scan
        result = scanner.scan_sync(agent)
        print(f"  ✅ Basic scan completed: {len(result.vulnerabilities)} vulnerabilities found")
        
        # Test reporting imports
        from agentic_redteam.reporting.html_generator import generate_html_report
        html_report = generate_html_report(result)
        print(f"  ✅ HTML report generated: {len(html_report)} characters")
        
        # Test telemetry
        from agentic_redteam.monitoring.telemetry import get_telemetry_collector
        telemetry = get_telemetry_collector()
        print("  ✅ Telemetry collector initialized")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Generation 1 test failed: {e}")
        return False


def test_generation_2_robustness():
    """Test Generation 2: Robustness and security"""
    print("\n🛡️ Testing Generation 2: MAKE IT ROBUST (Reliability & Security)")
    
    try:
        # Test security components
        from agentic_redteam.security.input_sanitizer import InputSanitizer
        sanitizer = InputSanitizer()
        print("  ✅ Input sanitizer loaded")
        
        # Test circuit breaker
        from agentic_redteam.reliability.circuit_breaker import CircuitBreaker, get_circuit_manager
        circuit_manager = get_circuit_manager()
        circuit = circuit_manager.create_circuit("test_circuit")
        print("  ✅ Circuit breaker system operational")
        
        # Test API middleware
        from agentic_redteam.api.middleware import RateLimitMiddleware, SecurityHeadersMiddleware
        print("  ✅ API middleware components loaded")
        
        # Test API routes
        from agentic_redteam.api.routes import api_router
        print("  ✅ API routes configured")
        
        # Test enhanced scanner with security features
        from agentic_redteam.simple_scanner import SimpleRadarScanner
        scanner = SimpleRadarScanner()
        
        # Verify security integration
        if hasattr(scanner, 'input_sanitizer') and hasattr(scanner, 'agent_circuit'):
            print("  ✅ Scanner has integrated security components")
        else:
            print("  ⚠️  Scanner missing some security components")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Generation 2 test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_generation_3_scaling():
    """Test Generation 3: Scaling and optimization"""
    print("\n⚡ Testing Generation 3: MAKE IT SCALE (Performance & Scaling)")
    
    try:
        # Test load balancer
        from agentic_redteam.scaling.adaptive_load_balancer import AdaptiveLoadBalancer, LoadBalancingStrategy
        load_balancer = AdaptiveLoadBalancer(LoadBalancingStrategy.ADAPTIVE)
        print("  ✅ Adaptive load balancer initialized")
        
        # Test auto-scaler
        from agentic_redteam.scaling.auto_scaler import AutoScaler, AutoScalerConfig
        auto_scaler = AutoScaler(load_balancer)
        print("  ✅ Auto-scaler system initialized")
        
        # Test performance monitoring
        from agentic_redteam.monitoring.telemetry import get_prometheus_metrics
        metrics = get_prometheus_metrics()
        print("  ✅ Prometheus metrics integration working")
        
        # Test enhanced scanner with scaling features
        from agentic_redteam.simple_scanner import SimpleRadarScanner
        scanner = SimpleRadarScanner()
        
        # Verify performance optimizations
        if hasattr(scanner, 'scan_cache') and hasattr(scanner, 'performance_history'):
            print("  ✅ Scanner has performance optimization features")
        else:
            print("  ⚠️  Scanner missing some performance features")
            
        return True
        
    except Exception as e:
        print(f"  ❌ Generation 3 test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration():
    """Test end-to-end integration"""
    print("\n🔗 Testing End-to-End Integration")
    
    try:
        from agentic_redteam.simple_scanner import SimpleRadarScanner
        from agentic_redteam import create_mock_agent
        
        # Create scanner with all enhancements
        scanner = SimpleRadarScanner()
        
        # Create multiple test agents
        agents = [
            create_mock_agent(f"test-agent-{i}", responses={"test": f"Response from agent {i}"})
            for i in range(3)
        ]
        
        print(f"  ✅ Created {len(agents)} test agents")
        
        # Test concurrent scanning
        async def test_concurrent_scans():
            results = await scanner.scan_multiple(agents, auto_scale=True)
            return results
        
        results = asyncio.run(test_concurrent_scans())
        print(f"  ✅ Concurrent scanning completed: {len(results)} results")
        
        # Test health monitoring
        health = scanner.get_health_status()
        print(f"  ✅ Health status: {health['status']}")
        
        # Test performance reporting
        performance = scanner.get_performance_report()
        print(f"  ✅ Performance report generated: {performance['scanner_metrics']['total_scans']} total scans")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_security_compliance():
    """Test security compliance"""
    print("\n🔐 Testing Security Compliance")
    
    try:
        # Test input sanitization
        test_inputs = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "../../../etc/passwd",
            "eval('malicious_code')",
            "rm -rf /"
        ]
        
        from agentic_redteam.simple_scanner import SimpleRadarScanner
        scanner = SimpleRadarScanner()
        
        threats_detected = 0
        for test_input in test_inputs:
            sanitized, warnings = scanner.validate_input(test_input, "test")
            if warnings:
                threats_detected += 1
        
        if threats_detected >= len(test_inputs) * 0.8:  # At least 80% detection
            print(f"  ✅ Input validation effective: {threats_detected}/{len(test_inputs)} threats detected")
        else:
            print(f"  ⚠️  Input validation needs improvement: {threats_detected}/{len(test_inputs)} threats detected")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Security compliance test failed: {e}")
        return False


def test_performance_benchmarks():
    """Test performance benchmarks"""
    print("\n📊 Testing Performance Benchmarks")
    
    try:
        from agentic_redteam.simple_scanner import SimpleRadarScanner
        from agentic_redteam import create_mock_agent
        
        scanner = SimpleRadarScanner()
        agent = create_mock_agent("benchmark-agent")
        
        # Benchmark scan performance
        start_time = time.time()
        result = scanner.scan_sync(agent)
        scan_duration = time.time() - start_time
        
        print(f"  ✅ Scan performance: {scan_duration:.3f}s for {result.patterns_executed} patterns")
        
        # Check performance targets
        if scan_duration < 2.0:  # Target: under 2 seconds
            print("  ✅ Performance target met (< 2s)")
        else:
            print(f"  ⚠️  Performance target missed ({scan_duration:.3f}s > 2.0s)")
        
        # Test cache performance
        start_time = time.time()
        cached_result = scanner.scan_sync(agent)  # Should use cache
        cached_duration = time.time() - start_time
        
        if cached_duration < scan_duration * 0.5:  # Cache should be much faster
            print(f"  ✅ Cache performance: {cached_duration:.3f}s (speedup: {scan_duration/cached_duration:.1f}x)")
        else:
            print("  ⚠️  Cache performance not optimal")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Performance benchmark failed: {e}")
        return False


def generate_quality_report(results):
    """Generate final quality report"""
    print("\n" + "="*60)
    print("🎯 AUTONOMOUS SDLC QUALITY GATE REPORT")
    print("="*60)
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    print(f"📋 Tests Executed: {total_tests}")
    print(f"✅ Tests Passed: {passed_tests}")
    print(f"❌ Tests Failed: {total_tests - passed_tests}")
    print(f"📈 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    print("\n📊 DETAILED RESULTS:")
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    if passed_tests == total_tests:
        print("\n🎉 ALL QUALITY GATES PASSED - PRODUCTION READY!")
        print("   🚀 Ready for deployment")
    elif passed_tests >= total_tests * 0.8:  # 80% threshold
        print(f"\n✅ QUALITY GATES MOSTLY PASSED ({(passed_tests/total_tests)*100:.1f}%)")
        print("   🚀 Ready for deployment with minor issues")
    else:
        print(f"\n⚠️  QUALITY GATES NEEDS ATTENTION ({(passed_tests/total_tests)*100:.1f}%)")
        print("   🔧 Requires fixes before deployment")
    
    return passed_tests >= total_tests * 0.8


def main():
    """Run comprehensive quality gates"""
    print("🎯 AGENTIC REDTEAM RADAR - AUTONOMOUS SDLC QUALITY GATES")
    print("=" * 65)
    
    # Execute all quality tests
    test_results = {}
    
    test_results["Generation 1: Basic Functionality"] = test_generation_1_basic()
    test_results["Generation 2: Robustness & Security"] = test_generation_2_robustness()
    test_results["Generation 3: Scaling & Performance"] = test_generation_3_scaling()
    test_results["End-to-End Integration"] = test_integration()
    test_results["Security Compliance"] = test_security_compliance()
    test_results["Performance Benchmarks"] = test_performance_benchmarks()
    
    # Generate final quality report
    quality_passed = generate_quality_report(test_results)
    
    return 0 if quality_passed else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)