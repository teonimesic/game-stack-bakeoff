#!/usr/bin/env python3
"""Controls for the resource measurement in `static.run`. Run:

    python3 judge/rusage_selftest.py

`peak_rss_mb` and `cpu_seconds` are the only NEW measurements task 25 added, and both
have the shape this project keeps getting burned by: a number that is always in range
and always plausible, whether or not it is measuring anything.

Two specific ways they could be silently wrong:

  * **Units.** `ru_maxrss` is BYTES on macOS/BSD and KILOBYTES on Linux. Getting it
    wrong by 1024 produces a number that looks like a reasonable answer to a different
    question. So the unit is asserted against a child that allocates a KNOWN amount,
    never against documentation.

  * **Scope.** `just film` is never the process that renders anything: it is
    `just` -> a shell -> cargo/node/Unity/godot. A measurement that covers only the
    direct child would report the cost of `just`, which is a constant, for all four
    arms - the exact "reports success and measures nothing" failure. So there is a
    control in which the ONLY memory is allocated by a grandchild.

Every control is paired with its discriminating opposite: a big allocation is only
evidence if a small one reads small.

The third failure mode is the EXIT STATUS ITSELF. `static.run` waits with
`os.wait4` in a waiter thread, and its failure branch used to answer a reap it
could not observe with `reaped.put((0, None))` - exit 0 from a command nobody saw
end, the `|| echo 0` shape, at the one function every tier-1 command goes through.
The forced-reap fixture below patches `os.wait4` in-process so it raises
ChildProcessError over a child whose true exit is 3, and holds that the answer is
127 with a note naming the HARNESS, never 0. A mutant that reinstates the
fabricated 0 is loaded from source and must reproduce exactly that.

Every control is paired with its discriminating opposite: a big allocation is only
evidence if a small one reads small, and the forced reap is only evidence if the
same command unforced still reads its true exit.

Exit code is 0 only if every expectation holds.
"""

from __future__ import annotations

import contextlib
import errno
import inspect
import os
import sys
import textwrap
import time
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import static  # noqa: E402

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  -- {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)


def py(code: str) -> list[str]:
    return [sys.executable, "-c", textwrap.dedent(code)]


HERE = Path(__file__).resolve().parent


def run(code: str, timeout_s: int = 120) -> static.Cmd:
    return static.run(HERE, "control", py(code), timeout_s=timeout_s)


@contextlib.contextmanager
def forced_wait4_failure():
    """Make `os.wait4` raise ChildProcessError inside `static.run`, in-process.

    `static.run` does `import os` locally, which binds the same module object, so
    the module attribute is the only seam - patching `static`'s namespace would
    reach nothing. Only `wait4` is patched: `waitstatus_to_exitcode`, Popen's own
    bookkeeping and the drain readers are untouched, so the forced run differs
    from a real one by exactly the mechanism under test. The restore is in
    `finally`, so a failing expectation cannot leave the process patching itself.
    """
    real = os.wait4

    def broken(pid, options):
        raise ChildProcessError(errno.ECHILD,
                                "No child processes (forced by rusage_selftest)")

    os.wait4 = broken
    try:
        yield
    finally:
        os.wait4 = real


# --------------------------------------------------------------------------- #

def test_exit_and_output_unchanged() -> None:
    print("\n[the existing contract still holds]")
    c = run("""
        import sys
        sys.stdout.write('on stdout\\n')
        sys.stderr.write('on stderr\\n')
        sys.exit(3)
    """)
    check("exit code is the child's", c.code == 3, str(c.code))
    check("stdout is captured", "on stdout" in c.tail, c.tail[:80])
    check("stderr is captured", "on stderr" in c.tail, c.tail[:80])
    check("wall seconds recorded", c.seconds >= 0.0, str(c.seconds))

    missing = static.run(HERE, "control", ["/nonexistent/binary-xyz"])
    check("a binary that does not exist is 127, not a crash", missing.code == 127,
          str(missing.code))
    check("...and its resource fields are null rather than zero",
          missing.peak_rss_mb is None and missing.cpu_seconds is None,
          f"{missing.peak_rss_mb} {missing.cpu_seconds}")


def test_reap_failure_is_not_exit_zero() -> None:
    print("\n[a reap the harness could not observe reads 127-with-note, never exit 0]")
    child = """
        import sys
        sys.stdout.write('on stdout\\n')
        sys.stderr.write('on stderr\\n')
        sys.exit(3)
    """
    # The control first, and it is the same command: the forced result is only
    # evidence if the unforced one still reads the exit the child actually has.
    control = run(child)
    check("CONTROL: the same command, unforced, reads its true exit",
          control.code == 3, str(control.code))

    with forced_wait4_failure():
        c = run(child)

    check("a reap failure is NOT reported as exit 0", c.code != 0, str(c.code))
    check("...it takes the module's unobservable-command convention, 127",
          c.code == 127, str(c.code))
    check("...and the note names the HARNESS as the party that failed to observe",
          c.note.startswith("could not reap:"), repr(c.note))
    check("...the child's own words are preserved in the streams",
          "on stdout" in c.out and "on stderr" in c.err,
          f"{len(c.out)} chars out, {len(c.err)} chars err")
    check("...resource fields are None - the honest third value, not 0.0",
          c.peak_rss_mb is None and c.cpu_seconds is None,
          f"{c.peak_rss_mb} {c.cpu_seconds}")
    d = c.to_dict()
    check("...the stored record carries the same two facts",
          d.get("exit") == 127 and str(d.get("note") or "").startswith("could not reap:"),
          f"exit={d.get('exit')} note={d.get('note')!r}")

    # The two neighbouring branches, in the same check: the change to the reap
    # branch must not move either of them.
    missing = static.run(HERE, "control", ["/nonexistent/binary-xyz"])
    check("spawn-failure path unchanged: still 127", missing.code == 127,
          str(missing.code))
    check("...still its own 'could not run' note, still null resources",
          missing.note.startswith("could not run:")
          and missing.peak_rss_mb is None and missing.cpu_seconds is None,
          repr(missing.note))
    t = run("import time; time.sleep(60)", timeout_s=2)
    check("timeout path unchanged: still 124", t.code == 124, str(t.code))
    check("...still the TIMEOUT note", t.note.startswith("TIMEOUT after 2s"),
          repr(t.note))


def test_reap_mutant_is_caught() -> None:
    print("\n[mutant: reinstating 'reaped.put((0, None))' must be caught]")
    src = inspect.getsource(static)
    anchor = "reaped.put((ex, None))"
    if anchor not in src:
        raise AssertionError(
            "rusage_selftest: static.py's reap-failure branch no longer puts the "
            f"exception ({anchor!r} absent). Either the fix was reverted - which the "
            "forced-reap fixture above should also catch - or the branch was "
            "rewritten; re-point this mutant at what the code does now.")
    mutant_src = src.replace(anchor, "reaped.put((0, None))")
    # Load the mutant as a separate module from source: the real `static` stays
    # whole, so the mutant's red comes from the fixture catching the defect and
    # not from corrupting the module every other check reads. Registered in
    # sys.modules BEFORE exec for the reason static.py's own loader comments:
    # @dataclass resolves string annotations via sys.modules, and an unregistered
    # module mid-exec fails there.
    mod = types.ModuleType("static_reap_mutant")
    mod.__file__ = static.__file__
    sys.modules["static_reap_mutant"] = mod
    try:
        exec(compile(mutant_src, static.__file__, "exec"), mod.__dict__)
    finally:
        del sys.modules["static_reap_mutant"]
    with forced_wait4_failure():
        c = mod.run(HERE, "control", py("import sys; sys.exit(3)"))
    check("mutant 'reaped.put((0, None))' is caught: it fabricates exactly the "
          "exit 0 the fixture refuses", c.code == 0,
          f"mutant returned exit {c.code}, note {c.note!r}")


def test_peak_rss_units() -> None:
    print("\n[peak_rss_mb: the unit is measured, not assumed]")
    big = run("""
        import time
        block = bytearray(400 * 1024 * 1024)
        for i in range(0, len(block), 4096):
            block[i] = 1
        time.sleep(0.2)
    """)
    small = run("""
        import time
        time.sleep(0.2)
    """)
    check("a 400 MiB allocation is measured", big.peak_rss_mb is not None)
    check("a small process is measured", small.peak_rss_mb is not None)
    if big.peak_rss_mb is None or small.peak_rss_mb is None:
        return
    check("400 MiB reads as roughly 400 MiB, not 0.4 and not 400000",
          380 <= big.peak_rss_mb <= 700, f"{big.peak_rss_mb} MiB")
    check("a small process reads small", small.peak_rss_mb < 120,
          f"{small.peak_rss_mb} MiB")
    check("DISCRIMINATION: big is at least 5x small",
          big.peak_rss_mb > small.peak_rss_mb * 5,
          f"{big.peak_rss_mb} vs {small.peak_rss_mb}")


def test_peak_rss_covers_descendants() -> None:
    print("\n[peak_rss_mb: the tree, not the direct child]")
    # The parent stays tiny; a GRANDCHILD allocates. This is the `just` -> shell ->
    # engine shape, and it is the only reason the number is worth recording.
    c = run(f"""
        import subprocess, sys
        inner = "import time; b = bytearray(400*1024*1024)\\nfor i in range(0,len(b),4096): b[i]=1\\ntime.sleep(0.2)"
        mid = "import subprocess,sys; sys.exit(subprocess.run([sys.executable,'-c',%r]).returncode)" % inner
        sys.exit(subprocess.run([{sys.executable!r}, '-c', mid]).returncode)
    """)
    check("a grandchild's allocation is visible", c.peak_rss_mb is not None)
    if c.peak_rss_mb is not None:
        check("...and reads as ~400 MiB", 380 <= c.peak_rss_mb <= 700,
              f"{c.peak_rss_mb} MiB")


def test_cpu_is_not_wall() -> None:
    print("\n[cpu_seconds: CPU, not wall clock]")
    busy = run("""
        import time
        t = time.process_time()
        while time.process_time() - t < 1.0:
            pass
    """)
    idle = run("""
        import time
        time.sleep(1.5)
    """)
    check("a busy child reports cpu", busy.cpu_seconds is not None)
    check("an idle child reports cpu", idle.cpu_seconds is not None)
    if busy.cpu_seconds is None or idle.cpu_seconds is None:
        return
    check("1 s of spinning reads as ~1 s of CPU", 0.7 <= busy.cpu_seconds <= 3.0,
          f"{busy.cpu_seconds} s")
    check("1.5 s of SLEEPING reads as almost no CPU", idle.cpu_seconds < 0.4,
          f"{idle.cpu_seconds} s cpu over {idle.seconds:.1f} s wall")
    check("DISCRIMINATION: cpu_seconds is not wall_seconds",
          idle.cpu_seconds < idle.seconds / 2,
          f"cpu {idle.cpu_seconds} vs wall {idle.seconds:.1f}")
    check("...and it sums descendants' CPU as well as their memory",
          busy.cpu_seconds > 0.0)


def test_timeout_still_kills_the_group() -> None:
    print("\n[timeout: unchanged, and no orphan left behind]")
    marker = Path(os.environ.get("TMPDIR", "/tmp")) / f"rusage-selftest-{os.getpid()}"
    if marker.exists():
        marker.unlink()
    t0 = time.monotonic()
    c = static.run(HERE, "control", py(f"""
        import subprocess, sys, time
        inner = "import time\\nwhile True: time.sleep(0.2)"
        p = subprocess.Popen([{sys.executable!r}, '-c', inner])
        p.wait()
    """), timeout_s=3)
    elapsed = time.monotonic() - t0
    check("a hung child times out as 124", c.code == 124, str(c.code))
    check("...promptly", elapsed < 25, f"{elapsed:.1f}s")
    # The grandchild must be gone. If the group kill missed it, it is still spinning.
    time.sleep(0.5)
    out = os.popen("ps -A -o command=").read()
    check("no orphaned grandchild is left spinning",
          "while True: time.sleep(0.2)" not in out)


def test_static_record_carries_the_fields() -> None:
    print("\n[the fields reach the stored record]")
    c = run("import time; time.sleep(0.1)")
    d = c.to_dict()
    for k in ("peak_rss_mb", "cpu_seconds"):
        check(f"Cmd.to_dict carries {k}", k in d, str(sorted(d)))
    check("peak_rss_mb is a number in the record",
          isinstance(d["peak_rss_mb"], (int, float)), str(d["peak_rss_mb"]))
    check("cpu_seconds is a number in the record",
          isinstance(d["cpu_seconds"], (int, float)), str(d["cpu_seconds"]))


def main() -> int:
    test_exit_and_output_unchanged()
    test_reap_failure_is_not_exit_zero()
    test_reap_mutant_is_caught()
    test_peak_rss_units()
    test_peak_rss_covers_descendants()
    test_cpu_is_not_wall()
    test_timeout_still_kills_the_group()
    test_static_record_carries_the_fields()
    print()
    if FAILURES:
        print(f"FAILED: {len(FAILURES)}")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("all controls hold")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
