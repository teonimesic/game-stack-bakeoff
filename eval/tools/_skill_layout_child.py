#!/usr/bin/env python3
"""The subject of `skill_layout_selftest.py`'s kills. Not a tool; not run by hand.

Plants one breakage into a FIXTURE repository, says so on stdout, then waits to be killed.
A separate process is what makes the kill real: a signal delivered to the test process
itself would be caught by the test runner, and an exception raised where a signal would land
tests `try/finally`, not the handler.

    argv[1]  fixture repository root
    argv[2]  guarded    - state file written, handlers installed (the shipped behaviour)
             no-handler - state file written, handlers NOT installed (the SIGTERM mutant)
             no-state   - handlers installed, state file NOT written (the SIGKILL mutant)
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skill_layout_control as slc

root, mode = sys.argv[1], sys.argv[2]
if mode != "no-state":
    slc.write_state(root)
if mode != "no-handler":
    slc.install_handlers(root)
slc.PointerAsRealCopy(root).plant()
print("planted", flush=True)
time.sleep(120)
