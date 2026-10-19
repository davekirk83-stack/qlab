# 89 — Pump chase with a trailing stop, and the EMA "about to cross" entries (19 Oct 2026)

DK, 18 Oct: *"do we have a strategy for chasing pumps with a trailing stop?"* and *"jumping in just before or as a major Gooner EMA crossover happens"*, with *"impending downward crosses (death crosses?) as shorts"*. Tested together because they share the exit. Code `src/pump_chase.py`; logs `runs/pump_chase_{1h,15m,1m,1h1d}.log`.

## Design
- **Pump chase (long):** close up ≥ X% over N bars, with N-bar volume ≥ 2× its trailing 30-day median (and without the filter). Grid: 1-min +2%/5, +3%/15, +5%/60 · 15-min +3%/4, +5%/16, +10%/96 · hourly +5%/4, +10%/24 · daily +15%/1, +25%/3, +40%/7.
- **Dump chase (short), alts only** (no directional BTC/ETH short): the mirror.
- **EMA 20/50 on each panel:** the cross itself, and "about to cross" = fast within 0.3 ATR of slow and converging; golden long, death short.
- **Exits:** trailing stop 1/2/3 ATR14 from the best price, capped; and DK's scale-out (half at +1 ATR → breakeven, trail the rest). Next-bar open entry, 4.5bp per side (10bp daily).
- **Controls:** 3 random bars per trade, same coin, side and exit; exit-free ±2-ATR barrier race; biggest-month share of P&L; top-5% share; median trade.
- **Panels:** 1-min 18 perps 13 months (10.2m bars) · 15-min 42 pairs 5 years (5.1m bars, the long-sample test) · hourly 33 perps 15 months · daily 162 alts incl. delisted, 2022–24.

## Pump chase — a lottery ticket, not a book
| panel | best row | n | per ep | t | win | ctrl | edge | median trade | biggest month | top 5% |
|---|---|---|---|---|---|---|---|---|---|---|
| 15-min, 5 yrs | +5%/16b, trail 3 | 9,874 | +0.11% | 2.2 | 39% | −0.06% | +0.17 | −0.99% | 38% of P&L | 647% |
| 15-min, 5 yrs | +3%/4b, trail 1 | 21,187 | +0.03% | 2.2 | 38% | 0.00% | +0.03 | −0.47% | 33% | 989% |
| hourly | +5%/4b, trail 1 | 1,336 | +0.41% | 4.2 | 42% | −0.06% | +0.47 | −0.44% | 26% (ex: +0.33%) | 137% |
| hourly | +5%/4b, scale-out | 1,336 | +0.26% | 2.3 | 63% | −0.09% | +0.34 | +0.87% | 31% (ex: +0.19%) | 201% |
| 1-min | +2%/5b, trail 3 | 1,881 | +0.77% | 6.1 | 42% | −0.05% | +0.82 | −0.37% | **94% (Oct 2025)**; ex +0.06% | 113% |
| daily | all rows | — | negative or too few | | | | | | | |

Read: a pump does continue on average — the race is 51–56% vs 48–50% random, and most rows beat their control — but the edge is tiny on the five-year panel (+0.03 to +0.17pp per episode, costs are 9bp), the median trade loses in every row, only about half of months are positive, and the P&L comes from the top 5% of trades (often more than 100% of it — the other 95% lose). The volume filter adds nothing. On the 1-minute panel 90–95% of the year's P&L is October 2025. This is the opposite of DK's objective (frequent small gains, 15 Oct); it is a strategy that bleeds for months and is paid by a few spikes. **Finding 159 — REJECTED as a book.** The continuation itself is recorded as real but small.

## Dump chase short — a crash-month artefact
Hourly −5%/4b trail 2: +1.51%/ep, t 4.8, 84% of coins — and **98% of it is October 2025**; ex that month +0.04%. On the five-year 15-minute panel the same trade loses −0.42%/ep (t −15), positive in 3% of coins, both halves. Consistent with docs 33–35 and rule 160: dips bounce, and the only time dump-chasing shorts pay is inside a crash, which the registered 4-hour death-cross book and the shorts-only kill-switch mode already cover.

## EMA cross and "about to cross" — equal to random on every panel
Golden cross, about-to-golden-cross, death cross, about-to-death-cross, trail 2 or 3 ATR: on 1-min (86k–115k trades), 15-min (41k–56k) and hourly (3k–4k) the edge over random is within ±0.01pp on 15-min and 1-min and within ±0.08pp on hourly, race equal to control everywhere. Getting in *before* the cross is no better than getting in on it. Finding 147 (15-min crosses carry no information) extends to 1-min, hourly and to the anticipatory entry. **Finding 160 — REJECTED.** The 4-hour death-cross short (finding 148/151) remains the only crossover trade with evidence, and it is already a paper book.

## Decisions
- No pump-chase book. No EMA-cross or about-to-cross entries on any panel below 4h.
- Rule 166: a strategy whose top 5% of trades carry more than 100% of its P&L and whose median trade is negative is not a book for this mandate, whatever its t-statistic.
- Golden-cross long v1 and Death-cross short v1 stay as they are.
