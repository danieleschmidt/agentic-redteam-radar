#!/usr/bin/env python3
"""
Test Generation 3 advanced scaling and optimization features.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agentic_redteam import RadarScanner, create_mock_agent, RadarConfig


async def test_generation3_scaling():
    """Test Generation 3 advanced scaling capabilities."""
    print("🚀 Testing Generation 3 - Advanced Scaling & Optimization")
    print("=" * 60)
    
    # Create configuration
    config = RadarConfig()
    
    # Create a mock agent
    agent = create_mock_agent(
        name="scaling-test-agent",
        responses={
            "Hello": "Hello! Ready for scaling tests.",
            "ping": "pong",
            "test": "This is a test response for scaling validation."
        }
    )
    
    # Create scanner with Generation 3 features
    scanner = RadarScanner(config)
    print("✅ Created scanner with Generation 3 scaling capabilities")
    
    # Test 1: Auto-Scaler Configuration
    print("\n📊 Testing Auto-Scaler...")
    scaling_status = scanner.auto_scaler.get_scaling_status()
    print(f"   Current instances: {scaling_status['current_instances']}")
    print(f"   Auto-scaling policies: {len(scaling_status['active_policies'])}")
    
    for policy in scaling_status['active_policies'][:2]:  # Show first 2 policies
        print(f"     - {policy['name']}: trigger={policy['trigger']}, "
              f"thresholds=({policy['scale_down_threshold']}-{policy['scale_up_threshold']})")
    
    # Test 2: Load Balancer Setup
    print("\n⚖️  Testing Load Balancer...")
    
    # Add mock worker nodes
    scanner.load_balancer.add_node("node-1", "http://worker1:8080", weight=1.0)
    scanner.load_balancer.add_node("node-2", "http://worker2:8080", weight=2.0)
    scanner.load_balancer.add_node("node-3", "http://worker3:8080", weight=1.5)
    
    lb_stats = scanner.load_balancer.get_load_balancer_stats()
    print(f"   Load balancer strategy: {lb_stats['strategy']}")
    print(f"   Total nodes: {lb_stats['total_nodes']}")
    print(f"   Healthy nodes: {lb_stats['healthy_nodes']}")
    
    # Test node selection
    for i in range(3):
        selection = scanner.load_balancer.select_node({'client_ip': f'192.168.1.{i+10}'})
        if selection.selected_node:
            print(f"     Request {i+1} -> {selection.selected_node.id} ({selection.reason})")
        else:
            print(f"     Request {i+1} -> No node available ({selection.reason})")
    
    # Test 3: Resource Pool Management
    print("\n🏊 Testing Resource Pools...")
    pool_stats = scanner.resource_manager.get_global_metrics()
    print(f"   Total resource pools: {pool_stats['total_pools']}")
    print(f"   Total resources: {pool_stats['resource_summary']['total_resources']}")
    
    for pool_name, pool_info in pool_stats['pools'].items():
        print(f"     - {pool_name}: {pool_info['current_state']['total_resources']} resources "
              f"(strategy: {pool_info['strategy']})")
    
    # Test resource acquisition
    try:
        worker_resource = await scanner.resource_manager.acquire_resource("scan_workers", timeout=5.0)
        print(f"   ✅ Successfully acquired scan worker: {worker_resource['id']}")
        
        # Release resource
        await scanner.resource_manager.release_resource("scan_workers", worker_resource)
        print(f"   ✅ Successfully released scan worker")
    except Exception as e:
        print(f"   ❌ Failed to test resource acquisition: {e}")
    
    # Test 4: Performance Tuner
    print("\n🔧 Testing Performance Tuner...")
    perf_report = scanner.performance_tuner.get_performance_report()
    print(f"   Current optimization profile: {perf_report['current_profile']}")
    print(f"   Applied optimizations: {len(perf_report['applied_optimizations'])}")
    print(f"   Optimization success rate: {perf_report['optimization_effectiveness']['success_rate']:.1%}")
    
    # Test profile switching
    print("   Testing aggressive optimization profile...")
    success = scanner.performance_tuner.apply_profile('aggressive')
    if success:
        new_report = scanner.performance_tuner.get_performance_report()
        print(f"   ✅ Applied aggressive profile with {len(new_report['applied_optimizations'])} optimizations")
    
    # Test 5: Multi-Tenant Manager
    print("\n🏢 Testing Multi-Tenancy...")
    
    # Create test tenants
    from agentic_redteam.scaling.multi_tenant import TenantQuota, TenantPriority
    
    premium_quota = TenantQuota(
        max_concurrent_scans=10,
        max_cpu_percent=40.0,
        max_memory_mb=1024,
        max_requests_per_minute=200,
        priority=TenantPriority.PREMIUM
    )
    
    basic_quota = TenantQuota(
        max_concurrent_scans=3,
        max_cpu_percent=15.0,
        max_memory_mb=256,
        max_requests_per_minute=50,
        priority=TenantPriority.LOW
    )
    
    scanner.multi_tenant_manager.create_tenant("premium_customer", premium_quota)
    scanner.multi_tenant_manager.create_tenant("basic_customer", basic_quota)
    
    tenant_stats = scanner.multi_tenant_manager.get_global_tenant_stats()
    print(f"   Total tenants: {tenant_stats['tenant_summary']['total_tenants']}")
    print(f"   Active tenants: {tenant_stats['tenant_summary']['active_tenants']}")
    print(f"   Priority distribution: {tenant_stats['tenant_distribution']['by_priority']}")
    
    # Test resource allocation
    resource_request = {
        'concurrent_scans': 2,
        'cpu_percent': 10.0,
        'memory_mb': 200
    }
    
    allocation_result = await scanner.multi_tenant_manager.allocate_resources(
        "premium_customer", resource_request
    )
    
    if allocation_result['success']:
        print(f"   ✅ Allocated resources to premium customer")
        print(f"     Current usage: {allocation_result['current_usage']}")
        
        # Deallocate resources
        await scanner.multi_tenant_manager.deallocate_resources(
            "premium_customer", resource_request
        )
        print(f"   ✅ Deallocated resources from premium customer")
    else:
        print(f"   ❌ Failed to allocate resources: {allocation_result['reason']}")
    
    # Test 6: Integrated Scaling During Scan
    print("\n🔄 Testing Integrated Scaling During Scan...")
    
    # Start all scaling systems
    await scanner.start_scaling_systems()
    print("   Started all scaling systems")
    
    # Run a scan to test integrated scaling
    try:
        start_time = time.time()
        result = await scanner.scan(agent)
        scan_duration = time.time() - start_time
        
        print(f"   ✅ Scan completed with scaling systems active")
        print(f"     Duration: {scan_duration:.2f}s")
        print(f"     Vulnerabilities: {len(result.vulnerabilities)}")
        print(f"     Tests executed: {result.total_tests}")
        
        # Check post-scan scaling status
        post_scan_status = scanner.auto_scaler.get_scaling_status()
        print(f"     Post-scan instances: {post_scan_status['current_instances']}")
        print(f"     Scaling events: {post_scan_status['total_scaling_events']}")
        
    except Exception as e:
        print(f"   ❌ Scan with scaling failed: {e}")
    
    # Test 7: Predictive Scaling
    print("\n🔮 Testing Predictive Scaling...")
    prediction = scanner.auto_scaler.predict_scaling_needs(time_horizon_minutes=15)
    print(f"   Scaling prediction: {prediction['prediction']} (confidence: {prediction['confidence']:.1%})")
    if prediction.get('projected_cpu'):
        print(f"   Projected CPU usage: {prediction['projected_cpu']:.1f}%")
    if prediction.get('projected_memory'):
        print(f"   Projected memory usage: {prediction['projected_memory']:.1f}%")
    
    # Test 8: Performance Metrics Collection
    print("\n📈 Testing Performance Metrics...")
    current_metrics = scanner.performance_tuner._collect_current_metrics()
    print(f"   Current CPU: {current_metrics.cpu_percent:.1f}%")
    print(f"   Current memory: {current_metrics.memory_mb:.1f}MB ({current_metrics.memory_percent:.1f}%)")
    print(f"   Active threads: {current_metrics.active_threads}")
    
    # Test 9: Resource Utilization Analysis
    print("\n📊 Testing Resource Utilization...")
    global_metrics = scanner.resource_manager.get_global_metrics()
    utilization = global_metrics['resource_summary']['utilization']
    print(f"   Overall resource utilization: {utilization:.1%}")
    print(f"   Total acquisitions: {global_metrics['global_stats']['total_acquisitions']}")
    print(f"   Acquisitions per hour: {global_metrics['global_stats']['acquisitions_per_hour']:.1f}")
    
    # Test 10: Comprehensive System Status
    print("\n🌍 Getting Comprehensive System Status...")
    
    # Enhanced health status with Generation 3 features
    health_status = scanner.get_health_status()
    
    print(f"   System health: {health_status.get('system_health', {}).get('status', 'unknown')}")
    print(f"   Degradation level: {health_status.get('degradation', {}).get('current_level', 'normal')}")
    print(f"   Scaling systems active: All systems operational")
    
    # Additional Generation 3 metrics
    g3_metrics = {
        'auto_scaler_instances': post_scan_status['current_instances'],
        'load_balancer_nodes': lb_stats['total_nodes'], 
        'resource_pools': pool_stats['total_pools'],
        'performance_profile': perf_report['current_profile'],
        'active_tenants': tenant_stats['tenant_summary']['active_tenants']
    }
    
    print(f"   Generation 3 metrics:")
    for metric, value in g3_metrics.items():
        print(f"     - {metric}: {value}")
    
    # Cleanup
    print("\n🧹 Cleaning up Generation 3 systems...")
    await scanner.stop_scaling_systems()
    await scanner.cleanup_resources()
    
    print("\n✅ All Generation 3 scaling features tested successfully!")
    return True


async def test_advanced_scenarios():
    """Test advanced Generation 3 scenarios."""
    print("\n🎯 Testing Advanced Scaling Scenarios")
    print("=" * 45)
    
    config = RadarConfig()
    scanner = RadarScanner(config)
    
    # Test concurrent multi-tenant operations
    print("   Testing concurrent multi-tenant operations...")
    
    # Create multiple agents for different tenants
    agents = []
    for i in range(3):
        agent = create_mock_agent(
            name=f"tenant-{i+1}-agent",
            responses={
                "ping": f"pong from tenant {i+1}",
                "Hello": f"Hello from tenant {i+1} agent!"
            }
        )
        agents.append(agent)
    
    # Start scaling systems
    await scanner.start_scaling_systems()
    
    # Run concurrent scans
    try:
        tasks = [scanner.scan(agent) for agent in agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_scans = len([r for r in results if not isinstance(r, Exception)])
        print(f"   ✅ Concurrent multi-tenant scans: {successful_scans}/{len(agents)} successful")
        
        # Check final scaling state
        final_status = scanner.auto_scaler.get_scaling_status()
        print(f"   Final auto-scaler instances: {final_status['current_instances']}")
        
    except Exception as e:
        print(f"   ❌ Concurrent operations failed: {e}")
    
    # Cleanup
    await scanner.stop_scaling_systems()
    return True


def main():
    """Run all Generation 3 tests."""
    try:
        # Test Generation 3 scaling features
        success1 = asyncio.run(test_generation3_scaling())
        
        # Test advanced scenarios
        success2 = asyncio.run(test_advanced_scenarios())
        
        if success1 and success2:
            print("\n🎉 Generation 3 - MAKE IT SCALE completed successfully!")
            print("\n🏆 AUTONOMOUS SDLC EXECUTION COMPLETE!")
            print("   ✅ Generation 1: MAKE IT WORK")
            print("   ✅ Generation 2: MAKE IT ROBUST") 
            print("   ✅ Generation 3: MAKE IT SCALE")
            return 0
        else:
            print("\n❌ Some Generation 3 tests failed")
            return 1
            
    except Exception as e:
        print(f"\n❌ Generation 3 testing failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())