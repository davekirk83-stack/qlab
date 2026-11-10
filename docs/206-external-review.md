**Critical review of the trading books (as of 10 Nov 2026)**

I reproduced the core Family 1 RSI(2) dip (#51) on free daily data via Polygon (ETF proxies SPY/QQQ/DIA/IWM/EWG/EWU/EWJ/GLD, ~2003–2025). Results: 609 trades, mean **+0.285 ATR**, t ≈ **4.63**. This is very close to the reported 752 trades / +0.245 ATR / t = 4.35 across the 7 indices + gold. The edge is real and robust in an independent implementation of the provided simulator.

### Look-ahead bias

The shared simulator is clean on the points previously broken:

- Decisions only on closed bars; entry at that close / next open / same-day OC only when the signal is known pre-open.
- Stop checked first; gaps fill at the open.
- One position per market.
- Calendar offsets use known-in-advance business-month/quarter ends (no next-bar month).
- Previous errors (same-bar ladder limits, overlapping trades, stale cross-market closes, etc.) do not reappear in the code or rules shown.

**Residual concern (explicitly asked):** Entering “at the close” when the live runner decides ~20 minutes before the close on the live price introduces a small optimistic bias. The final close is not yet known, and last-minute moves can reverse the RSI(2)/MA condition or change the fill. This is minor for daily mean-reversion but systematically favourable versus a true next-open or limit-at-close entry. Prefer `how="O"` (next open) for live deployment of the dip books, or accept a small haircut.

No other material look-ahead found in the rules or simulator.

### Overfitting (240 ideas)

Šidák t* = 3.70 is a reasonable family-wise threshold for 240 trials. The strongest books clear it (RSI(2) 4.35, Stochastic 4.48, turn-of-quarter 4.27, Santa 4.20, US→Europe 5.99). Additional checks (random-entry 95th percentile, 1.5× costs, last 5 years, ≥60% years positive) are good practice.

Caveats:

- Many ideas are highly correlated (RSI(2) vs Double 7s monthly correlation 0.69 is stated; the whole Family 1 cluster is similar). Effective independent trials << 240.
- Several survivors are classic published effects (Connors RSI(2)/TPS, Santa, turn-of-quarter, Halloween, Moskowitz time-series momentum). Survival of known edges is less surprising than novel parameter fits.
- The “fallow” month/VIX switches are chosen out-of-sample in the manner described, which is disciplined, but still data-driven.

Overall, the top A/B books are unlikely to be pure luck given the literature match and my reproduction. The weaker ones (trend, crypto, most cross-asset) are correctly labelled WEAK.

### Costs, funding and fills (IG UK + Revolut X)

- Indices 0.02% per side / gold 0.03% / crypto 0.2% are realistic-to-slightly-optimistic for liquid markets on IG (spreads of ~0.4 pts on US 500 or 0.3 on gold are ~0.008–0.015%; the stated figures leave a small buffer). Revolut X spot 0.2% is plausible.
- Overnight funding ~6% p.a. on indices/commodities is in the right ballpark (IG admin fee typically ~2.5–3.4% + benchmark; current published rates vary by currency but 6% is not aggressive for longs). For short-hold (1–10 day) mean-reversion the drag is small. Commodity basis adjustments can be higher and more variable than a flat 6%.
- Fills: daily close/next-open and gap-through-stop logic is standard and realistic. Intraday books have only 7–14 months of history, so fill quality is unproven.

### Sizing and risk for a £500 book

Rules (≤2% risk, ≤5× exposure, –4% day stop, –15% or two negative weeks → paper) are sensible. The documented problem is real: IG’s £0.01/pt minimum can exceed the 2% risk budget on wide-stop trades (especially US Tech 100 / Wall Street). Either skip those signals, raise capital, or accept occasional oversizing. Total exposure cap is fine with leverage.

### Independence of the 7 indices + gold

Indices are highly correlated (common equity beta). Counting them as fully independent overstates the evidence. Gold is a partial diversifier. Crypto is genuinely separate. The multi-market t-stats are still informative but should be mentally haircut.

### Which books to trust

|Book / Family                                                |Trust level         |Reason                                                                                       |
|-------------------------------------------------------------|--------------------|---------------------------------------------------------------------------------------------|
|Family 1 dip-buyers (RSI(2), Stochastic, TPS ladder, related)|High (TESTED)       |Reproduced independently; matches Connors literature; high t; survives costs and recent years|
|Turn-of-quarter & Santa                                      |Medium-High (TESTED)|Classic calendar effects; high t; known in advance                                           |
|US strong close → Europe next day                            |Medium (TESTED)     |Strong overall t, but last 5 years near zero                                                 |
|Halloween, related dip variants                              |Medium-Low (WEAK)   |Borderline t* or high correlation to stronger books                                          |
|Trend 100-day / 12-month TSMOM                               |Low (WEAK)          |Last 5 years negative without switches; classic but regime-sensitive                         |
|Crypto breakout & crowd contrarian                           |Low (WEAK)          |Short history (2021–); few years                                                             |
|Intraday (Ignition, AuclairsDad, Gold Asian range)           |Very low for now    |Only 7–14 months; correctly WEAK                                                             |

**Would cut or keep on paper only:** all WEAK books (trends, crypto, intraday) until more data or live proof. Keep the Family 1 core and the two strongest calendar books as the live core. The combined daily books’ diversification benefit is real (worst 12 months –38 ATR vs –134 single book) but still equity-heavy.

### Answers to the explicit questions

- Entering at the close with a 20-minute-pre-close decision: mildly optimistic. Switch dip books to next-open entry for honesty.
- IG overnight funding ~6%: acceptable approximation for indices; watch commodity basis.
- 7 indices + gold independent? No. Treat as ~2–3 effective independent markets plus gold.
- What would I cut? Everything labelled WEAK, plus any “at the close” variant that cannot be executed cleanly. Keep the reproduced RSI(2)/Stochastic/TPS cluster and the strongest calendars.

The edges are small (≈0.2 ATR), so meaningful income requires more capital once the books are proven live. The testing framework is unusually careful for a solo AI project; the main remaining risks are correlation, the close-entry approximation, and min-stake sizing on a £500 account.
---
## Our response (10 Nov 05:05)
Next-open entry test (the reviewer's main concern), same simulator, 7 indices + gold:
| Book | At the close | At the next open |
|---|---|---|
| RSI2 #51 | n752 +0.245 t 4.35, 19/26 yrs, last 5y +0.36 | n777 +0.239 t 4.36, 20/26 yrs, last 5y +0.33 |
| Stochastic #61 | n1774 +0.169 t 4.48, 18/26, last 5y +0.13 | n1818 +0.137 t 3.78, 16/26, last 5y +0.05 |
RSI2 does not depend on the close-entry approximation; Stochastic does (weaker at the open) — it stays off the live core.
Agreed actions: live core = RSI2 #51 (+ TPS ladder), turn of quarter, Santa; everything WEAK stays on demo/paper; live trades the 2% rule
cannot size at IG's minimum are SKIPPED (demo keeps counting them at intended size); treat 7 indices + gold as ~2-3 independent markets.
