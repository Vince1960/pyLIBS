import unittest

from pylibs.core.analysis_workflow import (
    irsac_correction_status,
    theoretical_spectrum_readiness,
)


class AnalysisWorkflowTests(unittest.TestCase):
    def test_theory_is_blocked_before_irsac(self):
        status = theoretical_spectrum_readiness(None, False, None, "")
        self.assertFalse(status.ready)
        self.assertIn("IRSAC", status.message)

    def test_palleschi_only_mode_does_not_unlock_theory(self):
        result = {
            "irsac_completed": False,
            "corrected_lines": 3,
            "applied": True,
            "enabled_lines": 3,
        }
        status = theoretical_spectrum_readiness(result, True, 1.0, "test")
        self.assertFalse(status.ready)
        self.assertIn("hybrid or IRSAC", status.message)

    def test_calculated_but_unapplied_irsac_is_not_enough(self):
        result = {
            "irsac_completed": True,
            "corrected_lines": 3,
            "applied": False,
            "enabled_lines": 0,
        }
        status = theoretical_spectrum_readiness(result, False, 1.0, "test")
        self.assertFalse(status.ready)
        self.assertIn("Apply", status.message)

    def test_post_irsac_reliable_temperature_is_required(self):
        result = {
            "irsac_completed": True,
            "corrected_lines": 3,
            "applied": True,
            "enabled_lines": 2,
        }
        status = theoretical_spectrum_readiness(result, True, None, "")
        self.assertFalse(status.ready)
        self.assertIn("Most reliable element", status.message)

    def test_complete_chain_unlocks_diagnostic_theory(self):
        result = {
            "irsac_completed": True,
            "corrected_lines": 3,
            "applied": True,
            "enabled_lines": 2,
        }
        status = theoretical_spectrum_readiness(
            result,
            True,
            0.82,
            "post-IRSAC most reliable element: Cu",
        )
        self.assertTrue(status.ready)
        self.assertAlmostEqual(status.temperature_ev, 0.82)
        self.assertIn("diagnostic only", status.message)

    def test_nonconverged_iterative_irsac_does_not_unlock_downstream_analysis(self):
        result = {
            "irsac_completed": True,
            "equation_mode": "iterative",
            "converged": False,
            "corrected_lines": 3,
            "applied": True,
            "enabled_lines": 3,
        }
        ready, message = irsac_correction_status(result, True)
        self.assertFalse(ready)
        self.assertIn("did not converge", message)

    def test_independent_no_evidence_decision_unlocks_uncorrected_theory(self):
        result = {
            "irsac_completed": True,
            "corrected_lines": 3,
            "applied": False,
            "enabled_lines": 0,
            "assessment_status": "No significant evidence",
        }

        status = theoretical_spectrum_readiness(
            result,
            False,
            0.91,
            "pre-correction most reliable element: Cd",
        )

        self.assertTrue(status.ready)
        self.assertAlmostEqual(status.temperature_ev, 0.91)
        self.assertIn("no significant self-absorption", status.message)


if __name__ == "__main__":
    unittest.main()
