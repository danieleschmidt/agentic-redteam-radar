#!/usr/bin/env python3
"""
Health check script for production deployment.
"""

import sys
import time
import asyncio
import requests
from typing import Dict, Any

def check_http_health() -> bool:
    """Check HTTP endpoint health."""
    try:
        response = requests.get('http://localhost:8080/health', timeout=5)
        return response.status_code == 200
    except Exception:
        return False

def check_scanner_health() -> Dict[str, Any]:
    """Check scanner component health."""
    try:
        from agentic_redteam import RadarScanner
        from agentic_redteam.config_simple import RadarConfig
        
        config = RadarConfig()
        scanner = RadarScanner(config)
        
        health = scanner.get_health_status()
        return {
            'status': 'healthy' if health.get('scanner', {}).get('scanner_healthy', False) else 'unhealthy',
            'details': health
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }

async def check_async_components() -> bool:
    """Check async components."""
    try:
        # Test basic async functionality
        await asyncio.sleep(0.1)
        return True
    except Exception:
        return False

def main():
    """Main health check function."""
    print("🏥 Agentic RedTeam Radar - Health Check")
    print("=" * 50)
    
    checks = {
        'http': False,
        'scanner': False,
        'async': False
    }
    
    # HTTP Health Check
    print("🌐 Checking HTTP endpoint...")
    checks['http'] = check_http_health()
    print(f"   HTTP: {'✅ Healthy' if checks['http'] else '❌ Unhealthy'}")
    
    # Scanner Health Check
    print("🔍 Checking scanner components...")
    scanner_health = check_scanner_health()
    checks['scanner'] = scanner_health['status'] == 'healthy'
    print(f"   Scanner: {'✅ Healthy' if checks['scanner'] else '❌ Unhealthy'}")
    
    if not checks['scanner'] and 'error' in scanner_health:
        print(f"      Error: {scanner_health['error']}")
    
    # Async Components Check
    print("⚡ Checking async components...")
    try:
        checks['async'] = asyncio.run(check_async_components())
    except Exception as e:
        checks['async'] = False
        print(f"      Async Error: {e}")
    
    print(f"   Async: {'✅ Healthy' if checks['async'] else '❌ Unhealthy'}")
    
    # Overall Health
    all_healthy = all(checks.values())
    print("\n" + "=" * 50)
    print(f"🎯 Overall Health: {'✅ HEALTHY' if all_healthy else '❌ UNHEALTHY'}")
    
    if all_healthy:
        print("🚀 All systems operational")
        sys.exit(0)
    else:
        failed_checks = [name for name, status in checks.items() if not status]
        print(f"🚨 Failed checks: {', '.join(failed_checks)}")
        sys.exit(1)

if __name__ == '__main__':
    main()