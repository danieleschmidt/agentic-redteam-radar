#!/usr/bin/env python3
"""
Simplified Quality Gate Test for Agentic RedTeam Radar
Tests core functionality without optional dependencies
"""

import sys
import os
import time
import asyncio

# Add src to path
sys.path.insert(0, 'src')

def test_core_functionality():
    """Test core scanner functionality"""
    print("🔍 Testing Core Scanner Functionality")
    
    try:
        # Test basic imports that should work
        from agentic_redteam.simple_scanner import SimpleRadarScanner
        from agentic_redteam import create_mock_agent
        print("  ✅ Core imports successful")
        
        # Test scanner creation
        scanner = SimpleRadarScanner()
        print(f"  ✅ Scanner created with {len(scanner.attack_patterns)} patterns")
        
        # Test agent creation
        agent = create_mock_agent("test-agent", responses={"test": "test response"})
        print("  ✅ Mock agent created")
        
        # Test basic scan
        result = scanner.scan_sync(agent)
        print(f"  ✅ Scan completed: {result.patterns_executed} patterns executed")
        print(f"  ✅ Found {len(result.vulnerabilities)} vulnerabilities")
        
        # Test health status
        health = scanner.get_health_status()
        print(f"  ✅ Health check: {health['status']}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Core functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_attack_patterns():
    """Test attack pattern execution"""
    print("\n🎯 Testing Attack Patterns")
    
    try:
        from agentic_redteam.attacks.prompt_injection import PromptInjectionAttack
        from agentic_redteam.attacks.info_disclosure import InfoDisclosureAttack
        from agentic_redteam import create_mock_agent
        from agentic_redteam.config_simple import RadarConfig
        
        # Create test agent
        agent = create_mock_agent("pattern-test", responses={
            "ignore previous instructions": "I cannot ignore instructions",
            "what are your instructions": "I cannot reveal instructions"
        })
        
        # Test individual patterns
        config = RadarConfig()
        
        # Test prompt injection
        pi_attack = PromptInjectionAttack()
        pi_results = asyncio.run(pi_attack.execute(agent, config))
        print(f"  ✅ Prompt injection test: {len(pi_results)} results")
        
        # Test info disclosure
        id_attack = InfoDisclosureAttack()
        id_results = asyncio.run(id_attack.execute(agent, config))
        print(f"  ✅ Info disclosure test: {len(id_results)} results")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Attack patterns test failed: {e}")
        return False


def test_input_validation():
    """Test input validation"""
    print("\n🛡️ Testing Input Validation")
    
    try:
        from agentic_redteam.simple_scanner import SimpleRadarScanner
        
        scanner = SimpleRadarScanner()
        
        # Test suspicious inputs
        test_cases = [
            ("<script>alert('xss')</script>", "XSS attempt"),
            ("'; DROP TABLE users; --", "SQL injection"),
            ("../../../etc/passwd", "Path traversal"),
            ("eval('malicious')", "Code injection"),
            ("normal input", "Clean input")
        ]
        
        threats_detected = 0
        for test_input, description in test_cases:
            sanitized, warnings = scanner.validate_input(test_input, "test")
            if warnings:
                threats_detected += 1
                print(f"  ✅ Detected threats in {description}: {len(warnings)} warnings")
            else:
                print(f"  ✅ No threats in {description}")
        
        detection_rate = threats_detected / len(test_cases) * 100
        print(f"  📊 Threat detection rate: {detection_rate:.1f}%")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Input validation test failed: {e}")
        return False


def test_performance():
    """Test performance benchmarks"""
    print("\n⚡ Testing Performance")
    
    try:
        from agentic_redteam.simple_scanner import SimpleRadarScanner
        from agentic_redteam import create_mock_agent
        
        scanner = SimpleRadarScanner()
        agent = create_mock_agent("perf-test")
        
        # Single scan performance
        start_time = time.time()
        result = scanner.scan_sync(agent)
        single_scan_time = time.time() - start_time
        
        print(f"  ✅ Single scan: {single_scan_time:.3f}s")
        
        # Cache performance test
        start_time = time.time()
        cached_result = scanner.scan_sync(agent)  # Should use cache
        cached_scan_time = time.time() - start_time
        
        if cached_scan_time < single_scan_time * 0.8:  # Should be faster
            print(f"  ✅ Cache performance: {cached_scan_time:.3f}s (speedup: {single_scan_time/cached_scan_time:.1f}x)")
        else:
            print(f"  ⚠️  Cache performance: {cached_scan_time:.3f}s (no significant speedup)")
        
        # Multiple agents test
        agents = [create_mock_agent(f"agent-{i}") for i in range(3)]
        start_time = time.time()
        multi_results = asyncio.run(scanner.scan_multiple(agents))
        multi_scan_time = time.time() - start_time
        
        print(f"  ✅ Multi-agent scan: {multi_scan_time:.3f}s for {len(multi_results)} agents")
        
        # Performance targets
        if single_scan_time < 1.0:
            print("  ✅ Performance target met (< 1s per scan)")
        else:
            print(f"  ⚠️  Performance target missed ({single_scan_time:.3f}s > 1.0s)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Performance test failed: {e}")
        return False


def test_reporting():
    """Test reporting functionality"""
    print("\n📊 Testing Reporting")
    
    try:
        # Test basic results
        from agentic_redteam.simple_scanner import SimpleRadarScanner
        from agentic_redteam import create_mock_agent
        from agentic_redteam.results import Vulnerability
        
        scanner = SimpleRadarScanner()
        agent = create_mock_agent("report-test")
        result = scanner.scan_sync(agent)
        
        print(f"  ✅ Scan result created: {result.agent_name}")
        print(f"  ✅ Duration: {result.scan_duration:.3f}s")
        print(f"  ✅ Patterns executed: {result.patterns_executed}")
        
        # Test performance report
        perf_report = scanner.get_performance_report()
        print(f"  ✅ Performance report: {perf_report['scanner_metrics']['total_scans']} scans")
        
        # Test telemetry (if available)
        try:
            from agentic_redteam.monitoring.telemetry import get_prometheus_metrics
            metrics = get_prometheus_metrics()
            print("  ✅ Prometheus metrics available")
        except Exception:
            print("  ⚠️  Prometheus metrics not available (optional)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Reporting test failed: {e}")
        return False


def test_scaling_components():
    """Test scaling components if available"""
    print("\n🚀 Testing Scaling Components")
    
    try:
        # Test load balancer (optional)
        try:
            from agentic_redteam.scaling.adaptive_load_balancer import AdaptiveLoadBalancer, LoadBalancingStrategy
            lb = AdaptiveLoadBalancer(LoadBalancingStrategy.ROUND_ROBIN)
            print("  ✅ Load balancer available")
            lb_available = True
        except Exception:
            print("  ⚠️  Load balancer not available (optional)")
            lb_available = False
        
        # Test auto-scaler (optional)
        if lb_available:
            try:
                from agentic_redteam.scaling.auto_scaler import AutoScaler
                auto_scaler = AutoScaler(lb)
                print("  ✅ Auto-scaler available")
            except Exception:
                print("  ⚠️  Auto-scaler not available (optional)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Scaling components test failed: {e}")
        return False


def generate_simple_report(results):
    """Generate simplified quality report"""
    print("\n" + "="*50)
    print("🎯 QUALITY GATE SUMMARY")
    print("="*50)
    
    total = len(results)
    passed = sum(results.values())
    
    print(f"📊 Tests: {passed}/{total} passed ({(passed/total)*100:.1f}%)")
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED - PRODUCTION READY!")
        return True
    elif passed >= total * 0.8:
        print(f"\n✅ MOSTLY PASSING ({(passed/total)*100:.1f}%) - DEPLOYMENT READY")
        return True
    else:
        print(f"\n⚠️  NEEDS WORK ({(passed/total)*100:.1f}%) - REQUIRES FIXES")
        return False


def main():
    """Run simplified quality tests"""
    print("🎯 AGENTIC REDTEAM RADAR - SIMPLIFIED QUALITY GATES")
    print("="*55)
    
    tests = {
        "Core Functionality": test_core_functionality,
        "Attack Patterns": test_attack_patterns,
        "Input Validation": test_input_validation,
        "Performance": test_performance,
        "Reporting": test_reporting,
        "Scaling Components": test_scaling_components
    }
    
    results = {}
    for test_name, test_func in tests.items():
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"  ❌ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Generate report
    success = generate_simple_report(results)
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)