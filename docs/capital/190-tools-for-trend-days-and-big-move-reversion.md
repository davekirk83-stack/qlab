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
