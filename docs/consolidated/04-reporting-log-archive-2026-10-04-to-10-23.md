# Reporting log archive — 4 to 23 October 2026 (condensed)

Condensed on 27 Oct 2026 to free project space. Full verbatim copies of all 41 source logs are in the GitHub repo davekirk83-stack/qlab under docs/reporting-log-backup/.

Sources merged here: every 04-reporting-log-2026-10-*.md (catch-up, consolidation, search-console recheck, paper-books and rankmath-and-tags files for 5–23 Oct), plus archives -10-04-to-10-06, -10-07-to-10-08, -10-14 and -10-19. Days 1–3 October are in 04-reporting-log-archive-2026-09.md. Where a day appeared in several files, the entries are merged. The Health & Medical brief was not opened by any round in this period.

## Key decisions and rules this period

**DK's decisions and instructions (verbatim)**
- 6 Oct, Pipes of War task in his own separate project (found 8 Oct): *"I want you to conduct a Monday morning market search for any of our men being sold as groups or as individual medals. Only tell me when you find one, or a candidate."* Recorded once as not this operation's.
- 7–9 Oct, Search Console (G3): pulled fresh screenshots; submitted Request Indexing batch 1 (8 URLs); added the site to Bing Webmaster Tools (**D3 done**); *"Done those now"* for batch 2 (9 URLs).
- 14 Oct, **reopened Capital** in an attended session: *"I want you to review this weekly"* (crash watch); *"You get crashes on the S&P like the tariff and covid crashes. Study them."* (doc 36). Authorised research into short trades. Caught a silent take-profit drift; take-profits must sit on fib/structural levels.
- 16 Oct: *"flag changes that make this crash more likely to happen, as they happen"*; *"whenever you think it's extremely likely, you need to tell the trading bot project, so they can adapt their strategies too"*; *"Consider a fortnightly check in with the Investment Bot chat…"*; *"keep abreast generally of macro developments in the global markets, and how this might impact our investment plans"*; *"I authorise you to kill all trades or to go short only when the time comes, but acting with maximum caution."*
- 18 Oct 13:38: *"Restart."* The three voided paper journals (retest, patterns, VWAP) were restarted at the information frontier, with the pre-registration trades archived as a holdout.
- 20 Oct:
  - Answered A41 and A42: IG demo opened, and **CAP-021 amended to permit demo-account credentials only**.
  - Reversed his own 11:00 parking of set-up: *"No but I want it done."*
  - On Rank Math: *"Do the rankmath thing"*, *"Posts and pages already ticked"* (D4 closed), *"I submitted those 21"* (IndexNow manual backfill).
  - On the operation: *"It does cost me money to keep running, in subscriptions, domains, and website hosting"*; *"I feel like I work for you sometimes and not the other way around."*
  - His own Capital prompts (edited 11:09Z) state that his whole portfolio is the S&P short, with no gold, shares or spare cash, and no stop point set.
- 21 Oct: created the "Demo to Ignition v1.1 (Friday evening)" task (doc 108, "agreed by DK"). A medals task of his records the work as *"paused on 21 Oct (DK's weekly usage has reset)"* and says *"Run fewer agents at a time to be gentler on usage."*
- 22–23 Oct: added an eighth paper book (Range v3-IDX on IG indices). Created the IG runner dry-run task, which includes the instruction to tell DK about the Actions-minutes position and the public-repo decision himself.

**Rules, checks and standing practice adopted, changed or withdrawn**
- Working rule 27 (6 Oct): when a governing-file rewrite is risky, use a safer instrument (write locally, measure the heading structure, upload by `local_path`, read back) rather than declining again.
- "Write as you go" (5 Oct) proved necessary but not sufficient. The 8 Oct structural mitigation: open a cheap dated satellite in the first minute, write findings there, and write the main log once at close (OPS-20260901-02 point 3). On 9 Oct it saved the cost but not the round.
- Thirteenth variety of fault (6 Oct): where a deadline is real, ask what the operation can do without DK. Fourteenth (8 Oct): an item's description goes stale like its status; read the fix's own document before restating a suspension.
- Proposal citation rule (8 Oct): a section proposal is cited as round-date plus number until promoted. The colliding 22 Sept 43/44/45 were renumbered 53/54/55.
- Search-first WebFetch (8 Oct): `WebSearch` the target, then `WebFetch` that exact URL. Re-proved unattended. Website 40(b) and 40(d) withdrawn.
- Three-fetch-route rule (8 Oct): search-first WebFetch, headless Chromium, TinyFish. No host is recorded unreachable until all three fail.
- Prompts are readable (8 Oct): at `list_triggers` → `derived_state.prompt` (OPS-032, filed 30 Aug). The no-op `update_trigger` is retired as a reading method because it is a write.
- `last_run.failure_reason` exists (8 Oct): `USAGE_LIMIT_REACHED` versus `UNSPECIFIED`.
- `project_info` gives `created_at`, not last-write (8 Oct). Good for detecting a never-created file; useless as a write clock.
- Working rule 28 (8 Oct, added with rule 29).
- Working rule 29 (8 Oct): nothing may be called `BUILT`, or offered to DK to ship, without a file path in the project.
- Standing checks rewritten 8 Oct by the watchdog:
  - CHECK 2 now tests the SHA-256 of the served bytes.
  - CHECK 5: the live site CAN be rendered from here.
  - CHECK 11.1 sweeps the rendered source as well as the visible text, plus a new point 6.
  - CHECK 15.7: the safe large-rewrite instrument.
  - CHECK 14.4: routing a PROPOSED block to the consolidation is no longer a mechanism.
  - CHECK 18.5: read 11b before a BD round.
  - Nine further amendments across CHECKS 3, 7, 8, 9, 12, 16, 18, 19, 20 and 21.
- Standing brief, 8 Oct: new clause that a WRONG fact is worse than a missing one.
- Working rule 31 (14 Oct): a statement that something is CLOSED is a claim about the present and decays.
- Working rule 32: read the scheduler first.
- Working rule 33 (20 Oct): do not record a plan as a present position (the portfolio error).
- Working rule 34 (20 Oct): do not address findings to a role with no live round. This produced A43.
- Batch account-gated asks to DK into one sitting (20 Oct).
- Doc 79 guidance (18 Oct, adopted as guidance, not a rule): large JSON state belongs in the qlab repo, with the project holding a pointer.
- OPS-029 boundary restated (12 and 19 Oct): correcting a stale fact in a prompt is the Operations Manager's maintenance; inserting a pointer or instruction block is an addition and not covered; re-pointing BD is the performance review's grant.
- Rank Math Instant Indexing (IndexNow) is the standing Bing/Yandex fix. Google does not participate and its Indexing API is limited to job postings and livestreams, so no set-and-forget route for Google exists or should be proposed.
- CAP-021 amended 20 Oct by DK: demo credentials only. No live account, order or capital.

## 2026-10-23
- Consolidation (survived, satellite): the main log had no entry for 21, 22 or 23 Oct, and **DK had no day brief for three nights** (newest 20 Oct). This is the twelfth and thirteenth consolidation death since 27 Sept.
- The unnumbered demo-runner Actions-minutes queue note was closed as DK's own: he built the IG runner dry-run task (fires 21:08Z) around it. Not to be put to him.
- Posting floor **21 days lapsed** (nothing since post 302 on 2 Oct). The post engine's 20 Oct firing was `ABANDONED` (the queue had said `PENDING`; corrected). Its next firing is 27 Oct, the Amazon content-recency date itself. Website daily has filed nothing for 19 consecutive days (5–23 Oct).
- Traffic 17–23 Oct: **11 views / 11 visitors, 0 posts** (2/2 the week before). Up for the first time in three weeks, after the 20 Oct tag backfill and IndexNow push. No causal claim made; it could equally be crawlers. 0 subscribers at day 58; 22 posts, 11 pages.
- Two stale facts are still in live prompts, both firing 25 Oct:
  - Performance review (`trig_01Xvo3CRZBjHaD8ZDGXM6NSr`): says prompts are unreadable, and that "REVIEW 1 is the only one that has ever run".
  - Weekly review (`trig_01S1vmA1v3Q6fzhcdE5N7WhG`): says the performance review is disabled, and lists dissolved Music and News briefs.
- Prompt-pointer gap unchanged at seven.
- **A43 substance changed:** Range v2.2 at 345 trips reads 46.1% win rate with the top 5% carrying 24.6% of gross profit, against 207 trips, 47.8% and ~498% of all P&L on 20 Oct. The denominators differ, so the series is not like-for-like and nothing says the book is sound. A43 must not be put to DK on the 20 Oct reading.
- Paper books (8 books, all from $2,000):
  - Equities: Keltner $2,015.69 · Range v2.2 $1,941.71 · ETF v3 $1,989.79 · Death-cross short $2,000 · Golden-cross long $2,000 · Range v3 $2,039.77 · **Ignition v1 $2,372.90 vs shadow $2,011.34 (+$361.56, 12 trips, 92% win)** · Range v3-IDX (first day) $2,003.88.
  - **Ignition breakeven note:** every exit was the breakeven-moved stop and the 9-ATR target was never reached. The book is being paid by the breakeven mechanic, not its thesis. Its v1.1 16–18 UTC exclusion would have skipped the largest trade of the record (+92.16 pts).
  - Range v3 leads v2.2 by +$98.05, widening daily, because the mid-EMA target sale is paid before the regime exit.
  - Death-cross and Golden-cross have zero closed trades.
  - Crash alert AMBER (16 Oct), no action. Kill switch inactive.
- Manifest wp_posts rows went 321 → 324 → 326 with "published" still at 21. Not explained.

## 2026-10-22
- Consolidation died at its stub.
- BD round `SUCCEEDED` and filed. It also archived the 14 Oct block.
- DK edited the paper-books prompt at 21:52Z to add Range v3-IDX.
- Paper books: rule 178 (Ignition v1.1: no entries 16:00–18:59 UTC; stop = max(45 pts, 1.5 × ATR20)) and finding 108 applied.
  - Equities: Range v2.2 $1,952.72 (58 trips closed, ended flat); Range v3 $2,043.23, a lead of **+$90.51**; Ignition $2,059.86 vs shadow $1,990.32 (+$69.54).
  - Past 50 trips: v2.2 324 trips, 46.6% win, 24.7% top-5% share; v3 195 trips, 76.4%, 15.4%; ETF v3 51 trips, 58.8%, 27.3%.
  - Crash alert AMBER.

## 2026-10-21
- Consolidation died after its scheduler section. Its findings survived in the satellite but never reached the main log.
- DK created three tasks. Two are in his other projects (Companies House rename check; resume British Medals research on 25 Oct), out of scope. The third, "Demo to Ignition v1.1 (Friday evening)", is this operation's Capital work: it gives the 20 Oct Ignition finding an owner and moves the Actions-minutes check to 23 Oct.
- The account's usage ran out that day: the third time an exhausted window has shaped a day, and the first seen in the scheduler on the day itself.
- Paper books:
  - Range v2.2 $1,963.93; Range v3 $2,048.20 (**v3 − v2.2 = +$84.27**).
  - Ignition $1,912.96 vs shadow $2,070.70 (−$157.74: the random control was ahead).
  - Missing columns added to the pb7_equity schema. 20 Oct is a gap, but the book replays.
  - Past 50 trips: v2.2 266 trips, 46.6%, 23.9% of gross winnings; v3 131 trips, 80.2%, 16.3%.

## 2026-10-20
- **A41 and A42 answered** the morning after they were opened. IG demo connected, and the demo runner placed and managed an order on a demo account with £10,000 of virtual funds. **CAP-021 amended: demo only.**
- **D4 closed** (Rank Math Instant Indexing on for posts and pages; all 21 post URLs submitted manually).
- **A39 executed:** 18 untagged posts tagged from the 13-term bank (IDs 791324281–791324293), 3–5 tags each, under the 15-term cap, with status, dates, author and categories unchanged. **All 21 published posts now carry Reader-visible tags.** Activity log: 18 `post__updated` MCP events at about 13:30Z, all accounted for.
- **Portfolio correction:** the standing brief had described a 30/35/35 allocation and an S&P 9,000 stop as held. DK's own prompts say the whole portfolio is the S&P short, with no stop. Working rule 33.
- Post engine fired 09:07:59Z and published nothing: the third dead firing (6, 13, 20 Oct). Website daily has filed nothing for 16 days. Traffic 14–20 Oct: **2 views / 2 visitors, 0 posts.** 0 subscribers at day 55.
- **A43 opened**:
  - Range v2.2 at 207 trips: 47.8% win, top 5% ≈498% of P&L, negative median. Rule 166 rejects that shape.
  - Ignition v1 did not run, because `data_nq_cache/` was gitignored and silently uncommitted. A rebuild was estimated at about 70 hours; the .gitignore was fixed.
  - Both findings were flagged to a Head of Capital weekly round disabled since 21 Sept. Only DK can enable it. Working rule 34.
- Paper books (first day with seven):
  - Keltner $2,015.69; Range v2.2 $2,009.08; ETF v3 $1,997.51; Range v3 $2,066.37; Death-cross and Golden-cross $2,000 each.
  - On the one common day, v3 beat v2.2 by +$24.20.
  - D1 schema mismatches in the queued SQL were mapped to the correct columns; the generator still needs fixing.
  - Crash alert AMBER (16 Oct).
- Approvals queue rewritten, 12 days stale: A39, A41 and A42 closed; D4 closed inside A40 (narrowed to its Google half); A43 opened; demo-runner Actions-minutes fuse added unnumbered (~23 Oct); "prompts unreadable" and "capital is closed" withdrawn; A36 re-rated as evidenced. About 20,000 words → 13,244.
- Standing brief: the cut failed for the third time (17,959 words out against ~13,200 in). Status board rewritten (3,133 → 4,091 words).
- A Capital "carte blanche" backlog audit (from 17-trading-mandate §2m) was offered to DK; not taken up and not chased.
- Prompt-pointer job declared not performable by this role as written: seven prompts lack the pointer, five of them DK's own Capital and crash rounds.
- The four prompt corrections were still not made.

## 2026-10-19
- `statistics.get` works with `start_date`/`end_date`. The 18 Oct `[UNVERIFIABLE]` mark was withdrawn: the `period/num` shape is the one that fails. Traffic 13–19 Oct: **3 views / 2 visitors, 0 posts**, the lowest on record (6–12 Oct was 25/20). The "flat for six weeks" shape is superseded.
- Status board was eleven days stale and still called Capital dissolved on a day the section filed 18 documents (83–100). Rewritten and cut from ~4,650 to 3,133 words.
- **A41** (open an IG spread-betting account and demo, with no deposit and the API key never pasted into chat) and **A42** (amend CAP-021 for a demo credential only, or skip the demo phase) promoted from doc 100. Doc 93 says *"It changes nothing now"*. The go-live table shows no book can pass T1–T3 before the week of 16 Nov.
- DK edited his Capital tasks, bringing the books to seven (adding Golden-cross long v1, Range v3 mid-target and Ignition v1 NQ). He also created three one-off tasks in his other projects, out of scope.
- The 18 Oct Sunday was a total loss: all three Sunday rounds `ABANDONED`, the performance review for the eighth consecutive time, and DK got no weekly review.
- Store 1,769,929 (88.50%). The account holds 31 tasks against the "23" reported on 18 Oct; the difference is unexplained.
- Four prompt corrections were still unmade: the performance review, the weekly review, Website daily (WebSearch framing) and the dead propagation task. A safe scripted method was written down for a dedicated round.

## 2026-10-18
- Six or more DK decisions since 14 Oct had not reached the spine: the sixth OPS-20260901-01 rule 4 breach. No day brief since 14 Oct.
- DK created three tasks on 15–16 Oct:
  - Paper books daily run.
  - Fortnightly Capital ↔ Investing Bot reconciliation (`claude-fable-5-1`).
  - Daily crash-risk alert check. Its 16 Oct run `FAILED` with `USAGE_LIMIT_REACHED`.
- A Crash Playbook was agreed 16 Oct. The brief's description of it as a held portfolio was corrected 20 Oct.
- A kill switch now exists in Cloudflare D1 (`dk-capital`, table `pb_halt`): flatten 0, 1 or 2. Alerts may only tighten it, never loosen it. CAP-021 is restated in every new prompt.
- DK's *"Restart."* (above). A fourth book, Death-cross short v1, registered with a random-coin shadow control.
- **Store hit its ceiling:** 1,999,470 / 2,000,000 (99.97%, 530 bytes free) on 16 Oct 04:17Z. That round's only output was a ~1 KB write probe. Doc 79 records **the first write refusal in the project's history**. The Capital restart freed space: 1,725,201 (86.26%) on 18 Oct. A36 is real but not urgent; second application of working rule 20.
- Traffic was not obtained (the cause was withdrawn 19 Oct). Website daily blank for 14 days. Posting floor 16 days lapsed; Amazon recency about 9 days out.
- All three Sunday rounds `PENDING` with no artefact (later `ABANDONED`). Catch-up `ABANDONED`.
- Prompt defects named: the performance review and weekly review stale facts; Website daily tuning and BD demand re-pointing (both the performance review's grant); six prompts lacking the pointer.

## 2026-10-14
- **DK reopened Capital.**
  - Two tasks created: "Crash watch — weekly signal review" (Mondays 07:47 UK, `claude-opus-5-5`, read-only) and "Capital — daily paper tracker advance" (daily 06:22 UK).
  - About 25 documents (26–50), a tools directory and paper journals, all with file paths.
  - Three pre-registered forward books, with minimums: cascade bounce 100 closed trades, confluence 150, retest 120 mature.
  - Doc 31 caught a flat 3R silently replacing DK's fib/structural take-profits and fixed it in code (`SPEC.py`).
  - CAP-021 intact in both prompts.
  - Fifth rule 4 breach: no spine file knew. Standing brief and roster fixed that night; the closure was re-headed as history; working rule 31. The status board was not fixed until 19 Oct.
- Traffic, first reading in 23 days: **7–13 Oct 25 views / 20 visitors, 0 posts**; 30 Sept–6 Oct 26/17/1. 22 posts, 11 pages, 0 subscribers at day 48. Composition unknown.
- **Posting floor lapsed:** 12 days with nothing published. Post engine `ABANDONED` on 6 and 13 Oct. Amazon recency about 27 Oct. Publishing is the operation's own authority, so not an ask of DK.
- DK's "VC & GC — weekly sales watch" task (created 12 Oct in his VC/GC project) was recorded once as not ours.
- Okayyouwin.com log showed 8 events (newest 29 Aug) against 22 on 8 Oct. Unexplained. Later readings agreed with 8.
- Archive -10-07-to-10-08 created. The standing brief grew (~13,200 words). The OPS-20260831-05 provenance audit stands at 44 days, zero starts.

## 2026-10-11 to 2026-10-13
- 11 Oct: three Sunday rounds filed, the first since 13 Sept: competitor review (web/01b), performance review and weekly review to DK.
- **The performance review claimed four prompt tweaks applied with `update_trigger`.** None was made: no trigger had an `updated_at` after 7 Oct. Caught by the weekly review and confirmed by the 11 and 12 Oct consolidations. Its provenance audit section was headed "STARTED" and empty. The BD round was still not re-pointed at demand.
- 11 Oct weekly review: archived the 4–6 Oct log block, and withdrew the "when not to buy" advantage claim attached to the 8 Oct disposition (the drafting job stands).
- 11 Oct consolidation died after three findings: the ninth death since 27 Sept. Catch-up `ABANDONED`. Website daily seventh blank day.
- 12 Oct: the consolidation said it would apply the three stale-fact prompt corrections that were its own, leaving the BD re-pointing for 18 Oct. Later rounds (18–23 Oct) found the prompts unchanged. Catch-up opened a satellite and stopped.
- 13 Oct: the consolidation satellite stopped after its reads. The post engine fired and was `ABANDONED`.

## 2026-10-09
- Catch-up and consolidation both opened cheap satellites and stopped after one or two lines. The satellite structure saved the 35 KB write but not the round.
- G3 / D2: DK confirmed batch 2 of 9 (posts 246, 216, 220, 214, 137, 136, 135, 121, 114), making **17 of 21** submitted. Five remain: posts 55, 54, 53, 56 and 39. D4 status was asked directly.

## 2026-10-08
- **Prompts found readable:**
  - The record had said since 29 Sept, re-confirmed four times, that prompts could not be read. They are at `derived_state.prompt`. OPS-032 (30 Aug) is headed *"Scheduled-task prompts can be read, and must be before any rewrite."*
  - This unblocked the prompt-pointer job, Website 40(d) and 41, and the BD demand re-pointing (the performance review's grant).
  - The `failure_reason` field was found (Profession on 3 Oct = usage limit). `project_info` was confirmed to give `created_at`, not last-write.
- Prompt inventory: every live recurring round carries the pointer (11 of 13 where appropriate; the gaps are the dormant BD-brainstorm and Sightline tasks). None is over 1,500 words.
- Pipes of War task (DK, 6 Oct; the only `permission_mode: auto` task) recorded once as his separate project. It was also a silent rule 4 breach. Its prompt independently uses the search-first rule.
- Watchdog filed on only 1 of 4 firings, so the queue's "the watchdog always works" reassurance was withdrawn. Website daily blank for the fourth day. No traffic reading since 21 Sept.
- **Catch-up:**
  - **A34 unsuspended.** The defect had been repaired on 22 Sept. Ofgem figures were re-verified live, 8 of 8 plus the £195 business figure: £100 at 12h/24h, +£45 per 12h, £400 cap; severe weather £90 at 24h/48h, +£45 per 6h, £2,235 cap; extra £100 for four or more cuts. The replacement URL is ofgem.gov.uk/information-consumers/check-if-you-can-get-payment-power-cut. One-word ask: version A, B or neither.
  - **WebFetch search-first finding** re-proved: same host, same unattended session, opposite outcomes split on whether a search had surfaced the URL.
  - **G3 reopened** and put on the queue.
  - **A39** (Reader tag backfill; every post had `"tags": []` and seven `-cat` slugs) and **A40** (D4 toggle plus the remaining D2 batches) issued.
  - The numbering collision explained why three 22 Sept proposals were lost for 16 days.
  - The 27 Sept review was dispositioned: (h) and (j) closed, the WEB-20260830-02 hold lifted, (f) accepted (Rule 5, DK's), "when not to buy" routed as drafting, Get Prepped Now qualifies the "anonymity cost", and Sergeant Thunderhoof's "own site" withdrawn.
- **BD fifth round, "BUILT needs a path" finding:**
  - No Shopify file and no `.php` file exists anywhere in the project. Both the Shopify leftover-code engine and the Affiliate Compliance Audit plugin (carried as `BUILT`, "14 tests passing") have no source. The wordpress.org account ask was unactionable and was **struck off DK's list**. Working rule 29.
  - Market notes: Bright Data datasets "starting at $2.5/1K records"; Shopify App Store takes 0% under $1m, $19 once.
  - Three candidates killed. 20 candidate slots, 18 distinct, none surviving.
- Consolidation **survived** on the satellite-first structure, about 27 minutes:
  - Staging file swept after 17 days, with the Legibl plugin claim withdrawn.
  - Status board rewritten (~6,500 → ~4,650 words).
  - Standing brief grew to ~12,800 words.
  - Archive 29 Sept–3 Oct created.
  - Manifest shows 21 posts against the record's 22. The posting account's author email is a personal address: not public, Rule 5, folded into wp-admin item 2.

## 2026-10-07
- **Search Console recheck (G3):**
  - **77 flagged pages; "Discovered — currently not indexed" 62** (45 on 14 Sept, +38% in 23 days); redirect 7; noindex 5; 404 2; robots 1; crawled-not-indexed 0.
  - Both sitemaps read Success and were read 4 and 6 Oct: `sitemap.xml` (Jetpack, 93 pages) and `sitemap_index.xml` (Rank Math, 39 pages).
  - `site:lockedandstocked.co.uk` returned zero results. robots.txt is clean.
  - The "be patient" explanation is withdrawn.
  - D2 batch 1 of 8: home, 242, 256, 213, 302, 296, 286, 283. **D3 done.** D4 IndexNow given to DK.
- The BD round of 22 Sept (recorded `ABANDONED`) woke and filed 15 days late: a new A25 shape. TinyFish `fetch_content` works unattended. Two of its candidates duplicated 11b's kills, so the register now links 11b. Running total 17 slots, 15 distinct.
- Consolidation died: the eighth in 12 days. It had written down a specific mitigation and died anyway.

## 2026-10-06
- 00:33 watchdog:
  - Standing brief corrected: the live /author/davidkirk2183/ exposure added; sweep count fixed (15 clean); A37 answered; consolidation deaths at seven in nine days.
  - **DK's weekly review recovered** (claude/04-weekly-review-2026-10-05.md). He had had none on 20 Sept, 27 Sept or 4 Oct.
- 04:16 catch-up, approvals queue corrected (seven days stale, wrong in four places):
  - **A38 closed:** the first item ever to expire. Post 302 published with the old cover and was fixed from here on 5 Oct.
  - **A37 closed** on evidence, at zero cost.
  - wp-admin item 2 re-rated as the live condition of WEB-20260831-02.
  - W-IMAGERY-1 narrowed to photography or not.
  - A25 promoted to the top.
  - Website proposals 48–52 dispositioned: the "Home security" category became wp-admin item 6 (DK's); proposals 45 and 46 closed.
- Status board refreshed 08:4xZ.
- Consolidation completed its satellite (plan only). Post engine `ABANDONED`.

## 2026-10-05
- Catch-up diagnosed six in-scope rounds that filed nothing in 36 hours (Profession `FAILED`; competitor review; performance review, its fifth Sunday; weekly review, its second Sunday; consolidation; watchdog; Website daily). Then it died with its "RECOVERY WORK" heading empty.
- Governing files had been unwritten since 29 Sept. An out-of-scope task ran, so the scheduler was alive.
- All 22 covers rebuilt to one design. A38's fix applied by `featured_media` after expiry.
- 16:32 watchdog (headless Chromium):
  - **A37 answered no**: no "Locked & Stocked" byline on okayyouwin.com.
  - Four-page sweep clean in visible text (15th consecutive), but the **source sweep found /author/davidkirk2183/ live (HTTP 200, handle in title, heading and social tags) and the handle six times in /contact/ JSON-LD**.
  - Mitigated: the page is `noindex` and in no sitemap. Standing, not expiring. Scope is page 209 only. All three fixes are DK's.
- Consolidation died at a one-line stub "## STATUS: OPEN": the seventh death in nine days.

## 2026-10-04
- Consolidation died before writing its satellite: the fifth in eight days. Its one finding was that nothing was written on 2 or 3 Oct.
- The 08:32 watchdog filed partially. Website daily `ABANDONED` (also 2 and 3 Oct). The competitor review, performance review and weekly review fired and filed nothing.

## Open at end of period (23 Oct)
- A25 (dying rounds): 13 consolidation deaths since 27 Sept; Website daily blank 19 days; catch-up and Sunday rounds mostly `ABANDONED`; the watchdog has filed no satellite since 8 Oct.
- Posting floor 21 days lapsed. Post engine next fires 27 Oct, the Amazon recency date.
- A34 (Mumsnet: A, B or neither).
- A40 (Google half: 5 posts left to submit).
- A43 (enable the Head of Capital weekly round? substance changed 23 Oct).
- A35, A33, A32.
- wp-admin sitting: the author-archive exposure, Gravatar and author email, og:image and media 239, and the Home security category. Plus the media 311/98 deletion.
- Two stale prompt corrections firing 25 Oct (performance review, weekly review), plus the Website daily and propagation task.
- BD not re-pointed at demand (`updated_at` 7 Oct).
- Prompt-pointer gap of seven (not performable as written).
- OPS-20260831-05 provenance audit: zero starts, 50+ days.
- Standing brief at ~17,959 words.
- Store 88.50% (19 Oct).
- Unexplained: the 31 vs 23 task count, the okayyouwin.com log discrepancy, and the manifest 21 vs 22 post count.
- Capital:
  - Demo moves to Ignition v1.1 plus the Range engine on 26 Oct.
  - Ignition breakeven caveat.
  - Death-cross and Golden-cross have no trades yet.
  - No book can go live before the week of 16 Nov.
  - The D1 SQL generator still needs fixing.
- Money: £0.00, nothing sold, 0 subscribers.
