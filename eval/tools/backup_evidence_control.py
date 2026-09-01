#!/usr/bin/env python3
"""Controls for the starter-baseline provenance tier of `backup_evidence.py`.

That tier decides whether the only surviving record of what starter an agent was
handed (FINDINGS #104) is still the commit it claims to be. If it can only ever
answer "yes", it is a mechanism that runs, reports success and measures nothing.

Git is the adjudicator, as it is for `evidence_set_control.py`: the fixture is a
REAL repository, and its baseline pair is produced by the same two commands the
harness uses — `git archive --prefix=<tid>/` and `git ls-tree -r`. Nothing about
the expected answer is hand-written.

  POSITIVE     a genuine pair verifies clean. Without this, a checker that always
               reported a problem would pass every adversarial case below.
  ADVERSARIAL  seven damaged pairs, each damaged in a way a real copy can be
               damaged, must each be caught: a flipped byte inside a member, a
               dropped member, an added member, a rewritten ls-tree line, a
               garbled commit header, an empty ls-tree, a truncated gzip, and a
               missing companion file.
  REAL DATA    (--runs-root) every baseline in the real tree verifies clean, so
               the checker is known to agree with the population it will judge.

And a MUTANT (`--mutate NAME`) removes one mechanism the checker relies on, to
prove the adversarial cases can go red for the reason they name.

**The default runs the clean pass AND every mutant**, and is red if any of them survives -
the repair `corpus_control.sweep` records from PR 54, which this file had not received: the
five mutants are the only proof that the seven adversarial cases can go red for the reason
each names, and with them opt-in the step repeated a clean pass nothing could fail while
they ran nowhere but an operator's terminal. The `--runs-root` arm runs ONCE, on the clean
pass: every mutant removes a check, so genuine baselines stay clean under all five, and
re-running the real tree per mutant would measure the same thing six times.

    ./backup_evidence_control.py                      # clean pass + every mutant - what CI runs
    ./backup_evidence_control.py --clean-only         # the controls alone, unmutated
    ./backup_evidence_control.py --mutate no_blob_compare
    ./backup_evidence_control.py --list-mutants
"""

from __future__ import annotations

import argparse
import gzip
import io
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import backup_evidence as BE  # noqa: E402

MUTANTS = {
    "no_blob_compare": "accept any content: never compare the recomputed blob id",
    "no_missing_check": "ignore an ls-tree path the archive does not carry",
    "no_extra_check": "ignore an archive member the ls-tree does not name",
    "no_header_check": "accept any first line as the root-commit header",
    "no_empty_check": "accept an ls-tree that records zero blobs",
}

TID = "g4_platformer__rust__t0"


def apply_mutant(name: str) -> None:
    """Break one mechanism inside `verify_starter_baseline`, by rebuilding it."""
    original = BE.verify_starter_baseline

    if name == "no_header_check":
        def patched(tar_path, blobs_path):
            return [p for p in original(tar_path, blobs_path)
                    if "root-commit header" not in p]
    elif name == "no_empty_check":
        def patched(tar_path, blobs_path):
            return [p for p in original(tar_path, blobs_path)
                    if "records zero blobs" not in p]
    elif name == "no_blob_compare":
        def patched(tar_path, blobs_path):
            return [p for p in original(tar_path, blobs_path)
                    if "!= recorded" not in p]
    elif name == "no_missing_check":
        def patched(tar_path, blobs_path):
            return [p for p in original(tar_path, blobs_path)
                    if "no such member" not in p]
    elif name == "no_extra_check":
        def patched(tar_path, blobs_path):
            return [p for p in original(tar_path, blobs_path)
                    if "not in the ls-tree" not in p]
    else:
        raise SystemExit(f"unknown mutant {name!r}; --list-mutants")

    BE.verify_starter_baseline = patched


# --------------------------------------------------------------------------
# fixture: a real repo, and a real baseline pair taken from it
# --------------------------------------------------------------------------

def git(repo: Path, *args: str, **kw) -> subprocess.CompletedProcess:
    env = dict(os.environ,
               GIT_AUTHOR_NAME="control", GIT_AUTHOR_EMAIL="control@example",
               GIT_COMMITTER_NAME="control", GIT_COMMITTER_EMAIL="control@example",
               GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_SYSTEM="/dev/null")
    return subprocess.run(["git", "-C", str(repo), *args],
                          env=env, check=True, capture_output=True, **kw)


def build_pair(scratch: Path) -> tuple[Path, Path]:
    """Make a genuine baseline pair the way the harness makes one."""
    repo = scratch / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "main.rs").write_text("fn main() { println!(\"hi\"); }\n")
    (repo / "Cargo.toml").write_text("[package]\nname = \"x\"\n")
    hook = repo / "verify.sh"
    hook.write_text("#!/bin/sh\nexit 0\n")
    hook.chmod(0o755)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "starter baseline")

    sha = git(repo, "rev-parse", "HEAD").stdout.decode().strip()
    tar_path = scratch / f"{TID}.starter-baseline.tar.gz"
    blobs_path = scratch / f"{TID}.starter-baseline.blobs.txt"
    with tar_path.open("wb") as fh:
        fh.write(git(repo, "archive", "--format=tar.gz",
                     f"--prefix={TID}/", "HEAD").stdout)
    ls = git(repo, "ls-tree", "-r", "HEAD").stdout.decode()
    blobs_path.write_text(f"# root commit {sha} subject 'starter baseline'\n{ls}")
    return tar_path, blobs_path


def rewrite_tar(src: Path, dst: Path, *, drop: str | None = None,
                mangle: str | None = None, add: str | None = None) -> None:
    """Copy an archive, optionally dropping, corrupting or adding one member."""
    buf = io.BytesIO()
    with tarfile.open(src, "r:gz") as tin, tarfile.open(fileobj=buf, mode="w") as tout:
        for m in tin:
            if drop and m.name == f"{TID}/{drop}":
                continue
            if mangle and m.name == f"{TID}/{mangle}":
                data = tin.extractfile(m).read()
                data = data[:-1] + bytes([data[-1] ^ 0x01])  # one flipped bit
                m.size = len(data)
                tout.addfile(m, io.BytesIO(data))
                continue
            f = tin.extractfile(m) if m.isfile() else None
            tout.addfile(m, f)
        if add:
            data = b"extra\n"
            info = tarfile.TarInfo(f"{TID}/{add}")
            info.size = len(data)
            tout.addfile(info, io.BytesIO(data))
    dst.write_bytes(gzip.compress(buf.getvalue()))


# --------------------------------------------------------------------------
# cases
# --------------------------------------------------------------------------

def run_cases(scratch: Path) -> tuple[int, list[str]]:
    tar_path, blobs_path = build_pair(scratch)
    failures: list[str] = []
    ran = 0

    def case(name: str, tar: Path, blobs: Path, want_problem: bool) -> None:
        nonlocal ran
        ran += 1
        probs = BE.verify_starter_baseline(tar, blobs)
        if want_problem and not probs:
            failures.append(f"{name}: expected a problem, got a clean verify")
        elif not want_problem and probs:
            failures.append(f"{name}: expected clean, got {probs[:3]}")

    # POSITIVE — the genuine pair. If this fails nothing below means anything.
    case("positive/genuine pair", tar_path, blobs_path, want_problem=False)

    d = scratch / "damaged"
    d.mkdir()

    t = d / "flipped.tar.gz"
    rewrite_tar(tar_path, t, mangle="src/main.rs")
    case("adversarial/flipped byte in a member", t, blobs_path, want_problem=True)

    t = d / "dropped.tar.gz"
    rewrite_tar(tar_path, t, drop="Cargo.toml")
    case("adversarial/member dropped", t, blobs_path, want_problem=True)

    t = d / "added.tar.gz"
    rewrite_tar(tar_path, t, add="injected.rs")
    case("adversarial/member added", t, blobs_path, want_problem=True)

    # An ls-tree line pointing at a blob id nothing in the archive hashes to.
    b = d / "rewritten.blobs.txt"
    lines = blobs_path.read_text().splitlines()
    lines[1] = lines[1].replace(lines[1].split()[2], "0" * 40)
    b.write_text("\n".join(lines) + "\n")
    case("adversarial/ls-tree oid rewritten", tar_path, b, want_problem=True)

    b = d / "noheader.blobs.txt"
    b.write_text("\n".join(blobs_path.read_text().splitlines()[1:]) + "\n")
    case("adversarial/commit header garbled", tar_path, b, want_problem=True)

    b = d / "empty.blobs.txt"
    b.write_text(blobs_path.read_text().splitlines()[0] + "\n")
    case("adversarial/ls-tree records zero blobs", tar_path, b, want_problem=True)

    t = d / "truncated.tar.gz"
    t.write_bytes(tar_path.read_bytes()[: len(tar_path.read_bytes()) // 2])
    case("adversarial/gzip truncated", t, blobs_path, want_problem=True)

    case("adversarial/companion missing", tar_path, d / "absent.blobs.txt",
         want_problem=True)

    return ran, failures


def run_real(runs_root: Path) -> tuple[int, list[str]]:
    """Every baseline in the real tree must verify clean."""
    pairs = sorted(runs_root.glob(f"*/starter-baselines/*{BE.BASELINE_SUFFIX}"))
    failures = []
    for tar in pairs:
        blobs = tar.parent / (tar.name[: -len(BE.BASELINE_SUFFIX)] + BE.BLOBS_SUFFIX)
        probs = BE.verify_starter_baseline(tar, blobs)
        if probs:
            failures.append(f"{tar.parent.parent.name}/{tar.name}: {probs[:2]}")
    return len(pairs), failures


def run_pass(runs_root: Path | None) -> tuple[int, list[str]]:
    """One full pass: the fixture cases, plus the real tree when an address was given."""
    scratch = Path(tempfile.mkdtemp(prefix="baseline-control-"))
    try:
        ran, failures = run_cases(scratch)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    real_n, real_failures = 0, []
    if runs_root:
        real_n, real_failures = run_real(runs_root.resolve())
        if real_n == 0:
            real_failures.append(
                f"--runs-root {runs_root} holds no starter baselines — this "
                f"control checked NOTHING against real data")

    print(f"fixture cases   {ran - len(failures)}/{ran} as expected")
    if runs_root:
        # `0/0` would read as a pass. Say the address was empty instead — rule 12:
        # the path is an input to the check, and a wrong one looks like a result.
        print(f"real baselines  {max(real_n - len(real_failures), 0)}/{real_n} clean"
              + ("   NO BASELINES AT THIS ADDRESS" if real_n == 0 else ""))
    for f in failures + real_failures:
        print(f"  FAIL {f}")
    return ran, failures + real_failures


def sweep(runs_root: Path | None) -> int:
    """The clean pass and EVERY mutant, in one invocation.

    THIS IS WHAT THE CI STEP RUNS, and it is why the step exists at all - the repair
    `corpus_control.sweep` records from PR 54, which this file had not received: with
    the default at the clean pass alone, the gate proved nothing could fail and no
    mutant ever ran outside an operator's terminal. A suite whose mutants are opt-in
    is a suite whose mutants are the one thing nobody re-runs.

    The real-tree arm runs on the clean pass only, for the reason the docstring gives.
    And the restore between mutants is LOAD-BEARING here rather than hygiene:
    `apply_mutant` captures `BE.verify_starter_baseline`'s CURRENT value as the
    original to filter, so a mutant that leaked would hand the next mutant a wrapped
    function and the pair would grade a composition neither name.
    """
    print("starter-baseline controls, clean pass first\n")
    ran, clean_bad = run_pass(runs_root)
    print(f"\nCLEAN  {'FAILED' if clean_bad else 'passed'}, expected passed\n")

    pristine = BE.verify_starter_baseline
    killed: list[str] = []
    survived: list[str] = []
    for name in MUTANTS:
        BE.verify_starter_baseline = pristine  # a mutant must not leak into the next
        apply_mutant(name)
        if BE.verify_starter_baseline is pristine:
            survived.append(f"{name}: rebound nothing - it is not testing anything")
            continue
        ran_m, bad = run_pass(None)
        print(f"\nMUTANT {name:<18} "
              + ("SURVIVED  <- the controls cannot see the mechanism it names"
                 if not bad else "went red, as it must"))
        (survived if not bad else killed).append(name)
    BE.verify_starter_baseline = pristine

    print(f"\n{len(killed)} of {len(MUTANTS)} mutants died; "
          f"{len(survived)} survived"
          + ("" if not survived else ":\n  " + "\n  ".join(survived)))
    if clean_bad or survived:
        return 1
    print("A mutant run is EXPECTED to fail its controls; a mutant that survives means "
          "the controls no longer reach the mechanism they name, and the gate's green "
          "is once again the ambiguity this file exists to prevent.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--runs-root", type=Path, default=None,
                    help="also verify every real baseline under this tree (clean pass only)")
    ap.add_argument("--mutate", help="break one mechanism and expect red")
    ap.add_argument("--list-mutants", action="store_true")
    ap.add_argument("--clean-only", action="store_true",
                    help="the controls on the unmutated checker, without the mutant sweep")
    a = ap.parse_args()

    if a.list_mutants:
        for k, v in MUTANTS.items():
            print(f"  {k:<18} {v}")
        return 0

    if a.mutate:
        if a.runs_root:
            # An accepted-but-ignored flag is worse than an unsupported one (AGENTS.md
            # rule 13): under a mutant the sweep runs fixture cases only, so a --runs-root
            # here would be read and then silently not used.
            raise SystemExit("--runs-root runs on the clean pass only; drop it or drop "
                             "--mutate")
        apply_mutant(a.mutate)
        print(f"MUTANT ACTIVE: {a.mutate} — {MUTANTS[a.mutate]}\n")

        scratch = Path(tempfile.mkdtemp(prefix="baseline-control-"))
        try:
            ran, failures = run_cases(scratch)
        finally:
            shutil.rmtree(scratch, ignore_errors=True)
        print(f"fixture cases   {ran - len(failures)}/{ran} as expected")
        # Under a mutant the fixture cases MUST fail. A mutant that changes
        # nothing means the mechanism it removed was not carrying the check.
        if failures:
            print(f"\nOK — the mutant was caught by {len(failures)} case(s); "
                  f"the controls can go red.")
            return 0
        print("\nMUTANT SURVIVED — these controls do not test the mechanism "
              "the mutant removed.")
        return 1

    if a.clean_only:
        _, bad = run_pass(a.runs_root)
        if bad:
            print("\nFAILED")
            return 1
        print("\nOK")
        return 0

    return sweep(a.runs_root)


if __name__ == "__main__":
    sys.exit(main())
