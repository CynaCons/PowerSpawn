"""
Robust subprocess execution for CLI providers.

The providers historically ran their CLI via
``subprocess.run(shell=IS_WINDOWS, capture_output=True, timeout=...)``. On
Windows that has two failure modes that make a spawn hang *forever*, well past
its own timeout:

1. ``capture_output=True`` uses OS pipes. On cleanup the parent must drain
   stdout/stderr to EOF — but if the CLI spawns a worker/daemon that inherits
   the pipe's write handle (grok's leader daemon, a node worker, ...), that EOF
   never arrives and the drain blocks indefinitely.
2. ``shell=True`` means the process we can see/kill is ``cmd.exe``; on timeout
   ``subprocess`` kills the shell but the real CLI (and its children) are
   orphaned and keep running, still holding the handles.

``run_captured`` fixes both while preserving the ``shell`` wrapper that is
required to launch the ``.cmd`` / ``.ps1`` CLI shims npm/installer put on PATH:

* stdout/stderr are redirected to temp FILES (no pipe → no EOF-drain hang);
* stdin is an explicit file (the prompt) or DEVNULL (never an inherited console
  that a child could block reading);
* on timeout the whole PROCESS TREE is killed (``taskkill /T`` on Windows,
  ``killpg`` elsewhere), so a wedged run always returns within ``timeout``.
"""

import os
import subprocess
import sys
import tempfile
from typing import Optional, Tuple

IS_WINDOWS = sys.platform == "win32"


def kill_process_tree(pid: int) -> None:
    """Kill a process and all of its descendants (best-effort)."""
    try:
        if IS_WINDOWS:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True, timeout=15,
            )
        else:
            import signal
            os.killpg(os.getpgid(pid), signal.SIGKILL)
    except Exception:
        pass


def _read_text_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def run_captured(
    cmd,
    *,
    cwd: Optional[str] = None,
    timeout: int = 300,
    stdin_text: Optional[str] = None,
    shell: Optional[bool] = None,
) -> Tuple[int, str, str, bool]:
    """Run ``cmd`` capturing stdout/stderr to temp files.

    Returns ``(returncode, stdout, stderr, timed_out)``. Never blocks longer
    than ``timeout`` (+ a short kill grace): on timeout the process tree is
    killed and whatever was captured so far is returned with ``timed_out=True``.

    ``stdin_text`` is delivered to the child's stdin via a temp file; when None,
    stdin is DEVNULL so a child that reads stdin gets EOF instead of blocking.
    """
    if shell is None:
        shell = IS_WINDOWS

    out_fd, out_path = tempfile.mkstemp(prefix="powerspawn-", suffix=".out")
    err_fd, err_path = tempfile.mkstemp(prefix="powerspawn-", suffix=".err")
    os.close(out_fd)
    os.close(err_fd)
    in_path = None
    stdin_handle = None
    proc = None
    timed_out = False

    try:
        if stdin_text is not None:
            in_fd, in_path = tempfile.mkstemp(prefix="powerspawn-", suffix=".in")
            with os.fdopen(in_fd, "w", encoding="utf-8") as fin:
                fin.write(stdin_text)
            stdin_handle = open(in_path, "r", encoding="utf-8")
            stdin_arg = stdin_handle
        else:
            stdin_arg = subprocess.DEVNULL

        with open(out_path, "w", encoding="utf-8") as fout, \
                open(err_path, "w", encoding="utf-8") as ferr:
            proc = subprocess.Popen(
                cmd,
                stdin=stdin_arg,
                stdout=fout,
                stderr=ferr,
                cwd=cwd,
                shell=shell,
            )
            try:
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                kill_process_tree(proc.pid)
                try:
                    proc.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    pass

        returncode = proc.returncode if proc is not None else -1
        return returncode, _read_text_file(out_path).strip(), _read_text_file(err_path).strip(), timed_out

    finally:
        if stdin_handle is not None:
            try:
                stdin_handle.close()
            except OSError:
                pass
        for path in (out_path, err_path, in_path):
            if path:
                try:
                    os.unlink(path)
                except OSError:
                    pass
