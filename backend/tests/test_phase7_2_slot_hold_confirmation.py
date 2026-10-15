"""
BADMINTON.AI - PHASE 7.2 TEST SUITE: SAFE SLOT HOLD & EXPLICIT USER CONFIRMATION
(Mirror in backend/tests/ for modular test runners)
"""

import os
import sys
import importlib.util

# Re-export / run the root test suite safely without circular import collision
TEST_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
root_test_file = os.path.join(TEST_ROOT, "test_phase7_2_slot_hold_confirmation.py")

spec = importlib.util.spec_from_file_location("root_test_phase7_2_slot_hold_confirmation", root_test_file)
_mod = importlib.util.module_from_spec(spec)
sys.modules["root_test_phase7_2_slot_hold_confirmation"] = _mod
spec.loader.exec_module(_mod)

TestPhase72SlotHoldConfirmation = _mod.TestPhase72SlotHoldConfirmation

if __name__ == "__main__":
    import unittest
    unittest.main()
