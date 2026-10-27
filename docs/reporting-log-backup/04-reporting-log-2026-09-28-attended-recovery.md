# Attended recovery — 2026-09-28, 09:1x–09:3xZ

**Owner:** Operations Manager, attended session (DK: "It ran out of usage. Continue now as best you can.") **Filed as a separate dated file, not by stubbing `claude/04-reporting-log.md` (~35 KB, CHECK 15/21 precedent).**

## What triggered this session

DK asked "what next" at 09:1xZ. Live state was checked rather than answered from the record, which was seven days stale (last written 2026-09-21). Found: the operation had gone almost entirely silent for most of a week.

## The outage, confirmed from `list_triggers` and `project_info`, not from any round's own account of itself

**Total silence, 2026-09-22T12:35Z → 2026-09-27T04:34Z — 4 days 16 hours. Nothing fired or filed anything.** (This was itself first noted by the 27 September consolidation's own IN-PROGRESS marker, which then stalled and never closed — `claude/04-reporting-log-2026-09-27-consolidation-IN-PROGRESS.md` is the last word from that round.)

**Since the partial resumption on 27 September, it is still failing.** `list_triggers` read live at 09:16Z today:

| Round | Fired | Status at 09:16Z | Normal duration |
|---|---|---|---|
| Nightly consolidation | 2026-09-27 20:13:18Z | `PENDING` — **13h+ and counting** | minutes |
| Catch-up (04:15) | 2026-09-28 04:15:23Z | `PENDING` — **5h+** | historical best +26 min |
| Website Manager daily | 2026-09-28 06:33:01Z | `PENDING` — **2h45m+** | +3 to +10 min |
| Spine watchdog | 2026-09-28 08:32:54Z | `PENDING` — 45 min | usually completes same hour |
| Performance review (Sunday) | 2026-09-27 17:31:52Z | `ABANDONED` | **third consecutive week with nothing filed** |
| Weekly review to DK | 2026-09-27 19:02:28Z | `ABANDONED` | DK's Sunday summary did not arrive |
| BD — independent venture generation | 2026-09-22 10:07:00Z | `ABANDONED` | the fortnightly round that was meant to be re-pointed at demand never ran |
| Website — weekly competitor review | 2026-09-27 15:01:32Z → 15:16:35Z | `SUCCEEDED` | **the one round that worked**, filed `claude/web/01a-competitor-review-2026-09-27.md` |
| VC/GC Archive tasks (not ours) | — | `SUCCEEDED` | unaffected — separate project, per DK's 3 September ruling |

**Action taken:** fired `trig_014aF7ic7vNerkaXP1iJxSz2` (catch-up round) manually at 09:17:13Z with context on the stall pattern, per the standing recovery mechanism DK approved 2 September (OPS-20260901-02: "either can be fired on demand"). Result not yet known at the time of this filing — check `project_info` for a new catch-up artefact dated after 09:17Z.

**Nothing else was fired.** Re-firing an already-`PENDING` round risks a duplicate session against the same stalled one; the catch-up round's own job is to assess and recover, so it was the one round manually triggered.

**🔴 CORRECTION, same session: the cause is not the A25 stalling pattern.** DK stated directly: *"I told you — it stopped because I ran out of usage credits."* This round's first pass at this file speculated about a scheduled-task bug and pointed at A25 (ten minutes with Anthropic support) as the fix. **That attribution was wrong and is withdrawn here, in this file, rather than left to stand.** A plain usage-limit exhaustion is exactly the scenario OPS-20260901-02 was written for on 2 September — DK had already told this operation to expect it and built the recovery mechanism (the catch-up round, fired on demand) for precisely this case. **Nothing here required Anthropic support; it required the usage window to reset, which the standing recovery mechanism already exists to handle.** The four rounds still shown `PENDING` in the table above are consistent with sessions that could not run to completion while the account was out of usage, not with a distinct infrastructure fault. **A25's own underlying pattern — individual rounds stalling mid-flight for hours even when usage is available — is a separate, longer-running observation from earlier in September and is not re-asserted or retracted by this correction; it simply is not what caused this week's multi-day blackout.**

## Live-site verification carried out this session (WordPress.com connector, read-only except where noted)

**`activity.get` on `lockedandstocked.co.uk` (blog 257001659), 20 most recent events, read in full:**

- **Post 296 published itself on schedule** via WordPress's own cron at 2026-09-28 ~06:20Z ("England Raised What Water Companies Must Pay You in 2025…") and auto-shared to Facebook, Instagram Business and Bluesky within ~15 seconds, all three carrying `connection_external_display: "Locked & Stocked"` — the brand, not DK. **This runs on WordPress's own scheduler, independent of the Claude scheduled-task infrastructure that is currently failing — the posting floor is not at risk from the outage above.**
- **The site icon is confirmed live-set**: `setting__changed_site_icon`, `old_value: "0"` → `new_value: "238"`. Matches the attended session's claim in `claude/web/13-attended-verification-2026-09-28.md`.
- **The tagline restore is confirmed live**: two `setting__changed_blogdescription` events, `""` → `"Practical preparedness for UK households"`. **A30 is genuinely closed.**
- **Anonymity sweep: clean.** No full name, location, employer, or personal detail in any of the 20 events or the post/publicize payloads. Author fields on record (`davekirk83@gmail.com`, display name "L S") are unchanged internal metadata, not published on the site, and already tracked in the standing brief.
- Remaining events are routine platform noise (theme-update notices, full-site backups) with `wpcom_user_id: -1`.

## Dispositions

- **A30 — CLOSED.** Tagline restored and verified live twice over (the attended session's own check, and this session's independent `activity.get` read).
- **wp-admin sitting — reduced to one item, per `claude/web/13-attended-verification-2026-09-28.md`, confirmed above.** Items 1 (Rank Math pairs — demoted, the site already generates good ones), 2 (author/display names — unchanged, still open separately), 3 (site icon — CLOSED, live-verified) are resolved or demoted. **What remains: the homepage `og:image` field (no connector path found) and regenerating media 239 at true 1200×630 before it's wired in** (it is currently 800×420 — clears Facebook's minimum but is undersized).
- **The three "impossible from here" claims corrected this morning (`og:*` tags, site icon path) are independently confirmed rather than taken on trust** — this session's own `activity.get` read shows the icon change landed, and the homepage `<head>` claim was not re-tested here but is not contradicted by anything found.

## What was not attempted this session

Full anonymity sweep of all four published pages (only the activity log was checked, which is a strong but not complete proxy) · a rewrite of `claude/00-dk-standing-brief.md` or `claude/01-team-roster.md` (both ten-plus pages; a rewrite under outage pressure is how this operation has previously introduced errors — CHECK 21) · re-tasking the BD round or the performance review (OPS-029 authority questions, not urgent enough to resolve blind) · anything on Capital, Music or Profession (no evidence any of them needed attention this session).

## What to check next (OPS-20260831-04)

`project_info` for a catch-up artefact dated after 2026-09-28T09:17Z, now that DK confirms usage is available again · `list_triggers` for the same four rounds shown `PENDING` above, to see whether they resolve now that the account is no longer out of usage, which would corroborate DK's stated cause · `claude/06-approvals-queue.md`, updated in the same session, for A30's closure and the wp-admin sitting's reduction.

**No scheduled task was created, altered, enabled or disabled (OPS-029) beyond the one on-demand fire of the existing catch-up trigger.** No live property was written to. Nothing published. No figure invented — every number above is a tool reading.
