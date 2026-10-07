
"""
Tests for Agent API
"""

import frappe
import unittest
import json

# `api/agent.py` was rewritten (5be228c) and no longer exports test / process /
# debug / generate_serial_numbers. The bare import below used to raise at
# collection time, and because frappe's discover_all_tests wraps ANY discovery
# exception in TestRunnerError (frappe/testing/discovery.py:66-68), that single
# raise aborted collection for the ENTIRE app — 94 cases collected, then exit 1,
# nothing run. Every other test in amb_w_tds was unreachable because of this line.
#
# The tests below are kept rather than deleted: they are the surviving description
# of the old agent API, and deleting them would erase that record. They are also
# not resurrected — the four functions are genuinely gone, so the class is skipped
# with a reason that says why.
try:
    from amb_w_tds.api.agent import test, process, debug, generate_serial_numbers

    _AGENT_API_AVAILABLE = True
    _AGENT_API_REASON = ""
except ImportError as exc:
    test = process = debug = generate_serial_numbers = None
    _AGENT_API_AVAILABLE = False
    _AGENT_API_REASON = (
        f"amb_w_tds.api.agent no longer exports test/process/debug/"
        f"generate_serial_numbers (module rewritten in 5be228c): {exc}"
    )


@unittest.skipUnless(_AGENT_API_AVAILABLE, _AGENT_API_REASON or "agent API unavailable")
class TestAgentAPI(unittest.TestCase):
    """Test cases for Agent API"""
    
    def setUp(self):
        """Set up test data"""
        self.test_data = {
            "work_order": "WO-TEST-001",
            "product_code": "0334009251",
            "quantity": 5,
            "test_mode": True
        }
    
    def test_001_test_endpoint(self):
        """Test the test() endpoint"""
        result = test()
        
        self.assertEqual(result["status"], "success")
        self.assertIn("timestamp", result)
        self.assertIn("version", result)
        print(f"✓ test() endpoint working: {result.get('version')}")
    
    def test_002_debug_endpoint(self):
        """Test the debug() endpoint"""
        result = debug()
        
        self.assertEqual(result["status"], "success")
        self.assertIn("system", result)
        self.assertIn("agent", result)
        print(f"✓ debug() endpoint working")
    
    def test_003_process_endpoint(self):
        """Test the process() endpoint"""
        result = process(self.test_data)
        
        self.assertEqual(result["status"], "success")
        self.assertIn("batch_id", result)
        self.assertIn("serials", result)
        self.assertEqual(len(result["serials"]), 5)
        print(f"✓ process() created batch: {result['batch_id']}")
    
    def test_004_generate_serial_numbers(self):
        """Test generate_serial_numbers()"""
        result = generate_serial_numbers({
            "quantity": 3,
            "work_order": "WO-SERIAL-TEST"
        })
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["serials"]), 3)
        print(f"✓ generate_serial_numbers() created {len(result['serials'])} serials")
    
    def test_005_error_handling(self):
        """Test error handling"""
        # Test with invalid quantity
        result = process({"work_order": "WO-ERROR", "quantity": 0})
        
        # Should return error status
        self.assertEqual(result["status"], "error")
        self.assertIn("message", result)
        print(f"✓ Error handling working: {result['message'][:50]}...")
    
    def test_006_async_detection(self):
        """Test if async is detected"""
        result = test()
        
        # Check if async support is reported
        self.assertIn("async_support", result)
        print(f"✓ Async support: {result['async_support']}")


def run_tests():
    """Run all tests"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAgentAPI)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return summary
    return {
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "successful": result.testsRun - len(result.failures) - len(result.errors)
    }


if __name__ == "__main__":
    print("=" * 80)
    print("🧪 RUNNING AGENT API TESTS")
    print("=" * 80)
    
    results = run_tests()
    
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    print(f"Tests run: {results['tests_run']}")
    print(f"Successful: {results['successful']}")
    print(f"Failures: {results['failures']}")
    print(f"Errors: {results['errors']}")
    
    if results['failures'] == 0 and results['errors'] == 0:
        print("✅ ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED")
