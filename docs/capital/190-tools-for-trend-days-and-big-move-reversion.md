# 190 — Tools for trending days, and mean reversion after big moves (6 Nov 2026)

DK 17:45: "What this tells me is that we lack the right tools at the moment to operate in all markets" / "We'll work on it".
DK 17:46: "We once talked about mean reversion from big moves. This is something we need to look into."
Context: the live IG book took no trades in its first 1.5 sessions (Thu 18:02–22:00, Fri 13:49–17:05) during the most violent week in months; no Ignition signal on either feed; the ladder correctly off in a trend.

Pre-registered test `src/trend_day_test.py` (one year of 5-min data, dev Nov–Apr / hold May–Oct, IG costs, random-direction control); results `runs/trend_day_test.txt`.
Pass = >= +0.10R in both halves, >= 30 trades per half, above control in both.

| | US Tech 100 dev / hold | US 500 dev / hold | FTSE 100 dev / hold |
|---|---|---|---|
| A trend-day pullback | −0.19 (39) / +0.05 (59) | −0.08 (49) / −0.24 (55) | +0.06 (53) / **+0.25 (61)**, beats control both |
| B ORB, volatile days | +0.04 (33) / −0.28 (15) | +0.10 (42) / −0.14 (26) | **+0.12 (49) / +0.13 (29)**, beats control both |
| B0 ORB, all days (control) | +0.03 / −0.09 | +0.02 / −0.07 | +0.05 / −0.10 |
| C big-move reversion | −0.51 (14) / −0.24 (18) | +0.06 (13) / +0.20 (17) | +0.02 (20) / −0.01 (19) |
| C2 reversion, VIX >= 20 | n 5 / 1 | n 3 / 1 | n 5 / 2 |

Verdict: nothing passes. Two near-misses, both on the FTSE only (ORB on volatile days: hold half 29 trades, one short; trend pullback: dev half +0.06). One market out of three, out of 15 tries, is what chance alone would throw up — not enough to trade.
Big-move mean reversion: one year gives only 13–20 big-move days per half — far too few to judge either way. Not rejected; untestable on this data.
Next step: pull 5–8 years of index 5-min history (Dukascopy) and re-run C, and the FTSE A/B near-misses, on the longer record with the same rules. Nothing goes on the demo until something passes there.

## Cross-market reversion scan (DK 17:46: "Identify an asset that has moved erratically, then monitor it for some kind of reversion")
20 IG-type markets (S&P, Nasdaq-100, Dow, FTSE, DAX, Nikkei, Hang Seng, Euro Stoxx, gold, silver, WTI, Brent, natgas, copper, EUR/USD, GBP/USD, USD/JPY, AUD/USD, BTC, ETH), 15 years of daily closes (Yahoo).
Event = a daily move of 3+ standard deviations (60-day). Trade = fade it at the close, hold 1/3/5/10 days; costs ~0.05–0.1% spread + 0.018%/night funding.
- 1,135 events. Fading them LOSES: 1d +0.04%, 3d −0.31%, 5d −0.72%, 10d −0.73% (win 45–52%). Calm-day control: −0.07/−0.11/−0.17/−0.31%.
- Worst after big moves: ETH −3.7% (5d), natgas −2.1%, Brent −2.0%, WTI −2.0%, BTC −1.4% — big moves in these CONTINUE.
- Only the US indices showed reversion on the whole sample (S&P +0.6%, Nasdaq +0.5% at 5d) — but by half: S&P 3σ down-day buys +0.49% (2011–18) then −0.59% (2018–26); Nasdaq +0.88% then −0.53%; Dow +0.55% then −1.78%. The old "buy the crash day" edge has gone in the second half.
Verdict: no general reversion after erratic moves on daily bars; if anything, momentum. Settled (add to doc 182 when the PA project is attached). Intraday big-move reversion (C) still needs longer intraday history.

## Reacting to shocks — ladder "no fading" pause (DK 17:48: "If there is a big piece of news which hits a market, we need to be able to react to it ... we don't want to be fighting developments in the news blindly")
Price reacts before any headline can be read, so the first layer is price-based. Test `src/shock_pause_test.py`, results `runs/shock_pause_test.txt`. Shock = a 15-min bar with range >= 3x the mean of the previous 96 bars (about 1.3-2 a day; many are at the open).
Ladder episode P&L sum, dev / hold:
- US Tech 100: baseline +2.56% / +5.79% -> S1 (no rungs AGAINST the shock for 2h) **+7.72% / +8.61%**; S2 (no rungs either side) +4.51 / +4.62; S3 (S1 for 4h) +6.23 / +7.53.
- FTSE 100: +2.99 / +7.84 -> S1 **+3.28 / +9.81**; S2 +1.36 / +8.20; S3 +4.04 / +8.72.
- US 500: +7.57 / +5.71 -> S1 +5.85 / +4.51 (worse), but its worst episode improves (-0.61 -> -0.42, -1.06 -> -0.42).
S1 improves profit in both halves on 2 of 3 markets (including the live one) and cuts the worst episode on all three, with ~30% fewer episodes (less margin tied up). Unlike doc 181 (pausing after level breaks: worse 6/6), this pause is keyed to abnormal bars and only blocks the side that fights the move. Candidate for the demo; awaiting DK.
Second layer (headlines): planned — a news watch that flags market-moving headlines and scheduled releases into the engines' calendar.
