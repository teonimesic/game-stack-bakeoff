#!/usr/bin/env python3
"""How much of a task file did the queue lint ever evaluate?

The producer behind #141's coverage figure. `tasks.py check` validated four frontmatter
values -- `id`, `title`, `status`, `done_when` -- and never read the body, so a wrong
filename that HIT an existing ticket produced a well-formed artifact the lint certified.
This measures the share of the corpus those four keys occupy.

    python3 eval/tools/lint_coverage.py            # the tasks/ tree as it stands now
    python3 eval/tools/lint_coverage.py 436bf64    # as it stood at a commit
    python3 eval/tools/lint_coverage.py --selftest

WHY THIS FILE EXISTS RATHER THAN A NUMBER IN A DOCUMENT. #141 first published
`27,156 of 328,692 bytes, 8.3%` and both terms were wrong. Nothing disagreed with it
because nothing else computed it -- AGENTS.md's rule about writing the producer beside
the quantity, failing exactly as described. Re-measurement at merge gave 29,591 of
329,185.

THE NUMERATOR IS METHOD-DEPENDENT AND THE DENOMINATOR IS NOT. Total bytes is a bare
count: `wc -c`, `git ls-tree -l` blob sizes, and this file agree to the byte, and any
disagreement there is a bug. "Bytes belonging to a key" is a choice -- this slices the
raw frontmatter lines, because that is the text a reader sees; parsing each frontmatter
as YAML and re-serialising `k: v` for the four keys is an equally defensible method and
lands 47 bytes away. `--selftest` pins BOTH, so the gap is a measurement rather than a
surprise for the next person who re-derives it and thinks they have found something.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# The four values every condition in the pre-fix `cmd_check` read. Not a guess: read it
# back with `git show 436bf64:eval/tools/tasks.py`. `refs` and `established_by` are
# frontmatter too and no check ever looked at either, which is why this is not simply
# "the frontmatter block" -- that answer is 44% and overstates the lint by a factor of
# five.
LINTED_KEYS = ("id", "title", "status", "done_when")


def _files_at(rev: str | None) -> list[tuple[str, bytes]]:
    """Every `tasks/*.md` blob, from the working tree or from a commit.

    Reads blobs through `git cat-file`, not a checkout, so this can be pointed at a
    commit without disturbing anything -- and so the denominator comes from the object
    store, where a stray `._` sidecar or an editor backup cannot join the population.
    """
    if rev is None:
        return sorted(
            (p.name, p.read_bytes())
            for p in (ROOT / "tasks").glob("*.md")
            if not p.name.startswith("._")
        )
    listing = subprocess.run(
        ["git", "-C", str(ROOT), "ls-tree", "-z", f"{rev}:tasks"],
        capture_output=True, check=True,
    ).stdout
    out = []
    for entry in listing.split(b"\0"):
        if not entry:
            continue
        meta, name = entry.split(b"\t", 1)
        mode, kind, sha = meta.split()
        name = name.decode()
        if kind != b"blob" or not name.endswith(".md") or name.startswith("._"):
            continue
        blob = subprocess.run(
            ["git", "-C", str(ROOT), "cat-file", "blob", sha.decode()],
            capture_output=True, check=True,
        ).stdout
        out.append((name, blob))
    return sorted(out)


def linted_bytes(blob: bytes) -> int:
    """Bytes of the raw frontmatter lines belonging to `LINTED_KEYS`.

    Continuation lines count: a `done_when` folded over four lines is four lines the
    lint read. A file with no frontmatter scores 0, which is correct and is also the
    malformation the lint COULD already see.
    """
    if not blob.startswith(b"---\n"):
        return 0
    end = blob.find(b"\n---\n", 4)
    if end == -1:
        return 0
    total, taking = 0, False
    for line in blob[4:end + 1].decode("utf-8", "replace").splitlines(keepends=True):
        if line[:1] not in (" ", "\t") and ":" in line:
            taking = line.split(":", 1)[0] in LINTED_KEYS
        if taking:
            total += len(line.encode())
    return total


def linted_bytes_via_yaml(blob: bytes) -> int:
    """The same quantity by an independent route, for `--selftest`.

    Parses the frontmatter and re-serialises `key: value` per linted key. It cannot
    agree to the byte -- folding and quoting are lost -- and that is the point: two
    methods landing 47 bytes apart bounds the method's contribution to the figure.
    """
    import yaml

    if not blob.startswith(b"---\n"):
        return 0
    end = blob.find(b"\n---\n", 4)
    if end == -1:
        return 0
    try:
        data = yaml.safe_load(blob[4:end + 1].decode("utf-8", "replace")) or {}
    except yaml.YAMLError:
        return 0
    return sum(len(f"{k}: {data[k]}\n".encode()) for k in LINTED_KEYS if k in data)


def measure(rev: str | None, method=linted_bytes) -> tuple[int, int, int]:
    files = _files_at(rev)
    return len(files), sum(method(b) for _, b in files), sum(len(b) for _, b in files)


def _selftest() -> int:
    """Pins on `436bf64`, the commit #141 is about, plus the extraction proof.

    Rule 12's corollary: prove the extraction on one case whose answer you can state in
    advance. `tasks/70` at that commit carries task 71's brief -- a long body under a
    short frontmatter -- so its linted share must be small and non-zero. A method that
    returned 0 or 100% for it would pass a total-bytes check and be useless.
    """
    fails = []

    def eq(label, got, want):
        print(f"  {'ok  ' if got == want else 'FAIL'}  {label}: {got}" +
              ("" if got == want else f"  (expected {want})"))
        if got != want:
            fails.append(label)

    print("436bf64 -- the tree #141 measures")
    n, lint, total = measure("436bf64")
    eq("files", n, 70)
    eq("total bytes", total, 329185)
    eq("linted bytes (raw-line slice)", lint, 29591)
    eq("percent x10", round(1000 * lint / total), 90)

    print("the independent method, and the gap between them")
    _, lint_yaml, _ = measure("436bf64", linted_bytes_via_yaml)
    eq("linted bytes (yaml re-serialise)", lint_yaml, 29544)
    eq("gap", lint - lint_yaml, 47)

    print("the denominator, from the object store rather than from this file")
    ls = subprocess.run(
        ["git", "-C", str(ROOT), "ls-tree", "-l", "436bf64", "tasks/"],
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    eq("git ls-tree -l summed", sum(int(r.split()[3]) for r in ls), 329185)

    print("extraction proved on a case whose answer is known in advance")
    blobs = dict(_files_at("436bf64"))
    t70 = next(b for n_, b in blobs.items() if n_.startswith("70-"))
    share = linted_bytes(t70) / len(t70)
    print(f"  {'ok  ' if 0.01 < share < 0.5 else 'FAIL'}  tasks/70 linted share: "
          f"{share:.1%} (a long misfiled body under short frontmatter)")
    if not 0.01 < share < 0.5:
        fails.append("tasks/70 share")

    print(f"\n{'FAILED: ' + ', '.join(fails) if fails else 'all pins hold'}")
    return 1 if fails else 0


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return _selftest()
    rev = next((a for a in argv if not a.startswith("-")), None)
    n, lint, total = measure(rev)
    where = rev or "working tree"
    print(f"{where}: {n} task file(s)")
    print(f"  {lint:,} of {total:,} bytes evaluated by the queue lint = {100 * lint / total:.1f}%")
    print(f"  keys read: {', '.join(LINTED_KEYS)}; the body is {100 - 100 * lint / total:.1f}% "
          f"and no check reads it")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
