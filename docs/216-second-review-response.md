# 216 — Response to the second external review (10 Nov 2026)

Two reviewer documents (DK 10:18, 10:19). Scripts: `src/review2_fixes.py` (runs/gate/review2_fixes.txt), `src/pairs_daily_test.py`
(runs/gate/pairs_daily_test.txt); live-code replays Nov 2019 – Nov 2026 via the live runner with scratch settings (LIVE_POT_CFG).

## Execution (reviewer: exits were at the signal-day close; TPS bought at the signal close)
Correct for the research simulator — fixed: entries, TPS rungs and ALL exits now trade at the next open after the deciding close.
(The £ replays already used the live runner, which trades the dip books at the next open; they were not affected.)
| Book (next open in AND out) | n | mean | t | same-day-clustered t | year-block 95% CI | full years + | last 5y |
|---|---|---|---|---|---|---|---|
| RSI(4), 8 markets | 1262 | +0.279 ATR | 5.31 | **4.07** | [+0.111, +0.418] | 18/25 | +0.317 |
| RSI(4), 8 markets, costs x1.5 | 1262 | +0.256 | 4.85 | 3.72 | [+0.094, +0.402] | 18/25 | +0.295 |
| TPS 4 rungs, 7 indices + gold | 1558 ep | +0.172% | 4.49 | **3.87** | [+0.073, +0.253] | 20/25 | +0.200 |
| TPS 3 rungs | 1558 | +0.133% | 5.47 | 4.44 | [+0.073, +0.187] | 19/25 | +0.142 |
| TOM, 6 traded markets | 1854 | +0.156 ATR | 4.42 | **2.47** | [+0.033, +0.286] | 16/26 | +0.082 |
| TOM, all 8 | 2462 | +0.125 | 3.97 | 1.91 | [−0.007, +0.260] | 15/26 | +0.052 |
| Santa, 7 indices | 174 | +0.495 | 4.20 | **2.13** | [+0.011, +0.912] | 20/26 | +0.060 |
- Counting same-day trades as ONE observation (reviewer's clustering point): RSI(4) and TPS still clear t* 3.74; **TOM and Santa do not**
  (their t was inflated by counting the same date in several markets). Both stay positive in the year-block bootstrap (CI above zero, just).
- The appendix "TOM/Santa call bug": the pack's code reads `run(k, bme, 1, None, 3, stop=5)` — the reviewer's copy lost the `1,`. No change.

## Robustness asked for
- RSI(4) exit level: >45 +0.218 (t 5.13), >50 +0.268 (5.67), >55 +0.279 (5.31), >60 +0.274 (4.70); fixed 5-day hold +0.176 (3.40). Broad plateau.
- RSI(4) by market (ATR): SPX +86, NDX +60, DAX +57, RUT +50, gold +48, FTSE +41, DJI +27, Japan −18. Without the best (SPX): +0.244, t 4.30.
- Santa without its best 3 years: +0.297, t 2.52; best 4: +0.242, t 1.99. TOM by year is lumpy (2010 +59, 2020 +70; 2018 −26, 2008 −22).
- TPS (4 rungs): win 87%, avg win +0.47%, avg loss −1.77%, worst −22.6%, worst open loss −25%, avg 5.7 days, avg 46% of budget used,
  longest losing run 4. Stopping after 3 rungs: worst −10.7%; after 2: −6.0%. Minimum 1–2% gap between rungs: lower mean, same worst.
- Yahoo open audit since 2010 (share of opens equal to the previous close): FTSE 95%, SPX 4%, DJI 3%, others 0–1%. Only FTSE is broken.

## Live risk proposals, replayed through the live code (Nov 2019 – Nov 2026, £500 start, IG 0.01/pt minimum, all caps on)
| Variant | End | Worst drawdown (daily equity) | Lowest | Worst month | 2020 |
|---|---|---|---|---|---|
| Current: TPS £100 stop + 200-day restart, 4 rungs, 3.5% exceptions | £1,579 | 28% | £382 | −£188 | −£2 |
| TPS 3 rungs | £1,433 | 25% | £400 | −£172 | −£47 |
| TPS 3 rungs, no exceptions | £1,432 | 24% | £403 | −£172 | −£45 |
| **Reviewer's TPS limit: stop 5% of pot (£25), TPS counted in the day stop/floor, no exceptions, + 200-day restart** | **£1,869** | **19%** | **£439** | −£204 | +£86 |
| Same, but NO restart (reviewer's full proposal) | £870 | 18% | £439 | −£68 | −£12 |
| TPS stop £50 counted in the floor, 3 rungs | £423 (floor hit Mar 2020, back to paper) | 19% | £423 | | −£81 |
| RSI(4) + TPS only (no TOM/Santa), 3 rungs | £1,137 | 27% | £385 | −£152 | −£91 |
- The reviewer's tighter TPS limit + our restart is better on BOTH return and drawdown. Caveat: the gap comes mostly from one event
  (stopping TPS early in the March 2020 crash); in other years it is similar or a little higher (compounding from the higher 2020 base).
- Removing the 3.5% exceptions changes nothing (£1,433 vs £1,432) — the reviewer is right that they aren't needed.
- TOM + Santa add ~£300 and lower the drawdown at portfolio level (£1,433 vs £1,137) — reviewer 2's "improves the portfolio" test — despite
  failing the clustered t on their own. Recommendation: keep them, labelled WEAK.
- No restart at all halves the profit (£870).

## Reviewer 2 (new strategy families)
- Donchian/Turtle, MA trend re-entry, opening-range breakout, Keltner/Bollinger-type breakouts: already tested earlier (docs 195–203) and failed
  after IG costs and funding. 12-month / multi-horizon trend: no edge after funding (doc 208).
- **Pairs trading (new test, daily, next-open both legs, z-score 2 in / 0 out, 3.5 stop, 20 days):** SPX/DJI −0.37%, NDX/SPX −0.28%,
  gold/silver −0.70%, DAX/FTSE −0.93%, SPX/DAX +0.07%, NDX/DJI −0.45%; all pairs −0.39% t −2.74, 8/27 years. Gross ≈ +0.03%: the spreads
  don't revert within 20 days, and two legs of IG funding eat the rest. FAIL. (Crypto 15-min pairs also failed, doc 127.)
- Adopted as a rule: a new book must improve the portfolio (return or drawdown), not just make money on its own.

## Proposed change for DK (one decision)
TPS stop £100 -> 5% of the pot (£25 now), counted in the account day stop and floor, keep the 200-day auto-restart; remove the 3.5% exceptions.
