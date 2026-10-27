# Reporting log — archive, 17 September 2026 (entries below the 21:04 consolidation)

**Moved here verbatim on 2026-09-18 by the nightly consolidation, under the rule that page adopted on 17 September: the live log holds the current day's entries plus the entry closing the previous day; everything older moves to a dated archive.** Nothing was edited, condensed or deleted. The 17 September 21:04 consolidation entry — the entry that closes that day — **remains in the live log**, not here.

---

## 🔴 CORRECTION, 2026-09-17 17:4x, by the round that made the error — **the day brief below was first published with three wrong identifiers, and is corrected here rather than quietly edited.**

**What went wrong.** That round stalled for nineteen hours. On waking it wrote its day brief from the approvals queue as that queue stood **before** the stall — the `2026-09-15` version — and allocated `A33`, `A34` and `A35` to items of its own. **In the interval, the 17 September catch-up round had already swept its abandoned work and had already issued `A33` (the Zapier Reddit rail) and `A34` (the Mumsnet paste and the uk-preppers rules look).** The first version of the brief therefore put a live ask to DK under a number that already meant something else.

**Caught by re-reading the queue before finishing, which is the only reason it did not stand.** This is the exact failure named at the top of this role's own tasking — *"when you ask me to do ANYTHING, make sure it hasn't been done yet"* — committed by the role that enforces it, and caused by a specific, avoidable thing: **a twenty-hour-old read treated as current.** A stalled round's context is stale by definition and every page it intends to write must be re-read on waking, not just the one it is writing.

**And the catch-up round was right on a point of substance that round got wrong.** It declined to put the spine-watchdog amendment to DK at all, because **OPS-029 already grants the Sunday performance review authority to *"add a constraint, check or required source"* to a prompt.** It is delegated, not DK's. **There was no `A35` then.** The amendment sits with the performance review on 20 September, and that round's "promote as A35" disposition was withdrawn in full. ⚠ **`A35` was allocated for the first and only time on 17 September at 21:2x, to the Jetpack Social platform expansion — an unrelated item. The withdrawn allocation never reached DK and never existed on the queue.**

---

## 2026-09-17 17:2x (UK) — nightly consolidation of 16 September, CLOSED. **⚠ That round stalled for 19h40m mid-flight and closed 20 hours late, three and a half hours before its successor fired.**

**Clock:** start `Wed Sep 16 21:04:01 BST 2026` (fired `20:03:50Z`, latency ≈11s, clean). **Resumed `Thu Sep 17 17:25:44 BST 2026`.** **Total elapsed 20h22m; actual work ≈50 minutes.**

**⚠ See the CORRECTION block above before reading on.** Three identifiers in this entry's first version were wrong and one disposition was withdrawn in full.

**⚠ THE STALL, measured rather than estimated.** The last tool call of 16 September completed at approximately `20:4xZ`. The next tool call to return — an `update_trigger` — is stamped `2026-09-17T16:25:29Z`. **Approximately 19 hours 40 minutes between two consecutive tool calls, with nothing inside the session detecting it.** A25 shape 4.

**🔴 A GENUINELY NEW OBSERVATION, which changes what a status means.** `list_triggers`, read fresh at `17:26Z`, recorded that round's run as **`ROUTINE_RUN_STATUS_ABANDONED`** with no `finished_at` — **while the session was alive and successfully executing tool calls.** Every prior entry in this record treats `ABANDONED` as terminal. **It is not.** ⚠ **Confirmed twice over by 21:0x the same day: the Capital research round, recorded `ABANDONED` that morning, reads `SUCCEEDED` with `finished_at 16:30:04Z` on the evening's read. `PENDING` → `ABANDONED` → `SUCCEEDED` on a single run. Only a project write time settles whether a round ran.**

**🔴 AND THE STALL'S REAL COST, which is not the lost time.** A stalled session wakes holding a snapshot of the record from before it slept, and **everything it then writes is built on a stale read unless it deliberately re-reads.** **On waking from a stall, re-read every page you intend to write, not only the one you are in.**

**✅ The 00:32 watchdog was right about that round in every particular, and right to leave it alone.** It found the stall by hand, correctly called the `[IN PROGRESS]` entry orphaned, correctly declined to re-run the sweep on two-author grounds. **And the 04:15 catch-up round then did the whole abandoned sweep properly.**

### §4 answers, 16 September

**Website Manager: no, but it produced the first finished distribution asset this operation has ever had.** `07-distribution-pack-2026-09-16.md` tested five UK communities against their own written rules and produced paste-ready copy for the one that permits it. **Nothing was posted, because every route needs a registered account and that is Rule 5.**

**Head of Capital: no, and it closed a route rather than opening one.** `41-venue-recosting-2026-09-16.md` re-priced the full suite against four real venue fee schedules and retired the "a cheaper venue would fix this" hypothesis with a number — best deflated Sharpe 0.0034 at the cheapest venue against a required 0.95, and all 23 surviving cells fail the random-entry benchmark. **A good negative result.**

**§4(b): the Mumsnet copy, and nothing else.** Everything else produced in those two days was the operation examining itself.

### What that round did

**1. ✅ CORRECTED A LIVE PROMPT WITH A THIRTEEN-DAY FUSE — `trig_019PnFkJ6mv3GuuJaxLgEYvr`, "Locked & Stocked — 30 Sept launch review".** It fires 30 September 08:00 UTC and still asked *"Is the site public, or still in coming-soon mode…?"* with a full escalation branch for briefing DK on why the launch had drifted. **DK launched the site himself on 29 August, three weeks early.** Applied within the OPS-029 stale-fact carve-out; original tasking retained verbatim below it, marked superseded. **Verified 395 → 746 words, `updated_at 2026-09-17T16:25:29Z`, re-read from an independent fresh `list_triggers` call.**

**2. ✅ CLOSED THE STANDING-BRIEF PROPAGATION JOB, on a live count — 17 of 22.** The five excluded: two VC/GC Archive tasks (DK: *"No thank you. Keep them distinct."*), Sightline and Business Development (dormant, no cron), and Health & Medical (that job's own explicit exception).

**3. ✅ ANSWERED THE BUSINESS DEVELOPMENT DUPLICATE-ROUND QUESTION.** From a fresh `list_triggers` read: **only ONE BD task fired** — `trig_01YJcKBLzNEZqQdWBejP8NYN`, `09:06:44Z` → `09:29:04Z`, `SUCCEEDED`. The other has not run since **30 August**. **No two sections were commissioned onto the same work; there is no roster change to make.** And **neither task's cron called for a run on 17 September** — the fortnightly task's cron is `0 10 8,22 * *`. **`[ASSUMPTION]`, marked as one: the same task appears to have been fired by hand twice.** What is not an assumption: the destroyed filing is real, `project_write` has no locking, and the losing round recovered its work only because it verified its write.

**4. ✅ LIVE SITE CHECK, both properties.** 15 events on Locked & Stocked since 15 September; everything on 16–17 September is the platform. **The 15 September weekly post engine scheduled post 283 and created draft 286, both accounted for.**

**5. 🟡 REDDIT IS UNREACHABLE FROM HERE BY EVERY ROUTE, WHICH WEAKENS `A33`.** `WebFetch` refused on both hosts; domain-restricted `WebSearch` rejected by the proxy (HTTP 400); unrestricted `WebSearch` returns no subreddit. **Marked `[UNVERIFIABLE FROM HERE — re-test monthly]` per CHECK 20.** **The rail cannot satisfy its own first safety condition without DK vouching for each subreddit's rules.** A33 demoted, not withdrawn.

**6. 🟡 `uk-preppers.co.uk` rules — a third attempt, also 404.** ⚠ **Overtaken 17 September: the Website Manager found the forum's binding registration terms at a different URL and read them in full. See A34(b).**

**7. 🔴 A SELF-CAUGHT ERROR IN THAT ROUND'S OWN ARITHMETIC.** The first count of standing-brief pointers returned "0 of 22" — an operator-precedence bug in its own script. **Caught because the result was implausible.** Corrected to 16 before the fix, 17 after. **Rule 4 binds this role's numbers exactly as it binds any section's.**

**Dispositions that round made, and which stand:** the BD "two sections on one commission" diagnosis **REJECTED ON THE EVIDENCE**; the BD standing-check proposal and the spine-watchdog amendment both **ROUTED to the Sunday performance review**; the BD recommendation to stop commissioning origination rounds **ENDORSED AS AN ASSESSMENT, no action (OPS-029)**.

---

## 2026-09-17 10:2x (UK) — ⚠ **TWO Business Development origination rounds ran this morning, simultaneously and independently. The second one's filing was silently overwritten by the first's.**

**Clock:** `Thu Sep 17 10:21:15 BST 2026` / `09:21:15 UTC`.

**What happened, from write times rather than inference.** A second BD session ran the same commission and wrote its results into `claude/capital/11-bd-ideas.md` at approximately `09:19Z`. When it verified that write by `project_search` (OPS-20260830-03), **the register came back holding the other session's round, written at `09:21:46Z`, which had replaced it.** The same then happened to this file. **Nothing was restored over the other round.**

**Where the second round now lives: `claude/capital/11b-bd-ideas-2026-09-17-parallel-round.md`.** It killed three different candidates — NHS trust board papers, an archive of superseded UK statutory guidance, and Companies House scanned charge instruments — all three `KILLED`, with four-part scoring, the strongest argument against each, a pre-screen list and a "could not establish" block.

**Three things in it that are additive:**

1. **The Apify figures the other round recorded itself as unable to obtain.** The "UK Company Charges Search" actor's parent page, as displayed 17 September: **from $2.97 / 1,000 results · 2 users · 1 monthly active user · 12 total runs · 0 bookmarks · 0.0 rating, 0 reviews.** Reproduces the 8 September demand finding on a different source, nine days on.
2. **A natural experiment.** `boardpaperscraper.com` — one operator, AI reading long public PDFs, sold to a named professional audience — states on its own page: *"Board Paper Scraper read NHS board papers so suppliers didn't have to. We're winding it down."* **No reason published `[UNVERIFIED]`; recorded as a data point about the shape of the bet, explicitly not as proof of failed demand.**
3. **The same conclusion, reached separately.** Both rounds independently killed the Companies House charge-instrument idea on the same fact, both closed the paper-and-microfiche frontier on physical-presence grounds, and **both independently recommend that origination rounds stop until the demand question gets one of its own.**

**🟠 THE DEFECT, for the Operations Manager.** Two sections appeared to be commissioned onto the same work; `project_write` has no locking, no append and no version history, so the loser of a race is destroyed silently. ✅ **ANSWERED by the consolidation, 17 September: only ONE BD task fired, and neither BD task's cron called for a run that day. Not a roster defect.**

**Nothing registered, purchased, published or committed to. No identifier allocated. No scheduled task created, altered, enabled, fired or deleted. No live property touched.**

---

## 2026-09-17 — Business Development, second independent origination round — **three candidates examined, all three KILLED, and the round closes the frontier the 8 September round left open rather than restating it.**

Read first, in order: `claude/00-dk-standing-brief.md` (OPS-20260831-02, the four-part test), `claude/capital/11-bd-ideas.md` and `claude/capital/15-claude-ecosystem-gaps.md`. **Candidates were deliberately chosen on the unscrapeable side of the line the 8 September round drew** — a statutory register held by ~350 separate bodies (Licensing Act 2003 premises licences), a corpus no scraper can reach because the documents do not exist until somebody asks (NHS trusts' FOI disclosure logs), and several million free image-only scans (Companies House filed charge instruments). Full write-ups in `claude/capital/11-bd-ideas.md`.

**The finding, which is worth more than the three kills.** The 8 September round priced the *scraping* of public data at `$2 per 1,000 records` and said its finding stopped at sources a scraper cannot reach. **It does not stop there: where a source cannot be scraped, the ASK has been commoditised instead, and this round priced it in all three cases** — Licensing Act 2003 s.8 obliges every licensing authority to make its register available for inspection *"without payment"*; mySociety's WhatDoTheyKnow Pro sells batch requests across a stated 43,174 authorities at **£20 per user per month, or £200 annually**; and Companies House's free `chargeDetails` resource already publishes the fields a lender screens on. **A tedium moat only exists where the buyer cannot cheaply commission the same result directly, and for UK public information they almost always can — because the statutes that make it public also oblige somebody to hand it over.** Two frontier items closed rather than deferred: paper-only council planning microfiche needs physical presence, which DK's 2–5 hours a week cannot supply; and manufacturing a dataset via batch FOI fails because WhatDoTheyKnow describes private requests as confidential *"for up to a year"*, so the asset is public by design and the moat expires on a published schedule.

**The recommendation on the record.** Three independent origination rounds have now run — 31 August, 8 September and today. **Eleven written-up candidates, none surviving, and the terminal cause in the clear majority was that there is no buyer this operation can reach.** The hard limits are demonstrably not the binding constraint: both recent rounds ran entirely outside DK's domains and still returned nothing. **The recommendation is to stop commissioning origination rounds until the demand question has had one of its own**, because a round that cannot end in a business regardless of what it finds is a round whose answer is already known.

**⚠ Honest limit on this round's evidence.** `WebFetch` on `apify.com` returned `PROVENANCE_REQUIRED` — the permission request went unanswered, which is what an unattended scheduled round should expect. **Nothing was routed around: no curl, wget or python against any blocked domain.** *(⚠ Added by the parallel round: those counts and prices were obtained — see above.)*

**Nothing registered, purchased, published or committed to. No identifier allocated — the section proposes, the Operations Manager numbers.**

---

## 2026-09-17 01:32 (UK) — spine watchdog, 00:32 UTC round — **one stall found. Nothing perishable at risk. Nothing re-run. Nothing put to DK.**

**Clock:** `Thu Sep 17 01:32:30 BST 2026` / `00:32:30 UTC`. **Fired `2026-09-17T00:32:20.991Z` — start latency ≈ 10 seconds, clean.** Second clock read `00:35:07 UTC`, no gap (CHECK 10 point 6).

**Full record: `claude/09-spine-watchdog-log-2026-09-17-0032.md`.** Filed as a dated file as well as here because the entry above it was an open `[IN PROGRESS]` marker from a session that might still hold its own copy of this document — **a second author on this path is how this file's history was destroyed on 15 September.**

**🟠 THE FINDING. `trig_01VUr2dPo5o18jq41uSXgBDb` — the nightly consolidation — fired `2026-09-16T20:03:50.933Z`, wrote its opening entry at `20:06:41Z` (2m50s in), and had written nothing since.** Still `PENDING` on two independent `list_triggers` reads, `00:32:30Z` and `00:35:07Z` — **+4h31m.** ✅ **RESOLVED 17 September 17:2x: that session woke after 19h40m and closed itself. The watchdog's reading was correct in every particular and its decision not to re-run the sweep was right.**

**How it was caught, which is the part worth keeping.** The 16 September catch-up round diagnosed a false negative in this watchdog — `PENDING` with nothing written is indistinguishable, at a status-only check, from `PENDING` and working — and proposed a STEP 1 amendment it correctly declined to apply itself. **That amendment is still unapplied. This round ran the check by hand instead — `project_info` write times for every round `PENDING` more than an hour past its firing — which is the only reason this stall was logged as a stall.** ✅ **ROUTED 17 September to the Sunday performance review, which holds the OPS-029 grant.**

**✅ The CHECK 19 test left by the prior round is answered: YES.** `claude/capital/41-venue-recosting-2026-09-16.md`, `2026-09-16T10:52:15Z`, after a ~9h18m delayed wake. **16 September does not join 13 and 14 September as a blank night.**

**✅ Perishable data (CAP-024) safe, from the artefact not the status.** The daily check-in ran `20:10:28Z`→`20:28:02Z` and filed `btc_4h_archive.csv` at `2026-09-16T20:20:39Z`. **No 4h candles at risk of ageing out.**

**Why nothing was re-run:** nothing the consolidation produces is perishable · shape-4 stalls have resumed and filed correctly three times in four days · it fires again at `20:03Z`, with the catch-up round at `04:15Z` before it. **Not escalated: broken, but not expiring.**

**Nothing re-run, re-fired, created, altered, enabled or deleted. No trigger touched. No live property touched. No order, credential or order-placement path anywhere in this round (CAP-021).**
