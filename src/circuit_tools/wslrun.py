"""Run a Linux solver under WSL with a time limit that stops the solver itself on timeout.

`subprocess.run(["wsl", ...], timeout=...)` stops only wsl.exe; the Linux process can keep running and compete with the
next case (audit of 9ca735d). This runner has the shell record its PID before exec'ing the solver, and on timeout stops
exactly that PID, after checking that /proc/<pid>/comm still names the expected solver (the host is shared: never kill by
name). On Linux hosts the solver is run directly.
"""
import platform
import subprocess
from pathlib import Path


def wsl_path(p):
    """Linux path of a Windows path; a string that is already a Linux path ("/...") is returned unchanged."""
    if isinstance(p, str) and p.startswith("/"):
        return p
    p = Path(p).resolve()
    return "/mnt/" + p.drive[0].lower() + p.as_posix()[2:]


def run_solver(binary, args, workdir, timeout, comm):
    """Run `binary args` in workdir; return the CompletedProcess. On timeout, stop the solver (checked by its comm name)
    and raise TimeoutError. `comm` is the Linux process name, e.g. "fasthenry" or "FasterCap"."""
    workdir = Path(workdir)
    pidfile = workdir / "solver.pid"
    if platform.system() == "Windows":
        cmd = ["wsl", "-e", "bash", "-c",
               f"cd '{wsl_path(workdir)}' && echo $$ > '{pidfile.name}' && exec '{wsl_path(binary)}' {args}"]
    else:
        cmd = ["bash", "-c", f"echo $$ > '{pidfile.name}' && exec '{binary}' {args}"]
    try:
        return subprocess.run(cmd, cwd=workdir, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        stop(pidfile, comm)
        raise TimeoutError(f"{comm} did not finish within {timeout:g} s")


def stop(pidfile, comm):
    """Stop the process recorded in pidfile if it is still `comm`; return True if a kill was sent."""
    pid = pidfile.read_text().strip() if pidfile.exists() else ""
    if not pid.isdigit():
        return False
    check = f'[ "$(cat /proc/{pid}/comm 2>/dev/null)" = {comm} ] && kill {pid} && echo killed'
    cmd = ["wsl", "-e", "bash", "-c", check] if platform.system() == "Windows" else ["bash", "-c", check]
    return "killed" in subprocess.run(cmd, capture_output=True, text=True, check=False).stdout
