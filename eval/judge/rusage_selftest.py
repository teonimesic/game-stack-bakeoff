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

Exit code is 0 only if every expectation holds.
"""

from __future__ import annotations

import os
import sys
import textwrap
import time
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
