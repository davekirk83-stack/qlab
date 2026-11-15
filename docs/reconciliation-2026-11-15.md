# Reconciliation — Capital crash watch ↔ Investing Bot (15 Nov 2026, second fortnightly run)

Read-only research (CAP-021). Nothing placed, sized or suggested; no task altered. Filed in the repo because the project store refused writes on 15 Nov (paper-books report says the same).

## 1. What each side has recorded since 1 Nov

**Investing Bot (long-term plan).** Still no new Drive file: the only alert in *PA Operation > 01 Capital* is **"CRASH ALERT — AMBER — 2026-10-16"**. Its record since the last reconciliation is in two places only: (a) the memory file `/areas/long-term-investing.md`, updated **6 Nov** — RED rule redefined as *trend broken AND stress confirmed* (VIX > 30 on 2 of 5 days, or credit stress, or 10-year above 5% for 4 weeks), and the VIX "rule of 16" bands (20/28/32/48/64/80) kept in the planning; (b) its own daily-check prompt, amended **5–6 Nov**, which records the 5 Nov sell-off: S&P −4.4% to 7,354 on its 200-day/10-month average, Nasdaq-100 −6.4%, SMH −33% from high, VIX 28.2, 10-year 4.84%, Brent ~$98, BoE hike to 4%, level **AMBER**. Its weekday alert check ran through **Fri 13 Nov** and `SUCCEEDED`; it files a new Drive file *only when the level changes*, so an unchanged AMBER never gets re-dated. Its messages to DK are not readable here.

**Capital.** Paper-books runs 3–15 Nov each read the 16 Oct AMBER file and took no action; docs 195, 196 and the 15 Nov report flagged the 30-day staleness every day. Filed on the crash since 1 Nov: doc 220 (regime layer — no dip-buying below the 200-day, adopted live), doc 221 (bear-market study: US Tech 100 correction −14.7% under way since 6 Oct; every mechanical short book fails the standard test), doc 222 (assessment to 1900: the dip edge is a post-1982 era effect; shorting breakdowns worked only in the old long bears), doc 223 (insurance short at new highs = crash-insurance profile, not an edge; DK 10 Nov: *"convinced we are about to enter a major 100 year crash like 1928"*), and the BTC correction work (doc 229 onward: 13 Nov low ~66,400, fib extensions of the 13 Nov range marked every Saturday low, 300-week MA ~57.8k as the cycle-low zone).

**Where they stand:** both say **AMBER**, and on the core signals they agree. The disagreement is procedural and lands today.

## 2. The hand-off gap (the most important item)

The 16 Oct file crosses 30 days at **16:45 UTC today**. Capital's protocol then treats it as unreadable → **EXIT** → tomorrow's 07:23 run writes `pb_halt active=1, flatten=1` and flattens all fourteen paper books for 14 days. The Investing Bot's prompt only writes a file on a level *change*, so by its own rules it will not refresh an unchanged AMBER. Both watches have logged this; neither has the authority to fix it. One new file "CRASH ALERT — AMBER — 2026-11-15" (or any level) in 01 Capital before 07:23 UK Monday resets the clock. Simulated money only; the mechanism is working as designed.

## 3. Core signals at Fri 13 Nov close (Yahoo daily; protocol definitions)

| signal | 1 Nov recon | now | status |
|---|---|---|---|
| Trend: Oct month-end vs 10-month avg | 7,580 vs 7,304 | unchanged; S&P 7,562, +3.0% vs 200-day, −3.3% vs 52-wk high | intact (A not met) |
| Nasdaq-100 | — | 27,944, **−10.5% vs 52-wk high** | in correction |
| US 10-year | 4.93% (eased) | **5.15%**; closes 5.00 / 5.10 / 5.15 on 11–13 Nov | **back above 5% — the 4-week clock for stress B starts ~11 Nov** |
| Credit HYG/IEF vs 200-day | −0.4% | +0.8% | calm |
| VIX | 19.4 | 19.3; 28.2 spike on 5 Nov, no close > 30 | calm |
| Gold GLD | $356, −13.8% vs 200-day | $355, −13.0% | still weak |
| Brent | $117.80 | $95.84 | eased |
| Exit trigger | not met | not met (no QE, caps or emergency cut found) | — |

RED needs A (trend broken) **and** B (stress). Neither is met; B's nearest route is the 10-year holding above 5% into early December.

## 4. DK's theses against the fortnight

- **Stocks battered soon:** the 5 Nov day (−4.4%) was the first real hit; the S&P has since recovered to 7,562 and the trend is intact. Nasdaq-100 is in a 10% correction. Not yet.
- **Crypto bull regardless:** **against, and widening.** BTC 63,878 (15 Nov): −21.6% since 16 Oct and −17.3% since 30 Oct, while the S&P is −1.3% and −0.2% over the same spans. ETH −35.9% from its 52-week high.
- **Bitcoin the escape mechanism (falls with stocks, then decouples):** it has decoupled — **downward**. On 5 Nov BTC fell −5.6% to the S&P's −4.4%; since then the S&P is +2.8% and BTC −16%. Daily correlation since 1 Nov +0.81 (n=9, too small to lean on). The thesis is not on the record this fortnight; the April 2025 shape has not repeated.
- **Bitcoin a separate animal from other coins:** holds on the downside too — BTC −26% from its high, ETH −36%.
- **Neither watch's alert set includes BTC at all**; Capital's doc 229 series is the only place the BTC fall is being tracked.

## 5. Housekeeping
- The Trading & Investment project's memory files (`capital-research.md`, `crash-alert-handoff.md`) are out of this session's scope (Project-bound); summary written to this project's copy instead.
- Nothing placed, sized or suggested. No task altered.
