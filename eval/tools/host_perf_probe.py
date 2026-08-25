#!/usr/bin/env python3
"""Measure what this HOST does to a performance number, before any stack is compared on it.

    python3 eval/tools/host_perf_probe.py --selftest        offline, no load, runs anywhere
    python3 eval/tools/host_perf_probe.py --caps            can CPU or RAM be bounded here?
    python3 eval/tools/host_perf_probe.py --gpu             is there a GPU lever, and is GPU work isolated?
    python3 eval/tools/host_perf_probe.py --spread N        N launches of one fixed workload, idle gaps between
    python3 eval/tools/host_perf_probe.py --drift MINUTES   the same workload back to back, bucketed over time

`eval/PERF-HOST.md` is the report these arms produced and the authority for what they
mean; this file is only the producer. If the two disagree, the document wins.

THE SUBJECT IS THE MACHINE, NOT A SUBMISSION
--------------------------------------------
`eval/SCENES.md` proposes scoring a scene as a **ramp**: raise complexity until median
frame time crosses a budget, report the highest level sustained. That reads the stack
only if the machine underneath holds still. Nothing here renders a scene or grades one —
it runs one fixed synthetic GPU workload whose cost cannot change, so every difference
it reports belongs to the host.

A synthetic workload is a FLOOR and never a substitute. A real submission adds process
start, shader compilation, asset loading and engine-side variance on top of whatever is
measured here, so a spread figure from this tool bounds a submission's spread from
below and can never bound it from above.

EVERY CAP ARM RUNS THE SAME HOG TWICE
-------------------------------------
Once unrestricted, to establish it really can exceed the bound, and once under the
candidate cap. A flag that is accepted and then does nothing is worse than one that is
rejected, because no exit code separates it from a working guard (#61) — so a cap is
reported ENFORCED only where the hog measurably could not get past it, and IGNORED where
it sailed through at exit 0.

WHAT THE TWO CLOCKS ARE
-----------------------
`gpu_ms` is the GPU's own `gpuEndTime - gpuStartTime` per command buffer. `wall_ms` is
the host clock around commit-and-wait, so it carries host scheduling jitter as well. On
this machine they disagree by a factor of three in run-to-run spread, and which one a
ramp reads is a design decision rather than a detail.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# One dispatch is one "frame": its own command buffer, committed and waited on, which is
# the shape of an uncapped real-time render loop. The kernel is pure ALU, so its cost is
# fixed by (threads, iters) and cannot drift with anything the machine does.
GPU_SRC = r'''
import Foundation
import Metal

let src = """
#include <metal_stdlib>
using namespace metal;
kernel void burn(device float *out [[buffer(0)]],
                 constant uint &iters [[buffer(1)]],
                 uint gid [[thread_position_in_grid]]) {
    float x = float(gid) * 1e-6f + 1.0f;
    float a = 0.0f;
    for (uint i = 0; i < iters; ++i) {
        x = fma(x, 1.0000001f, 1e-7f);
        a += precise::sin(x) * precise::cos(x);
    }
    out[gid] = a;
}
"""

func arg(_ name: String, _ dflt: Int) -> Int {
    let a = CommandLine.arguments
    if let i = a.firstIndex(of: "--" + name), i + 1 < a.count, let v = Int(a[i + 1]) { return v }
    return dflt
}

let frames = arg("frames", 120)
let iters = arg("iters", 1024)
let threads = arg("threads", 1 << 20)

guard let dev = MTLCreateSystemDefaultDevice() else {
    FileHandle.standardError.write("no metal device\n".data(using: .utf8)!)
    exit(3)
}
let lib = try dev.makeLibrary(source: src, options: nil)
let pipe = try dev.makeComputePipelineState(function: lib.makeFunction(name: "burn")!)
let q = dev.makeCommandQueue()!
let out = dev.makeBuffer(length: threads * 4, options: .storageModePrivate)!
var it = UInt32(iters)

var gpuMs: [Double] = []
var wallMs: [Double] = []
let t0 = Date()
for _ in 0..<frames {
    let w0 = DispatchTime.now().uptimeNanoseconds
    let cb = q.makeCommandBuffer()!
    let enc = cb.makeComputeCommandEncoder()!
    enc.setComputePipelineState(pipe)
    enc.setBuffer(out, offset: 0, index: 0)
    enc.setBytes(&it, length: 4, index: 1)
    enc.dispatchThreads(MTLSize(width: threads, height: 1, depth: 1),
                        threadsPerThreadgroup: MTLSize(width: pipe.threadExecutionWidth, height: 1, depth: 1))
    enc.endEncoding()
    cb.commit()
    cb.waitUntilCompleted()
    let w1 = DispatchTime.now().uptimeNanoseconds
    gpuMs.append((cb.gpuEndTime - cb.gpuStartTime) * 1000.0)
    wallMs.append(Double(w1 - w0) / 1e6)
}
let elapsed = Date().timeIntervalSince(t0)
func f(_ xs: [Double]) -> String { xs.map { String(format: "%.5f", $0) }.joined(separator: ",") }
print("{\"device\":\"\(dev.name)\",\"frames\":\(frames),\"iters\":\(iters),\"threads\":\(threads),"
      + "\"elapsed_s\":\(elapsed),\"gpu_ms\":[\(f(gpuMs))],\"wall_ms\":[\(f(wallMs))]}")
'''

# The thing a cap has to stop. `mem` prints how far it got, so a partial stop is
# distinguishable from no stop at all; `cpu` exits on the WALL clock, so the quantity
# that varies between arms is the CPU-seconds it managed to consume.
HOG_SRC = r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <pthread.h>

static double now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec / 1e9;
}

static double spin_seconds;
static void *spin(void *arg) {
    (void)arg;
    double t0 = now();
    volatile double x = 1.0;
    while (now() - t0 < spin_seconds) {
        for (int i = 0; i < 2000000; i++) x = x * 1.0000001 + 1e-9;
    }
    return NULL;
}

int main(int argc, char **argv) {
    if (argc < 3) { fprintf(stderr, "usage: hog mem MB | hog cpu SECONDS THREADS\n"); return 2; }
    if (strcmp(argv[1], "mem") == 0) {
        long mb = atol(argv[2]);
        for (long i = 0; i < mb; i++) {
            char *p = malloc(1 << 20);
            if (!p) { printf("FAILED_AT_MB %ld\n", i); fflush(stdout); return 1; }
            memset(p, (int)(i & 0xff), 1 << 20);
        }
        printf("ALLOCATED_MB %ld\n", mb);
        return 0;
    }
    if (strcmp(argv[1], "cpu") == 0) {
        spin_seconds = atof(argv[2]);
        int n = argc > 3 ? atoi(argv[3]) : 1;
        if (n < 1 || n > 64) return 2;
        pthread_t th[64];
        for (int i = 0; i < n; i++) pthread_create(&th[i], NULL, spin, NULL);
        for (int i = 0; i < n; i++) pthread_join(th[i], NULL);
        printf("SPUN_SECONDS %.1f THREADS %d\n", spin_seconds, n);
        return 0;
    }
    return 2;
}
"""

# Asks the kernel rather than the shell builtin. bash prints one message for every
# refusal; errno separates "this rlimit does not exist here" from "you may not raise it",
# and RLIMIT_STACK is set to its own hard limit so a value error cannot be mistaken for
# an unsupported limit.
RLIMIT_SRC = r"""
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <sys/resource.h>

struct row { int id; const char *name; };

int main(void) {
    struct row rows[] = {
        {RLIMIT_AS, "RLIMIT_AS"}, {RLIMIT_DATA, "RLIMIT_DATA"}, {RLIMIT_RSS, "RLIMIT_RSS"},
        {RLIMIT_STACK, "RLIMIT_STACK"}, {RLIMIT_CPU, "RLIMIT_CPU"},
        {RLIMIT_NPROC, "RLIMIT_NPROC"}, {RLIMIT_NOFILE, "RLIMIT_NOFILE"},
    };
    for (unsigned i = 0; i < sizeof rows / sizeof rows[0]; i++) {
        struct rlimit r;
        if (getrlimit(rows[i].id, &r) != 0) {
            printf("%-13s getrlimit_failed %s\n", rows[i].name, strerror(errno));
            continue;
        }
        struct rlimit n = r;
        if (rows[i].id == RLIMIT_STACK) n.rlim_cur = r.rlim_max;
        else if (rows[i].id == RLIMIT_CPU || rows[i].id == RLIMIT_NPROC || rows[i].id == RLIMIT_NOFILE) n.rlim_cur = 60;
        else n.rlim_cur = (rlim_t)512 << 20;
        errno = 0;
        int rc = setrlimit(rows[i].id, &n);
        printf("%-13s cur=%llu hard=%llu set=%s %s\n", rows[i].name,
               (unsigned long long)r.rlim_cur, (unsigned long long)r.rlim_max,
               rc == 0 ? "OK" : "FAILED", rc == 0 ? "-" : strerror(errno));
    }
    printf("ALIASED RLIMIT_AS==RLIMIT_RSS %s\n", RLIMIT_AS == RLIMIT_RSS ? "YES" : "no");
    return 0;
}
"""

FRAMES = 600
ITERS = 1024


# ---------------------------------------------------------------- analysis


def pct(xs: list[float], p: float) -> float:
    """The observed value at the rounded `p/100 * (n-1)` index of a sorted copy. `p` is 0..100.

    **This is not the nearest-rank definition and the two disagree**, which matters because the
    difference is silent: nearest rank is `ceil(p/100 * n)`, so on `[1,2,3,4]` at p25 it returns
    `1` where this returns `2`. Both are standard, this one is numpy's `interpolation="nearest"`,
    and `--selftest` pins that exact pair so the docstring and the formula cannot drift apart
    again. It always returns a value that was actually observed — never an interpolation between
    two frames, which is not a frame time anything measured.
    """
    if not xs:
        raise ValueError("empty series")
    s = sorted(xs)
    i = max(0, min(len(s) - 1, int((p / 100.0) * (len(s) - 1) + 0.5)))
    return s[i]


def summarise(xs: list[float]) -> dict[str, float]:
    return {
        "n": len(xs),
        "median": pct(xs, 50),
        "p10": pct(xs, 10),
        "p90": pct(xs, 90),
        "min": min(xs),
        "max": max(xs),
    }


def spread(xs: list[float]) -> dict[str, float]:
    """Launch-to-launch spread of a per-launch statistic, as a share of its own median.

    `range_pct` is the number a ramp has to be read against: the widest the same
    unchanged workload was ever seen to be, not a standard error around a mean.
    """
    m = statistics.median(xs)
    return {
        "n": len(xs),
        "median": m,
        "min": min(xs),
        "max": max(xs),
        "range_pct": 100.0 * (max(xs) - min(xs)) / m,
        "cv_pct": 100.0 * statistics.pstdev(xs) / statistics.fmean(xs),
    }


def drift(samples: list[tuple[float, float]], bucket_s: float = 60.0) -> dict:
    """Bucket `(seconds_since_start, value)` and report how far the value moved.

    `degraded_pct` is the last bucket against the FIRST bucket rather than against the
    minimum: the question a perf pass asks is what a trial measured late in a run reads
    relative to one measured early, and the first bucket is what an early trial got.
    """
    if not samples:
        raise ValueError("no samples")
    buckets: dict[int, list[float]] = {}
    for t, v in samples:
        buckets.setdefault(int(t // bucket_s), []).append(v)
    rows = [(k * bucket_s, statistics.median(v), len(v)) for k, v in sorted(buckets.items())]
    first, last = rows[0][1], rows[-1][1]
    return {
        "buckets": rows,
        "first_bucket_median": first,
        "last_bucket_median": last,
        "degraded_pct": 100.0 * (last - first) / first,
        "span_s": samples[-1][0] - samples[0][0],
    }


# ---------------------------------------------------------------- building


def _cache_dir() -> Path:
    d = Path(tempfile.gettempdir()) / "host_perf_probe"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _build(name: str, source: str, compile_cmd) -> Path:
    """Compile an embedded program once per content hash.

    Keyed on the source, so editing a workload in this file cannot leave a stale binary
    behind answering for the new one — the address of the thing measured is an input to
    the measurement (AGENTS.md rule 12).
    """
    tag = hashlib.sha256(source.encode()).hexdigest()[:12]
    exe = _cache_dir() / f"{name}-{tag}"
    if exe.exists():
        return exe
    ext = {"gpu": ".swift", "hog": ".c", "rlimit": ".c"}[name]
    # Compile to a pid-unique path and publish with os.replace. The cache lives in the shared
    # system temp directory, so concurrent sessions race here: without this, one probe can see
    # `exe.exists()` while another is still writing it, and an interrupted compile leaves a
    # partial executable that every later run reuses. eval/AGENTS.md: one writer per artifact
    # path, temp file plus os.replace.
    stem = _cache_dir() / f".{name}-{tag}.{os.getpid()}"
    src = stem.with_suffix(stem.suffix + ext)
    src.write_text(source)
    tmp_exe = stem.with_suffix(stem.suffix + ".out")
    try:
        p = subprocess.run(compile_cmd(src, tmp_exe), capture_output=True, text=True, check=False)
        if p.returncode != 0:
            # The compiler's own message, not a traceback about a subprocess: an embedded
            # workload that stops compiling is edited in THIS file, and the line number the
            # compiler prints is the only thing that says where.
            raise SystemExit(f"could not build {name} from {src}:\n{p.stderr.rstrip()}")
        os.replace(tmp_exe, exe)
    finally:
        src.unlink(missing_ok=True)
        tmp_exe.unlink(missing_ok=True)
    return exe


def gpu_bin() -> Path:
    return _build("gpu", GPU_SRC, lambda s, e: ["swiftc", "-O", str(s), "-o", str(e)])


def hog_bin() -> Path:
    return _build("hog", HOG_SRC, lambda s, e: ["clang", "-O2", str(s), "-o", str(e)])


def rlimit_bin() -> Path:
    return _build("rlimit", RLIMIT_SRC, lambda s, e: ["clang", "-O2", str(s), "-o", str(e)])


def gpu_median(frames: int = FRAMES, iters: int = ITERS,
               prefix: list[str] | None = None) -> tuple[float, float, float]:
    """One launch of the fixed workload: (median gpu ms, median wall ms, total elapsed s)."""
    cmd = [*(prefix or []), str(gpu_bin()), "--frames", str(frames), "--iters", str(iters)]
    p = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if p.returncode != 0:
        raise SystemExit(f"gpu workload exit {p.returncode}: {p.stderr[:400]}")
    r = json.loads(p.stdout)
    return pct(r["gpu_ms"], 50), pct(r["wall_ms"], 50), r["elapsed_s"]


# ---------------------------------------------------------------- host facts


def host_line() -> str:
    def s(k):
        return subprocess.run(["sysctl", "-n", k], capture_output=True, text=True,
                              check=False).stdout.strip()
    ram = int(s("hw.memsize") or 0) // (1 << 30)
    return (f"{s('machdep.cpu.brand_string')}  {s('hw.ncpu')} cpu "
            f"({s('hw.perflevel0.logicalcpu')}P+{s('hw.perflevel1.logicalcpu')}E)  {ram} GB  "
            f"{platform.system()} {platform.mac_ver()[0] or platform.release()}  "
            f"load1={os.getloadavg()[0]:.2f}")


def require_darwin(arm: str) -> None:
    if platform.system() != "Darwin":
        raise SystemExit(f"NOT MEASURED: --{arm} probes darwin host mechanisms; this is "
                         f"{platform.system()}. No arm ran and nothing passed.")


# ---------------------------------------------------------------- arms


def arm_caps() -> int:
    require_darwin("caps")
    print(host_line())
    print("\n== rlimits, asked of the kernel directly")
    print(subprocess.run([str(rlimit_bin())], capture_output=True, text=True,
                         check=True).stdout.rstrip())

    hog = str(hog_bin())
    print("\n== RAM: the same hog wanting 2048 MB, unrestricted and under each candidate bound")
    for label, prefix in (("control (no restriction)", []),
                          ("taskpolicy -m 512", ["taskpolicy", "-m", "512"]),
                          ("taskpolicy -m 64 -j 10 -a", ["taskpolicy", "-m", "64", "-j", "10", "-a"])):
        p = subprocess.run([*prefix, hog, "mem", "2048"], capture_output=True, text=True,
                           check=False)
        got = p.stdout.strip() or f"(no stdout) {p.stderr.strip()[:120]}"
        # THE HOG'S OWN MARKER DECIDES, NOT THE EXIT CODE. A `taskpolicy` that is missing,
        # or that rejects a flag, exits non-zero having never launched the hog — and reading
        # that as ENFORCED would report a working cap from an arm that never ran, which is
        # the fail-open channel AGENTS.md rule 7 is about.
        reached = got.startswith("ALLOCATED_MB 2048")
        if not reached and not got.startswith("FAILED_AT_MB"):
            raise SystemExit(f"NOT MEASURED: `{' '.join([*prefix, 'hog', 'mem', '2048'])}` "
                             f"exited {p.returncode} without either of the hog's own markers. "
                             f"The arm did not run, so no row of it is a result.\n  {got}")
        if not prefix:
            # THE CONTROL DECIDES WHETHER THE OTHER ROWS MEAN ANYTHING. A host too short of
            # memory to reach 2048 MB unrestricted makes every policy row below read ENFORCED
            # while the policy did nothing — a positive control failing, reported as a result.
            if not reached:
                raise SystemExit(f"NOT MEASURED: the UNRESTRICTED control did not reach 2048 MB "
                                 f"({got}). Until it does, a capped row failing says nothing "
                                 f"about the cap. No verdict is printed.")
            verdict = ""
        else:
            verdict = "IGNORED" if reached else "ENFORCED"
        print(f"  {label:28s} exit={p.returncode:<4d} {got:22s} {verdict}")
    print("  a bound is ENFORCED only where the hog did NOT reach 2048 MB and the")
    print("  unrestricted control did.")

    print("\n== CPU: CPU-seconds taken in a fixed 6 s wall window, 16 spinning threads.")
    print("   Interleaved over 3 rounds, because the machine's own load moves between arms.")
    arms = {
        "control": [],
        "taskpolicy -b": ["taskpolicy", "-b"],
        "taskpolicy -c background": ["taskpolicy", "-c", "background"],
        "taskpolicy -c utility": ["taskpolicy", "-c", "utility"],
        "nice -n 20": ["nice", "-n", "20"],
    }
    got: dict[str, list[float]] = {k: [] for k in arms}
    for _round in range(3):
        for label, prefix in arms.items():
            p = subprocess.run(["/usr/bin/time", "-p", *prefix, hog, "cpu", "6", "16"],
                               capture_output=True, text=True, check=False)
            # Same guard as the RAM rows: `/usr/bin/time` prints a `user` line whatever the
            # child did, including not starting, so a policy this host rejects would otherwise
            # contribute a small and entirely plausible CPU-second figure to the table.
            if not p.stdout.startswith("SPUN_SECONDS"):
                raise SystemExit(f"NOT MEASURED: the `{label}` arm exited {p.returncode} without "
                                 f"the hog's own marker. No row of this arm is a result.\n"
                                 f"  {p.stdout.strip()[:200]} {p.stderr.strip()[:200]}")
            got[label].append(next(float(line.split()[1]) for line in p.stderr.splitlines()
                                   if line.startswith("user")))
    base = statistics.median(got["control"])
    for label, xs in got.items():
        s = spread(xs)
        print(f"  {label:26s} median={s['median']:7.2f} cpu-s  x{s['median'] / base:5.2f} of control"
              f"   run-to-run range={s['range_pct']:5.1f}%")
    print("  a restriction whose own run-to-run range is this wide is a scheduling BIAS,")
    print("  not a cap: what it grants depends on what else wanted the same cores.")
    return 0


def arm_gpu(rounds: int = 4) -> int:
    require_darwin("gpu")
    print(host_line())
    print("\n== GPU: interleaved arms, median frame time of one fixed workload")
    labels = ("control", "taskpolicy -b", "taskpolicy -c utility", "contended")
    arms: dict[str, list[float]] = {k: [] for k in labels}
    for _round in range(rounds):
        arms["control"].append(gpu_median(300)[0])
        arms["taskpolicy -b"].append(gpu_median(300, prefix=["taskpolicy", "-b"])[0])
        arms["taskpolicy -c utility"].append(
            gpu_median(300, prefix=["taskpolicy", "-c", "utility"])[0])
        hog = subprocess.Popen([str(gpu_bin()), "--frames", "4000", "--iters", str(ITERS)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            time.sleep(1)
            arms["contended"].append(gpu_median(300)[0])
        finally:
            hog.terminate()
            hog.wait()
    base = statistics.median(arms["control"])
    for label in labels:
        xs = arms[label]
        print(f"  {label:24s} median={statistics.median(xs):7.3f} ms  "
              f"x{statistics.median(xs) / base:5.2f} of control   "
              f"per-round={[round(x, 3) for x in xs]}")
    print("  a lever that does not move this number is not a GPU lever.")
    print("  `contended` adds one more GPU process on the same machine and nothing else,")
    print("  so its ratio is how much isolation this host gives GPU work.")
    print("  READ THE CONTROL ROW ACROSS ITS OWN ROUNDS BEFORE READING ANY RATIO: under")
    print("  sustained load it drifts, and a ratio taken against a moving base is not one.")
    return 0


def arm_spread(n: int, gap_s: float = 25.0) -> int:
    require_darwin("spread")
    print(host_line())
    print(f"\n== {n} launches of the same fixed workload, {gap_s:.0f} s idle between")
    gpu, wall, elapsed = [], [], []
    for i in range(n):
        if i:
            time.sleep(gap_s)
        g, w, e = gpu_median()
        gpu.append(g)
        wall.append(w)
        elapsed.append(e)
        print(f"  launch {i:2d}  gpu_median={g:7.3f} ms  wall_median={w:7.3f} ms  elapsed={e:5.2f} s")
    for label, xs in (("gpu median", gpu), ("wall median", wall), ("total elapsed", elapsed)):
        s = spread(xs)
        print(f"  {label:15s} median={s['median']:8.4f}  min={s['min']:8.4f}  max={s['max']:8.4f}  "
              f"range={s['range_pct']:6.3f}%  cv={s['cv_pct']:6.3f}%")
    print("  the idle gap is what makes this arm about LAUNCHES rather than about heat;")
    print("  --drift is the same workload with the gap removed.")
    return 0


def arm_drift(minutes: float) -> int:
    require_darwin("drift")
    print(host_line())
    print(f"\n== the same workload back to back for {minutes:g} minutes, no idle")
    samples: list[tuple[float, float]] = []
    t0 = time.time()
    while time.time() - t0 < minutes * 60:
        samples.append((time.time() - t0, gpu_median()[0]))
    d = drift(samples)
    for t, med, n in d["buckets"]:
        print(f"  t+{t:5.0f}s  median={med:7.3f} ms  (n={n})")
    print(f"  first bucket {d['first_bucket_median']:.3f} ms -> last {d['last_bucket_median']:.3f} ms"
          f"  = {d['degraded_pct']:+.1f}% over {d['span_s']:.0f} s")
    print("  START STATE IS AN INPUT: a machine already warm from a previous arm reports")
    print("  less drift than a cold one, so this figure is a floor unless the host was idle.")
    return 0


# ---------------------------------------------------------------- selftest


def arm_selftest() -> int:
    """The analysis, both directions, with no load and on any platform.

    It does NOT pretend to have measured the host. The host arms refuse to run off
    darwin by name; the only claim here is that the arithmetic every arm reports
    through is right, and that it would notice if it were not.
    """
    failures = []

    def check(name, got, want):
        ok = abs(got - want) < 1e-9
        print(f"  {'ok  ' if ok else 'FAIL'} {name}: got {got!r} want {want!r}")
        if not ok:
            failures.append(name)

    print("== analysis, against series whose answers are known in advance")
    check("pct p50 of 1..9", pct([9, 1, 5, 3, 7, 2, 8, 4, 6], 50), 5)
    check("pct p10 of 1..11", pct(list(range(1, 12)), 10), 2)
    check("pct p90 of 1..11", pct(list(range(1, 12)), 90), 10)
    # The case where this convention and nearest-rank disagree, pinned so the docstring and
    # the formula cannot drift apart: nearest rank would return 1 here.
    check("pct p25 of 1..4 is the rounded-index value, not nearest rank",
          pct([1, 2, 3, 4], 25), 2)
    check("summarise max", summarise([1.0, 2.0, 30.0])["max"], 30.0)
    check("spread range_pct", spread([8.0, 10.0, 9.0])["range_pct"], 100 * 2 / 9)
    d = drift([(0.0, 8.0), (10.0, 8.0), (70.0, 10.0), (80.0, 10.0)])
    check("drift degraded_pct", d["degraded_pct"], 25.0)
    check("drift buckets", len(d["buckets"]), 2)

    print("\n== mutants: each removes the mechanism the row above names")
    mutants = [
        ("pct returns the mean",
         lambda: statistics.fmean([1, 2, 3, 400]) == pct([1, 2, 3, 400], 50)),
        ("drift compares against the minimum, not the first bucket",
         lambda: drift([(0.0, 10.0), (70.0, 8.0)])["degraded_pct"] >= 0),
        ("spread reports cv where range is asked for",
         lambda: abs(spread([8.0, 10.0, 9.0])["range_pct"]
                     - spread([8.0, 10.0, 9.0])["cv_pct"]) < 1e-9),
    ]
    for name, alive in mutants:
        dead = not alive()
        print(f"  {'ok  ' if dead else 'FAIL'} mutant dies: {name}")
        if not dead:
            failures.append(f"mutant survived: {name}")

    print("\n== variants: inputs the analysis could get wrong while still returning a number")
    # A drift series that RECOVERS must report a negative degradation, not its magnitude.
    v = drift([(0.0, 10.0), (70.0, 8.0)])["degraded_pct"]
    check("drift is signed (10 -> 8 is -20%)", v, -20.0)
    # One outlier frame must not move the median; a mean-based reader would move 100x.
    check("one 900 ms frame does not move the median",
          pct([8.0] * 99 + [900.0], 50), 8.0)
    # A single-launch spread is 0% range, not a crash and not a division by zero.
    check("single-launch spread range is 0", spread([8.0])["range_pct"], 0.0)

    print("\n== the dispatch and the cache, which decide whether an arm runs at all")
    for argv, why in ((["--spread", "0"], "--spread 0 must be refused, not fall through to drift"),
                      (["--drift", "0"], "--drift 0 must be refused, not sample nothing")):
        p = subprocess.run([sys.executable, __file__, *argv], capture_output=True, text=True,
                           check=False)
        ok = p.returncode == 2
        print(f"  {'ok  ' if ok else 'FAIL'} {why} (exit {p.returncode})")
        if not ok:
            failures.append(why)
    # THE CACHE ROWS GO THROUGH `_build` ITSELF, with a stand-in compiler. A row that writes a
    # file and asks whether it is executable tests nothing `_build` does: it would stay green
    # if `_build` compiled straight to the looked-up name, and green is the reassuring answer.
    #
    # The expected path is spelled out here rather than taken from `_build`. A control that
    # imports its expectation from its subject is not a control (rule 12's corollary), and the
    # mutant that matters — publishing to the looked-up name without the rename — is exactly
    # the one a shared helper would hide.
    def expected(src: str) -> Path:
        return _cache_dir() / f"hog-{hashlib.sha256(src.encode()).hexdigest()[:12]}"

    # The stand-in compiler WRITES ITS OUTPUT AND THEN FAILS, which is what an interrupted
    # compile looks like. A compiler that merely exits non-zero leaves nothing behind, so it
    # would keep this row green against the very mutant it exists for — `_build` compiling
    # straight to the looked-up name.
    failing_src = f"/* selftest, compiler writes then fails: {os.getpid()} */\n"
    want = expected(failing_src)
    want.unlink(missing_ok=True)
    try:
        _build("hog", failing_src,
               lambda s, e: ["sh", "-c", 'cp /bin/echo "$1"; exit 1', "_", str(e)])
        raised = False
    except SystemExit:
        raised = True
    for name, got in (("a failed build raises rather than returning", raised),
                      ("a failed build leaves the looked-up path ABSENT", not want.exists())):
        print(f"  {'ok  ' if got else 'FAIL'} {name}")
        if not got:
            failures.append(name)
    want.unlink(missing_ok=True)

    ok_src = f"/* selftest, compiler succeeds: {os.getpid()} */\n"
    want_ok = expected(ok_src)
    want_ok.unlink(missing_ok=True)
    built = _build("hog", ok_src, lambda s, e: ["cp", "/bin/echo", str(e)])
    rows = [
        ("_build returns the path this selftest computed independently", built == want_ok),
        ("a successful build publishes an executable there", os.access(built, os.X_OK)),
        ("the intermediate paths are cleaned up",
         not list(_cache_dir().glob(f".hog-*.{os.getpid()}*"))),
    ]
    for name, got in rows:
        print(f"  {'ok  ' if got else 'FAIL'} {name}")
        if not got:
            failures.append(name)
    want_ok.unlink(missing_ok=True)

    print("\n== what this selftest does NOT establish")
    print("  anything about this host. --caps, --gpu, --spread and --drift each refuse to")
    print(f"  run off darwin by name; this platform is {platform.system()}.")
    if platform.system() == "Darwin":
        for tool in ("swiftc", "clang", "taskpolicy"):
            print(f"  {'ok  ' if shutil.which(tool) else 'FAIL'} {tool} on PATH")
            if not shutil.which(tool):
                failures.append(f"missing {tool}")

    print(f"\n{'PASS' if not failures else 'FAIL: ' + '; '.join(failures)}")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--selftest", action="store_true", help="offline: the analysis, with mutants")
    g.add_argument("--caps", action="store_true", help="can CPU or RAM be bounded on this host?")
    g.add_argument("--gpu", action="store_true",
                   help="is there a GPU lever, and is GPU work isolated?")
    g.add_argument("--spread", type=int, metavar="N", help="N launches of one fixed workload")
    g.add_argument("--drift", type=float, metavar="MINUTES", help="back-to-back for MINUTES")
    a = ap.parse_args()
    if a.selftest:
        return arm_selftest()
    if a.caps:
        return arm_caps()
    if a.gpu:
        return arm_gpu()
    # `is not None`, never truthiness: `--spread 0` is falsy, so a truthiness test falls through
    # to the drift arm with `--drift` unset. Both counts are refused rather than run empty — a
    # zero-launch spread and a zero-minute drift each produce a number-shaped nothing.
    if a.spread is not None:
        if a.spread < 1:
            ap.error("--spread needs at least 1 launch")
        return arm_spread(a.spread)
    if a.drift <= 0:
        ap.error("--drift needs a positive number of minutes")
    return arm_drift(a.drift)


if __name__ == "__main__":
    sys.exit(main())
