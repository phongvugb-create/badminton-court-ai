"""
BADMINTON.AI - PHASE 7.1 TEST SUITE: REALTIME BUSINESS TOOLS INTEGRATION
(Mirror in backend/tests/ for modular test runners)
"""

import os
import sys
import importlib.util

# Re-export / run the root test suite safely without circular import collision
TEST_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
root_test_file = os.path.join(TEST_ROOT, "test_phase7_1_realtime_tools.py")

spec = importlib.util.spec_from_file_location("root_test_phase7_1_realtime_tools", root_test_file)
_mod = importlib.util.module_from_spec(spec)
sys.modules["root_test_phase7_1_realtime_tools"] = _mod
spec.loader.exec_module(_mod)

TestPhase71RealtimeTools = _mod.TestPhase71RealtimeTools

if __name__ == "__main__":
    import unittest
    unittest.main()
