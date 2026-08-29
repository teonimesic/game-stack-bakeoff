#!/usr/bin/env python3
"""WHAT THE NON-CODE JUDGE ROUNDS READ, against what their packs carried.

THE PRODUCER for the population figures in `eval/RUNS.md`'s 2026-08-28
pre-registration of the `claude -p` prompt keyed on the pack's `sees`
(`field.JUDGE_PROMPT_SEES`). Until that change the prompt told every judge to
read code in A/ through H/ whatever its pack held. These figures are the
LATENT-NULL measurement: did any stored non-code round actually read the
evidence its prompt named and its pack did not carry? Do not quote them from
memory; run this.

Population: every JSON record under the root carrying `aspect` and `order_seed`
(the same predicate `blurb_selftest.py --stored-rounds` counts), whose pack
carries no code — `provenance.sees` lacking `code`, or for a round stored
before `provenance` existed, the aspect's `sees`.

Per aspect it reports six counts; the first four are round states and sum to
the aspect's n, the fifth counts targets, the last counts reads:

* **capture** — a `files_opened` list of strings is stored. The key did not
  exist before task 09 (2026-08-22), so absence is a THIRD value and not a
  clean bill: what that round read is permanently unaskable (#83's shape).
* **null** — the key is present but null. Only null counts as null.
* **absent** — the key is not in the record.
* **malformed** — the key is present but its value is neither null nor a list
  of strings: a shape the capture code never writes, refused whole. The unit
  is the RECORD — a bad shape poisons the capture, so nothing in it is
  classified.
* **truncated** — a read target of exactly 200 characters inside an
  otherwise-usable list: the length the capture in `field.py` stored at until
  2026-08-28 (task 204, since when it stores the full target), so in every
  round captured before then the stored tail — where the filename lives —
  cannot be vouched for. The unit is the TARGET: refused from classification,
  counted per target, itemised in full, and never counted as carried or as
  un-carried, while the list's good targets still classify. The walk never
  aborts on any of this.
* **un-carried reads** — reads naming anything the pack does not carry. This is
  the column the pre-registration is about; its content would make the wording
  change a re-scoring event rather than a wording change. The pack holds four
  kinds of thing and nothing else, so a read target naming NO known bucket —
  a `.src` path, a `.png` outside `frames/` — is un-carried too, and is
  itemised under its filename rather than folded away: a classifier with a
  residual bucket is a classifier that decides by default what it did not
  expect.

One read target is classified by the path it names, against the layout
`build_pack` writes: `<label>/frames/*.png`, `<label>/audio.json`,
`<label>/telemetry.json`; `BRIEF.md`, `SCENE.md` and anything under `/.claude/`
are housekeeping every judge is handed.

The classification is proven on a fixture tree (`--selftest`) whose every
answer is written out as a literal beside it, including the two rows that
discriminate: a code read inside a frames pack (the leak the column exists to
catch) and a `.png` read NOT under `frames/` (which must land in `other`, not
in frames — the exact bug a right-splitting path parse had here once).

Run:  python3 judge/prompt_capture_census.py --runs-root <main checkout>/eval/runs
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import aspects  # noqa: E402

#: `sees` for a round stored before `provenance` existed — the aspect is the
#: only thing those records carry. Same table and same reason as the census in
#: `blurb_selftest.py`: kept beside the code that uses it so a `sees` change
#: surfaces here as a mismatch rather than silently reclassifying rounds.
_SEES_BY_ASPECT = {"idiomatic": "code", "architecture": "code",
                   "fun": "frames+telemetry", "fun_frames": "frames",
                   "audio": "audio", "ux": "frames"}


def named_bucket(target: str) -> str:
    """Which evidence bucket a read target names, or `housekeeping`/`other`.

    The bucket is named by the FILENAME for audio and telemetry and by the
    DIRECTORY for frames, and the housekeeping files by their names — so a
    RELATIVE target (`BRIEF.md`, `frames/f0.png`, `A/audio.json`) classifies
    exactly as an absolute one. Under the earlier `/frames/`-and-slash rules a
    relative read fell into `other` and was counted un-carried: a false
    positive shaped like a finding, which is the direction a latent-null
    census must not fail in.

    THE LIMIT, stated because it cannot be engineered away here: the stored
    record carries no pack root — the pack tmpdir is deleted after the round —
    so a target OUTSIDE the pack that mimics the layout classifies by its
    shape, not by where it really was. The compensating controls are that
    every un-carried read is itemised with its full target path, and any
    target naming no known bucket is itemised by filename rather than folded
    into a bucket.
    """
    t = target.replace("\\", "/")
    name = t.rsplit("/", 1)[-1]
    if name.endswith(".png") and ("/frames/" in t or t.startswith("frames/")):
        return "frames"
    if name == "audio.json":
        return "audio"
    if name == "telemetry.json":
        return "telemetry"
    if (name in ("BRIEF.md", "SCENE.md") or "/.claude/" in t
            or t.startswith(".claude/")):
        return "housekeeping"
    return "other"


def rounds(runs_root: Path) -> list[dict]:
    """Every stored round record the population predicate accepts."""
    out = []
    for p in sorted(runs_root.rglob("*.json")):
        try:
            d = json.loads(p.read_text())
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not (isinstance(d, dict) and "aspect" in d and "order_seed" in d):
            continue
        prov = d.get("provenance") or {}
        aid = d["aspect"]
        sees = prov.get("sees") or _SEES_BY_ASPECT.get(aid)
        if not sees or "code" in sees.split("+"):
            continue
        out.append({"path": p, "aspect": aid, "sees": sees, "record": d})
    return out


def census(runs_root: Path) -> int:
    rs = rounds(runs_root)
    if not rs:
        print(f"no non-code judge rounds under {runs_root} - UNMEASURED, not clean",
              file=sys.stderr)
        return 2

    per: dict[str, dict[str, int]] = {}
    leaks: list[str] = []
    truncs: list[str] = []
    others: dict[str, int] = {}
    for r in rs:
        row = per.setdefault(r["aspect"], {"n": 0, "capture": 0, "null": 0,
                                           "absent": 0, "uncarried": 0,
                                           "malformed": 0, "truncated": 0})
        row["n"] += 1
        rec = r["record"]
        # MEMBERSHIP, not `.get`: a key that is absent and a key stored null are
        # two different unassessable states, and `.get` reads both as None -
        # which collapsed the columns in the fixture before it touched the
        # corpus. A third: only None counts as null. Anything else that is not
        # a list of strings is a shape the capture code never writes - named
        # `malformed` and skipped WHOLE, because classifying a dict as null
        # reads a shape error as a recorded state, and classifying the string
        # elements of a bad list would silently keep the readable half.
        # (Review round 2: both shapes used to be worse - the dict read as
        # null, and a list holding a non-string reached the classifier and
        # aborted the whole walk at `target.replace`.)
        if "files_opened" not in rec:
            row["absent"] += 1
            continue
        opened = rec["files_opened"]
        if opened is None:
            row["null"] += 1
            continue
        if (not isinstance(opened, list)
                or any(not isinstance(t, str) for t in opened)):
            row["malformed"] += 1
            continue
        row["capture"] += 1
        carried = set(r["sees"].split("+"))
        for t in opened:
            # A stored target of EXACTLY 200 characters may be a truncation:
            # until 2026-08-28 the capture in field.py stored
            # str(target)[:200], so anything longer than the cap was stored
            # at exactly this length with its tail - the filename - gone, and
            # anything shorter was never cut. The capture now stores the full
            # target (task 204), but every round captured before that date
            # remains 200-capped, so the arm stays for the stored corpus.
            # Classifying it would be a guess; refused and itemised, never a
            # carried read and never a leak. Counted per TARGET under
            # `truncated` - a different unit from `malformed` above, which is
            # per record: two truncated targets in one list are two, and the
            # list's good targets still classify. (Round 4: both used to add
            # to the same column, which made a count that named no unit.)
            if len(t) == 200:
                row["truncated"] += 1
                truncs.append(f"{r['path'].name}: {t}")
                continue
            b = named_bucket(t)
            if b == "housekeeping" or b in carried:
                continue
            row["uncarried"] += 1
            others[Path(t).name] = others.get(Path(t).name, 0) + 1
            leaks.append(f"{r['path'].name}: {t}")

    print(f"non-code judge rounds under {runs_root}: {len(rs)}")
    print(f"  {'aspect':12s} {'n':>3s} {'capture':>8s} {'null':>5s} {'absent':>7s} "
          f"{'un-carried reads':>17s} {'malformed':>10s} {'truncated':>10s}")
    for aid, row in sorted(per.items()):
        print(f"  {aid:12s} {row['n']:3d} {row['capture']:8d} {row['null']:5d} "
              f"{row['absent']:7d} {row['uncarried']:17d} {row['malformed']:10d} "
              f"{row['truncated']:10d}")
    n_cap = sum(r["capture"] for r in per.values())
    n_unc = sum(r["uncarried"] for r in per.values())
    n_mal = sum(r["malformed"] for r in per.values())
    n_trc = sum(r["truncated"] for r in per.values())
    print(f"  totals: {len(rs)} rounds, {n_cap} carrying a usable files_opened "
          f"capture, {len(rs) - n_cap} unassessable, {n_mal} malformed records, "
          f"{n_trc} truncated targets, {n_unc} reads of un-carried evidence")
    if others:
        print("  un-carried reads by filename (what they named, not folded away):")
        for name, n in sorted(others.items()):
            print(f"    {n:3d}  {name}")
    if leaks:
        print("  UN-CARRIED READS (each makes the prompt wording a scoring event):")
        for ln in leaks:
            print(f"    {ln}")
    if truncs:
        print("  REFUSED-TARGET reads (exactly 200 chars - the length the capture "
              "in field.py stored at until 2026-08-28, so rounds captured before "
              "then may be cut; the tail cannot be vouched for, so the "
              "target is classified as neither carried nor un-carried):")
        for ln in truncs:
            print(f"    {ln}")
    return 0


def _fixture(root: Path) -> Path:
    """A stored-runs tree whose every census answer is written out beside it."""

    def write(rel: str, rec: dict) -> None:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(rec))

    def rnd(aid: str, opened) -> dict:
        d: dict = {"aspect": aid, "order_seed": 0, "game": "g9_probe"}
        if opened is not ...:
            d["files_opened"] = opened
        return d

    P = "/tmp/pack"
    # audio: reads its own bucket plus the housekeeping every judge is handed.
    write("run-a/a.json", rnd("audio", [f"{P}/A/audio.json", f"{P}/A/BRIEF.md",
                                        f"{P}/.claude/skills/sampling-code/SKILL.md"]))
    # audio again, ALL RELATIVE TARGETS - the shape that classified as `other`
    # and read as a false leak under slash-anchored rules.
    write("run-a/a2.json", rnd("audio", ["A/audio.json", "BRIEF.md",
                                         ".claude/skills/sampling-code/SKILL.md"]))
    # fun_frames: the discriminating row - one code read inside a frames pack.
    write("run-f/f1.json", rnd("fun_frames", [f"{P}/B/frames/f0.png",
                                              f"{P}/B/frames/f1.png",
                                              f"{P}/B/BRIEF.md",
                                              f"{P}/B/code/sim/01.src"]))
    # ux: key present but null. fun: key absent altogether.
    write("run-f/f2.json", rnd("ux", None))
    write("run-f/f3.json", rnd("fun", ...))
    # telemetry read by a frames aspect is carried (fun_frames sees frames only,
    # so this one IS un-carried); fun sees frames+telemetry, so this is not.
    write("run-t/t1.json", rnd("fun", [f"{P}/C/telemetry.json"]))
    write("run-t/t2.json", rnd("fun_frames", [f"{P}/D/telemetry.json"]))
    # A png NOT under frames/ names no known bucket: `other`, never `frames`.
    write("run-o/o1.json", rnd("audio", [f"{P}/E/stills/x.png"]))
    # MALFORMED captures, one per shape no capture ever takes: a dict where
    # the list belongs, and a list holding a non-string. The second mixes a
    # real target with the bad element to pin that a malformed shape is
    # refused WHOLE - the good element must not be classified, and neither
    # shape may abort the walk.
    write("run-m/m1.json", rnd("ux", {}))
    write("run-m/m2.json", rnd("fun", [f"{P}/C/telemetry.json", None]))
    # TARGETS AT THE CAP LENGTH, TWO IN ONE LIST. field.py's capture stored
    # str(target)[:200] until 2026-08-28 (task 204; it stores the full target
    # since), so a stored target of exactly 200 characters may be a
    # truncation whose tail - the filename - is gone. Stated in advance: each
    # is refused from classification and counted per TARGET under `truncated`,
    # never as a frames read and never as a leak, while the record's good
    # targets still classify - the unit differs from `malformed`, which is per
    # RECORD. Without the rule these targets classify as `other` and read as
    # false un-carried leaks - the direction a latent-null census must not
    # fail in.
    t200 = "/tmp/pack/B/frames/" + "z" * (200 - len("/tmp/pack/B/frames/"))
    t200b = ("/tmp/pack/B/frames/deep/"
             + "y" * (200 - len("/tmp/pack/B/frames/deep/")))
    write("run-l/l1.json", rnd("fun_frames", [t200, t200b,
                                              f"{P}/B/frames/f0.png"]))
    # Round shapes that must stay out of the population.
    write("run-c/c.json", rnd("architecture", [f"{P}/G/code/sim/01.src"]))  # code
    write("run-x/x.json", {"aspect": "fun"})                                # no seed
    (root / "run-x/notjson.json").write_text("{")
    return root


def selftest() -> int:
    import tempfile
    failures: list[str] = []

    def expect(name: str, cond: bool, detail: str) -> None:
        if not cond:
            failures.append(f"{name}: {detail}")

    # Unit rows first, on the classifier alone - one case per branch, each with
    # its answer stated in advance.
    cases = [
        ("/tmp/p/A/frames/frame_00.png", "frames"),
        ("/tmp/p/A/audio.json", "audio"),
        ("/tmp/p/A/telemetry.json", "telemetry"),
        ("/tmp/p/A/BRIEF.md", "housekeeping"),
        ("/tmp/p/A/SCENE.md", "housekeeping"),
        ("/tmp/p/.claude/skills/sampling-code/SKILL.md", "housekeeping"),
        ("/tmp/p/A/code/sim/01.src", "other"),
        ("/tmp/p/A/stills/x.png", "other"),  # png outside frames/: NOT frames
        # Relative targets classify as their absolute shapes.
        ("BRIEF.md", "housekeeping"),
        ("frames/frame_00.png", "frames"),
        ("A/audio.json", "audio"),
        (".claude/skills/sampling-code/SKILL.md", "housekeeping"),
        # THE DOCUMENTED LIMIT: a target outside the pack that mimics the
        # layout classifies by its shape, because the record carries no pack
        # root. Pinned here as stated, so the limit is a decision rather than
        # an accident.
        ("/elsewhere/pack/B/frames/x.png", "frames"),
    ]
    for target, want in cases:
        expect(f"named-bucket[{Path(target).name}]", named_bucket(target) == want,
               f"named_bucket({target!r}) returned {named_bucket(target)!r}, "
               f"expected {want!r}")

    with tempfile.TemporaryDirectory() as td:
        root = _fixture(Path(td))
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = census(root)
        out = buf.getvalue()
        expect("selftest-census-runs", rc == 0, f"census returned {rc}: {out}")
        # Stated in advance: 11 population rounds. audio: 3 rounds, all capture,
        # 1 un-carried (the png outside frames/ - an audio pack carries no
        # such file, wherever it was read from); the relative-target round is
        # carried throughout. fun: 1 capture (telemetry is carried) + 1
        # key-absent + 1 malformed RECORD (a list holding a non-string).
        # fun_frames: 3 captures, 2 un-carried (the .src read and the
        # telemetry read - frames-only carries neither) and 2 truncated
        # TARGETS (exactly 200 chars - the length the capture stored at until
        # 2026-08-28, so never classified; the count is per target, and the
        # good frames read
        # in the same list still classifies). ux: 1 key-stored-null + 1
        # malformed RECORD (a dict where the list belongs). Everything else
        # is housekeeping.
        want_rows = {"audio": (3, 3, 0, 0, 1, 0, 0),
                     "fun": (3, 1, 0, 1, 0, 1, 0),
                     "fun_frames": (3, 3, 0, 0, 2, 0, 2),
                     "ux": (2, 0, 1, 0, 0, 1, 0)}
        for aid, (n, cap, null, absent, unc, mal, trc) in want_rows.items():
            hit = next((ln for ln in out.splitlines() if ln.split()[:1] == [aid]),
                       "")
            got = tuple(int(v) for v in hit.split()[1:8]) if hit else ()
            expect(f"fixture-row[{aid}]",
                   got == (n, cap, null, absent, unc, mal, trc),
                   f"the {aid} row reads {got}, expected "
                   f"{(n, cap, null, absent, unc, mal, trc)}\n{out}")
        expect("fixture-malformed-total",
               "2 malformed records" in out,
               f"the totals line must name the malformed captures it refused "
               f"whole - the unit is the record:\n{out}")
        expect("fixture-truncated-total",
               "2 truncated targets" in out,
               f"the totals line must count truncated targets per target, not "
               f"per record - two in one list are two:\n{out}")
        expect("fixture-truncated-reported",
               "l1.json: /tmp/pack/B/frames/" in out,
               f"the 200-char target must be itemised in full under the round "
               f"that stored it, refused from classification rather than read "
               f"as a frames read or as a leak:\n{out}")
        expect("fixture-un-carried-total",
               "3 reads of un-carried evidence" in out,
               f"the un-carried total line is wrong:\n{out}")
        expect("fixture-other-reported",
               "stills/x.png" in out,
               f"a png outside frames/ must appear in the un-carried itemisation "
               f"under the name it carried, never counted as a frames read:\n{out}")

    if failures:
        print(f"PROMPT CAPTURE CENSUS SELFTEST: {len(failures)} unmet\n")
        for f in failures:
            print(f"  FAIL {f}")
        return 1
    print("PROMPT CAPTURE CENSUS SELFTEST: the classifier answers every branch "
          "as stated, and the fixture rows - including the code-read leak and "
          "the png outside frames/ - come back exactly as written.")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs-root", type=Path, metavar="RUNS_ROOT",
                    help="the MAIN checkout's eval/runs - a worktree's is "
                         "gitignored and empty, which reads as UNMEASURED.")
    ap.add_argument("--selftest", action="store_true",
                    help="run the fixture tree instead of the corpus")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(selftest())
    if not args.runs_root:
        ap.error("--runs-root is required (or --selftest)")
    raise SystemExit(census(args.runs_root))
