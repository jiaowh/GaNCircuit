import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from fastercap_known_answer import run_problem  # noqa: E402

LINE = "Weighted Frobenius norm of the difference between capacitance (auto option): {}\n"
CONVERGED = "Iteration number #1\n" + LINE.format("0.004") + "Iteration number #2\n" + LINE.format("0.0007")


class RunProblem(unittest.TestCase):
    def test_converged_log_is_accepted(self):
        self.assertIsNone(run_problem(CONVERGED, 0.001))

    def test_memory_termination_is_rejected(self):
        text = CONVERGED + ("Error: available free memory is not enough to allocate any chunk\n"
                            "       Cannot go out-of-core, terminating process\n")
        self.assertIn("memory", run_problem(text, 0.001))

    def test_unconverged_stop_is_rejected(self):
        self.assertIn("without converging", run_problem(LINE.format("0.00204824"), 0.001))

    def test_manual_mode_has_no_convergence_test(self):
        self.assertIsNone(run_problem("Capacitance matrix is:\n", None))


if __name__ == "__main__":
    unittest.main()
