import shutil
import subprocess
import time
import uuid
import unittest
from pathlib import Path

from circuit_tools.wslrun import run_solver


def _bash_ok():
    try:
        return subprocess.run(["wsl", "-e", "true"], capture_output=True, timeout=60).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return shutil.which("bash") is not None


def _workdir():
    # kept under the git-ignored runs/ (WSL may hold a just-used directory open, so it is not deleted)
    d = Path(__file__).resolve().parents[1] / "runs" / "test-wslrun" / uuid.uuid4().hex[:8]
    d.mkdir(parents=True)
    return d


@unittest.skipUnless(_bash_ok(), "needs WSL or bash")
class RunSolver(unittest.TestCase):
    def test_timeout_stops_the_solver_itself(self):
        # /bin/sleep stands in for a solver: on timeout its own PID must be gone, not just wsl.exe
        d = _workdir()
        t0 = time.time()
        with self.assertRaises(TimeoutError):
            run_solver("/bin/sleep", "30", d, 3, "sleep")
        self.assertLess(time.time() - t0, 25)
        pid = (d / "solver.pid").read_text().strip()
        alive = subprocess.run(["wsl", "-e", "bash", "-c", f"cat /proc/{pid}/comm 2>/dev/null"],
                               capture_output=True, text=True).stdout.strip()
        self.assertNotEqual(alive, "sleep")

    def test_normal_completion(self):
        p = run_solver("/bin/echo", "hello", _workdir(), 60, "echo")
        self.assertEqual(p.stdout.strip(), "hello")


if __name__ == "__main__":
    unittest.main()
