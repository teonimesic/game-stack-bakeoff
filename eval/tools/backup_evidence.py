#!/usr/bin/env python3
"""Copy the evidentiary core of `eval/runs/` somewhere else, and prove it arrived.

    backup_evidence.py --dest /Volumes/Whatever/game-research-evidence
    backup_evidence.py --dest ... --verify-only

The set copied is whatever `evidence_set.py` classifies as evidence — see that
file for the rule. This one is about the copy and, mostly, about the check.

WHY THE CHECK IS THE LARGER HALF. rsync's exit code says rsync did not report an
error. It does not say the bytes are readable at the destination, that a JSON
record still parses, or that a tarball still extracts. This project has a rule
about exactly that shape (AGENTS.md rule 2: never infer a process's state from
its artifact's state; rule 3: a pipeline's exit status is the last stage's), and
a backup verified by its own exit code is that failure with the highest possible
cost, because it is discovered on the day the original is gone.

So verification runs in three tiers, all of them reading the DESTINATION:

  1. INVENTORY   every source path exists at the destination, same size.
  2. CONTENT     SHA-256 of every destination file matches the source's.
                 This is the one that catches a truncated or half-written copy.
  3. SEMANTIC    a sample of report.json files are parsed with json.load, and a
                 sample of submission.tar.gz are opened and their members
                 counted. Bytes matching is not the same as a file still being
                 the thing it claims to be, and these are the two formats
                 everything downstream depends on.

A MANIFEST.sha256 is written next to the copy so a THIRD location — an external
disk, another machine — can be verified against this one later without either
being trusted a priori.

Exit status is 0 only if every tier passed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import subprocess
import sys
import tarfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evidence_set as ES  # noqa: E402

CHUNK = 1 << 20


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        while chunk := fh.read(CHUNK):
            h.update(chunk)
    return h.hexdigest()


def human(n: int) -> str:
    return f"{n / 1e9:.3f} GB"


def do_rsync(src_root: Path, dest_runs: Path, rels: list[str]) -> int:
    dest_runs.mkdir(parents=True, exist_ok=True)
    payload = b"\0".join(r.encode() for r in rels) + b"\0"
    argv = ["rsync", "-a", "--from0", "--files-from=-",
            f"{src_root}/", f"{dest_runs}/"]
    print(f"  {' '.join(argv[:-2])} <{len(rels):,} paths> {src_root}/ {dest_runs}/")
    # check=False: the exit code is this function's return value and the caller decides
    # what a partial mirror means. A raise here would abort before the verify pass that
    # says WHICH files are missing.
    r = subprocess.run(argv, input=payload, check=False)
    return r.returncode


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", type=Path, required=True,
                    help="backup root; the mirror lands in <dest>/runs/")
    ap.add_argument("--runs-root", type=Path, default=ES.DEFAULT_RUNS_ROOT)
    ap.add_argument("--verify-only", action="store_true",
                    help="skip the copy; check what is already there")
    ap.add_argument("--sample", type=int, default=8,
                    help="how many report.json and tarballs to open (default 8; "
                         "0 means all)")
    ap.add_argument("--seed", type=int, default=None,
                    help="fix the sample for a reproducible check")
    a = ap.parse_args()

    src_root = a.runs_root.resolve()
    dest_root = a.dest.resolve()
    dest_runs = dest_root / "runs"

    if not src_root.is_dir():
        print(f"runs root missing: {src_root}", file=sys.stderr)
        return 2
    if dest_root == src_root or src_root in dest_root.parents:
        print("destination is inside the source — refusing", file=sys.stderr)
        return 2

    print(f"source      {src_root}")
    print(f"destination {dest_runs}")

    print("\n[1/5] classifying")
    part = ES.partition(src_root)
    if part.errors:
        print(f"  {len(part.errors)} paths unreadable — the set is incomplete, "
              f"refusing to copy a partial set as if it were whole",
              file=sys.stderr)
        for e in part.errors[:10]:
            print(f"    {e}", file=sys.stderr)
        return 1
    rels = sorted(str(p.relative_to(src_root)) for p, _n in part.evidence)
    print(f"  {len(rels):,} evidence files  {human(part.evidence_bytes)}")
    print(f"  {part.regenerable_files:,} regenerable files "
          f"{human(part.regenerable_bytes)} not copied")

    if not a.verify_only:
        print("\n[2/5] copying")
        t0 = time.time()
        rc = do_rsync(src_root, dest_runs, rels)
        print(f"  rsync exit {rc} in {time.time() - t0:.1f}s "
              f"(NOT evidence the copy is good — see [3/5])")
        if rc != 0:
            return 1
    else:
        print("\n[2/5] copy skipped (--verify-only)")

    # ---- tier 1: inventory -------------------------------------------------
    print("\n[3/5] verifying inventory at the destination")
    missing, wrong_size = [], []
    for rel in rels:
        s, d = src_root / rel, dest_runs / rel
        try:
            dn = d.lstat().st_size
        except OSError:
            missing.append(rel)
            continue
        if dn != s.lstat().st_size:
            wrong_size.append(rel)
    print(f"  present {len(rels) - len(missing):,}/{len(rels):,}   "
          f"missing {len(missing)}   size mismatch {len(wrong_size)}")
    for rel in (missing + wrong_size)[:10]:
        print(f"    BAD {rel}")

    # ---- tier 2: content ---------------------------------------------------
    print("\n[4/5] verifying content (SHA-256, reading both sides)")
    bad_hash, manifest = [], []
    checked_bytes = 0
    t0 = time.time()
    for rel in rels:
        s, d = src_root / rel, dest_runs / rel
        if not d.exists():
            continue
        try:
            hs, hd = sha256(s), sha256(d)
        except OSError as e:
            bad_hash.append(f"{rel}: {e}")
            continue
        checked_bytes += d.lstat().st_size
        manifest.append(f"{hd}  runs/{rel}")
        if hs != hd:
            bad_hash.append(f"{rel}: {hs} != {hd}")
    print(f"  hashed {len(manifest):,} files, {human(checked_bytes)} "
          f"in {time.time() - t0:.1f}s   mismatches {len(bad_hash)}")
    for b in bad_hash[:10]:
        print(f"    BAD {b}")

    # ---- tier 3: semantic --------------------------------------------------
    print("\n[5/5] opening files at the destination")
    rng = random.Random(a.seed)

    # Only JSON the HARNESS wrote is checked for parseability. A work tree's
    # own .json is the agent's source, and its format is not our contract:
    # `tsconfig.json` is JSONC and `json.load` rejects it, so a full sweep
    # reported 26 "corrupt" files on a copy that was byte-perfect. A verifier
    # that cries wolf on a good copy gets ignored on a bad one.
    #
    # The boundary is derived, not listed: `evidence_set.partition` already
    # identified every git work tree, so "inside one" is the test.
    work_tree_rels = tuple(f"{p.relative_to(src_root)}/" for p in part.work_trees)
    reports = [r for r in rels
               if r.endswith(".json") and not r.startswith(work_tree_rels)]
    tarballs = [r for r in rels if r.endswith("submission.tar.gz")]
    print(f"  ({len(reports):,} harness JSON records eligible; "
          f"{sum(1 for r in rels if r.endswith('.json')) - len(reports):,} "
          f"in-work-tree .json excluded — agent source, not our format)")

    def pick(xs: list[str]) -> list[str]:
        if a.sample <= 0 or a.sample >= len(xs):
            return xs
        return rng.sample(xs, a.sample)

    json_ok, json_bad = 0, []
    for rel in pick(reports):
        try:
            with (dest_runs / rel).open() as fh:
                json.load(fh)
            json_ok += 1
        # noqa BLE001, deliberately blind: this is a VERIFIER, and a verifier that
        # enumerates the ways a backup can be corrupt only checks the ways someone
        # thought of. Every failure lands in `json_bad` with its message and is
        # reported; nothing is swallowed, and the counts are printed as k/n so a
        # verifier that opened nothing cannot read as a verifier that found nothing.
        except Exception as e:  # noqa: BLE001
            json_bad.append(f"{rel}: {e}")

    tar_ok, tar_bad, members_total = 0, [], 0
    for rel in pick(tarballs):
        try:
            with tarfile.open(dest_runs / rel, "r:gz") as tf:
                n = 0
                for m in tf:
                    n += 1
                    if m.isfile() and n <= 3:
                        # Actually decompress a few members. An archive whose
                        # index reads but whose data stream is truncated passes
                        # a member count and fails here.
                        f = tf.extractfile(m)
                        if f is not None:
                            f.read()
            if n == 0:
                raise ValueError("archive holds zero entries")
            members_total += n
            tar_ok += 1
        # noqa BLE001, same reason as the JSON loop above: a truncated data stream, a
        # bad gzip header and a member that will not extract raise different types and
        # all mean the same thing here -- this archive will not re-judge.
        except Exception as e:  # noqa: BLE001
            tar_bad.append(f"{rel}: {e}")

    print(f"  report/record JSON parsed  {json_ok}/{json_ok + len(json_bad)}")
    print(f"  submission tarballs opened {tar_ok}/{tar_ok + len(tar_bad)}  "
          f"({members_total:,} members read)")
    for b in (json_bad + tar_bad)[:10]:
        print(f"    BAD {b}")

    # `0/0` reads as a pass and is indistinguishable from a tier that could not
    # fail (AGENTS.md rule 1). Say which, rather than letting the reader assume.
    if not reports and not tarballs:
        print("  NOTE: this tree holds no harness records and no tarballs, so "
              "tier 3 checked NOTHING. Only tiers 1-2 (inventory, SHA-256) "
              "cover this copy.")

    # ---- manifest ----------------------------------------------------------
    ok = not (missing or wrong_size or bad_hash or json_bad or tar_bad)
    if ok:
        dest_root.mkdir(parents=True, exist_ok=True)
        (dest_root / "MANIFEST.sha256").write_text("\n".join(manifest) + "\n")
        (dest_root / "MEASURED.json").write_text(json.dumps({
            "verified_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "source": str(src_root),
            "evidence_files": len(rels),
            "evidence_bytes": part.evidence_bytes,
            "regenerable_files_not_copied": part.regenerable_files,
            "regenerable_bytes_not_copied": part.regenerable_bytes,
            "sha256_verified_files": len(manifest),
            "sha256_verified_bytes": checked_bytes,
            "json_parsed": json_ok,
            "tarballs_extracted": tar_ok,
            "tarball_members_read": members_total,
        }, indent=2))
        print(f"\nOK — {len(manifest):,} files verified by content at "
              f"{dest_runs}")
        print(f"manifest: {dest_root / 'MANIFEST.sha256'}")
        return 0

    print("\nFAILED — the copy is not verified. Do not treat it as a backup.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
