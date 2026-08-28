"""Specialist aspects for the subjective layer.

One judge per aspect. Each judge sees the WHOLE FIELD for a game -- all eight
submissions, four stacks by two trials -- and must place them relative to one
another. A judge shown one submission can only ask "is this good?", which is the
question that saturated at 13/13 on 15 of 24 submissions in the first rubric.

Every aspect here must state a question whose answer could plausibly differ
across the field. An aspect that cannot separate a competent field is inert and
should be retired rather than re-tuned; see `JUDGING.md`.

TWO TASK CLASSES, ONE REGISTRY. Games and scenes are graded separately and their
scores are never pooled (`eval/SCENES.md`), so every aspect declares the class it
may be asked of in `Aspect.task_class`. The registry stays one dict because a
second dict is a second place a reader has to know about, and `docstat.py`'s
aspect census parses this one; `GAME_ASPECTS` and `SCENE_ASPECTS` are DERIVED from
it, never listed by hand. `applicability()` is the guard, and all 6 paths that reach a
graded task call it before anything is spent.

IT GUARDS DETERMINISTIC INSTRUMENTS TOO, which is why it is not called
`aspect_applicability`. "May this instrument be run against this task" is one question
whether the instrument is an LLM aspect or a play-bot, and the play-bot is the one that
fails silently: `evaluate.BOTS[task]` refuses a scene by raising `KeyError`, which is an
accident of a dict lookup rather than a design, and a dict that gained a scene key would
drive a bot at a scene with no player. `INSTRUMENTS` declares the class of every
non-aspect instrument, and `applicability()` answers for both registries.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, replace
from pathlib import Path


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
    #: The id of the aspect this one is the CONTROL for; `""` for a scored opinion.
    #:
    #: A control asks a scored aspect's question with one channel of evidence removed, so
    #: its answer is only meaningful AGAINST that aspect. Pooling it with the scored ones
    #: computes a mean over a population that is heterogeneous by construction (rule 4),
    #: and `field_ranks.assert_poolable` refuses to.
    #:
    #: THIS FIELD REPLACED ONE CALLED `diagnostic_only`, and the rename is the repair.
    #: That field was never set on any aspect and was read by no code, while `probe.py`
    #: and the three play bots carry a field of the SAME NAME holding CRITERION IDS - a
    #: different mechanism entirely. The collision was enough for `FUN_FRAMES`'s own
    #: comment to claim a guard that did not exist, and for a `grep diagnostic_only` to
    #: return twenty hits that all belonged to the other mechanism (task 90).
    control_for: str = ""
    #: `"game"` or `"scene"` - the TASK CLASS this aspect may be asked of.
    #:
    #: A scene has no player, so `fun` has no referent and `fun_frames` controls a
    #: question nothing asks; a game has no scene brief, so `fidelity` and `motion`
    #: have nothing to be faithful to. Scene and game scores are never pooled
    #: (`eval/SCENES.md`), and an aspect run against the wrong class produces eight
    #: confident numbers about a question that was not asked - the same shape as
    #: judging `fun` over a code-only pack, which `run_field` already refuses.
    #:
    #: `applicability()` is the guard, and it answers for `INSTRUMENTS` as well. It is
    #: called from `field.run_field`, `field.py pack`, `field_sweep.main` and the 3
    #: paths the runner reaches a grading instrument or a judge pack by, because the
    #: resource being protected is "a graded task" and it is reached by six paths.
    task_class: str = "game"
    #: WHY A CROSS-STACK RANKING OF THIS ASPECT IS MEANINGLESS; `""` if there is none.
    #:
    #: Not a boolean, for `control_for`'s reason: a flag says a bar exists and a reader
    #: still has to go and find out why, so the reason travels with the fact and is
    #: printed beside every figure `field_ranks.py` produces for the aspect.
    #:
    #: Two aspects carry one, for the SAME structural reason and not by coincidence:
    #: the judge can tell which stack it is looking at, so the ordering it returns is
    #: partly a statement about the stacks rather than about the submissions.
    #: `idiomatic` was barred on measurement (#53) and the bar has lived in prose in
    #: `JUDGING.md` and `RUBRIC.md` ever since; `framework_fluency` is barred by
    #: construction, because the question IS which engine's facilities appear in the
    #: source and naming the stack is therefore the measurement rather than a leak of it.
    #:
    #: WHAT THIS FIELD DOES. `field_ranks` reads it twice. Every figure printed for a
    #: barred aspect carries the reason and the per-stack means; and `assert_poolable`
    #: refuses to pool a barred aspect with any other, exactly as it refuses a control,
    #: because a pooled figure is a BETWEEN-STACK range and that is the one reading the
    #: bar withholds. The aspect's own per-aspect pair is still computed and printed -
    #: barring is not a refusal to measure, it is a refusal to rank across stacks.
    #:
    #: It was a declaration nothing acted on from task 135 until `tasks/146`: the bar was
    #: printed beside a pooled figure that contained the barred rounds, which documents a
    #: contradiction rather than removing it.
    cross_stack_bar: str = ""


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
    cross_stack_bar=(
        "the pack keeps its real file extensions, because you cannot ask whether a "
        "language was written like itself with the language taken out -- so this judge "
        "is told which stack each submission is. Measured consequence: its per-stack "
        "means were identical across two entirely different games (#53). Report the "
        "grades per stack; never read a rank across them."
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
#: It is a control, not a sixth opinion, and `control_for="fun"` below is what says so TO
#: CODE rather than to a reader. `field_ranks.assert_poolable` raises on any population that
#: mixes this aspect with another, so a pooled figure either excludes it or does not run;
#: `field_ranks.report` names, in its output, the aspects each pooled figure is over and the
#: rounds it left out. Until 2026-08-23 that guarantee lived only in this comment: the field
#: was called `diagnostic_only`, was never set, and was read by nothing (task 90, and see
#: `control_for` on `Aspect` for why the name itself was half the defect). The measurement
#: that closed it: `runs/wg-aspect-reliability` pooled 30 rounds of which 5 were this control.
FUN_FRAMES = replace(
    FUN,
    id="fun_frames",
    control_for="fun",
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

# =============================================================================
# SCENES. A second task class, `eval/SCENES.md`, and a different set of questions.
#
# A scene is a timed sequence with no player, so `fun` has no referent, `fun_frames`
# controls a question nothing asks, and `audio` has nothing to hear -- the scene
# prompts state in as many words that the scene has no sound. What is left that a
# script cannot already answer is what these three ask.
#
# `scene_probe.py` is tier 2 and carries the weight. Read its criteria before adding
# anything here: a tier-3 aspect that re-asks a question the probe answers
# deterministically is worse than absent, because it dresses a script's answer up as
# an opinion. The probe already measures parallax ordering, seam continuity, wheel
# speed, occlusion, the light ramp, water level under tilt, mass balance, refraction,
# fragment count and rest, seed pairing and reversal. None of the three below is one
# of those.
#
# NONE OF THEM HAS EVER MET A SUBMISSION. No scene has been built, so no scene field
# has been packed and no round has been run. They ship at tier-3 weight 0.00 like
# every other aspect, and `RUBRIC.md` records what would have to be measured before
# that could change.
# =============================================================================


# The scale for a scene's RESULT. Same shape and the same reason as `PLAY_SCALE`:
# "it works and is unremarkable" sits at 2, so a field where every submission
# renders something spreads instead of piling at the top. It differs from
# `PLAY_SCALE` only in having no player in it -- nobody plays a scene, so
# "would you want another go" is not a question that can be asked of one.
SCENE_SCALE = {
    0: "does not read as the sequence it was asked for -- what should be there is "
       "absent, or nothing about it changes across the strip",
    1: "the elements are present and the sequence happens, but it reads as a diagram "
       "of the idea rather than a rendering of it",
    2: "competent and unremarkable -- a working version of this scene",
    3: "convincing -- the parts hold together and the sequence is legible without "
       "being told what to look for",
    4: "you would show it to someone -- the craft is the point, not an afterthought",
}


#: WHAT THIS ASPECT IS MEASURED AGAINST, and why it is a file rather than the field.
#:
#: "Does this read as the scene it was asked for" needs what was asked for, and the pack
#: carries it: `field.SCENE_STATEMENTS`, written into every scene pack as `SCENE.md`. It
#: is one hand-written statement per scene, identical in all 8 submissions' packs, so it
#: separates nothing.
#:
#: THE RENDERED PROMPT IS NOT A CANDIDATE AND NEVER WAS. It exists per stack, and
#: `anonymise.find_stack_names` returns a stack token in every one of the 8 -- handing a
#: judge one would name the arm in its own evidence, which is the leak `neutralise` and
#: `blind_extensions` exist to close. `verify_blind.py --packs` gates the statement
#: instead, and `blurb_selftest.py` greps it with `tools/prompt_guard.py`'s closed lists
#: so that a criterion cannot reach the judge through it either.
#:
#: WHAT THE STATEMENT BOUGHT. Until 2026-08-25 the aspect recovered the subject from the
#: field of 8 and scored how completely each realised it, so it could find a submission
#: that omitted what 7 others drew and could NOT find one where all 8 missed the same
#: requirement -- the case a fidelity aspect exists for. Read against the statement, a
#: requirement no submission met is a finding about the field, and the notes below ask
#: for it in `field_note`.
FIDELITY = Aspect(
    id="fidelity",
    task_class="scene",
    title="Fidelity to the scene",
    question=(
        "Does this read as the scene it was asked for? `SCENE.md` in this directory "
        "states that scene. Judge how completely and how convincingly each submission "
        "realises it."
    ),
    anchors=SCENE_SCALE,
    sees="frames",
    evidence_rule=(
        "Name the frame and the region of it you are describing, and name the element "
        "you are looking for. 'Frame 0 shows no horizon anywhere, and six others do' "
        "is evidence; 'this one looks unfinished' is not."
    ),
    notes=(
        "You are looking at PNGs sampled at even intervals across one run: the first "
        "is the opening state, the last is late in the run. Read `SCENE.md` before you "
        "open a strip -- it states what every submission here was asked to build, in "
        "the same words for all of them -- and score each strip against it.\n"
        "Ask, in order: are the things the statement describes present at all; do they "
        "hold together as one scene rather than as separate objects sharing a frame; "
        "does the sequence go somewhere between the first frame and the last, or is "
        "the strip a set of views of one unchanging moment.\n"
        "Something the statement asks for that NO strip shows is a finding about the "
        "whole field, not a reason to leave every score where it is. Say so in "
        "`field_note` and score each submission on what it did do.\n"
        "Do not reward decoration and do not reward ambition you cannot see. A plain "
        "strip that clearly depicts the subject beats an elaborate one that does not. "
        "And do not infer from an absent frame: if the run produced fewer frames than "
        "the others, say the evidence is missing rather than scoring it down for it.\n"
        + FRAMES_BLIND_SPOT
    ),
)


MOTION = Aspect(
    id="motion",
    task_class="scene",
    title="Weight and easing of the motion",
    question=(
        "Does what moves in this strip move as though it had mass -- gathering speed, "
        "easing off, settling, overshooting and coming back -- or does it travel at "
        "one unchanging rate and stop dead?"
    ),
    anchors=SCENE_SCALE,
    sees="frames",
    evidence_rule=(
        "The frames are sampled at EVEN intervals, so the spacing between successive "
        "positions is the speed. Cite the frames you compared and say how the spacing "
        "changed across them. A claim about weight with no positions behind it is an "
        "opinion."
    ),
    notes=(
        "You have one kind of evidence: a strip of PNGs sampled at even intervals "
        "across one run. That even spacing is what makes this question answerable at "
        "all -- equal distance between successive positions is constant speed, "
        "widening spacing is acceleration, narrowing spacing is a slow-down, and a "
        "position that goes past its resting place and comes back is an overshoot.\n"
        "Judge the SHAPE of the movement, not its amount. A thing that crosses the "
        "frame quickly is not better than one that crosses it slowly; a thing that "
        "starts and stops abruptly at one unchanging rate is what this aspect is "
        "for.\n"
        "Where a strip cannot answer the question -- too few distinct positions, or "
        "nothing in it moves far enough to measure -- SAY SO and score on what you "
        "can see. An invented trajectory is worse than an absent one.\n"
        + FRAMES_BLIND_SPOT
    ),
)


#: THE UNBLINDABLE ONE, and it is unblindable BY CONSTRUCTION rather than by an
#: unclosed leak. The question is which of an engine's own facilities appear in the
#: source; naming the engine IS the measurement, not a leak of it. So there is nothing
#: to repair and no rewrite that would help -- `blind_language` here would delete the
#: evidence the aspect exists to read.
#:
#: `cross_stack_bar` below is what says that to code. It is the same wall `idiomatic`
#: hit and was barred on (#53), reached from the opposite direction: `idiomatic`'s
#: leak was measured and then declined as unclosable, this one is declared before the
#: first round is ever run.
FRAMEWORK_FLUENCY = Aspect(
    id="framework_fluency",
    task_class="scene",
    title="Use of the engine's own facilities",
    question=(
        "Did this submission reach for the facilities its engine or library already "
        "provides -- animation and tweening, physics and collision, particles, "
        "shaders and materials, the scene graph, post-processing -- or did it "
        "hand-roll equivalents in general-purpose code and drive them itself?"
    ),
    anchors=SCALE,
    evidence_rule=(
        "Cite the file and the specific API. Name the facility that was reached for, "
        "or the one that was available in this stack and was not used, and say what "
        "was written instead."
    ),
    cross_stack_bar=(
        "the question IS which of one engine's APIs appear in the source, so this "
        "judge is told which stack it is looking at by the evidence itself. Its "
        "ordering is therefore partly a statement about the stacks; report the grades "
        "per stack and never read a rank across them."
    ),
    notes=(
        "Score each submission against the facilities ITS OWN stack offers, never "
        "against another's. A stack with no built-in tweening is not worse for lacking "
        "one; what is comparable is HOW FLUENTLY each used what it had.\n"
        "Hand-rolling is not automatically worse and must not be scored as though it "
        "were. A facility reached for and misused, or reached for where it does not "
        "fit, is worse than a small purpose-written routine. What this aspect is "
        "looking for is a submission that re-implemented, badly and by hand, something "
        "its own stack already does well -- interpolation written as a per-frame "
        "position assignment where the engine has a tween, collision written as "
        "distance comparisons where the engine has a physics body, a particle effect "
        "written as a list of manually moved objects where the engine has an emitter.\n"
        "Say plainly where the evidence runs out. A facility can be used through a "
        "helper you cannot see from this pack, and 'I could not tell' is a better "
        "answer than a guess."
    ),
)


ASPECTS = {a.id: a for a in (IDIOMATIC, ARCHITECTURE, FUN, FUN_FRAMES, AUDIO, UX,
                             FIDELITY, MOTION, FRAMEWORK_FLUENCY)}

#: The scored opinions, and the controls, as two disjoint sets over `ASPECTS`.
#:
#: Derived, never listed by hand: a hand-written membership list is a second source of truth
#: that a new aspect silently falsifies, which is #38's shape. `aspects_selftest.py` pins the
#: three properties that make them usable - a control names a real aspect, a control does not
#: control a control, and the two sets partition `ASPECTS`.
SCORED_ASPECTS = tuple(i for i, a in ASPECTS.items() if not a.control_for)
CONTROL_ASPECTS = {i: a.control_for for i, a in ASPECTS.items() if a.control_for}


def is_control(aspect_id: str) -> bool:
    """True for a known control aspect. False for a scored one AND for an unknown id.

    An id this module has never heard of is not a control - it is UNMEASURABLE, and callers
    that pool must say so rather than treating "not a control" as "safe to pool". That is
    why `field_ranks.assert_poolable` asks about `ASPECTS` membership, not about this.
    """
    return bool(ASPECTS[aspect_id].control_for) if aspect_id in ASPECTS else False


#: The two task classes as disjoint sets over `ASPECTS`, and the barred ids, DERIVED.
#:
#: Same reason as `SCORED_ASPECTS` above: a hand-written membership list is a second
#: source of truth that the next aspect silently falsifies (#38). `aspects_selftest.py`
#: pins that these two partition `ASPECTS` and that every barred id is a real aspect.
GAME_ASPECTS = tuple(i for i, a in ASPECTS.items() if a.task_class == "game")
SCENE_ASPECTS = tuple(i for i, a in ASPECTS.items() if a.task_class == "scene")
CROSS_STACK_BARRED = {i: a.cross_stack_bar for i, a in ASPECTS.items()
                      if a.cross_stack_bar}

#: Task ids whose class this module can state, read from the suites that define them.
#:
#: `wholegame_prompts.TASKS` and `scene_prompts.SCENES` are the only places a task
#: exists, so they are the address (rule 12). The import is lazy and cached: every
#: consumer of `ASPECTS` would otherwise take a dependency on `eval/suites/` to read a
#: dataclass.
_TASK_CLASSES: dict[str, str] | None = None

#: The id-shape fallback, for a task id the suites do not define.
#:
#: Every real task id is `g<N>_name` or `s<N>_name`, and the selftest asserts this
#: agrees with the suites on all 6 of them -- so it is a CORROBORATED second channel
#: rather than an invented rule. It exists because the judge fixtures grade a synthetic
#: `g9_probe` field that no suite defines, and a guard that refuses every fixture is a
#: guard that gets removed.
_ID_SHAPE = re.compile(r"^(?P<klass>[gs])\d+_")
_SHAPE_CLASS = {"g": "game", "s": "scene"}

UNKNOWN_TASK = "unknown"


def _task_classes() -> dict[str, str]:
    """Every task id the suites define, mapped to its class. Imported once, then cached.

    The import is deferred to the first call so that reading a dataclass out of this
    module does not drag `eval/suites/` in behind it.
    """
    global _TASK_CLASSES
    if _TASK_CLASSES is None:
        suites = Path(__file__).resolve().parent.parent / "suites"
        sys.path.insert(0, str(suites))
        import scene_prompts
        import wholegame_prompts
        _TASK_CLASSES = {**{t: "game" for t in wholegame_prompts.TASKS},
                         **{t: "scene" for t in scene_prompts.SCENES}}
    return _TASK_CLASSES


def task_class(task_id: str) -> str:
    """`"game"`, `"scene"` or `UNKNOWN_TASK` for one task id.

    Three-valued on purpose. `prompt_guard.py` reads "not a scene" as "a game", which
    is safe there because it only ever walks ids the suites define; anything guarding a
    launch has to be able to say it does not know, or an id nobody recognises reads as
    a game and every scene aspect refuses it for the wrong reason.
    """
    known = _task_classes().get(task_id)
    if known:
        return known
    m = _ID_SHAPE.match(task_id or "")
    return _SHAPE_CLASS[m.group("klass")] if m else UNKNOWN_TASK


#: NON-ASPECT INSTRUMENTS, and the ONE task class each may be run against.
#:
#: An aspect declares its class on `Aspect.task_class`; a play-bot, the scene probe and
#: the retired generalist judge have no `Aspect` to declare it on, and until 2026-08-25
#: nothing declared it for them. What stood in for a guard was `evaluate.BOTS[task]`
#: raising `KeyError` -- a refusal that exists only because the dict happens to hold four
#: keys, and that disappears the moment anyone adds a fifth. `judge.py` had not even
#: that: `GAME_BRIEF.get(game, "(unknown game)")` hands a scene to 13 criteria written
#: about games and answers every one of them.
#:
#: These are ids, not modules, for the reason `Aspect.control_for` is a sentence rather
#: than a flag: the thing that must be comparable across the two registries is the CLASS,
#: and a module reference would make this table a second import graph.
INSTRUMENTS: dict[str, str] = {
    #: tier 2 for a game -- `judge/bot_*.py`, driven by `probe.drive`.
    "playbot": "game",
    #: tier 2 for a scene -- `judge/scene_probe.py`. Same weight, different instrument.
    "scene_probe": "scene",
    #: the RETIRED 13-criterion generalist judge, `judge/judge.py`, opt-in behind
    #: `--with-legacy-judge`. Every one of its criteria is written about a game.
    "legacy_judge": "game",
}


def declared_class(instrument_id: str,
                   registry: dict[str, Aspect] | None = None) -> str | None:
    """The task class `instrument_id` may be run against, or None if it declares none."""
    registry = ASPECTS if registry is None else registry
    aspect = registry.get(instrument_id)
    if aspect is not None:
        return aspect.task_class
    return INSTRUMENTS.get(instrument_id)


def applicability(instrument_id: str, task_id: str,
                  registry: dict[str, Aspect] | None = None) -> str | None:
    """`None` if this instrument may be run against this task; otherwise why it may not.

    THE GUARD FOR "asked only of scenes", called from all 6 paths that reach the
    resource rather than from whichever one was in front of the author (rule 13):
    `field.py pack`, `field.run_field`, `field_sweep.main`, and the 3 by which the RUNNER
    reaches a grading instrument or a judge pack -- `evaluate.evaluate`'s up-front class
    resolution, its tier-2 dispatch and its legacy tier-3 call.
    `eval/tools/scene_runner_control.py --paths` prints 6 routes, not just these 3.
    P2-P4 are the runner paths above, each guarded by this function.
    `wholegame.select_tasks` guards P1, and argparse `choices` guards P5 and P6 at the
    CLI surface -- mechanisms that never call this function.

    `instrument_id` is an aspect id or an `INSTRUMENTS` id. Both declare a task class
    and the question asked of them is identical, so there is one guard rather than two
    that can drift apart.

    Fails closed on an id it cannot classify: a field is one judge invocation over all
    8 submissions, and "I do not know what this task is" is not a reason to make it.

    `registry` exists so `aspects_selftest.py` can drive this function with a mutated
    aspect set. Callers in the harness pass nothing and get `ASPECTS`.
    """
    registry = ASPECTS if registry is None else registry
    want = declared_class(instrument_id, registry)
    if want is None:
        return (f"{instrument_id!r} is not an aspect and not a declared instrument. "
                f"Aspects: {sorted(registry)}; instruments: {sorted(INSTRUMENTS)}")
    kind = "aspect" if instrument_id in registry else "instrument"
    klass = task_class(task_id)
    if klass == UNKNOWN_TASK:
        return (f"{task_id!r} is in neither eval/suites/wholegame_prompts.py nor "
                f"eval/suites/scene_prompts.py and is not shaped like a task id, so "
                f"its class cannot be established. Refusing rather than assuming: "
                f"{instrument_id!r} is asked only of {want}s.")
    if klass != want:
        peers = sorted(i for i, a in registry.items() if a.task_class == want)
        peers += sorted(i for i, c in INSTRUMENTS.items() if c == want)
        return (f"{instrument_id!r} is a {want} {kind} and {task_id!r} is a "
                f"{klass}. Scene and game scores are never pooled (eval/SCENES.md), "
                f"and an instrument run against the wrong class returns confident "
                f"numbers about a question nobody asked. {want}s here: {peers}")
    return None
