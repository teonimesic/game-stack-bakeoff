"""Specialist aspects for the subjective layer.

One judge per aspect. Each judge sees the WHOLE FIELD for a game -- all eight
submissions, four stacks by two trials -- and must place them relative to one
another. A judge shown one submission can only ask "is this good?", which is the
question that saturated at 13/13 on 15 of 24 submissions in the first rubric.

Every aspect here must state a question whose answer could plausibly differ
across the field. An aspect that cannot separate a competent field is inert and
should be retired rather than re-tuned; see `JUDGING.md`.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace


@dataclass(frozen=True)
class Aspect:
    id: str
    title: str
    question: str
    anchors: dict[int, str]
    evidence_rule: str
    sees: str = "code"
    #: Normalise file extensions in this aspect's pack.
    #:
    #: `anonymise.py` flattens filenames to `sim/01.gd`, `view/03.rs`, `view/06.cs` and
    #: KEEPS THE EXTENSION - one per stack, uniquely identifying, in every file the
    #: judge reads, while the brief tells it "you are not told which is which".
    #: Measured consequence: `idiomatic`'s per-stack means were identical across two
    #: entirely different games (FINDINGS #53).
    #:
    #: `idiomatic` MUST keep it - you cannot ask whether Rust was written like Rust
    #: without saying it is Rust, and that aspect is therefore within-stack only, which
    #: is a result rather than a defect to engineer away. `architecture` asks a
    #: structural question that does not need the language, so it should not be handed
    #: it.
    blind_language: bool = False
    notes: str = ""
    diagnostic_only: frozenset[str] = field(default_factory=frozenset)


# The scale is shared. It deliberately places "competent, works, unremarkable"
# at 2 so that a uniformly-working field spreads instead of piling at the top.
SCALE = {
    0: "actively wrong for this stack -- fights the engine or the language",
    1: "works, but reads as written by someone who does not know this stack",
    2: "competent and unremarkable -- a working hobby project",
    3: "clearly written by someone fluent in this stack",
    4: "exemplary -- the code a maintainer of this stack would show off",
}


IDIOMATIC = Aspect(
    id="idiomatic",
    title="Idiomatic stack use",
    question=(
        "Does this submission use its own stack the way a fluent practitioner of "
        "THAT stack would, or does it use the stack as a generic host for code "
        "that could have been written anywhere?"
    ),
    anchors=SCALE,
    evidence_rule=(
        "Cite specific file paths and constructs. Name the idiom that was used "
        "well, or the one that was available and was not used."
    ),
    notes=(
        "Score each submission against the idioms of ITS OWN stack, never against "
        "another stack's idioms. Rust is not worse for lacking a MonoBehaviour and "
        "C# is not worse for lacking a borrow checker. The comparison across stacks "
        "is of HOW FLUENTLY each used what it had -- that, and only that, is "
        "comparable. Things a fluent practitioner would reach for, per stack:\n"
        "  - Rust/Bevy: systems, queries, resources, components, iterator chains, "
        "the type system doing work; NOT god-structs, index loops, unwrap-everywhere.\n"
        "  - Unity/C#: the component model, serialised fields, ScriptableObjects, "
        "the right update callback; NOT one giant MonoBehaviour, GameObject.Find in "
        "hot paths, LINQ allocation per frame.\n"
        "  - TypeScript/three.js: the type system, object/geometry reuse, disposal, "
        "scene-graph structure; NOT `any` everywhere, per-frame allocation, "
        "re-creating materials each draw.\n"
        "  - Godot: nodes and the scene tree, signals, `@export`, `_process` vs "
        "`_physics_process`; NOT one monolithic script driving everything by path."
    ),
)


ARCHITECTURE = Aspect(
    blind_language=True,
    id="architecture",
    title="Architecture and extensibility",
    question=(
        "If you were handed this codebase tomorrow and asked to add one substantial "
        "feature -- a second enemy type, a new piece shape, a power-up -- how much of "
        "the existing code would you have to change, and how much would you merely "
        "extend? Judge the shape of the code, not its fluency in the stack."
    ),
    anchors=SCALE,
    evidence_rule=(
        "Name the specific change you imagined, then the files and functions it would "
        "force you to touch. An architecture claim with no worked example is an opinion."
    ),
    notes=(
        "This is deliberately NOT a question about idiomatic style. A submission can be "
        "written in perfect idiom and still hard-code every entity, or be stylistically "
        "plain and cleanly extensible. Look for: where new cases must be registered, "
        "whether adding one requires edits in several places at once, whether data and "
        "behaviour are separable, whether the tick pipeline declares what it touches. "
        "Ignore naming, formatting and language-specific flourish entirely."
    ),
)



#: THE FRAMES CHANNEL'S BLIND SPOT, stated to every aspect that reads frames.
#:
#: Measured 2026-08-23 (task 68, FINDINGS #107): the four arms' `just film` harnesses
#: are not equivalent in WHAT A FRAME CAN CONTAIN. One steps the whole app per tick, so
#: its renderer observes every tick of the run; the other three advance the simulation
#: to the sampled tick with no renderer attached and draw once, so their renderer is
#: shown exactly ONE tick per PNG. A probe painting one cell per observed tick read
#: 1, 1, 1 at ticks 8/60/240 in three arms and 9, 32, 32 in the fourth, with a positive
#: control reaching 32 in every arm.
#:
#: Two rules govern the wording, and both are load-bearing:
#:
#: 1. **It must not name or count the arms.** The judge is blinded to which submission
#:    is which stack (`verify_blind.py`, FINDINGS #32). "In some of them" leaks nothing;
#:    "in three of the four" hands over the size of the partition.
#: 2. **It must be BYTE-IDENTICAL in `fun` and `fun_frames`.** `fun_frames` is `fun`'s
#:    control with the telemetry withheld, and a control whose briefing differs from its
#:    treatment's is not a control. It is defined once here for that reason -- do not
#:    inline a copy into either.
FRAMES_BLIND_SPOT = (
    "THE FRAMES HAVE A KNOWN BLIND SPOT, AND IT BELONGS TO THE CAPTURE HARNESS RATHER "
    "THAN TO THE SUBMISSION. The harnesses that produce these strips are not all "
    "equivalent: in some of them the simulation is advanced to the sampled moment with "
    "no renderer attached and the picture is then drawn once, so presentation state "
    "that BUILDS UP over the moments in between -- a motion trail, a particle burst, a "
    "screen shake, a hit flash that fades, a tween still in flight -- cannot reach the "
    "PNG at all. It is structurally absent, and it looks exactly like a submission that "
    "never wrote one.\n"
    "So the ABSENCE of an accumulating effect is not evidence that the submission lacks "
    "one, and its PRESENCE is partly a property of the harness. Neither credit nor "
    "penalise it, and do not build a ranking on it. Judge what the frames DO show -- "
    "layout, legibility, what is on screen, and what visibly changes between the first "
    "frame of the strip and the last."
)


# The scale for aspects about the RESULT rather than the code. Same shape, same
# reason: "it works and is unremarkable" sits at 2, so a field where everything
# works spreads instead of piling at the top.
PLAY_SCALE = {
    0: "a player would stop within a minute -- broken pacing, no challenge, or no "
       "way to tell what is happening",
    1: "playable but flat -- the mechanics run and nothing about them invites a "
       "second go",
    2: "competent and unremarkable -- a working version of this game",
    3: "genuinely engaging -- pacing, feedback and difficulty support each other",
    4: "you would show it to someone -- the tuning and presentation are the point, "
       "not an afterthought",
}


FUN = Aspect(
    id="fun",
    title="Gameplay and fun",
    question=(
        "Playing this, would you want another go? Judge the PACING and the CHALLENGE: "
        "does the game give the player something to do that gets harder, does it tell "
        "them what just happened, does anything stall, and is the difficulty curve "
        "real rather than nominal?"
    ),
    anchors=PLAY_SCALE,
    sees="frames+telemetry",
    evidence_rule=(
        "Quote the telemetry numbers you used -- interval medians, seconds between "
        "points, longest quiet stretch, events per second -- and name the frames you "
        "looked at. A pacing claim with no number attached is an opinion."
    ),
    notes=(
        "You have two kinds of evidence and they answer different questions.\n"
        "  - `telemetry.json` is measured from a real driven run of THIS submission: "
        "how often things happen, how long the gaps are, whether the run ever goes "
        "quiet, how long a round lasts. This is the pacing evidence.\n"
        "  - `frames/` is a strip of frames sampled evenly across one run. This is the "
        "readability evidence: can you tell what is happening, is progress visible.\n"
        "Every submission here passes its correctness checks, so 'the mechanics work' "
        "separates nothing and must not earn a point. What separates them is whether "
        "the numbers describe a game with a rhythm: a long quiet stretch, a first "
        "event that never arrives, an interval that never changes as the run goes on, "
        "or a round that ends in three seconds are all real defects that correctness "
        "checks cannot see.\n"
        "Do not reward mechanical richness for its own sake. A game with six systems "
        "and no rhythm is worse than one with two and a good one.\n"
        + FRAMES_BLIND_SPOT
    ),
)


AUDIO = Aspect(
    id="audio",
    title="Audio design",
    question=(
        "Does the sound suit this game and this moment? Judge the MUSIC's fit and the "
        "sound effects' readability: could a player tell these events apart by ear, is "
        "anything harsh, repetitive or fatiguing over a few minutes of play?"
    ),
    anchors=PLAY_SCALE,
    sees="audio",
    evidence_rule=(
        "Name the specific cue and the specific property -- its duration, its "
        "brightness, how close it sits to another cue. Refer to the measured numbers "
        "in `audio.json`; do not invent acoustic properties you cannot hear."
    ),
    notes=(
        "The mechanical half of audio is already graded deterministically: whether the "
        "manifest is complete, whether the files decode, whether they are silent, "
        "whether they are the same clip under different names, whether the music is "
        "long enough to loop. NONE of that is your question and repeating it scores "
        "nothing.\n"
        "Your question is what is left: fit and readability. A set of five technically "
        "distinct clips that are all the same bright square-wave blip is worse than "
        "three well-chosen ones. A four-second music loop with an audible seam is worse "
        "than a plainer one that loops cleanly.\n"
        "You cannot hear the files. You are given measured descriptions -- duration, "
        "RMS, peak, and a coarse spectral profile per clip -- plus the source that "
        "triggers them. Reason from those and from how the cues relate to the events "
        "they mark, and say plainly where the evidence runs out."
    ),
)



UX = Aspect(
    id="ux",
    title="Presentation and onboarding",
    question=(
        "Could someone who has never seen this game work out what to do, see their "
        "progress while playing, and tell when it has ended -- from the screen alone? "
        "Judge what the frames COMMUNICATE, not whether they are pretty."
    ),
    anchors=PLAY_SCALE,
    sees="frames",
    evidence_rule=(
        "Name the frame and the region of it you are describing. 'Frame 0 has no "
        "instruction anywhere' is evidence; 'the UI is weak' is not."
    ),
    notes=(
        "You are looking at PNGs sampled evenly across one run: the first is the "
        "opening state, the last is late in the run. Everything the player sees is in "
        "these pixels -- there is no second display, no console output and no manual.\n"
        "Ask, in order: does the first frame tell a newcomer anything about what to do; "
        "is the score or progress visible while playing and does it change; is the "
        "state of play legible at a glance, or does it take effort to work out what is "
        "happening; is there any end state.\n"
        "Do not reward decoration. A plain frame that says exactly what is going on "
        "beats an elaborate one that does not. And do not infer from an absent frame: "
        "if the run never reached an end state, say the evidence is missing rather than "
        "scoring the submission down for it.\n"
        + FRAMES_BLIND_SPOT
    ),
)


#: THE CONTROL FOR `fun`, and it is the experiment `fun`'s own result requires.
#:
#: `fun` sees `frames+telemetry`. After the #52 repair its scores track the pacing numbers
#: (quiet stretch -0.63, events/second +0.51..+0.77 across both orders) - but a livelier
#: game also LOOKS livelier in 12 PNGs, so the correlation cannot say whether the judge read
#: the telemetry or the pictures. This aspect asks the identical question with the telemetry
#: WITHHELD.
#:
#:   rankings agree  -> the telemetry contributed nothing; `fun` is `ux` with extra evidence
#:   rankings differ -> the telemetry is doing work, and `fun`'s pacing claim has support
#:
#: It is a control, not a sixth opinion. It must never be pooled with the other five, and it
#: is `diagnostic_only` so no aggregate can absorb it by accident.
FUN_FRAMES = replace(
    FUN,
    id="fun_frames",
    title="Gameplay and fun (frames only - CONTROL for `fun`)",
    sees="frames",
    evidence_rule=(
        # DO NOT SAY WHAT WAS WITHHELD. `ux` reads frames only and its brief never
        # mentions telemetry; this one must read the same way, or the judge is told it
        # is being controlled. It cannot fake agreement with `fun` - it does not know
        # what the telemetry said - but a brief that announces an absence invites the
        # judge to reason about the absence instead of the frames.
        "Name the frames you looked at and say what in them you are reading. If a claim "
        "needs a number these frames cannot give you, say you cannot make it rather "
        "than estimating one from the pictures."
    ),
    # THE NOTES MUST BE OVERRIDDEN TOO, not just `sees`.
    #
    # `replace()` copies everything not named, and FUN's notes describe `telemetry.json`
    # at length. Building the pack and diffing it against the brief caught it: the pack
    # had 96 files and no telemetry, while the brief still said "telemetry.json is
    # measured from a real driven run of THIS submission".
    #
    # That is not cosmetic. A control whose briefing announces the evidence it withheld
    # tells the judge something was taken away, and a judge that knows it is being
    # controlled is not a control. It is also the pack-integrity rule one level up: an
    # aspect must not PROMISE evidence its pack does not carry, exactly as it must not
    # silently score a field that lacks it.
    notes=(
        "You have one kind of evidence: `frames/`, a strip sampled evenly across one "
        "real run of this submission. Read it for rhythm and readability - can you tell "
        "what is happening, does the state visibly change across the strip, is there "
        "any sign of progress or escalation between the first frame and the last.\n"
        "Every submission here passes its correctness checks, so 'the mechanics work' "
        "separates nothing and must not earn a point.\n"
        "Where a frame strip cannot answer a pacing question, SAY SO and score on what "
        "you can see. An invented interval is worse than an absent one.\n"
        # BYTE-IDENTICAL to `fun`'s copy, by construction. See FRAMES_BLIND_SPOT.
        + FRAMES_BLIND_SPOT
    ),
)

ASPECTS = {a.id: a for a in (IDIOMATIC, ARCHITECTURE, FUN, FUN_FRAMES, AUDIO, UX)}
