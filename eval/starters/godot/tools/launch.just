# Launch discipline, shared by all four starters. ONE source: `starters/_shared/launch.just`.
#
# ============================================================================
# THE RULE IS ABOUT A RESOURCE, NOT A LIST OF RECIPES.
#
#   ANY recipe that opens a WINDOW or an AUDIO DEVICE must go through the
#   variables below. Not "run". Not "demo". Any of them, including the one you
#   are about to add.
#
# This is stated as the resource because the previous attempt was stated as a
# list. Guards were added to the CAPTURE and TEST recipes -- `--audio-driver
# Dummy` on godot's render tests, `-disable-audio` on unity's batchmode editor
# invocations -- and both tasks were marked done. Those recipes were already
# offscreen and silent. The recipes that actually open a window on somebody's
# desktop with sound on their speakers, the `run` family, were untouched, and a
# Unity player window appeared in the foreground of the operator's machine with
# audio playing, twice.
#
# A guard that names the recipes someone enumerated does not cover the resource.
# ============================================================================
#
# SILENT_LAUNCH=1 (the default) means: do not open an audio device.
#
#   It suppresses audio in the LAUNCH PATH ONLY. It must never disable audio at
#   project level or strip audio from the build. The task asks the agent to
#   produce sound and the audio criteria grade it, by decoding the shipped clip
#   FILES with ffmpeg -- verified: `judge/audio.py` decodes to a pipe, and there
#   is no playback call anywhere in the grader. Silencing the launch therefore
#   changes no criterion. Silencing the PRODUCT would change the deliverable.
#
# NO_RAISE=1 (the default) means: do not take keyboard focus or raise above
# other windows. A visible window is fine. Stealing focus is not.
#
# WHAT THE GUARD DELIVERS: SILENCE, NOT "NO AUDIO DEVICE". Read this before
# concluding it failed.
#
#   A future reader will run `sample <pid>` on a guarded game and find CoreAudio
#   IO threads, because zeroing the listener does not close the device. MEASURED:
#   5 IO threads with the guard on and 5 with it off, in an audio-capable build.
#   The guard is still working — the harness logs
#   "SILENT LAUNCH ACTIVE - AudioListener.volume=0" and that is what carries the
#   claim.
#
#   Closing the device would need Unity's project-level "Disable Unity Audio",
#   which bakes into the build and would ship a DIFFERENT ARTIFACT than the agent
#   wrote. The requirement is that a launch must not disturb the operator, and a
#   CoreAudio client at zero volume takes no exclusive access and mixes normally,
#   so it costs them nothing. ARTIFACT FIDELITY OUTRANKS DEVICE CLEANLINESS, and
#   the stricter form was considered and rejected on that ground rather than
#   overlooked.
#
# AND THE INSTRUMENT'S OWN LIMIT, because a probe that cannot fail is not a probe:
#
#   `sample <pid> | grep -cE 'HALC_ProxyIOContext|com.apple.audio.IOThread|AQClient'`
#   is a VALID probe for "was an audio device opened" — validated both ways
#   against `afplay` of a silent WAV (5) and `sleep` (0), where `lsof` returned
#   1-2 in both arms and discriminated nothing.
#   It is NOT a probe for "is this silent": it returned 5 with the guard on and
#   off. Silence is asserted from the harness log, never from this number.
#
# WHY NOT ROUTE TO A CAPTURE-ONLY DEVICE, which is what was originally asked:
# macOS cannot bind one application to one output device natively, and no
# virtual device is installed here. Even with BlackHole present it needs a
# router. So it is not implementable today and is not pretended to be.
# `AUDIO_TARGET` exists so that when a device does arrive, this file changes and
# nothing else does.

# "none" = open no audio device at all. A device NAME here is the future case.
AUDIO_TARGET := env_var_or_default("STARTER_AUDIO_TARGET", "none")

# BOTH DEFAULT TO OFF, and that is what keeps this SCAFFOLDING rather than a change
# to the product.
#
# A human running `just run` gets the game exactly as its author wrote it: it makes
# sound and it raises. Only the evaluation harness sets these, in the trial
# environment (`wholegame.py`), where nobody is watching and the operator's machine
# is doing other work.
#
# The inverse - defaulting them ON - would mean the agent building the game never
# sees it behave the way a player will, and would make the guard a property of the
# artifact instead of a property of the launch. That is the same line that made
# Unity's `AudioListener.volume = 0` acceptable and project-level "Disable Unity
# Audio" not.
SILENT_LAUNCH := if AUDIO_TARGET == "none" { env_var_or_default("STARTER_SILENT_LAUNCH", "0") } else { "0" }

# 1 = launch without taking focus.
NO_RAISE := env_var_or_default("STARTER_NO_RAISE", "0")

# Per-stack mechanisms are NOT interchangeable and each was verified against the
# engine rather than against its documentation:
#
#   godot   --audio-driver Dummy        engine prints the active driver
#   unity   -starter-silent + a runtime hook in the harness (AudioListener.volume
#           = 0). NO FLAG EXISTS: `-disable-audio` is an EDITOR flag, is accepted
#           by the standalone player WITHOUT ERROR, and does nothing. It played
#           sound. An accepted-but-ignored flag is worse than an unsupported one
#           -- it looks like a working fix and no exit code can tell them apart.
#   rust    bevy's `AudioPlugin` is NOT ADDED when the variable is set. This row said
#           the opposite until 2026-08-23 -- "nothing to silence, no audio feature" --
#           and the feature is now on (task 26): `bevy_audio` is compiled in and
#           `AudioPlugin` opens the default output stream the moment it is added,
#           before any sound exists, so a pristine tree CAN take the device. Not
#           adding a plugin is a stronger guard than asking one to be quiet, and it is
#           the property `-disable-audio` lacks: there is nothing left to ignore the
#           request. The CAPTURE and TEST path disables it unconditionally
#           (crates/game/src/harness.rs) the way godot's render recipe passes
#           `--audio-driver Dummy`; measured, removing it took `just test-render` from
#           11.7 s to 8.5 s, which is what a device being opened six times costs.
#   ts      nothing to do: `just run` starts a dev SERVER. It opens no window and
#           no audio device; a browser opened by a human is outside the harness.
#
# Launch mode:
#   unity   open -g -j   (-g do not foreground, -j launch hidden). MEASURED:
#           plain `open` moves the frontmost-application ASN; `open -g -j` does
#           not, with the control run in both directions.
#   godot   --audio-driver Dummy plus the window flags in the render tests.
#   rust    NO MECHANISM EXISTS, and `just run` is REFUSED during trials because of
#           it. Measured, three escalating attempts: `Window { focused: false }` at
#           creation still raises; `set_minimized(true)` hides the window and leaves
#           the APPLICATION frontmost; adding `visible = false` changes nothing. The
#           frontmost app stayed `game` at 3s, 6s, 10s and 14s and returned only when
#           the process was killed. The fix would be `[NSApp deactivate]`, which Bevy
#           0.19 does not expose, and shell-side reactivation does not work in this
#           environment either. Bevy on macOS cannot be prevented from taking keyboard
#           focus, and cannot correct it from inside itself. That is a property, not a
#           defect in this file.
