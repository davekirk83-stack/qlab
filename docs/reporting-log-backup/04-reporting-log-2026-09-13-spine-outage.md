# Spine Outage — 8 to 13 September 2026

**Filed by:** the spine watchdog round (`trig_01FFSwYfNtSdLGvEW9JpY8Un`), firing `2026-09-13T00:32:26Z`
**Owner:** Chief Operations Manager · **Opened:** 2026-09-13

**Why this file exists at a new path rather than inside `claude/04-reporting-log.md`:** that log is ~9,000 words and `project_write` replaces a document whole, with no merge and no undo (CHECK 15). Re-emitting it from a retyped copy is the operation that destroyed `claude/capital/18-multimarket-results.md` on 7 September and put DK's county back on the live About page on 5 September. **A write to a new path can only add a copy; it can never destroy one.** The reporting log carries a pointer to this file.

**Clock, read from `TZ=Europe/London date`, both ends:**

| Read | BST | UTC |
|---|---|---|
| First, before any other tool call | `Sun Sep 13 01:32:40 BST 2026` | **00:32:40** |
| Second, mid-round | `Sun Sep 13 01:37:02 BST 2026` | **00:37:02** |
| Third, before filing | `Sun Sep 13 01:38:34 BST 2026` | **00:38:34** |

**This round's own firing is recorded `PENDING`, `fired_at 2026-09-13T00:32:26.248936966Z`.** First tool call fourteen seconds later. **No start latency and no mid-round stall** — the three reads are six minutes apart in a round that has felt like six minutes (CHECK 10 point 6, which exists because two rounds on 8 September froze for 7h 11m and 15h 25m between consecutive tool calls without noticing).

---

## 🔴 THE FINDING: THE ENTIRE SCHEDULED SPINE HAS PRODUCED NOTHING FOR FIVE DAYS

**Judged from artefacts, never from run status (OPS-20260831-04, and the reporting log's own header rule that no status is evidence of anything).**

**`project_info`, read this round: the most recent write to this project is `claude/06-approvals-queue.md` at `2026-09-08T14:39:17Z`.** Nothing has been written since. That is **five days and ten hours**, across which the roster's scheduled rounds have fired on the order of fifty times.

### What `list_triggers` shows — read `2026-09-13T00:32Z`, 23 tasks

**Ten rounds carry `last_run.status = ROUTINE_RUN_STATUS_FAILED`, and nine of the ten failed on 12 September:**

| Round | `fired_at` | `finished_at` | Elapsed |
|---|---|---|---|
| Capital research — nightly backtest | `2026-09-12T01:34:46Z` | `01:34:58Z` | **12s** |
| Catch-up round | `2026-09-12T04:15:35Z` | `04:15:44Z` | **9s** |
| Website Manager — daily | `2026-09-12T06:08:33Z` | `06:08:43Z` | **10s** |
| Music & Social Media — daily | `2026-09-12T07:07:01Z` | `07:07:11Z` | **10s** |
| Weekly TSMOM scan | `2026-09-12T08:03:03Z` | `08:03:14Z` | **11s** |
| *VC/GC Archive — daily* | *`2026-09-12T12:37:17Z`* | *`12:37:25Z`* | *8s* |
| News Analyst — nightly | `2026-09-12T18:37:15Z` | `18:37:25Z` | **10s** |
| Operations Manager — consolidation | `2026-09-12T20:04:15Z` | `20:04:23Z` | **8s** |
| Head of Capital — daily check-in | `2026-09-12T20:10:32Z` | `20:10:40Z` | **8s** |
| Profession — monthly | `2026-09-03T09:05:22Z` | `09:27:40Z` | 22m — old, and it filed its brief anyway |

**Every one of the nine is a fast-fail of 8 to 12 seconds.** Each carries a distinct `session_id`, so a session was created and then died. **No error text is exposed anywhere in the response** — there is no `error`, no `suspension_reason` and no `ended_reason` on any of them; all ten remain `enabled: true` with a valid `next_run_at`.

**This is A25, at a scale it has never previously reached.** The known shapes of `FAILED` include a long run that nevertheless committed real work — so the status alone proves nothing. **What settles it here is that there are no artefacts.** Five days, no writes.

### 🔴 Both recovery mechanisms DK authorised on 3 September are themselves down

**`trig_01FFSwYfNtSdLGvEW9JpY8Un` — the spine watchdog, every 4h** — last filed to `claude/09-spine-watchdog-log.md` at **`2026-09-08T08:42:35Z`**. At six firings a day that is roughly **thirty firings that produced nothing.** *(This round is the exception and is the reason this file exists.)*

**`trig_014aF7ic7vNerkaXP1iJxSz2` — the catch-up round, daily 04:15 UTC** — `FAILED` at 9 seconds on 12 September; last filed 8 September.

**That is the part that matters most.** OPS-20260901-02 exists because DK said, on 2 September: *"If we hit a usage limit again — ensure that this operation resumes asap after the limit resets."* **The two mechanisms built to answer that instruction have both been silently down for five days, so nothing was watching the watchers.** The operation had no way to notice its own five-day disappearance, and did not.

### What is NOT the cause — checked rather than assumed

- **Not a disabled or expired task.** All the affected rounds read `enabled: true`, with `ended_reason` and `suspension_reason` both empty and `next_run_at` populated.
- **Not a bad prompt.** An 8-second fast-fail happens before a prompt is read, and the four prompts corrected on 8 September were verified byte-identical at the time.
- **Not the model setting.** Untouched since 3 September.
- **Not the project store filling up.** `project_info` reports **1,174,199 of 2,000,000 — 58.7%.** Room to spare.
- **Not something this round can retry or diagnose.** Nothing reachable from inside a session exposes why a sibling session was refused at creation.

---

## ✅ WHAT THIS ROUND RE-RAN: THE PERISHABLE ITEM, AND ONLY THAT

**One item in this operation cannot be recovered later, and it was about three days from being lost.**

**CAP-024 / CAP-025:** Crypto.com's `get_candlestick` returns exactly **50 candles**, with no `limit`, no `start_ts`, no cursor and no pagination. Deeper 4h history **cannot be fetched, only accumulated at six bars a day.** A bar that ages out of the rolling ~eight-day window is gone permanently. `run_session.py` calls the archive *"the one genuinely irreplaceable asset this section holds."*

**The position found:**

- `claude/capital/system/signal_state.json` — `last_evaluated_bar` **BTC and ETH both `2026-09-07 16:00:00+00:00`**, `updated 2026-09-07 20:19:12.652574+00:00`, `project_info created_at 2026-09-07T20:20:17Z`. **Byte-identical to the reading the 8 September 08:33 watchdog took**, which is exactly right: the archive advances only when the check-in runs, and the check-in has not run since.
- `claude/capital/system/btc_4h_archive.csv` — `created_at 2026-09-07T20:20:06Z`, last row `2026-09-07 20:00:00+00:00`, close 79241.66, **volume 9.63212 — a still-forming bar**, which is the ordinary CAP-029 condition.
- **Twenty-six 4h bars per asset were outstanding.**

**The pull, taken at approximately `00:35Z` between the first and second clock reads:** `mcp__Crypto_com__get_candlestick`, `BTC_USDT` and `ETH_USDT`, `4h`. **50 bars each, newest `2026-09-13T00:00:00Z` (still forming), oldest `2026-09-04T20:00:00Z`.**

### 🟢 The window still overlapped the archive. Nothing has been lost.

**The oldest bar the exchange served is `2026-09-04 20:00`, which is eighteen bars BEFORE the archive's last stored bar.** So the eight-day window had not yet begun to bite, and there is no hole. **This was verified by reading the returned data, not by arithmetic on the dates.**

**The corroboration bar matches exactly.** `2026-09-07 16:00`, the last settled bar in both the archive and `signal_state.json`:

| | open | high | low | close | volume |
|---|---|---|---|---|---|
| Archive, filed 7 Sept | 78824.81 | 79416.07 | 78792.0 | 79357.65 | **141.54558** |
| Fresh pull, this round | 78824.81 | 79416.07 | 78792.00 | 79357.65 | **141.54558** |

**Identical to the last decimal of volume**, which is the CAP-025 instrument test. The archive is `BTC_USDT` and the pull is `BTC_USDT`; **no splice risk.**

**Committed to `claude/capital/system/fresh_candles_2026-09-13.json`** — a **new path**, result `replaced: false`, so nothing was overwritten. It holds both instruments' full 50 bars with a provenance block, the overlap finding, and the two bars flagged (`2026-09-13 00:00` still forming at pull time; `2026-09-07 20:00` settled here but stored still-forming in the archive, where last-pull-wins on merge per CAP-029).

**The perishable item is now permanently safe and the deadline is gone.** Had this round also fast-failed, the next successful pull would have found a permanent hole in the one asset the section cannot rebuild.

### ⛔ What this round deliberately did NOT do

**It did not merge, and it did not advance the state.** `btc_4h_archive.csv`, `eth_4h_archive.csv`, `signal_state.json` and `paper_trade_log.csv` were **read and not written.** No signal was evaluated, no bar replayed, no paper trade opened or closed.

**Why, stated so the next round does not have to re-derive it:**

1. **The perishable half is done.** Once the raw candles are in the project, the merge and the replay can happen on any later date with no loss. **They are no longer time-critical; the pull was.**
2. **The archives are Tier 3 objects under CHECK 8** — `project_write` has no version history, no merge and no undo, and a botched write to the one irreplaceable asset in the section is a worse outcome than a late merge.
3. **A signal replay is the check-in's job, not a watchdog's.** It runs the duplicate-position, cooldown and weekly-cap gates in sequence state (CAP-030); a watchdog reproducing that by hand would be inventing a result, which Rule 4 forbids.

**So the merge is owed, it is safe to defer, and the data it needs is filed.**

---

## What every other failed round needs — one line each

**Nothing else here is perishable, and nothing was re-run.**

| Round | What is owed | Perishable? |
|---|---|---|
| **Capital daily check-in** | The merge and replay from `fresh_candles_2026-09-13.json`, taking `signal_state.json` from `2026-09-07 16:00` to `2026-09-12 20:00` or later | **Was. Now not** — rescued above |
| **Capital nightly research** | Four nights of the §2k programme | No |
| **Nightly consolidation** | Four nights, plus the staging sweep already seven days overdue | No |
| **News Analyst** | Four days of brief. Yesterday's news is on the same pages today | No |
| **Website daily** | Four days. **Post 246 was scheduled for `2026-09-10T14:26` and no round has confirmed it published** — see below | No, but unverified |
| **Music daily** | Four days | No |
| **Weekly TSMOM scan** | The 12 September scan | No |
| **Watchdog / catch-up** | The five days above | No |
| *VC/GC Archive* | *Not this operation's. DK, 3 Sept: "Keep them distinct." **Recorded only because it evidences the fault is platform-wide and not confined to this project's tasks.** Not recovered, not reported on, not touched* | *n/a* |

**🟠 One thing this round could not establish and did not guess.** The Website round scheduled **post 246** for `2026-09-10T14:26 BST`, `status: future`. **Whether it actually published is unverified** — the site was not called this round. It is not perishable (a `future` post either fired or is still queued, and either state is recoverable), but **it is the only live-property item outstanding and the next Website round should check it first**, along with the WEB-20260831-02 anonymity sweep, which has not been run against the live pages since 8 September. **Five days is the longest that gate has gone unchecked since it was breached on 5 September, and the record's own standing position is that it is fragile, not fixed.**

---

## Escalated to DK

**Push notification sent this round.** The escalation test is **broken AND expiring**, and this clears both halves — which is why it was sent when the last several watchdog rounds correctly sent nothing.

- **Broken:** five days, zero artefacts, ten rounds fast-failing, and both authorised recovery mechanisms down.
- **Expiring:** the candle window was ~three days from a permanent hole *(now defused)*; the anonymity gate is five days unchecked; and the outage sits inside **DK's own end-of-September review of the Head of Capital role**, where he required every Capital round to produce checkable external evidence. **Five of those days have produced none, and the cause is the scheduler, not the section.** That distinction is the reason this was worth his attention rather than left in a log.
- **What only he can do:** the fault looks like a refusal at session creation. Checking the account's usage or subscription state is outside anything reachable from here. **Until the spine runs, the candle archive needs rescuing roughly every three days, and only a working round can do that.**

---

## What to check, without re-running this round

- **`claude/capital/system/fresh_candles_2026-09-13.json`** — 50 bars per instrument, newest `2026-09-13T00:00:00Z`, oldest `2026-09-04T20:00:00Z`. **The `2026-09-07 16:00` BTC bar should read `78824.81 / 79416.07 / 78792.00 / 79357.65 / 141.54558`, matching row `2026-09-07 16:00:00+00:00` of `btc_4h_archive.csv` exactly.**
- **The untouched files:** `signal_state.json` should still read `created_at 2026-09-07T20:20:17Z` and `last_evaluated_bar 2026-09-07 16:00:00+00:00`; `btc_4h_archive.csv` `2026-09-07T20:20:06Z`; `eth_4h_archive.csv` `2026-09-07T20:20:09Z`. **If any of those has moved, a check-in has since run and the merge is already done.**
- **The outage itself:** `project_info` — before this round, no doc `created_at` later than `2026-09-08T14:39:17Z`.
- **The failures:** `list_triggers` — the nine `fired_at`/`finished_at` pairs tabulated above, all on 12 September, all 8–12 seconds.
- **Store:** 1,174,199 / 2,000,000.

## Constraints observed

**CAP-021 — paper only.** One read-only public market-data call to a public endpoint. **No order, no credential, no exchange authentication, no order-placement path, no account, nothing moved.** No trade was opened, closed or evaluated.

**Rule 5 — nothing published, spent, signed, registered or committed on DK's behalf.** **No live property was called at all this round** — no WordPress tool, neither site, no page or post read or written.

**OPS-029 — no scheduled task created, altered, enabled, disabled or deleted, and no prompt touched.** **One task was FIRED after this file was written: `trig_014aF7ic7vNerkaXP1iJxSz2`, the catch-up round.** Authority is explicit and is not inferred: **OPS-20260901-02 names the watchdog and the catch-up round as the two standing recovery mechanisms and states in terms that "either can be fired on demand with `fire_trigger` rather than waited for"**, and this watchdog task exists on DK's express instruction of 2 September — *"If we hit a usage limit again, ensure that this operation resumes asap after the limit resets."* **Its next scheduled firing was 04:15Z, three hours forty minutes away; with five days of backlog and a fault of unknown duration, waiting for it was the wrong call.** It was fired last, after every write above had landed, precisely so it cannot collide with this round's filing. **No other task was fired, and the check-in was NOT fired** — its merge is safe to defer and firing section rounds is DK's under OPS-029.

**Rule 4 — no figure, date, price or result invented.** Every timestamp, price and volume above is from a server response quoted verbatim; the two clock stamps are from `TZ=Europe/London date`. **The "roughly fifty firings" is stated as an order of magnitude from published crons, not as a count, and is marked as such.**

**OPS-007 — nothing touching Morton & Eden. OPS-006 — nothing in coins, medals, bullion or collectables.** `claude/health/00-health-brief.md` not opened. **The VC/GC Archive's failure is noted as evidence of the fault's scope and is otherwise left entirely alone (DK, 3 September).**

**Writes made by this round, in full:** `claude/capital/system/fresh_candles_2026-09-13.json` (new path, `replaced: false`), this file (new path), and a pointer entry in `claude/04-reporting-log.md`. **No other project document was written**, and the two archives, the state file and the trade log were read and left exactly as found.
