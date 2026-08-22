# Backend, netcode, transport & deterministic simulation testing (verified 2026-08-10)

## THE SINGLE MOST CONSEQUENTIAL FINDING

**`turmoil` (the best Rust deterministic-simulation-testing tool) simulates UDP but NOT QUIC.**
Verified by absence: `turmoil::net` exposes `TcpListener`, `TcpStream`, `UdpSocket`,
`lookup_host` — no QUIC type, zero QUIC issues in the repo. Layering `quinn` over turmoil's
`UdpSocket` via `AsyncUdpSocket` is theoretically possible but GSO/ECN requirements make it
non-trivial and nobody has landed it.

Meanwhile QUIC is the right production transport (see below). These two recommendations are in
direct tension.

**Resolution: define a `Transport` trait between the simulation and the wire from day one.**
```rust
trait Transport { fn send_unreliable(..); fn send_reliable(..); fn recv(..); }
```
Implement over `quinn` for production and over `turmoil::net::UdpSocket` for tests. **Cheap now,
expensive to retrofit.** It also buys the WebSocket fallback transport for free. This belongs in
the template's architecture from the first commit.

## Determinism — the concrete levers

**Floating point is not deterministic across platforms.** Gaffer On Games: *"determinism on the
same machine does not necessarily mean it would also be deterministic across different compilers,
a different OS or different machine architectures"* — including debug vs release. *"There's no
silver bullet."*

But there is one very concrete, actionable lever (verified from glam 0.33.3 docs, 2026-08-03):

> *"By default, glam attempts to provide **bit-for-bit identical results on all platforms**.
> Using this [`fast-math`] feature will enable platform specific optimizations that may not be
> identical to other platforms."*

👉 **NEVER enable glam's `fast-math` feature.** This should be a CI-enforced lint in the template.
Also: avoid platform libm transcendentals (pin an implementation), watch FMA contraction
differences, and use the **`fixed` crate 1.31.0** (2026-03-20, 13.3M downloads) for anything that
must be bit-exact across a client/server split.

**Desync detection**: hash world state every N ticks, compare client vs server, log
seed + tick + input history on divergence. Combine with `insta` snapshots of N-tick runs from a
seeded initial state — catches "someone changed physics" immediately.

## Deterministic simulation testing (DST)

Canonical ingredients (from Antithesis + TigerBeetle VOPR): single-threaded deterministic
scheduler · seeded PRNG · virtual clock · all I/O behind a swappable layer · injected faults ·
time acceleration. TigerBeetle's VOPR runs real code in a fully simulated cluster with
*"all kinds of network, storage and process faults, at 1000x speed"* on 1024 cores continuously.

| Tool | Version | Notes |
|---|---|---|
| **`turmoil`** | **0.7.2** (2026-04-24), 15.7M dl | **The pick.** Recently split into a crate family: `turmoil-net` 0.1.0 (drop-in for `tokio::net`), `turmoil-fs`, `turmoil-io-uring`. Active through 2026-07-21. |
| `madsim` | 0.2.34 (2025-10-11) | FoundationDB-inspired, mocks tokio/tonic/etcd/kafka/s3. Aimed at distributed *services*, not game loops. More invasive. |
| Shadow | v3.3.0 (2025-10-16) | Syscall interposition — runs **real unmodified binaries**, TCP+UDP, deterministic. Linux-only, heavy. Nightly job, not `cargo test`. Needs no code changes — genuinely interesting third option. |
| `shuttle` | 0.9.1 (2026-04-21, AWS Labs) | Deterministic *concurrency-interleaving* testing. Complements turmoil (threads, not network). |
| `antithesis_sdk` | 0.2.9 (2026-06-12) | Commercial deterministic hypervisor. Gated behind requesting a container registry. |

`turmoil` `Builder` knobs: `rng_seed` (the determinism lever), `min/max_message_latency`,
`fail_rate`, `repair_rate`, `tick_duration`, `enable_random_order`.
`Sim` control: `partition()`/`repair()`, **`partition_oneway()`** (models NAT),
and **`hold()`/`release()`** — suspend in-flight messages, inspect, then deliver. That last pair
is how you write *deterministic reordering* tests instead of hoping randomness finds the bug.

**Tokio determinism**: `#[tokio::test]` defaults to `current_thread` — use it whenever you want
reproducibility (single deterministic task-polling order). `tokio::time::pause()` **requires
`current_thread`**; when paused and idle the clock auto-advances to the next timer, so
`sleep(1 hour).await` returns instantly. Two gotchas: it **only affects Tokio's `Instant`** —
`std::time::Instant`/`SystemTime` escape your control, so audit for those; and `spawn_blocking`
inhibits auto-advance.

## Transport: `quinn` 0.11.11 + QUIC DATAGRAM (RFC 9221)

quinn 0.11.11 (2026-06-22, 5,208★, 256M dl). `send_datagram()` **drops the *oldest* queued
datagram when full** — exactly right for a state stream where newest wins.

Why QUIC over raw UDP:
- One handshake = TLS 1.3 + server auth + client identity. You don't hand-roll crypto (the
  biggest source of security bugs in custom game protocols).
- DATAGRAM frames: no retransmission, no head-of-line blocking. Reliable streams on the *same*
  connection give chat/RPC/match-config for free. **Never put the 60 Hz stream on a QUIC
  *stream*** — within a stream ordering is still enforced.
- **Connection migration** survives a phone moving Wi-Fi → cellular mid-match. Raw UDP +
  netcode.io does not. Large iOS win.
- Pure Rust, no C toolchain — materially simpler iOS cross-compilation than quiche or GNS.

Caveats: datagrams share the connection's congestion controller and are **not** flow-controlled —
under loss you can be blocked from sending; treat "no send window" as "skip this tick", never
queue. Effective payload ~1.2 KB and `max_datagram_size()` **changes with path MTU** — re-read it.

⚠️ **quinn's README lists tested platforms as Linux, macOS, Windows — iOS is NOT among them.**
`quinn-udp`'s GSO/GRO fast paths are Linux-specific and fall back to per-packet syscalls.
Validate on physical iOS devices over cellular early.

**Build a WebSocket-over-TLS:443 fallback** — some networks block all outbound UDP.

Rejected: `s2n-quic` datagram support is behind `unstable-provider-datagram`, off by default.
**Steam Datagram Relay is not available** — the OSS `GameNetworkingSockets` build excludes SDR;
iOS builds are NDA'd and not in the public tree.

### Netcode crate landscape (crates.io, 2026-08-10)
| Crate | Latest | Status |
|---|---|---|
| **`lightyear`** | **0.29.0 (2026-08-10)** | Very active, Bevy 0.19. udp/webtransport(native+WASM)/websocket/steam/netcode/crossbeam. Prediction + rollback + lag compensation. |
| **`bevy_replicon`** | 0.42.1 (2026-08-09) | Very active, transport-agnostic |
| `renet` | 2.0.0 (2026-01-20) | Maintained, slower |
| `naia-server` | 0.25.0 | ⚠️ repo alive but **474 recent downloads** — adoption collapsed |
| `laminar` | 0.5.0 (**2021**) | ❌ DEAD |
| `netcode` (crates.io) | 0.3.1 (**2017**) | ❌ **A TRAP** — stale FFI wrapper, 45 downloads. Live impls are `renetcode` 2.0.0 / `lightyear_netcode` 0.29.0 |

**WebTransport browser support closed in 2026**: Chrome 97+, Edge 98+, Firefox 114+, **Safari
26.4 desktop + iOS**. MDN: Baseline 2026, "newly available since March 2026", 89.96% global.

## iOS compliance — two things that will bite

1. **UDP is allowed.** Apple TN3151: *"BSD Sockets is an acceptable choice if you have
   compatibility constraints, for example: When writing cross-platform code."* Apple also says
   *"If you're building a custom network protocol, consider using QUIC instead of TCP."*
   QUIC-over-UDP is first-class and review-safe.
2. 🚨 **IP literals are the #1 App Store risk.** All apps must work on IPv6-only DNS64/NAT64
   networks. Apple explicitly names *"IP address literals embedded in protocols"* as top breakage.
   **The matchmaker must hand the client a hostname, never an IP** —
   `match-7a3f.gs.example.com:7777`. NAT64 only fires when the client *resolves a name*, because
   DNS64 is what synthesizes the v6 address. An IPv4 literal bypasses DNS and therefore NAT64, and
   the connection simply fails on IPv6-only carrier networks.
   ⚠️ **This directly contradicts what the Agones Allocator Service returns (name/IP/port) — you
   need a DNS layer between allocation and the client.**

**NAT traversal: don't.** The server is dedicated, authoritative, on a public IP; the client dials
out and its own 60 Hz traffic maintains the NAT binding. There is no NAT to traverse. P2P also
exposes players' IPs to each other (harassment/DDoS) with zero anti-cheat benefit.

## Elixir/Phoenix side

Versions: Elixir **1.20.3** (2026-08-04), Phoenix **1.8.9** (2026-07-07) — **there is no Phoenix
1.9**. LiveView 1.2, Bandit 1.12.4, Thousand Island 1.5.0.

### 🚨 Pin Phoenix ≥ 1.8.9 — two 2026 CVEs hit this architecture directly
- **CVE-2026-56811** — *"Phoenix transports do not limit channel joins per connection"*,
  **CVSS 8.7 High**. Process-exhaustion DoS. Affects 0.11.0 → <1.8.9. **This is *the* lobby-service
  DoS vector.**
- CVE-2026-32689 — long-poll NDJSON body splitting → unbounded memory, CVSS 8.7, patched 1.8.6.
- **Elixir `protobuf` < 0.16.1** — CVE-2026-54451, unbounded recursion in embedded-message
  decoding, **CVSS 8.2 High**. Latest 0.17.0.

### Discord validates the architecture at 100× our scale
100M+ MAU, 12M+ concurrent, **26M WebSocket events/sec**, on **400–500 machines with 5 engineers**
running 20+ Elixir services. They **abandoned Mnesia** after production failures, rebuilt on
GenServer + ETS. Their Rust NIF lesson: pure-Elixir OrderedSet 4–640 µs at 250k items vs Rust NIF
**0.61–3.68 µs at 1M items** — the point isn't the speedup, it's that *immutable data structures
are the wrong tool for large mutable hot state*, which is exactly a game world.

### Hard boundary
**Elixir owns connections, rooms, orchestration and social state; it must NEVER be on the 60 Hz
data path.** An Erlang process is 338 words (~2.7 KB) — cheap for a process per connection/room,
not cheap for a process per entity at 60 Hz. There is no global stop-the-world GC pause (per-process
generational collector), which is why BEAM is good at soft-realtime *messaging* — but a single
large lobby GenServer gets a proportionally large pause that blocks *that* room.

Phoenix Channels caveats: **at-most-once delivery**, no server-side persistence, **no documented
backpressure**, client-queued messages discarded after 5s. Only WebSocket and LongPoll transports
ship — **no WebTransport/QUIC transport exists in Phoenix.** Binary frames are supported at the
serializer layer.

### The Elixir game ecosystem is genuinely thin
Top GitHub hits: `fly-apps/tictac` (375★, last pushed **2021**), `elvengard_network` (49★),
`gamend` (18★). **There is no Elixir equivalent of Nakama or Colyseus.** Plan to build
meta-services from Phoenix primitives — that's the honest baseline, not a research failure.

## Orchestration & matchmaking

- **Agones v1.59.0 (2026-07-01)**, 6,968★ — the mature piece. **Official Rust SDK: crate `agones`
  1.59.0.** The **Allocator Service** is external-facing mTLS gRPC+REST, designed exactly for
  "matchmaker outside the cluster allocates a server, gets back name/IP/port." **Recommended.**
- **Open Match**: was **never archived** (repo `archived: false`), but its **last release is
  v1.8.1 from 2023-12-13** — de facto maintenance-only. **Open Match 2** is a **59★ public preview
  with no tagged releases**. Not a safe foundation. **Write the matchmaker in Elixir** — ETS-backed
  ticket pools + a periodic GenServer + Registry sharding. Very likely cheaper than adopting a
  preview-stage Go framework for a single title.
- **Rivet has pivoted away from games** ("built for AI agents, collaborative apps, durable
  execution"). **Hathora is gone** — hathora.dev 301s to gamefabric.com.
- Nakama v3.40.0 — **clustering is Enterprise-only; OSS Nakama is single-node.**
- **SpacetimeDB v2.8.0 (2026-08-05), 24,990★** — a database that *is* your game server. The most
  interesting adjacent entrant; worth a "why not this instead" evaluation.
- **Do NOT use Horde for server allocation.** Its README: *"Horde is eventually consistent… cannot
  guarantee consistency. This means you may end up with duplicate processes in your cluster."*
  Duplicate game-server allocations are an intolerable correctness bug. Use libcluster for BEAM
  clustering only (libcluster 3.5.0, last released 2025-01-09 — stable but static).
- Dev/alpha tier: Elixir supervises Rust servers as OS ports with **`muontrap` 1.8.0** (built
  precisely to guarantee OS-process cleanup when the BEAM process dies) + ETS port pool.
- Skill rating: `skillratings` (Rust) / `openskill.ex`. TrueSkill is Microsoft-patent-encumbered;
  OpenSkill exists to avoid that.

## Schema & interop

| Format | Rust | Elixir | Verdict |
|---|---|---|---|
| **Protobuf** | `prost` 0.14.4 | `protobuf` 0.17.0 | ✅ **Only option with maintained first-class libs on both sides** |
| MessagePack | `rmp-serde` | `msgpax` 2.4.0 (2023) | ✅ viable, schema-less, static on Elixir side |
| Cap'n Proto | active | ❌ none maintained | ❌ |
| FlatBuffers | active | ❌ `eflatbuffers` last pushed 2023-06-18 | ❌ |
| `bincode` | ⚠️ **repo ARCHIVED** | ❌ | ❌ avoid |
| `postcard` | 1.1.3, 50M dl, active | ❌ | ✅ Rust↔Rust only |

**Split the problem**: `postcard` for the Rust↔Rust 60 Hz path (Elixir isn't on it);
**protobuf** for the Elixir↔Rust control plane and Elixir↔client meta APIs.

**Rustler 0.38.0** (2026-05-25, 4,848★). **The single most important operational fact: any NIF
exceeding ~1 ms MUST set `#[nif(schedule = "DirtyCpu")]`** (or `DirtyIo`) or you stall a BEAM
scheduler thread and destroy latency for every process on it.

**Do NOT load the simulation crate as a NIF.** It makes Elixir and Rust share one OS process and
one failure domain — a panic in the sim takes down the node holding thousands of lobby connections,
negating the fault isolation you chose BEAM for. Reserve NIFs for small, pure, hot, bounded
functions. Use gRPC (`elixir-grpc/grpc` v1.0.3, reached 1.0 in 2026-07) for the control plane and
ports (`muontrap`) for local process supervision. Skip C nodes.

## The Phoenix → Rust handoff: netcode.io connect-token pattern

1. Client authenticates to **Phoenix** over HTTPS.
2. Phoenix matchmakes, allocates via the **Agones Allocator Service**, mints a **connect token**.
3. Token = public part (client-readable: **server hostnames**, per-connection key, 30–60s expiry)
   + private part (AEAD-encrypted: client ID, entitlements) under a **32-byte secret shared only by
   Phoenix and the Rust servers — never in the client binary**.
4. Client dials the Rust server over QUIC, presents the token in the first datagram.
5. **Rust server decrypts locally — no round-trip to Phoenix on the hot path.** Admission is O(1)
   local crypto, so a connection storm cannot DDoS the Elixir tier.
6. Short-lived seen-nonce set for replay protection. Two overlapping valid secrets for rotation.
7. Rust server reports match started/ended/results back over a separate authenticated control
   channel.

A Phoenix deploy or restart cannot disconnect players mid-match. The only coupling is a shared
secret and a hostname list.

## Testing the Elixir side

`stream_data` 1.4.0 · **`mimic` 2.3.1** (prefer over Mox 1.2.0) · **`slipstream` 1.2.2** (the
channel client for fake-client harnesses — `phoenix_client` is abandoned, last release 2020) ·
`local_cluster` 2.1.0 (`:peer`-based; `ex_unit_clustered_case` is stale and predates `:peer`).

**ChannelTest**: `assert_broadcast` tests PubSub; `assert_push` tests what the client actually
receives — people get this wrong. Assertion macros default to a **100 ms timeout**. `leave/1` and
`close/2` **crash the test process** unless you `Process.unlink(socket.channel_pid)` first.

**The landmine: Ecto sandbox ownership.** Channels run in a separate process and Presence `fetch/2`
in *yet another*; both hit `DBConnection.OwnershipError` unless you thread `Sandbox.allow/3` to each
pid. `{:shared, self()}` fixes it but forces `async: false`. Budget for some suites being sync.

**Stateful property testing is a real gap**: StreamData has **no stateful API** (issue #94 open,
last updated **2018**). PropCheck has no commits since 2025-04-21 and wraps PropEr which is
**GPL-3.0** — a genuine problem for a commercial backend.
👉 **Hand-roll command generation on StreamData** (~100 lines: generate a command list, run against
a reference model and the real system, compare). Avoids both the GPL question and the staleness.

**There is no deterministic scheduler for the BEAM.** Substitute is **Concuerror** (346★, pushed
2026-06-24) — stateless model checking with dynamic partial order reduction; can prove *absence* of
concurrency errors. Caveat: flags benign races too.
**DST lives on the Rust side; Elixir gets Concuerror + `local_cluster` partition tests. Don't try
to make the BEAM deterministic.**
