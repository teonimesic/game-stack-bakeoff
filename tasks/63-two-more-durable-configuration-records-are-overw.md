---
id: 63
title: 'Two more durable configuration records are overwritten in place: REPRODUCIBILITY.json and MEASURED.json'
status: done
priority: 5
refs: 'eval/judge/field_sweep.py, eval/tools/backup_evidence.py, eval/findings/documentation.md #119, DECISIONS.md'
done_when: Both writers route through tools/manifest.py write_manifest or an equivalent append-only path, with a control that fails on the pre-repair writer the way manifest_selftest.py does. If either is decided to be genuinely regenerable and not worth guarding, that is an acceptable outcome - but it must be recorded in DECISIONS.md with the argument, not left as silence, since the whole point of the resource-shaped guard is that a record nobody protected looks identical to one nobody needed.
established_by: 'Branch task-63-append-only-records, commit 56cd350. BROKEN STATE ESTABLISHED FIRST, before any edit: two field_sweep --repeats runs into one --out left exactly one REPRODUCIBILITY.json, sha256 819aa7a4 replaced by c722f069, the first sweep gone; two backup_evidence syncs into one --dest left one MEASURED.json and one MANIFEST.sha256, and the first sync''s manifest survived only because I had copied it aside by hand. SIX WRITERS, NOT TWO: field_sweep writes GATES.json, SEQUENTIAL.json and REPRODUCIBILITY.json, one per mode, and backup_evidence writes MANIFEST.sha256, DEST_ONLY.txt and MEASURED.json in one block; guarding only the two named would be the enumeration failure the ticket''s own last sentence warns about. THE SHAPE IS THE FINDING: write_manifest pins the canonical name to the FIRST record, which is right where a directory is named for one launch and wrong here, and applying it would have looked like a fix while breaking two documented readers - PROTOCOL.md tells a reader to take the evidence count from MEASURED.json, and judge_ledger.explain_gap looks for carried-over rounds at the HEAD of the mtime order because the counter is the last invocation''s, so a first-invocation counter makes the gap the suffix and every resumed sweep returns UNEXPLAINED exit 1. manifest.py now carries both shapes in one file with the criterion between them, argument in DECISIONS.md, table in eval/AGENTS.md. CONTROLS BOTH WAYS: manifest_selftest.py gains a rolling half, 13 expectations, whose MUTANT is the pre-repair bare write_text and which must destroy a record; VARIANTS cover a text record with no embedded timestamp stamped from mtime, an unparseable timestamp still kept, a repeated identical stamp not colliding, and an identical restatement writing nothing. Each of the four call sites reverted to its pre-repair line turns the suite red and names the right expectation, verified mechanically and restored, suite green again after. judge_ledger --selftest gains a superseded-sibling case, 29 expectations, 0 unmet. REAL DATA: ran backup_evidence against /Users/stefano/game-research-evidence. --verify-only first reported 6 missing files, the six MANIFEST-DEFECT.json markers task 30 wrote and never synced, which is the PROTOCOL trigger firing correctly; after the sync all three pre-repair records were kept byte-identical to hashes read before the run - MANIFEST 717ba7ef, MEASURED 573e6950, DEST_ONLY 7634695f - and the canonical names hold the current verification, 14,276 files, 1.118 GB, 765/765 harness JSON, 89/89 tarballs, 22/22 starter baselines from 1,238 blob ids. A second consecutive verification left the 2.5 MB MANIFEST.sha256 sibling count at one, proving the identical-bytes rule on real data. Also repaired: judge_ledger.SUMMARIES was an exact-name tuple and field_sweep had the same enumeration as f.name equals GATES.json, both now one is_summary predicate, and the two spellings are asserted equal at import. field_sweep summaries now record started_at and out_dir, which they carried neither of before. NO FINDING NUMBER TAKEN - eight peers are in flight and the collision rule says hand it to the orchestrator; the lesson is recorded as a decision in DECISIONS.md and a rule table in eval/AGENTS.md instead. docstat --sweep exit 0 unpiped, tasks.py check well-formed, lint 51 findings against 53 on main. Filed task 72: docstat --renumbered reports 33 decided stale citations across 16 files after the 2026-08-23 merge wave, of which the two inside sentences I rewrote were repaired here.'
---

Task 30 fixed the run manifest and stated the guard as the resource: any durable record of what a measurement was configured to be is append-only. A survey of every JSON writer in the harness found two more with the same overwrite shape, both left alone because they were outside task 30 and neither is currently known to have lost anything. (1) field_sweep.py writes REPRODUCIBILITY.json to an operator-supplied --out; re-running a sweep into the same directory replaces the previous sweep's reproducibility verdict, and that verdict is the gate-0 record for a set of judge rounds that cost real money. (2) backup_evidence.py writes MEASURED.json at the destination root on every sync; each sync erases what the previous one measured, which is exactly the question #116 turned on - what the copy held at an earlier time. Both are regenerable in principle and neither is, in practice, because the inputs move. Checked and found SOUND, for the record: judge pack mapping.json is destroyed by build_pack's rmtree, but each stored round copies order_seed into its own record (field.py line 865), so a rebuilt pack does not orphan a stored round; prompts/index.json has been kept-not-overwritten since #57; runner.py floors.json lands in a fresh scratch directory.

## What the work found, so the next agent does not re-derive it

**The ticket names two files; the writers hold six, and the resource covers all six.**
`field_sweep.py` writes three summaries, one per mode - `GATES.json` (--orders),
`SEQUENTIAL.json` (--sequential), `REPRODUCIBILITY.json` (--repeats) - and every one had the
overwrite shape. `backup_evidence.py` writes three destination records in one block -
`MANIFEST.sha256`, `DEST_ONLY.txt`, `MEASURED.json` - and guarding only the one the ticket
names would have been the enumeration failure the ticket's own last sentence warns about.
`MANIFEST.sha256` is arguably the most valuable of the three: it is the only per-file record
of what the copy held, and #116's stale prefix was a file that CHANGED at the destination
under a green SHA-256 verification.

**`write_manifest` is the wrong layout for both, and applying it would have looked like a
fix.** The property is that no record on disk is destroyed; two layouts satisfy it and they
differ in what the canonical name means afterwards. `write_manifest` pins the canonical name
to the FIRST record, which is right for `runs/<run>/suite.json` because the directory is named
for one launch. A sweep directory and a backup destination have no such identity - they
accumulate - and pinning them breaks two documented readers:

- `eval/PROTOCOL.md` instructs a reader to take the evidence count from `MEASURED.json`. Pin
  that name to the first sync ever and it returns a stale number that nothing disagrees with.
- `judge_ledger.explain_gap` looks for the carried-over rounds at the HEAD of the mtime order,
  because the counter is the last invocation's. Against a first-invocation counter the gap
  becomes the SUFFIX, and every resumed sweep returns UNEXPLAINED and exits 1.

So `tools/manifest.py` now carries both shapes with the criterion between them, and
`DECISIONS.md` has the argument. Do not "simplify" this to one writer.

**Integration points that are easy to miss.** `judge_ledger.SUMMARIES` was an exact-name
tuple; superseded siblings needed `is_summary()`, and `field_sweep.warn_rounds_without_
provenance` had the same enumeration written as `f.name == "GATES.json"`. Both now share one
predicate. `field_sweep.SUMMARIES` and `judge_ledger.SUMMARY_STEMS` are asserted equal at
import rather than promised equal.

**The stamp on a kept copy comes from a timestamp INSIDE the record where there is one**
(`RECORD_TIME_KEYS`), falling back to mtime only for plain text. mtime is weaker for the
reason `judge_ledger.MIN_SPLIT_S` exists: a `cp` rewrites every mtime in glob order.
`field_sweep`'s three summaries carried no timestamp at all before this and now record
`started_at` and `out_dir`.

**An identical restatement writes nothing.** Without that, `--verify-only` - which
`eval/PROTOCOL.md` tells you to run freely - would add a 2.5 MB `MANIFEST.sha256` copy every
time. Confirmed on the real destination: two consecutive verifications, one MANIFEST sibling.
