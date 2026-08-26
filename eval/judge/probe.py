#!/usr/bin/env python3
"""Drive a submitted game through the probe protocol.

This is the SCRIPTED PLAY-BOT TIER. It is where most of the gameplay signal comes
from, because it is deterministic and reproducible, unlike anything a model can tell
you from looking at frames.

The protocol is deliberately language-agnostic: `just probe SEED` is a long-lived
headless process that reads one JSON input object per line on stdin and writes one JSON
trace line per tick on stdout. So one Python bot drives Rust, TypeScript, Unity and
Godot submissions identically, and the play-bot assertions cannot accidentally be
easier on one stack than another.

FAIL CLOSED. Every failure mode here - the recipe missing, the process dying, stdout
polluted, a timeout, a malformed line - scores the criteria FALSE with a recorded
reason. It never scores them "skipped" or "not applicable". A submission that cannot
be driven has not demonstrated gameplay, and the whole point of this file is that a
broken game scores near zero rather than silently scoring nothing.
"""

from __future__ import annotations

import hashlib
import json
import os
import queue
import shutil
import signal
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

try:                                   # POSIX only; absent on Windows
    import fcntl
except ImportError:                    # pragma: no cover - not a supported platform
    fcntl = None  # type: ignore[assignment]


class ProbeError(RuntimeError):
    """The submission could not be driven. Normally a FALSE, never a silent skip.

    `lock_conflict` marks the ONE failure mode that says nothing whatsoever about the
    submission: the engine refused to open a second session on a project a previous
    session still holds. That is a property of the engine and of this harness, and it
    can only occur on the stacks that take a project-wide lock - so scoring it FALSE
    deducts from one arm of a four-way comparison and from no other. That is bias, not
    noise (FINDINGS #25), and it is the single defect class this file exists to prevent.

    Callers turn `lock_conflict` into `Criterion(scored=False)`: measured, reported,
    and excluded from the score, exactly as `layer.clears` already is.
    """

    def __init__(self, message: str, *, lock_conflict: bool = False) -> None:
        super().__init__(message)
        self.lock_conflict = lock_conflict


@dataclass
class Tick:
    tick: int
    hash: str
    state: dict[str, Any]
    events: list[str]
    raw: str = ""

    @classmethod
    def parse(cls, line: str) -> "Tick":
        try:
            d = json.loads(line)
        except json.JSONDecodeError as e:
            raise ProbeError(f"trace line is not JSON: {line[:200]!r} ({e})") from e
        if not isinstance(d, dict):
            raise ProbeError(f"trace line is not a JSON object: {line[:200]!r}")
        for key in ("tick", "hash", "state", "events"):
            if key not in d:
                raise ProbeError(f"trace line missing {key!r}: {line[:200]!r}")
        if not isinstance(d["state"], dict):
            raise ProbeError("trace line 'state' is not an object")
        if not isinstance(d["events"], list):
            raise ProbeError("trace line 'events' is not an array")
        return cls(int(d["tick"]), str(d["hash"]), d["state"],
                   [str(e) for e in d["events"]], raw=line)


# One live probe per repository, enforced process-wide. See ProbeSession._claim_repo.
_SESSION_GUARD = threading.RLock()
_ACTIVE: dict[tuple[str, int], "ProbeSession"] = {}
_REPO_LOCKS: dict[str, threading.Lock] = {}


def _repo_key(repo: Path) -> str:
    try:
        return str(Path(repo).resolve())
    except OSError:
        return str(repo)


def _repo_lock(key: str) -> threading.Lock:
    with _SESSION_GUARD:
        return _REPO_LOCKS.setdefault(key, threading.Lock())


@dataclass
class ProbeSession:
    """One `just probe SEED` process, driven tick by tick.

    Use as a context manager. `step(inputs)` sends one line and returns one Tick.

    At most one session per repository is alive at a time, process-wide - see
    `_claim_repo`. That is not tidiness: sixteen adjudicated criterion failures came
    from sibling sessions opened while the previous one was still running.
    """

    repo: Path
    seed: int = 7
    # Wall-clock budget for the WHOLE session. Unity pays ~4 s of editor start-up
    # before the header line, so the default is generous; the per-line timeout is
    # what actually catches a hung game.
    startup_timeout_s: float = 120.0
    step_timeout_s: float = 20.0
    total_timeout_s: float = 900.0
    env: dict[str, str] | None = None

    #: How long to wait for another session on the SAME repository to finish before
    #: starting anyway. Generous: a Unity session that is closing pays editor shutdown.
    lock_wait_s: float = 300.0

    proc: subprocess.Popen | None = field(default=None, init=False)
    _q: "queue.Queue[str | None]" = field(default_factory=queue.Queue, init=False)
    _reader: threading.Thread | None = field(default=None, init=False)
    _stderr_tail: list[str] = field(default_factory=list, init=False)
    _notes: list[str] = field(default_factory=list, init=False)
    _t0: float = field(default=0.0, init=False)
    history: list[Tick] = field(default_factory=list, init=False)
    ticks_sent: int = field(default=0, init=False)

    _key: str = field(default="", init=False)
    _claimed: bool = field(default=False, init=False)
    _repo_lock_held: bool = field(default=False, init=False)
    _flock_fd: int | None = field(default=None, init=False)
    superseded: bool = field(default=False, init=False)

    # -- lifecycle ---------------------------------------------------------- #

    def __enter__(self) -> "ProbeSession":
        self.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def start(self, attempts: int = 4) -> Tick:
        """Start the probe, retrying while a previous session still holds a lock."""
        last: ProbeError | None = None
        for attempt in range(1, attempts + 1):
            try:
                return self._start_once()
            except ProbeError as e:
                last = e
                if not self._looks_like_lock_conflict(e):
                    raise
                self._note(f"[probe-lock] start attempt {attempt}/{attempts} refused "
                           f"by what reads as a project lock; retrying")
                self.close()
                time.sleep(min(20.0, 4.0 * attempt))
        assert last is not None
        # Every attempt was refused with a project-lock signature. The submission has
        # not been measured, so callers must not score this as a failure - see
        # ProbeError's docstring and `unusable_criteria`.
        raise ProbeError(
            f"probe never started after {attempts} attempts, every one refused with a "
            f"project-lock signature: {last}", lock_conflict=True)

    @classmethod
    def _looks_like_lock_conflict(cls, err: BaseException) -> bool:
        """Only the CHILD's own output may vote. Harness notes are excluded on purpose:
        a note containing the word "lock" would otherwise make every later failure look
        like a lock conflict, which would turn fail-closed into fail-open."""
        msg = str(err).lower()
        return any(h in msg for h in cls.LOCK_HINTS)

    def _start_once(self) -> Tick:
        if shutil.which("just") is None:
            raise ProbeError("`just` is not on PATH")
        env = dict(os.environ)
        if self.env:
            env.update(self.env)
        self._claim_repo()
        # A fresh queue per attempt. The previous attempt's reader thread owns the old
        # one and will push its EOF sentinel into it after this call returns; reusing
        # the queue would hand that stale `None` to the NEW session's first read and
        # report the new probe as having exited immediately.
        self._q = queue.Queue()
        self._stderr_tail = []
        self._t0 = time.monotonic()
        try:
            self.proc = subprocess.Popen(
                ["just", "probe", str(self.seed)],
                cwd=self.repo,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=env,
                start_new_session=True,  # so we can kill the whole group
            )
        except OSError as e:
            raise ProbeError(f"could not start `just probe`: {e}") from e

        self._reader = threading.Thread(
            target=self._pump_stdout, args=(self.proc, self._q), daemon=True)
        self._reader.start()
        threading.Thread(target=self._pump_stderr, args=(self.proc, self._stderr_tail),
                         daemon=True).start()

        header = self._read_line(self.startup_timeout_s, "waiting for the tick-0 header")
        return self._finish_start(header)

    # Engines that take a project-wide lock (Unity refuses a second batchmode process
    # on an open project) need the previous session fully gone before the next starts.
    # A bot opens 4-8 sessions per submission, so this fires often. MEASURED: it cost
    # Unity both determinism criteria on every trial - a deduction that could only ever
    # land on one arm of a four-way comparison, which is bias rather than noise
    # (FINDINGS #25).
    LOCK_HINTS = ("another unity instance", "cannot open the same project",
                  "lock", "already running", "resource busy")

    # -- one session per repository, enforced rather than hoped for --------- #

    def _claim_repo(self) -> None:
        """Serialise sessions on one repository. Retry logic was never enough.

        The retry loop this replaces could only react AFTER the engine had already
        refused. It never asked why a second session was being opened, and the answer
        was that every bot opens its sibling sessions from INSIDE `with
        ProbeSession(...)` - so the outer probe is still running, still holding the
        project, and the conflict is guaranteed rather than incidental. Retrying a
        conflict this harness is itself causing cannot succeed.

        So: at most one live session per repository.

        - Same thread, same repo: the outer session is closed first. It is always a
          nested sibling session, and by construction the bots have finished stepping
          the outer one before they open a sibling. A session closed this way reports
          `superseded`, and stepping it afterwards raises with that as the reason
          rather than something that reads like a submission defect.
        - Another thread, same repo: wait for it (`lock_wait_s`).
        - Another PROCESS, same repo: an advisory `flock`, so two graders pointed at
          one project directory serialise too.
        """
        if self._claimed:
            return
        self._key = _repo_key(self.repo)
        me = threading.get_ident()
        with _SESSION_GUARD:
            prev = _ACTIVE.get((self._key, me))
        if prev is not None and prev is not self:
            prev.superseded = True
            prev.close()
            self._note("[probe-lock] closed this thread's previous session on the same "
                       "repository before starting a new one")
        lock = _repo_lock(self._key)
        if lock.acquire(timeout=self.lock_wait_s):
            self._repo_lock_held = True
        else:
            self._note(f"[probe-lock] another thread held {self._key} for "
                       f"{self.lock_wait_s:.0f}s; starting anyway")
        self._claim_file_lock()
        self._claimed = True
        with _SESSION_GUARD:
            _ACTIVE[(self._key, me)] = self

    def _claim_file_lock(self) -> None:
        if fcntl is None:
            return
        path = Path(tempfile.gettempdir()) / (
            "probe-repo-" + hashlib.sha1(self._key.encode()).hexdigest()[:16] + ".lock")
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_RDWR, 0o644)
        except OSError as e:
            self._note(f"[probe-lock] could not open {path}: {e}")
            return
        end = time.monotonic() + self.lock_wait_s
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self._flock_fd = fd
                return
            except OSError:
                if time.monotonic() >= end:
                    # Never turn a stale lock file into a criterion failure: say so and
                    # go. The in-process lock above is the one that matters here.
                    self._note(f"[probe-lock] {path.name} was held by another process "
                               f"for {self.lock_wait_s:.0f}s; starting anyway")
                    os.close(fd)
                    return
                time.sleep(0.25)

    def _release_repo(self) -> None:
        if not self._claimed:
            return
        me = threading.get_ident()
        with _SESSION_GUARD:
            if _ACTIVE.get((self._key, me)) is self:
                del _ACTIVE[(self._key, me)]
        if self._flock_fd is not None:
            try:
                fcntl.flock(self._flock_fd, fcntl.LOCK_UN)   # type: ignore[union-attr]
            except OSError:
                pass
            try:
                os.close(self._flock_fd)
            except OSError:
                pass
            self._flock_fd = None
        if self._repo_lock_held:
            self._repo_lock_held = False
            _repo_lock(self._key).release()
        self._claimed = False

    def _finish_start(self, header: str) -> "Tick":
        t = Tick.parse(header)
        if t.tick != 0:
            raise ProbeError(f"first trace line must be tick 0, got tick {t.tick}")
        self.history.append(t)
        return t

    @staticmethod
    def _pump_stdout(proc: subprocess.Popen, q: "queue.Queue[str | None]") -> None:
        # Bound to the process and queue of ONE attempt, so a thread left over from a
        # refused attempt cannot feed the next one.
        assert proc.stdout
        for line in proc.stdout:
            q.put(line)
        q.put(None)

    @staticmethod
    def _pump_stderr(proc: subprocess.Popen, tail: list[str]) -> None:
        assert proc.stderr
        for line in proc.stderr:
            tail.append(line.rstrip("\n"))
            del tail[:-60]

    def _note(self, text: str) -> None:
        """A harness annotation. Kept OUT of `_stderr_str()` deliberately - see
        `_looks_like_lock_conflict`."""
        self._notes.append(text)
        del self._notes[:-20]

    def _read_line(self, timeout_s: float, what: str) -> str:
        deadline = time.monotonic() + timeout_s
        while True:
            if time.monotonic() - self._t0 > self.total_timeout_s:
                raise ProbeError(
                    f"probe exceeded its total budget of {self.total_timeout_s:.0f}s"
                )
            try:
                line = self._q.get(timeout=max(0.05, deadline - time.monotonic()))
            except queue.Empty:
                raise ProbeError(
                    f"probe produced no output within {timeout_s:.0f}s while {what}. "
                    f"stderr tail: {self._stderr_str()}"
                ) from None
            if line is None:
                code = self.proc.poll() if self.proc else None
                raise ProbeError(
                    f"probe exited (code {code}) while {what}. "
                    f"stderr tail: {self._stderr_str()}"
                )
            line = line.strip()
            if not line:
                continue
            if not line.startswith("{"):
                # stdout pollution: an engine banner, a `just` echo, a warning. The
                # protocol says stdout carries nothing but JSON. Skip a small number
                # of non-JSON lines rather than failing outright, because `just` itself
                # echoes recipe lines in some configurations - but record it.
                self._stderr_tail.append(f"[stdout pollution] {line[:200]}")
                continue
            return line

    def _stderr_str(self) -> str:
        """The CHILD's output only. This is what goes into ProbeError messages, and
        therefore what votes on whether a failure was a lock conflict."""
        return " | ".join(self._stderr_tail[-8:]) or "(empty)"

    def report_stderr(self) -> str:
        """Child output plus harness notes - for the report, never for a verdict."""
        return " | ".join([*self._notes[-4:], *self._stderr_tail[-8:]]) or "(empty)"

    def close(self) -> None:
        """Stop the probe and release the repository. Idempotent."""
        proc, self.proc = self.proc, None
        if proc is not None:
            try:
                if proc.stdin and not proc.stdin.closed:
                    proc.stdin.close()
            except OSError:
                pass
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    proc.kill()
                # Reap it. Without this the child can linger as a zombie holding
                # whatever the engine locked, and the NEXT session fails to start.
                try:
                    proc.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    pass
        # AFTER the child is gone, never before: the point of the lock is that the next
        # session sees a released project, not a closing one.
        self._release_repo()

    # -- driving ------------------------------------------------------------ #

    def step(self, **inputs: bool) -> Tick:
        """Advance exactly one tick with the given controls held."""
        return self.step_raw({k: bool(v) for k, v in inputs.items() if v})

    def step_raw(self, inputs: dict[str, Any]) -> Tick:
        if self.superseded:
            raise ProbeError(
                "this session was closed because a sibling session started on the same "
                "repository; a bot must finish stepping a session before opening "
                "another (this is a bot bug, not a submission defect)")
        if not self.proc or not self.proc.stdin:
            raise ProbeError("probe is not running")
        try:
            self.proc.stdin.write(json.dumps(inputs, separators=(",", ":")) + "\n")
            self.proc.stdin.flush()
        except (BrokenPipeError, OSError) as e:
            raise ProbeError(
                f"probe closed its stdin after {self.ticks_sent} ticks: {e}. "
                f"stderr tail: {self._stderr_str()}"
            ) from e
        self.ticks_sent += 1
        line = self._read_line(self.step_timeout_s, f"after tick {self.ticks_sent}")
        t = Tick.parse(line)
        if t.tick != self.ticks_sent:
            raise ProbeError(
                f"probe reported tick {t.tick} after {self.ticks_sent} inputs - "
                "one input line must advance exactly one tick"
            )
        self.history.append(t)
        return t

    def hold(self, n: int, **inputs: bool) -> list[Tick]:
        return [self.step(**inputs) for _ in range(n)]

    def idle(self, n: int) -> list[Tick]:
        return [self.step_raw({}) for _ in range(n)]

    @property
    def last(self) -> Tick:
        return self.history[-1]

    def events_since(self, tick_index: int) -> list[str]:
        out: list[str] = []
        for t in self.history[tick_index:]:
            out.extend(t.events)
        return out

    def count_event(self, name: str, start: int = 0) -> int:
        return sum(t.events.count(name) for t in self.history[start:])


# --------------------------------------------------------------------------- #
# Criterion plumbing
# --------------------------------------------------------------------------- #


@dataclass
class Criterion:
    """One binary check. Binary, never a 1-5 scale - see research/05.

    `evidence` is the observation that justifies the verdict, recorded so a human can
    audit a run without re-running it.
    """

    id: str
    question: str
    passed: bool
    evidence: str
    # A criterion is DIAGNOSTIC when the instrument has been shown not to pass a
    # known-correct implementation. It is still measured and still reported, but it
    # does not contribute to the score. Scoring an assertion that a correct submission
    # cannot satisfy manufactures false negatives, and a false negative is
    # indistinguishable from a real failure in the aggregate.
    scored: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "question": self.question,
                "passed": bool(self.passed), "evidence": self.evidence[:600],
                "scored": bool(self.scored)}


def unusable_criteria(pairs: list[tuple[str, str]], err: BaseException, what: str,
                      diagnostic: frozenset[str] = frozenset()) -> list[Criterion]:
    """Verdicts for criteria whose probe session could not be opened or kept alive.

    FAIL CLOSED is the default and stays the default: a submission that cannot be
    driven has not demonstrated gameplay. The single exception is a project-lock
    conflict, which is not a fact about the submission at all - it is the engine
    refusing this harness a second door key. Those come back `scored=False`: measured,
    reported, excluded from the score. See `ProbeError` and FINDINGS #25.
    """
    lock = bool(getattr(err, "lock_conflict", False))
    reason = (
        f"NOT MEASURED during {what}: every attempt to open a probe session was refused "
        f"with a project-lock signature, which is a fact about the engine and this "
        f"harness rather than about the submission (FINDINGS #25). Excluded from the "
        f"score rather than counted as a failure. {err}"
        if lock else f"probe unusable during {what}: {err}")
    return [Criterion(cid, q, False, reason,
                      scored=(not lock) and cid not in diagnostic)
            for cid, q in pairs]


# --------------------------------------------------------------------------- #
# The end condition, in two phases
# --------------------------------------------------------------------------- #
#
# THE CLAIM EVERY GAME'S END CONDITION MAKES is the task prompt's: an ended game
# "stops accepting play until it is reset". That sentence has two halves, and a
# criterion that tests only one of them is wrong in a direction:
#
#   PRESS THE CONTROLS and ask whether the game is still over, and a submission that
#   binds the reset the sentence itself contemplates fails for obeying the spec.
#   `g1_pong__rust` holds a game-over card for `GAME_OVER_LOCKOUT_TICKS = 96` and then
#   lets any control start a new match; the bot's held inputs pressed that control and
#   the criterion read the fresh match's live state as a failure to end.
#
#   PRESS NOTHING and a game that reports `game_over` while its simulation keeps
#   running passes, because with the player dead there is nobody left to earn points
#   and the score sits still. Measured on `ref_arena` with the step function's
#   `game_over` early-out deleted: an idle-only reading returns `score 0 -> 0` and the
#   mutant SURVIVES.
#
# So both phases run, in this order, and the second one is READ THROUGH THE RESET.
#
#   1. IDLE. Nothing is pressed. The end state must hold on its own - still over, the
#      guarded value unmoved, the player not back. This is the half that says play
#      STOPPED rather than that input was refused.
#   2. PRESS. The bot's own controls go down, one tick at a time, and the phase stops
#      at the first tick the game is no longer over. Reaching that tick is a RESET, and
#      a reset is correct: what it must then show is the game's own tick-0 state. Never
#      reaching it means the game refused play, which is equally correct, and then the
#      guarded value must not have moved.
#
# What fails is the third case: the game stayed over and kept playing anyway, or it
# came back without resetting.
#
# WHAT "RESET" IS READ AGAINST IS THE GAME'S OWN TICK 0, which is the only definition
# available to a bot that knows nothing about the submission. The stated limit: a game
# whose new run carries its score forward would read as a resume rather than a reset and
# fail. Nothing in the prompt asks for that and the submission this shape came from zeroes
# its score, so it is a limit rather than a known false negative - if one turns up, it is
# a `Pending` with a fixture, not an argument.
#
# THE GUARDED VALUE IS THE CALLER'S, AND IT MUST BE SOMETHING THE SIMULATION MOVES.
# "The score" is the obvious choice and it is the wrong one in half the games here: a
# dead arena player earns nothing and a full tetris well clears no layer, so in both
# the score is a constant whatever the game does. Each bot picks a value its own game
# advances - `kills` beside the arena's score, the filled-cell total beside tetris's -
# and the mutant that ends the game and keeps stepping is what says whether the pick
# works.
#
# THERE IS ONE COPY OF THIS BECAUSE THERE USED TO BE FOUR. Pong's `match.ends` was
# repaired to idle and the other three bots kept holding fire, aim, move, jump, attack
# and hard_drop, so two of them were red on a correct game and the third passed only
# because the restarted run lost again inside the same window (`tasks/157`). A per-bot
# copy of a policy is a policy that gets repaired once; every bot reaches this through
# its `Bot.end_condition` criterion, so the next repair cannot reach only one of them.


@dataclass(frozen=True)
class EndCondition:
    """What an ended game did across the idle phase and then the pressed phase.

    `alive` is the player's own flag where the game has a player and `None` where it
    does not - a third value, not `False`, and every test here reads it that way.
    """

    #: phase 1
    idle_ticks: int
    at_end: Any
    after_idle: Any
    alive_after_idle: Any
    #: EVERY idle tick is read, not only the last. A game that clears `game_over`,
    #: brings the player back or moves the guarded value and then returns to where it
    #: started passes an endpoint comparison and has not held (raised by CodeRabbit on
    #: PR #40). This is the first idle tick at which it did not hold, and why.
    idle_broke_at: int | None
    idle_broke_why: str
    #: phase 2
    press_ticks: int
    reset_at: int | None
    #: ticks idled after a detected reset before reading it; 0 when none was detected
    settle_ticks: int
    #: the reset did not survive its settle window - it was a flicker, not a new run
    reset_reverted: bool
    at_start: Any
    #: the player's flag AT TICK 0, so a reset is read against this game's own opening
    #: state rather than against "not dead". `None` there and `None` after is a game
    #: with no player; `True` there and `None` after is a game that dropped the field,
    #: which is not the tick-0 state (raised by CodeRabbit on PR #40)
    alive_at_start: Any
    after_press: Any
    alive_after_press: Any

    @property
    def held_while_idle(self) -> bool:
        """The end state survived every tick of the window with nothing pressed."""
        return self.idle_broke_at is None

    @property
    def answered_the_press(self) -> bool:
        """Either the game reset - and came back to its own tick-0 state, and stayed
        reset - or it refused the input and did not move."""
        if self.reset_at is not None:
            return (not self.reset_reverted
                    and self.after_press == self.at_start
                    and self.alive_after_press == self.alive_at_start)
        return (self.after_press == self.after_idle
                and self.alive_after_press is not True)

    @property
    def passed(self) -> bool:
        return self.held_while_idle and self.answered_the_press

    def detail(self, label: str) -> str:
        """`label` names what the caller sampled, and it is REQUIRED.

        It used to default to `"score"` while 3 of the 4 bots sample a pair, so the
        stored evidence read `score (0, 3) -> (0, 4)` about a `(score, kills)` tuple.
        An audit trail that mislabels what the instrument read is worse than one that
        says nothing (raised by CodeRabbit on PR #40).
        """
        idled = (f"the end state held every tick, {label} {self.at_end} -> "
                 f"{self.after_idle}, alive={self.alive_after_idle}"
                 if self.idle_broke_at is None else
                 f"BROKE at tick {self.idle_broke_at}: {self.idle_broke_why}")
        pressed = (
            f"reset at tick {self.reset_at}, settled {self.settle_ticks} ticks"
            f"{' and went over again' if self.reset_reverted else ''}, and {label} "
            f"came back to {self.after_press} (alive={self.alive_after_press}) "
            f"against a tick-0 {self.at_start} (alive={self.alive_at_start})"
            if self.reset_at is not None else
            f"still over, {label} {self.after_idle} -> {self.after_press}, "
            f"alive={self.alive_after_press}")
        return (f"over {self.idle_ticks} ticks with NO input: {idled}; then under "
                f"{self.press_ticks} ticks of input: {pressed}")


def _alive(t: Tick) -> Any:
    p = t.state.get("player")
    return p.get("alive") if isinstance(p, dict) else None


#: Ticks to let a detected reset settle before reading it against tick 0. Clearing the
#: card and re-initialising the world need not land on the same tick, and reading the
#: transition tick would fail a correct game that takes two (raised by CodeRabbit on
#: PR #40). It is SMALL on purpose and the smallness is the safety: a freshly reset game
#: cannot move any bot's guarded value this fast - the arena needs a kill, tetris needs a
#: lock at a fall interval of 48, pong and the platformer need a point.
RESET_SETTLE_TICKS = 4


def end_condition_holds(s: ProbeSession, *, idle_ticks: int, press_ticks: int,
                        inputs: dict[str, Any] | Callable[[int], dict[str, Any]],
                        sample: Callable[[Tick], Any]) -> EndCondition:
    """Drive both phases of the end condition. See the block comment above.

    Call it once the end condition has fired. `sample` reads the value that must not
    move while play is stopped, and choosing it is the caller's job: it has to be
    something this game's simulation ADVANCES, which the score is not in half of them.

    `inputs` is the bot's own busy set, the controls a player would be holding. Pass a
    CALLABLE of the press-phase tick index where the game reads an input as a rising
    edge rather than as a held control: `bot_tetris3d`'s `hard_drop` is `_edge`-driven,
    so a set held flat for the whole window drops once and then does nothing, and a
    game that kept playing would have nothing left to move.
    """
    press = inputs if callable(inputs) else (lambda _i: inputs)
    at_start = sample(s.history[0])
    at_end = sample(s.last)

    broke_at: int | None = None
    broke_why = ""
    for _ in range(idle_ticks):
        t = s.idle(1)[0]
        if broke_at is not None:
            continue          # keep stepping: the window's length is part of the claim
        if t.state.get("game_over") is not True:
            broke_at, broke_why = t.tick, "game_over went False with nothing pressed"
        elif sample(t) != at_end:
            broke_at, broke_why = t.tick, f"the guarded value moved to {sample(t)}"
        elif _alive(t) is True:
            broke_at, broke_why = t.tick, "the player was alive again"

    after_idle = sample(s.last)
    alive_after_idle = _alive(s.last)

    reset_at: int | None = None
    settled = 0
    reverted = False
    for i in range(press_ticks):
        t = s.step_raw(dict(press(i)))
        if t.state.get("game_over") is not True:
            reset_at = t.tick
            settled = RESET_SETTLE_TICKS
            reverted = any(st.state.get("game_over") is True for st in s.idle(settled))
            break
    return EndCondition(
        idle_ticks=idle_ticks, at_end=at_end, after_idle=after_idle,
        alive_after_idle=alive_after_idle,
        idle_broke_at=broke_at, idle_broke_why=broke_why,
        press_ticks=press_ticks, reset_at=reset_at, settle_ticks=settled,
        reset_reverted=reverted, at_start=at_start,
        alive_at_start=_alive(s.history[0]),
        after_press=sample(s.last), alive_after_press=_alive(s.last))


class Bot:
    """Base class for a per-game scripted play-bot."""

    game: str = ""
    criteria: list[tuple[str, str]] = []  # (id, question)

    def run(self, session: ProbeSession) -> list[Criterion]:
        raise NotImplementedError

    #: ids that are measured and reported but deliberately NOT scored - see Criterion.
    diagnostic_only: frozenset[str] = frozenset()

    # -- the representative play session ----------------------------------- #
    #
    # PACING EVIDENCE MUST NOT COME FROM THE CRITERIA SESSION. It used to, and the
    # result was measured: the criteria session for `g2_tetris3d` emits 6-9 events in
    # 6-9 seconds, because the bot spends it opening sibling sessions rather than
    # playing. `longest_quiet_stretch_seconds` was therefore 93-100% of the run for
    # ALL EIGHT submissions - a degenerate number that is run length wearing a pacing
    # label - and the `fun` judge's scores tracked run length at rho -0.45 to -0.60
    # (FINDINGS #52).
    #
    # A bot that wants its game judged on pacing must therefore say how to PLAY it,
    # for long enough that the answer is a property of the game. A bot that does not
    # gets `representative: false` and the judge is told the evidence is not usable,
    # rather than being handed a plausible number derived from nothing.
    play_ticks: int = 0

    def play_inputs(self, tick: "Tick") -> dict[str, Any]:
        """One tick of competent play, for the representative pacing session."""
        return {}

    def all_false(self, reason: str) -> list[Criterion]:
        """Every criterion fails with the same reason. Used when the probe dies."""
        return [Criterion(cid, q, False, reason, cid not in self.diagnostic_only)
                for cid, q in self.criteria]

    def unusable(self, err: BaseException, what: str = "the main session"
                 ) -> list[Criterion]:
        return unusable_criteria(self.criteria, err, what, self.diagnostic_only)

    # -- shared shape for a criterion that could not be SET UP --------------- #

    @staticmethod
    def not_established(cid: str, question: str, why: str) -> Criterion:
        """The precondition the experiment needs could not be created.

        Not a pass and not a fail: an experiment that never ran. This is the honest
        verdict for e.g. a Tetris piece that spans the well in every direction, where
        "it did not move" is the correct behaviour and scoring it FALSE would be a
        false negative by construction.
        """
        return Criterion(cid, question, False,
                         f"NOT MEASURED - the experiment could not be set up: {why}",
                         scored=False)


def drive(bot: Bot, repo: Path, seed: int = 7,
          env: dict[str, str] | None = None,
          total_timeout_s: float = 2400.0,
          audio_game: str | None = None) -> dict[str, Any]:
    """Run one bot against one submission. Never raises.

    `audio_game` opts the submission into `audio.triggered`, which is answered from the
    events this run ACTUALLY produced rather than from the ones the task declares. Pass
    it only for runs whose task asked for sound - applying it to a submission built
    before audio entered the task set would score the task change, not the work.
    """
    t0 = time.monotonic()
    fired: list[str] = []
    tele: dict[str, Any] = {"usable": False, "reason": "the probe never ran"}
    try:
        with ProbeSession(repo=repo, seed=seed, env=env,
                          total_timeout_s=total_timeout_s) as s:
            crits = bot.run(s)
            stderr = s.report_stderr()
            ticks = s.ticks_sent
            fired = sorted({e for t in s.history for e in t.events})
            # Pacing evidence from the trace the bot already produced. The
            # deterministic tiers use it to assert correctness; a specialist judge
            # uses the same numbers to ask whether the game is TUNED. One drive, two
            # readers, so they cannot disagree about what happened.
            import telemetry as telemetry_mod
            tele = telemetry_mod.from_trace(s.history)
            tele["representative"] = False
            tele["source"] = "the criteria session"
    except ProbeError as e:
        crits = bot.unusable(e)
        stderr, ticks = str(e), 0
    # noqa BLE001, deliberately blind and FAIL-CLOSED: a bot is arbitrary per-game
    # Python, so the exception set is open by construction. Everything not a ProbeError
    # is scored all-false with the exception named in the evidence -- a bot bug costs a
    # trial, never a false pass, which is the trade AGENTS.md rule 7 asks for.
    except Exception as e:  # noqa: BLE001
        crits = bot.all_false(f"bot raised {type(e).__name__}: {e}")
        stderr, ticks = str(e), 0
    # A SECOND, DEDICATED SESSION whose only job is to be a representative play. It
    # scores nothing - a bot bug here must not turn into a submission failure - and it
    # replaces the criteria session's telemetry only if it actually ran.
    if bot.play_ticks:
        import telemetry as telemetry_mod
        try:
            with ProbeSession(repo=repo, seed=seed, env=env,
                              total_timeout_s=total_timeout_s) as ps:
                prev = ps.last
                # Keep what was SENT, aligned with the history, so telemetry can tell
                # a world event from an echo of the bot's own key press.
                sent: list[dict] = [{}]
                for i in range(bot.play_ticks):
                    # EVERY OTHER TICK IS DELIBERATELY IDLE, and that is not a detail.
                    # It is what makes the world-vs-echo classification reliable: a real
                    # world event (a piece landing under gravity, an enemy closing, a
                    # wave starting) lands on an idle tick within a few occurrences,
                    # while an echo of a key press never can. Without guaranteed idle
                    # ticks the classifier called `lock` an echo, because a lock caused
                    # by a hard drop genuinely fires on the tick the drop was pressed.
                    # It also gives edge-triggered inputs the release they need.
                    inp = bot.play_inputs(prev) if i % 2 == 0 else {}
                    prev = ps.step_raw(inp)
                    sent.append(dict(inp))
                    if prev.state.get("game_over") is True:
                        break
                play = telemetry_mod.from_trace(ps.history, inputs=sent)
            play["representative"] = True
            play["source"] = (f"a dedicated play session of {bot.play_ticks} ticks, "
                              f"separate from the criteria drive")
            tele = play
        # noqa BLE001, deliberately blind: same open exception set as the criteria
        # session above, and this one SCORES NOTHING -- it only replaces telemetry. The
        # failure is recorded (`representative` false, `play_session_error` named) so a
        # reader can tell a missing representative play from one that was never asked
        # for. Nothing here can turn into a submission failure.
        except Exception as e:  # noqa: BLE001
            tele = dict(tele)
            tele["representative"] = False
            tele["play_session_error"] = f"{type(e).__name__}: {e}"

    if audio_game is not None:
        import audio as audio_mod
        crits = [*crits, audio_mod.triggered_criterion(repo, audio_game, fired, env)]
    for c in crits:
        if c.id in bot.diagnostic_only:
            c.scored = False
    scored = [c for c in crits if c.scored]
    passed = sum(1 for c in scored if c.passed)
    # `unscored` is not decoration. A criterion excluded because the instrument could
    # not measure it must be visible as such, or `total` silently shrinking looks
    # exactly like a criterion that quietly passed.
    unscored = {c.id: c.evidence[:200] for c in crits if not c.scored}
    return {
        "tier": "playbot",
        "game": bot.game,
        "seed": seed,
        "ticks_driven": ticks,
        "events_fired": fired,
        "telemetry": tele,
        "passed": passed,
        "total": len(scored),
        "usable": bool(scored),
        "diagnostic_only": sorted(bot.diagnostic_only),
        "diagnostics": {c.id: c.passed for c in crits if not c.scored},
        "unscored": unscored,
        "score": passed / len(scored) if scored else 0.0,
        "wall_s": round(time.monotonic() - t0, 1),
        "criteria": [c.to_dict() for c in crits],
        "probe_stderr": stderr[-1500:],
    }
