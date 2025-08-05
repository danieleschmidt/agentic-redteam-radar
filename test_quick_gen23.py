#!/usr/bin/env python3
"""
Quick test for Generation 2 & 3 core functionality.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_security_basics():
    """Test basic security functionality."""
    print("🛡️ Testing Security...")
    
    from agentic_redteam.security import InputSanitizer, SecurityPolicy
    
    policy = SecurityPolicy(allow_html=False)
    sanitizer = InputSanitizer(policy)
    
    # Test XSS protection
    clean_text, warnings = sanitizer.sanitize_string("<script>alert('xss')</script>")
    # Should either escape HTML or block the pattern
    assert "&lt;" in clean_text or "[BLOCKED]" in clean_text
    assert len(warnings) > 0  # Should have warnings
    
    print("   ✅ XSS protection working")
    
    # Test URL validation
    clean_url, url_warnings = sanitizer.sanitize_url("https://example.com")
    assert clean_url == "https://example.com"
    
    print("   ✅ URL validation working")
    print("✅ Security tests passed")

def test_error_handling_basics():
    """Test basic error handling."""
    print("🚨 Testing Error Handling...")
    
    from agentic_redteam.monitoring import ErrorHandler, ErrorCategory, ErrorSeverity
    
    handler = ErrorHandler(enable_recovery=False)  # Disable recovery for testing
    
    # Test error stats
    stats = handler.get_error_stats()
    assert isinstance(stats, dict)
    assert "total_errors" in stats
    
    print("   ✅ Error handler initialized")
    print("✅ Error handling tests passed")

def test_performance_basics():
    """Test basic performance features."""
    print("⚡ Testing Performance...")
    
    from agentic_redteam.performance import PerformanceProfiler, PerformanceMetrics
    
    profiler = PerformanceProfiler()
    
    # Test metric recording
    metric = PerformanceMetrics(
        operation="test_op",
        duration=0.1,
        success=True
    )
    
    profiler.record_metric(metric)
    
    # Get stats
    stats = profiler.get_stats("test_op")
    assert stats["sample_count"] == 1
    assert stats["duration_stats"]["mean"] == 0.1
    
    print("   ✅ Performance profiler working")
    print("✅ Performance tests passed")

def main():
    """Run quick tests."""
    print("🎯 Quick Generation 2 & 3 Test")
    print("=" * 40)
    
    try:
        test_security_basics()
        test_error_handling_basics()
        test_performance_basics()
        
        print("\n" + "=" * 40)
        print("🎉 ALL QUICK TESTS PASSED!")
        print("✅ Generation 2 & 3 features working")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()