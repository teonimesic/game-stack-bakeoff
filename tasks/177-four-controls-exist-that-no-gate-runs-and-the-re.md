---
id: 177
title: Four controls exist that no gate runs and the register does not record as excluded, and nothing produces that list
status: todo
priority: 2
refs: .github/workflows/README.md,eval/tools/fragment_control.py,eval/tools/evidence_set_control.py,eval/tools/ci_minutes.py,tasks/175
done_when: 'A producer answers ''which controls does no gate run, and which of those does the register record as deliberately excluded'' - most naturally a flag on `ci_minutes.py`, which already reads the workflows and already derives the hook list by RUNNING the hook rather than restating it. It must be pinned in both directions: a planted ungated control goes red, and a control recorded as excluded in the register stays green. Then each of the four above is either placed in a tier with its measured runtime added to the register''s cost column, or recorded as excluded with the reason. `fragment_control.py` and `evidence_set_control.py` at about a second each are the two where ''excluded'' would need a real argument. Coordinate with `tasks/175`: whichever runs second should find the other already done rather than re-deciding it.'
---

Found by the cleanup pass of 2026-08-27, the first to open `eval/tools/`.

`.github/workflows/README.md` is the register: what runs in which tier, what each costs, and every gate deliberately left out WITH THE REASON. AGENTS.md tells a session to read it before adding a gate, before concluding one is missing, and before assuming a green run covered something. The register's promise is only as good as something checking it, and nothing does.

Measured: of the 46 scripts in `eval/tools/`, 15 are invoked by no workflow and no git hook. Most of those are manual by design (`heartbeat.py`, `prune_scan.py`, `disclosure.py`). Four are not - they are CONTROLS, whose entire purpose is to be run as a gate, and none of the four is named anywhere in the register:

| tool | reachable from | runtime |
|---|---|---|
| `fragment_control.py` | **nothing at all** | 1.1s, exit 0, 12/12 |
| `evidence_set_control.py` | **nothing at all** (one prose mention in a sibling's docstring) | 1.5s, exit 0, 11/11 |
| `starter_gate_control.py` | `precampaign_smoke.py`, which is itself ungated | not run here |
| `disclosure_mutants.py` | `precampaign_smoke.py`, same | not run here |

The first two are the sharp cases. `fragment_control.py`'s own docstring says why it exists: it pins `docstat._check_duplicate_fragment` in both directions, and its `whole_line` mutant is 'the design that was tried first and measured as a complete false negative, so this control is what stops it being tried again silently'. Nothing runs it, so nothing stops that. Both cost about a second, which is pre-commit money.

The extraction was proved on a known case before being believed: `skill_layout_control.py`, which AGENTS.md says pins the layout gate red, is correctly detected as gated.

**The general defect is that this census has no producer.** `tasks/175` is one instance of the same shape found independently, one tool over - and fixing 175 alone leaves the next one, which is the enumeration-versus-property failure AGENTS.md's rule audit describes. A list of ungated controls that a human compiled is a list that goes stale the next time somebody adds a control.
