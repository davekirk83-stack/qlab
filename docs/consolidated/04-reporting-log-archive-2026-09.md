# Reporting log archive — 13 September to 3 October 2026 (condensed)

Condensed on 27 Oct 2026 to free project space. Full verbatim copies of all 41 source logs are in the GitHub repo davekirk83-stack/qlab under docs/reporting-log-backup/.

Sources merged here: 04-reporting-log-2026-09-13-spine-outage, -09-15-catch-up, -09-22-web-weekly, -09-27-web-competitor-review, -09-28-attended-recovery; archives -09-15-to-16, -09-17, -09-18, -09-20, -09-21, -09-29-to-10-03. Where the same day appeared in several files, the entries are merged. The Health & Medical brief was not opened by any round in this period.

## Key decisions and rules this period

**DK's decisions and instructions (verbatim)**
- 2 Sept (cited as the basis of OPS-20260901-02, the watchdog and catch-up recovery mechanisms): *"If we hit a usage limit again, ensure that this operation resumes asap after the limit resets."*
- 3 Sept (cited throughout, about the VC/GC Archive and later his other projects): *"No thank you. Keep them distinct."*
- 14 Sept: *"I have no intention to implement your suggestions here."* Declined a direction the Capital weekly prompt was still telling the round to pursue. A29 closed, not to be re-raised. Written into the Capital weekly prompt on 15 Sept.
- 15 Sept: approved four efficiency recommendations ("Do the above, as you suggest"): trim the bloated prompts, add CHECK 20, open A32, batch questions to him.
- 16 Sept: *"we have to keep it posting on L&S at least once a week, any social posting has to be in tandem or in addition to this."* Added as the new top section of the Website Manager daily prompt (a 7-days-since-last-post check before anything else).
- 18 Sept, to the Head of Capital: *"Tell him to forget the costs. Just focus on quality strategies that work."* / *"He's using it as an excuse to do nothing."* / *"Reopen every strategy he tried regardless of costs, just win rate, probability, quality of signal etc."* Put into the Capital research prompt as its only job. Not filed to the record until that night's consolidation.
- 21 Sept: *"remove the existence of the head of capital, it's been a total waste of time and energy"* / *"make it stop"* / *"do it now"*. Four Capital triggers disabled, plus claude/09-capital-section-closure-2026-09-21.md. Reached the standing brief only at the 21:0x consolidation.
- 28 Sept: *"It ran out of usage. Continue now as best you can."* and *"I told you — it stopped because I ran out of usage credits."* (cause of the 22–27 Sept blackout).
- 29 Sept: *"The quality of the title image lettering is very poor on our homepage and looks pixellated."* Root-caused and fixed the same day.

**Rules, checks and standing practice adopted, changed or withdrawn**
- CHECK 20 (15 Sept): a route that has failed the same way for two or more weeks is marked `[UNVERIFIABLE FROM HERE]` and re-tested monthly, not every round. 18 Sept: the HTTP-only redirect loop (WebFetch forces HTTPS) is marked `[UNREACHABLE FROM HERE — permanent]` (Website 35).
- WEB-20260915-01 (15 Sept): okayyouwin.com reassigned. The Website prompts were corrected to match.
- CAP-20260915-01 replaced the retired 0.95 deflated-Sharpe bar.
- Reporting-log split rule (17 Sept): the live log holds the current day plus the entry closing the previous day. Everything older moves verbatim to a dated archive. 21 Sept addendum: never summarise an entry out of the main log; move it verbatim.
- Status is not evidence (A25): `ABANDONED` is not terminal, and one run went `PENDING` → `ABANDONED` → `SUCCEEDED` (17 Sept). Only a project write settles whether a round ran.
- On waking from a stall, re-read every page you intend to write (17 Sept).
- Before writing to a scheduled prompt, check that no other round is `PENDING` mid-flight (15 Sept).
- Proposed 22nd standing check rejected as a duplicate of CHECK 16 (17 Sept).
- Spine-watchdog STEP 1 amendment (proposed 16 Sept: a round `PENDING` more than 1h past firing with no artefact counts as missed). Routed 17 Sept to the Sunday performance review, which holds the OPS-029 grant to "add a constraint, check or required source". Not applied in this period.
- Nextdoor permanently killed for Jetpack Social (17 Sept). Personal profiles are real-name and address-verified, so connecting it would breach WEB-20260831-02. This was the first off-site application of the anonymity rule.
- Website 34 (18 Sept): author new posts as block markup so they stay editable. Corrected 22 Sept: editability comes from the `<!-- wp: -->` delimiter comments, not the authoring date.
- Website 36 (18 Sept): the traffic baseline is restated as about six visitors a week.
- Working rule 20 (21 Sept): re-read the number before you repeat the alarm.
- 21 Sept: when a finding is corrected, first correct anything already in DK's hands that states the old version. Writing a satellite document is not filing a decision (sharpening of OPS-20260901-01 rule 4).
- Website 40 (21 Sept): `PROVENANCE_REQUIRED` is an unanswered permission prompt, not a blocked host. "Reddit is unreadable by every route" withdrawn.
- Search-first fetching (22 and 27 Sept): search for the URL, then fetch the URL the search returned. Five pages were read this way on 27 Sept. Not yet in the governing files at period end.
- Proposal 46 (22 Sept): the posting floor counts as Amazon compliance, not traffic progress.
- 29 Sept: the ~4,000-character base64 upload rule is retired. Uploads go `media.upload` → multipart POST → `media.create`, then verify the SHA-256 of the served file. Accepted as the CHECK 2 replacement (not written into the checks file until 8 Oct).
- 29 Sept: "no round can read a scheduled task's prompt" asserted. **Withdrawn 8 Oct** (prompts are at `derived_state.prompt`; OPS-032 had said so since 30 Aug).
- 21 Sept "17 of 23 prompts carry the standing-brief pointer" withdrawn as uncheckable on 29 Sept.

## 2026-10-03
- No round filed anything on 2 or 3 October.
- Profession monthly round `FAILED` after 6 seconds on 3 Oct. Shown on 8 Oct to carry `failure_reason: USAGE_LIMIT_REACHED`.
- Post 302 published on 2 Oct still carrying the old pixellated cover and auto-shared to three channels. A38 expired unanswered.

## 2026-10-01
- Nightly consolidation wrote its marker at 20:14:52Z and nothing else. Its promised satellite never existed. Fourth consolidation in eight days to die this way (27, 28, 30 Sept, 1 Oct).

## 2026-09-30
- Nightly consolidation died. Its IN-PROGRESS satellite is the only record.

## 2026-09-29
- Cover images: DK's pixellation complaint traced to the post cover cards, not the header. 16 of 20 live covers had only two or three colours because the generator hard-thresholded letter edges. Six were replaced and verified. Media 318 (the post 302 cover) was uploaded but not attached.
- A38 opened: attach media 318 to post 302 before 2 Oct. It expired (see 3 Oct).
- A37 opened: okayyouwin.com's administrator display name reads "Locked & Stocked". Answered 5 Oct as having no public rendering.
- A30 (tagline) and A26 came off the list.
- Dispositions: base64 rule retired; served-SHA-256 CHECK 2 accepted; the Family A re-render folded into W-IMAGERY-1 (superseded 5 Oct, when all 22 covers were rebuilt); converging cover families not promoted (a design decision, Rule 5); deleting corrupt media 311 and 98 left as DK's (irreversible, CHECK 8).
- Standing brief condensed from about ten pages to five. Approvals queue and status board rewritten. Archive -09-21 created.
- Live site: page 199 "TEMP render test" deleted 14:13:04Z, actor 151173282 `is_cron: true`. No filed round accounts for it; not attributed. Manifest showed 20 posts and 4 pages.
- Not done: the PROPOSED blocks in web/12-round-2026-09-22 and the 27 Sept competitor review stayed undispositioned until 8 Oct.
- No weekly review reached DK on Sunday 27 Sept.

## 2026-09-28 (attended recovery)
- DK asked "what next". The record was seven days stale (last written 21 Sept).
- Outage confirmed: total silence from 22 Sept 12:35Z to 27 Sept 04:34Z (4 days 16 hours). Rounds were still stuck afterwards: consolidation 13h+ `PENDING`, catch-up and Website daily `PENDING`, Sunday performance review `ABANDONED` (third consecutive week), weekly review to DK `ABANDONED`, and the 22 Sept BD round `ABANDONED`. Only the 27 Sept competitor review worked.
- Catch-up round fired manually at 09:17:13Z under OPS-20260901-02.
- The first attribution of the outage to A25 or a scheduler bug was withdrawn on DK's statement that usage credits ran out.
- Live site: post 296 self-published about 06:20Z and auto-shared to Facebook, Instagram and Bluesky as the brand. Site icon set (0 → media 238). Tagline restored to "Practical preparedness for UK households". **A30 closed.** Activity-log anonymity check clean.
- wp-admin sitting reduced: the Rank Math pairs item demoted; site icon closed; the author/display-name item still open. Remaining: the homepage og:image, and regenerating media 239 at 1200×630 (currently 800×420).

## 2026-09-27
- Weekly competitor review (Review 5) was the only round that worked:
  - PreparedBritain trackers read *"Last checked 27 September 2026, 13:06"* and UK Prepper Hub's brief ran on 25–27 Sept. The WEB-20260830-02 hold is lifted, and proposals (h) and (j) are closed without DK. (j) was moot because the cause was the method, not the slot.
  - Get Prepped Now found: an anonymous, Amazon-affiliate UK prepping site with a live-signal layer, i.e. L&S's model already built.
  - Proposal (f) re-ranked Medium → High: label the okayyouwin.com contact address by purpose.
  - Note for DK, not an ask: keep `okayyouwin.com` renewing. marsredsky.net shows what happens to a lapsed band domain.
  - Three self-corrections, all "search-tool output mistaken for the world".
- The consolidation's marker noted the 22–27 Sept silence, then stalled and never closed.

## 2026-09-22 to 2026-09-26
- 22 Sept, weekly post engine:
  - Post 302 scheduled for 2 Oct 15:38 BST (police advice on security lighting).
  - Reserve draft post 304 written (home safes and insurance cash ratings), closing the reserve-draft gate.
  - Met Office: no warnings for the week.
- Traffic 16–22 Sept: **8 views / 7 visitors**, against a launch-week baseline of 26/23, with 20 posts live after 24 days. The section dropped its "more posts" recommendation, because the 1 Sept round's 15 Sept checkpoint had passed with traffic still in single digits.
- Binding constraint: DK's 14 Sept Search Console screenshot showed **45 pages "Discovered — currently not indexed"**. Amazon content-recency lapses around 27 Oct. Three qualifying sales by 23 Feb 2027 (154 days out) are unlikely on the current trajectory.
- Proposal 45: Reddit cannot be reached search-first either. Domain-filtered WebSearch returns HTTP 400 and unfiltered search returns no reddit.com result. Marked attended-session only.
- Anonymity sweep clean, 15th consecutive (partial sweep). The dead About CTA has been live 25 days.
- Found on 8 Oct: the 22 Sept Website round had already corrected the Mumsnet paste in web/07-distribution-pack (five wrong compensation figures and a dead Ofgem link fixed). It also created 13 tag terms and applied them to posts 286 and 296.
- The BD round fired 22 Sept and was recorded `ABANDONED`. It woke and filed on 7 Oct.
- 22 Sept 12:35Z onward: total silence until 27 Sept (DK's usage credits ran out).

## 2026-09-21
- **Capital closed by DK** (quote above). The four Capital triggers were disabled. The standing brief, roster, status board and queue still described the section as live until the 21:0x consolidation rewrote them. This was the fourth decision in eight days to reach a prompt, chat or side document but not the record (14, 18, 20, 21 Sept).
- Pine files corrected at the artefact (header commentary only, no code changed), using doc 48's matched benchmark:
  - DONCHIAN_20: −0.1715 R, t = −3.28, p = 0.0036. Worse than random, so "the single best entry signal on file" was withdrawn.
  - DONCHIAN_55: −0.3283 R, t = −6.48.
  - TSMOM_60: +0.1852 R, t = +2.39, p = 0.026, and labelled NOT an edge (p ≈ 0.31 corrected for twelve, against 434 trials).
- Store:
  - Readings: 1,912,102 (95.61%) at 04:29Z, 1,904,895 at 11:30Z, 1,909,772 at 12:32Z, then **1,407,929 (70.40%, 592,071 free)** at 20:0xZ.
  - Causes: DK disabled the nightly Capital research round (41,037 bytes on its last night). Separately, **about 502 KB was removed between 12:32Z and 20:0xZ** by an actor that could not be established (bulk backtest CSVs and run logs; btc_4h_archive.csv gone). Not attributed.
  - Everything DK holds survived, including all seven Pine files.
  - A36 (opened 04:3xZ as the top item, with a 0.8–1.3 day runway) was demoted below A33, and A25 returned to the top. Working rule 20 adopted.
- Website 40: `PROVENANCE_REQUIRED` is a permission timeout. A33's "Reddit unreadable" claim withdrawn. **A34 suspended**: the paste cited an unverified Ofgem URL with figures last read 16 Sept. Found on 8 Oct to have been fixed on 22 Sept.
- Website 25 (share-link fix) closed as unfixable from here, and G-SOCIAL-1's "gate now open" note withdrawn.
- Traffic 14–20 Sept: 8/7, not comparable because post 283's publication fell in that window. A30 corrected to eight days, not nine.
- No live prompt over 1,500 words: the 1,791-word Capital weekly was disabled.
- Weekly review (week ending 20 Sept), filed about 16h late after a stall:
  - Eight rounds died in two days.
  - The performance review is enabled but filed nothing.
  - The OPS-20260831-05 provenance audit stands at 21 days, four owners, zero starts.
  - Recommendation: give one round the demand question. Three origination rounds have killed eleven candidates, mostly for lack of a reachable buyer.
- Okayyouwin.com's first live date of the run (26 Sept) was noted as owned by no section. DK had not touched either live property since 15 Sept.

## 2026-09-20
- Competitor review 4: first-page results for the site's own topics are held by manufacturers and retailers (EcoFlow; EVAQ8; nine of ten PAS 24 results are door and window makers). Its conclusion: *"the content that can rank is the content that does not sell, and the content that sells cannot rank."* Accepted as a brake on writing more "best X" guides.
- Proposal (h) closed without DK: PreparedBritain trackers read "Checked 20 Sep 2026" with 15 signals (13 on 30 Aug), and UK Prepper Hub's brief was dated 12–14 Sept.
- Capital:
  - Doc 46: seven TradingView Pine scripts handed to DK to keep regardless of the section's fate. The missing seventh file (1_HoC_Gooner_SFP.pine) was recovered by its owner at 16:09Z.
  - Doc 47 (combined signal): 633 trades on 10 instruments, **+0.107 R/trade gross (t = +1.81, p = 0.071), +0.056 net (p = 0.35)**. BTC and ETH carry 86% of gross profit; the other eight are +0.019 R gross and negative net.
- Four rounds fired and filed nothing: Website daily, the 16:32 watchdog, the Sunday performance review (carrying six routed jobs) and the weekly review. None was re-fired.
- Store 1,896,825 (94.84%). The status board's "fuse of about a day" was corrected that night, then re-instated by the 21 Sept catch-up, then rendered moot (see 21 Sept).
- A31's first half closed: post 283's Facebook and Instagram shares carry the `jetpack-sync-actions` string where the link belongs; Bluesky is clean.
- 19 Sept: post 283 published by cron at 19:52 BST and auto-shared to three channels within 38 seconds, as the brand. This was the first unattended publish-and-share. Posting floor covered to 5 Oct. Manifest: 18 posts, 4 pages.

## 2026-09-18
- **DK's cost-blind instruction to Capital** (quote above). Found by reading the live prompt (edited 14:23Z and 17:38Z). It was filed to the standing brief that night, which repaired a breach of OPS-20260901-01 rule 4. The trial count stands at 434 (407 → 434).
- **Traffic correction:** the "145 views/week" figure was about 96% crawler traffic on 10 Sept (derived from two windows, not a measured split). The clean window 11–17 Sept was **7 views / 6 visitors**, adopted as the baseline.
- Website daily ran clean in 15 minutes. Post 286 scheduled for 24 Sept, covering the floor to 1 Oct. Live classic posts cannot be block-edited; posts authored since about 15 Sept can.
- Capital research round of 18 Sept died with nothing filed. Not re-fired.
- DK was active but the site had no human event since 15 Sept: A30, A31, A33, A34 and A35 all unanswered. 17 published posts, 4 pages.
- Standing brief: stale figures fixed (317 → 434; CAP-20260915-01). Still about ten pages long.
- The Capital weekly prompt (1,791 words) was the only prompt over 1,500 words. Its trim was routed to the performance review.

## 2026-09-17
- The 16 Sept consolidation stalled 19h40m mid-flight and closed 20h late. Platform status went `PENDING` → `ABANDONED` → `SUCCEEDED` on one run.
- Identifier correction: the stalled round allocated A33–A35 from a pre-stall copy of the queue. A33 (Zapier Reddit rail) and A34 (Mumsnet paste and uk-preppers rules) had already been issued by the catch-up. A35 was later allocated, for the first time, to Jetpack Social → Threads, Mastodon and Tumblr. The spine-watchdog amendment went to the performance review, not to DK.
- The LS-023 "30 Sept launch review" prompt was corrected under the stale-fact carve-out: DK launched the site himself on 29 Aug.
- Standing-brief propagation job closed: 17 of 22 prompts carry the pointer, with five deliberate exclusions.
- Two BD origination rounds ran in parallel. One overwrote the other in 11-bd-ideas.md; the second was recovered as 11b. Only one BD task actually fired, so there was no roster defect.
  - Findings: Apify charges search actor "from $2.97 / 1,000", with 2 users. boardpaperscraper.com is winding down. WhatDoTheyKnow Pro is £20 per user per month.
  - All candidates killed. Recommendation: stop origination rounds until demand gets a round of its own (11 candidates, none surviving).
- Capital doc 42 (resting-order liquidation): 35,451 trades across 27 cells. It failed decision rule 5 of 6, and the gradient ran opposite to the hypothesis (−18.85% on cascade days, +22.61% on up days). Trials 407 → 434; best deflated Sharpe 0.0000.
- Website 08 distribution round: Reddit unreachable (later withdrawn). The uk-preppers.co.uk registration terms were read: no rule against links, so A34(b) was narrowed to a note.
- Status board rebuilt. Two false A25 rows corrected (Capital research and Website daily had in fact succeeded). A35 promoted above A33. Nextdoor killed.
- 00:32 watchdog caught the consolidation stall by hand. Perishable candles were safe.

## 2026-09-16
- DK's posting-floor rule (above) applied to the Website daily prompt.
- Capital doc 41 (venue re-costing against IBKR, Coinbase, Kraken and PrimeXBT): crypto trend survives costs, but all 23 cells fail the random-entry benchmark, and the best deflated Sharpe is **0.0034 vs the required 0.95**. The "cheaper venue would fix it" idea is retired. The holdout cannot test CAP-THRESHOLD-1 requirement 5. Revenue £0, 106 days to the 31 Dec milestone.
- Website doc 07 (distribution pack):
  - Community rules: MoneySavingExpert and P2S ban self-promotion. Mumsnet Preppers is a live target, with paste copy written. The uk-preppers rules page returned 404.
  - Routes: WebFetch was refused on Reddit. No connector can re-share to socials. Zapier has a Reddit app with write actions, which DK would need to authorise.
- The catch-up found Capital nightly research filed on only one of four nights (13 and 14 Sept blank; 16 Sept resumed after a ~9h18m delayed wake). The watchdog had read `PENDING` with no artefact as healthy, which was a false negative.
- DK pressed "update" on two stalled sessions. Both completed shortly after; not verifiable from here.

## 2026-09-15
- The catch-up found no failed round to recover, but **two healthy rounds were deleted from the roster**: News Analyst nightly (trig_01SgVUwYSBdqvPoes4fEBFQU) and Music & Social Media daily (trig_01JKVX8dzwRRgXCNbq4jtHei). The task count went from 23 to 21. Both prompts are preserved verbatim at claude/09-roster-deletions-2026-09-15.md. Not recreated (OPS-029). DK was asked by push: deliberate, or restore? Who deleted them was not established. Both sections were later recorded as dissolved by DK on 15 Sept.
- **A27 closed:** the Sunday performance review re-enabled at 13:23:31Z (settled in chat, outcome not on record).
- Capital prompts corrected (stale-fact carve-out):
  - Trial count 287 → 353.
  - Cost "0.73R either way" replaced by 0.477–1.239R, mean 0.764R.
  - Watch-only list retired.
  - DK's 14 Sept refusal quoted in place of an instruction to pursue it.
- The catch-up itself stalled twice (9h25m and 7h24m) and was recorded `ABANDONED` while still writing. This is the sixth shape of A25.
- system/portfolio_measure.py line 32 cannot be imported (flagged to Capital).
- 15 Sept consolidation (DK-approved efficiency pass):
  - Four prompts trimmed: Website daily 2,228 → ~1,101 words; competitor review 1,743 → 1,090; Capital weekly 1,722 → 1,132; consolidation 1,541 → 1,423.
  - Fixed the WEB-20260915-01 stale fact and the Capital weekly's routing to the dissolved News Analyst.
  - CHECK 20 added. **A32** opened (one batched spot-check of 25 unverifiable Amazon claims).

## 2026-09-13
- **Spine outage of 8–13 Sept:**
  - No project write since 8 Sept 14:39:17Z (5 days 10 hours).
  - Nine rounds fast-failed in 8–12 seconds on 12 Sept, with no error text and all still enabled.
  - Both recovery mechanisms (the 4-hourly watchdog and the 04:15 catch-up) were also down. The watchdog had about 30 empty firings.
  - Store was 1,174,199 / 2,000,000 (58.7%), so not the cause.
- Perishable candle rescue (CAP-024/025): Crypto.com serves only 50 candles. The 00:32 watchdog pulled 50 4h bars each for BTC and ETH (oldest 4 Sept 20:00, overlapping the archive's last bar of 7 Sept 16:00, matching to the volume decimal). Saved to fresh_candles_2026-09-13.json at a new path. Nothing lost. The merge was deferred to the check-in.
- Push notification sent to DK (broken and expiring). The catch-up round was fired on demand under OPS-20260901-02.
- Post 246 (scheduled 10 Sept) had not been confirmed published. The anonymity sweep had been unchecked for five days.

## Open at end of period (3 Oct)
- A25 (stalls and dying rounds): DK's ten minutes with Anthropic support. Consolidations died on 27, 28 and 30 Sept and 1 Oct.
- A38 expired: post 302 is live with the old cover.
- A37 unverified.
- A34 suspended (repair already made 22 Sept, unnoticed).
- Also open: A35, A33, A32, W-IMAGERY-1, W-WIDGET-1 / W-FOOTER-1, the media 311/98 deletion (DK's), and the wp-admin sitting (author/display names, og:image, media 239).
- Undispositioned PROPOSED blocks from 22 Sept (including proposals 43–45, later lost to a numbering collision) and 27 Sept.
- The CHECK 2 replacement is not written into the checks file.
- OPS-20260831-05 provenance audit: never started.
- Spine-watchdog STEP 1 amendment: routed to a performance review that kept failing.
- BD round to be re-pointed at demand: not done.
- Standing brief length; roster and decision logs not rewritten since 21 Sept.
- G3 recorded closed on 14 Sept, with 45 pages discovered but not indexed.
- Money: £0.00, nothing sold, 0 subscribers.
