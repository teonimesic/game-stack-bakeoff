#!/usr/bin/env python3
"""Criteria for the design judge: aesthetics and game feel.

WHY THIS TIER EXISTS WHEN THE CODE JUDGE WAS DROPPED
The code judge asked 13 binary questions about code hygiene that the deterministic
tiers largely already answered, so removing it cost nothing. This is the opposite case:
the play-bot can prove the ball bounces and cannot tell you whether the game looks good
or feels good to play. No deterministic tier will ever cover that. If it is measured at
all, a subjective judge is the only instrument available.

GRADED, NOT BINARY. Binary was right for "is the placeholder gone" - a fact with an
answer. It is wrong for "does this look coherent", where all the information is in the
middle and a yes/no throws it away. Each level below has an ANCHOR describing what that
score looks like, so the scale means the same thing across submissions and across runs.

WHAT IT SEES
Not source code. The artifact as a player meets it: rendered frames in order across a
real play session, plus play-bot telemetry as evidence of TUNING rather than
correctness - pacing, time-to-first-action, rally lengths, time-to-score, whether
anything ever stalls.

NO WEIGHT until it separates a tuned fixture from a detuned one by more than its own
run-to-run noise. Assigning a weight before that number exists is exactly the error
that made the code judge worthless at 0.10.
"""

SCALE = """0 = absent      the property is simply not present
1 = poor        present but actively works against the player
2 = adequate    present and inoffensive; does its job, no more
3 = good        deliberate and effective; a player would notice if it were removed
4 = excellent   considered; several elements reinforcing each other"""

DESIGN_CRITERIA: list[tuple[str, str, dict[int, str]]] = [
    ("look.coherence",
     "Do the frames read as one deliberate scene rather than assorted debug shapes?",
     {0: "no discernible scene; shapes on a void",
      1: "elements clash in scale or colour; looks accidental",
      2: "consistent palette and scale; unremarkable but unified",
      3: "a considered look - background, play area and entities clearly belong together",
      4: "a distinct visual identity a player would recognise again"}),
    ("look.readability",
     "Can the game's state be read at a glance from a single frame - where the player "
     "is, what matters, what is about to happen?",
     {0: "cannot tell what is happening",
      1: "important elements blend into the background or each other",
      2: "the main entities are distinguishable",
      3: "clear visual hierarchy; the eye goes to what matters",
      4: "state is unambiguous at a glance, including secondary information"}),
    ("look.feedback",
     "Do the game's important moments produce a visible on-screen response - scoring, "
     "clearing, being hit, ending?",
     {0: "nothing changes visibly when anything happens",
      1: "only a number changes somewhere",
      2: "important events have a clear visible consequence",
      3: "events are announced legibly and promptly",
      4: "layered feedback - the event is unmissable without being noisy"}),
    ("feel.pacing",
     "From the telemetry, is the game paced so a player has time to act and a reason "
     "to keep acting?",
     {0: "unplayable - nothing happens, or everything happens instantly",
      1: "badly tuned: far too fast to react to, or so slow it stalls",
      2: "playable; no obvious tuning problem",
      3: "well judged - rounds resolve in a satisfying span, difficulty is felt",
      4: "deliberate rhythm, with escalation or variation over a session"}),
    ("feel.completeness",
     "Is this a finished game rather than a working mechanic - start state, end state, "
     "score, and whatever else a player expects to be there?",
     {0: "a mechanic in a window",
      1: "the core loop runs but nothing frames it",
      2: "the expected states exist",
      3: "the whole loop is present and legible without explanation",
      4: "finished feeling; nothing obviously missing"}),
]

# The measurement that decides whether this tier ships. Two fixtures differing ONLY in
# the judged property - same game, same mechanics, same tests green.
FIXTURE_PAIR = {
    "tuned":   "legible palette, visible score, sane ball speed, visible event feedback",
    "detuned": "ball ~3x too fast, no event feedback, low-contrast colours, no score",
}

FALSIFIER = """If the design judge cannot separate `tuned` from `detuned` by more than
the spread across repeated judgings of the SAME fixture, it measures nothing and does
not ship. A difference smaller than the instrument's own variance is not a difference.

Also required before it can be trusted, all from FINDINGS #21:
  * validate on BORDERLINE artifacts, not only the two extremes - a gorgeous and a
    broken submission will both judge unanimously and prove nothing
  * report run-to-run variance on identical input SEPARATELY from forward/reverse
    instability; subjective criteria are expected to be noisier, and the question is
    whether they discriminate despite the noise
  * check every criterion is EXERCISED - one answered identically every run because the
    question never arose has not been tested
  * the fixture pair is authored by the same person as the criteria, so a positive
    result means "it detects these specific defects", not "it judges design". The 24
    matrix submissions are the artifacts nobody planted, and generalisation must be
    shown there."""

if __name__ == "__main__":
    print(SCALE, "\n")
    for cid, q, anchors in DESIGN_CRITERIA:
        print(f"{cid}\n  {q}")
        for lvl in sorted(anchors):
            print(f"    {lvl}: {anchors[lvl]}")
        print()
    print(FALSIFIER)
