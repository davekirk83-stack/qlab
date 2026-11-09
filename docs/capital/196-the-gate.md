# 196 — THE GATE: one standard test for every book (9 Nov 2026, DK: "you don't have a standardised test")

Code: `src/gate.py` (the test), `src/gate_books.py` (every book plugged in), results `runs/gate/results.txt` + per-book JSON/trades.
Rules are fixed in the code's docstring and do not change per idea:
- look-ahead detector: signals recomputed on data cut at 25 random points must match the full-data signals before each cut;
- the gate (not the strategy) fills orders: close / next open / limit strictly through / stop through; stop before target in every bar;
  gaps fill at the open; trailing changes apply from the next bar; one position per market; costs per trade;
- holdout = last 365 days (last 40% if under 2 years of data), never used to build;
- TESTED = holdout n >= 50, mean R > 0, t >= 2, both holdout halves > 0, above the 95th percentile of 200 random-entry runs;
  WEAK = holdout mean and both halves > 0 but fails a count/significance/random test; FAILED = otherwise.

## First run, 9 Nov (every existing book)
| Book | Label | Holdout | Note |
|---|---|---|---|
| Ignition v1.1, US Tech 100 | FAILED (borderline) | n39, +0.14R, halves +0.30 / -0.02, t 1.3 | dev n48 +0.24R; overall positive but the latest 2 months flat |
| Spike, US Tech 100 | FAILED | n18, -0.08R | dev +0.29R |
| Spike, US 500 | FAILED | n8, +0.08R, halves -0.51 / +0.67 | dev +0.44R; too few |
| Spike, Wall Street | WEAK | n10, +0.46R both halves | 7 months of data only |
| Spike pooled (3 indices) | — | n36, +0.11R, halves -0.32 / +0.53 | |
| ORB gold London | FAILED | n46, -0.03R | dev +0.14R — did not hold |
| Book 15 sweep BTC / ETH / SOL | FAILED / WEAK / FAILED | -0.09 / +0.10 / -0.17R (n78-89) | pooled n255 -0.06R; at 0.1% round-trip costs (research used 0.04%) |
| Book 16 OBV divergence BTC / ETH / SOL | FAILED | n9 / 3 / 5 | pooled n17 -0.04R; dev pooled +0.17R n72; research counted overlapping trades |
| Keltner Range v1 (daily, 26 coins) | FAILED | pooled n21, -0.15R | dev pooled n127 -0.01R |

Nothing reaches TESTED. The live account now runs Ignition (borderline) and the spike engine (failed on US Tech 100, too few on US 500)
at IG minimum stakes. Decision for DK at the review: keep them as minimum-stake real-fill measurement, or pause.
