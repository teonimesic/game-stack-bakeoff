#!/usr/bin/env python3
"""A subjective layer designed for DISCRIMINATION, not difficulty.

The old rubric asked 13 binary questions and nearly every submission scored 13/13.
A ceiling is not fixed by adding more criteria of the same kind - a harder rubric that
everything still passes is exactly as useless.

Three structural changes:

1. COMPARATIVE, not absolute (judge_pairwise.py). "Is this good?" saturates when
   everything is good. "Which of these two is better, and why?" cannot saturate: a
   comparison is contested by construction. This also sidesteps FINDINGS #21 - absolute
   criteria are borderline for some artifacts and obvious for others, so their stability
   is artifact-dependent, whereas every pair is contested and reliability is measurable
   one consistent way.

2. GRADED where absolute, with anchors written around what separates COMPETENT from
   EXCELLENT. The deterministic tiers already catch broken. An anchor set spanning
   broken-to-working has nowhere to put twenty-four functionally perfect submissions.

3. EXISTENCE -> QUALITY. Every old criterion asked whether something exists. All 24
   submissions are functionally complete, so the rubric has to start where they finish:
   not "is there feedback" but "is the feedback legible at a glance and does it
   distinguish states a player must tell apart".
"""

GRADED_SCALE = """0  absent
1  present but poor - a player would call it broken or unhelpful
2  competent - what a careful hobby project produces; correct, unremarkable
3  strong - deliberate craft; a good indie release would ship this
4  excellent - considered and cohesive; better than most shipped indie work"""

# Anchors deliberately place "competent" at 2, so a functionally perfect but plain
# submission lands mid-scale and has room to be beaten.
HARD_CRITERIA: list[tuple[str, str, dict[int, str]]] = [
    ("craft.feedback_legibility",
     "Is on-screen feedback legible at a glance, and does it distinguish the states a "
     "player must actually tell apart mid-play?",
     {0: "no feedback of any kind",
      1: "feedback exists but is ambiguous - states a player must distinguish look alike",
      2: "each important state has a distinct, readable indicator",
      3: "feedback is immediate and positioned where the eye already is",
      4: "layered and prioritised - the urgent reads first, the ambient never competes"}),
    ("craft.visual_hierarchy",
     "Does the presentation direct attention to what matters right now, rather than "
     "drawing everything with equal emphasis?",
     {0: "no hierarchy; everything is equally loud or equally flat",
      1: "hierarchy works against the player - decoration outweighs the play area",
      2: "the player-controlled and interactive elements are the most prominent",
      3: "a clear three-level hierarchy: acting, reacting, context",
      4: "hierarchy shifts appropriately with game state"}),
    ("craft.tuning",
     "From the telemetry: are the numbers chosen so the game is playable and has a "
     "reason to continue - reaction time, round length, escalation?",
     {0: "unplayable pacing - instant or stalled",
      1: "playable only in principle; reaction windows too tight or rounds interminable",
      2: "reasonable intervals; nothing egregious",
      3: "evidence of deliberate tuning - rounds resolve in a satisfying span",
      4: "tuning shapes a session: escalation, variation, a difficulty curve"}),
    ("craft.test_strength",
     "Would these tests catch a regression an author would plausibly introduce, or do "
     "they only confirm the code does what it does?",
     {0: "no meaningful tests",
      1: "tests restate the implementation; a wrong rule would still pass",
      2: "behavioural assertions covering the main rules",
      3: "tests target the failure modes this genre actually has",
      4: "adversarial - invariants, boundaries, and regressions a careful author fears"}),
    ("craft.code_economy",
     "Is the implementation the size the problem warrants - neither padded with "
     "ceremony nor compressed past readability?",
     {0: "unreadable or grossly padded",
      1: "noticeable ceremony or duplication for its own sake",
      2: "proportionate and readable",
      3: "economical - each abstraction earns its place",
      4: "notably clear; a reader could extend it without asking questions"}),
]

# Forced differentiation. Extracts signal even when every score saturates, because a
# judge that must name the single best and single worst thing cannot rate everything
# equally.
FORCED = [
    ("best_thing", "The single best thing about this submission, in one sentence, with "
                   "the specific evidence for it."),
    ("worst_thing", "The single weakest thing about it, in one sentence, with the "
                    "specific evidence. 'Nothing' is not an acceptable answer - name "
                    "the weakest thing even if the submission is strong."),
]

CEILING_GATE = """CEILING TEST IS THE GATE, and it runs before anything else.

Score the 24 stored submissions - free, no rebuilds. If more than ~30% hit the maximum
on a criterion, that criterion is still too easy and gets rewritten before the layer is
used for anything. A criterion everything passes and a criterion everything fails are
equally useless.

Validate on the REAL submissions, never on hand-written fixtures. I authored both the
fixtures and the criteria, so fixtures only confirm my own assumptions - that lesson is
already paid for twice (FINDINGS #21, and the sixteen play-bot false negatives)."""

if __name__ == "__main__":
    print(GRADED_SCALE, "\n")
    for cid, q, a in HARD_CRITERIA:
        print(f"{cid}\n  {q}")
        for k in sorted(a):
            print(f"    {k}: {a[k]}")
        print()
    print(CEILING_GATE)
