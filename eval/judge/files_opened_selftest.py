#!/usr/bin/env python3
"""THE AUDIT CAPTURE STORES THE FULL READ TARGET, TRUNCATED AT NO LENGTH.

`field.run_field` records every tool call the judge CLI makes -- `tool_calls`,
and, for Read and NotebookRead, `files_opened` -- because the record of what a
judge actually read is the only thing that can answer "what did this round
see?" after the round is over (#83's question). Until 2026-08-28 (task 204) it
stored `str(target)[:200]`, so a target longer than the cap was stored with its
tail -- where the filename lives -- gone; and a target with no tail cannot be
classified against what the pack carried, which is exactly why
`prompt_capture_census.py` has to refuse exactly-200-character stored targets
instead of reading them. A capture that degrades its own entries below
classifiability fails the audit-trail rule, so the cap is gone: the full target
is stored, at any length.

Pinned here against `run_field` itself, with the `claude -p` subprocess stubbed
the way `blurb_selftest.py` stubs it -- no model, no network, no spend:

* a Read target longer than the old 200 cap is stored at full length, tail and
  filename intact, in both `tool_calls` and `files_opened`;
* a Bash command and a Grep pattern past the old cap are stored untruncated in
  `tool_calls` -- one statement carried every tool's target;
* a Grep target is NOT counted into `files_opened`: only Read and NotebookRead
  are reads, which is the split the census classifies through;
* a short target is stored exactly as it was given.

Red direction: with the cap restored, every long target comes back at exactly
200 characters with its tail gone, and each row above fails. Shown against the
pre-fix capture on 2026-08-28, before the fix landed.

THE STORED CORPUS IS NOT RE-READ UNDER THE NEW SHAPE. Rounds captured before
2026-08-28 remain 200-capped, and the census keeps refusing their
exactly-200-character targets as unclassifiable -- never re-read as carried and
never as un-carried. `files_opened` is an audit field scored by nothing, so no
scored round is affected either way.

Run:  python3 judge/files_opened_selftest.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import field  # noqa: E402

#: The cap the capture carried until 2026-08-28, named because the pin is ABOUT
#: it: the fixture premise is a target past this length, and the red direction
#: is the capture storing exactly it.
OLD_CAP = 200

_TAIL = "frames_and_telemetry_report.json"
_LONG_PATH = "/tmp/packs/wg-selftest/pack-A/" + "nested/deeper/" * 11 + _TAIL
_LONG_CMD = ("python3 -c \"import json; json.dump({'note': '"
             + "x" * (OLD_CAP + 40) + "'}, open('out.json', 'w'))\"")
_LONG_PATTERN = "def draw_" + "p" * (OLD_CAP + 30)
_SHORT_PATH = "/tmp/packs/wg-selftest/pack-A/audio.json"


def _events() -> list[dict]:
    """The stream-json the stubbed judge prints: 4 tool calls, then the verdict."""
    def tool_use(name: str, key: str, value: str) -> dict:
        return {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": name, "input": {key: value}}]}}

    verdict = {"submissions": [{"label": lab, "score": 2, "rank": 1,
                                "evidence": "e"} for lab in field.LABELS],
               "best": "A", "worst": "B", "field_note": "stubbed"}
    return [tool_use("Read", "file_path", _LONG_PATH),
            tool_use("Read", "file_path", _SHORT_PATH),
            tool_use("Bash", "command", _LONG_CMD),
            tool_use("Grep", "pattern", _LONG_PATTERN),
            {"type": "result", "structured_output": verdict,
             "total_cost_usd": 0.0}]


class _StubJudge:
    """`field.subprocess` for one round that must not spend anything."""

    TimeoutExpired = subprocess.TimeoutExpired

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def run(self, argv, **kw):
        self.calls.append(argv)
        body = "\n".join(json.dumps(ev) for ev in _events())
        return subprocess.CompletedProcess(argv, 0, body + "\n", "")


def _round(root: Path) -> dict:
    """A minimal game pack -- mapping BESIDE it, nothing in it -- judged stubbed."""
    pack = root / "pack"
    pack.mkdir()
    mapping = {"game": "g9_probe", "run": "files-opened-selftest",
               "order_seed": 7, "sees": "frames",
               "mapping": {lab: f"g9_probe__stub__t{i}"
                           for i, lab in enumerate(field.LABELS)},
               "evidence_counts": {}, "capture_geometry": None,
               "knowingly_truncated": False}
    field.mapping_path(pack).write_text(json.dumps(mapping))
    stub = _StubJudge()
    real, field.subprocess = field.subprocess, stub
    try:
        return field.run_field(pack, "ux")
    finally:
        field.subprocess = real


def selftest() -> int:
    failures: list[str] = []

    def expect(name: str, cond: bool, detail: str) -> None:
        if not cond:
            failures.append(f"{name}: {detail}")

    expect("fixture-premise",
           len(_LONG_PATH) > OLD_CAP and len(_LONG_CMD) > OLD_CAP
           and len(_LONG_PATTERN) > OLD_CAP and len(_SHORT_PATH) < OLD_CAP,
           f"the fixture must state its own premise: long targets past the old "
           f"{OLD_CAP} cap and a short one under it "
           f"(got {len(_LONG_PATH)}/{len(_LONG_CMD)}/{len(_LONG_PATTERN)}/"
           f"{len(_SHORT_PATH)})")

    with tempfile.TemporaryDirectory() as td:
        rec = _round(Path(td))
        expect("round-usable", rec.get("usable") is True,
               f"run_field returned usable={rec.get('usable')!r} after a "
               f"stubbed judge: {str(rec.get('error'))[:200]!r}")
        calls = [(c.get("tool"), c.get("target"))
                 for c in (rec.get("tool_calls") or [])]
        opened = rec.get("files_opened")

        # THE PIN. A target past the old cap, stored whole -- tail and filename
        # intact -- in both places the capture writes it.
        expect("long-read-whole-in-tool-calls", ("Read", _LONG_PATH) in calls,
               f"a Read target of {len(_LONG_PATH)} characters (past the old "
               f"{OLD_CAP} cap) must be stored untruncated in tool_calls; got "
               f"{[t for tool, t in calls if tool == 'Read']}")
        expect("long-read-whole-in-files-opened",
               opened is not None and _LONG_PATH in opened,
               f"the same target must reach files_opened untruncated - a capture "
               f"that cuts the tail cuts the filename, and a target with no "
               f"filename cannot be classified against what the pack carried; "
               f"got {opened}")
        # The tail row reads the STORED target, not the fixture string: a check
        # whose subject is the fixture proves nothing about the capture.
        stored_long = next((t for t in (opened or [])
                            if t.startswith(_LONG_PATH[:80])), None)
        expect("long-read-tail-intact",
               stored_long is not None and stored_long.endswith(_TAIL),
               f"the STORED target must still end in the filename it named "
               f"({_TAIL}) - the tail is where the filename lives; got "
               f"{stored_long!r}")

        # A short target was never cut, before or after.
        expect("short-read-exact",
               opened is not None and _SHORT_PATH in opened,
               f"the short read must be stored exactly as given; got {opened}")
        expect("n-files-opened", rec.get("n_files_opened") == 2,
               f"exactly the 2 Read targets are reads; got "
               f"{rec.get('n_files_opened')} over {opened}")

        # One statement carries every tool's target, and the read/non-read
        # split the census classifies through is untouched.
        expect("bash-whole-in-tool-calls", ("Bash", _LONG_CMD) in calls,
               f"a Bash command past the old cap must be stored untruncated in "
               f"tool_calls; got {[t for tool, t in calls if tool == 'Bash']}")
        expect("grep-whole-in-tool-calls", ("Grep", _LONG_PATTERN) in calls,
               f"a Grep pattern past the old cap must be stored untruncated in "
               f"tool_calls; got {[t for tool, t in calls if tool == 'Grep']}")
        expect("grep-not-a-read",
               opened is not None and _LONG_PATTERN not in opened,
               f"only Read and NotebookRead are reads - a pattern in "
               f"files_opened would hand the census a target that names no "
               f"file; got {opened}")

    if failures:
        print(f"FILES OPENED SELFTEST: {len(failures)} unmet\n")
        for f in failures:
            print(f"  FAIL {f}")
        return 1
    print("FILES OPENED SELFTEST: the capture stores the full read target - a "
          f"Read past the old {OLD_CAP} cap lands whole in tool_calls and "
          "files_opened, tail and filename intact; Bash and Grep targets are "
          "not cut either; a short target is exact; and only reads count as "
          "reads.")
    return 0


if __name__ == "__main__":
    raise SystemExit(selftest())
