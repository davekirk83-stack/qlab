# 88 — Absorption with true aggressor delta: the free test (19 Oct 2026)

DK, 19 Oct 10:09: *"Try the free alternative first."* Binance Vision 1-minute klines carry `taker_buy_base_volume`, so delta = 2×taker_buy − volume is the real aggressor side, not a tick-rule proxy. 18 perps, 2 Sep 2025 – 30 Sep 2026, 10.2 million minutes. Code `src/ingest_binance_1m.py` → `data_1m_delta/`, test `src/absorb_crypto.py`, log `runs/absorb_crypto.log`.

## The test
Doc 87's lead: heavy delta while price does not move → trade against the pressure. Windows 5/15/60 min; delta z-scored against the trailing day; "price did not move" = |move| < 0.25 ATR (also 0 and 0.5). Control reads: go-with (dz > 2, buy), go-with with price confirming, and exhaustion fades. AuclairsDad management in ATR14(15m) units (stop 1.5, half at +1 → breakeven, trail 1.5, 2-hour cap), 4.5bp per side, 3 random controls per trade, same coin and side; exit-free ±1 ATR barrier race.

## Result
**True delta carries no forward information.** Correlation of windowed delta with the *same* window's move: +0.58 to +0.62 (it is real flow — it moves price as it happens). Correlation with the *next* window's move: −0.001, −0.0002, −0.002 at 5, 15, 60 minutes.

| read (15-min window) | n | per ep | t | random ctrl | edge | coins | race | ctrl |
|---|---|---|---|---|---|---|---|---|
| absorption, z>1.5, move<0.25 ATR | 41,667 | −0.029% | −6.3 | −0.045% | +0.016 | 83% | 50% | 50% |
| absorption, z>2 | 20,454 | −0.032% | −4.9 | −0.048% | +0.015 | 72% | 50% | 50% |
| absorption, z>3, move<0.5 | 9,657 | −0.031% | −3.1 | −0.058% | +0.027 | 61% | 50% | 49% |
| go-with, z>2 | 72,115 | −0.057% | −16.3 | −0.044% | −0.013 | 28% | 49% | 50% |
| go-with + price confirms | 62,730 | −0.058% | −15.8 | −0.043% | −0.016 | 28% | 49% | 50% |
| exhaustion fade | 47,410 | −0.029% | −6.4 | −0.044% | +0.016 | 72% | 51% | 50% |

Same picture at 5 and 60 minutes, every month, both sides, Asia session. Absorption's edge over random is 1.5bp — a third of one side's cost — and it never beats zero; the exit-free race is 50% in every cell. Going *with* heavy delta is reliably worse than random (17–39% of coins), the clearest result in the table: by the time aggressive flow is visible in aggregate, the move it caused is over.

## What this settles
The one lead from his market is dead on real flow. Aggregate order-flow delta — proxy or true, with or against, confirmed or absorbed, 5 minutes to an hour — predicts nothing at these horizons on either panel. If AuclairsDad has an edge, it is not "the delta" as a short-horizon signal; it would have to be in per-price-level footprint detail or his hand-drawn levels, neither of which an aggregate feed can show, and the paid CME trade data would only give the same aggregate at better fidelity. **Recommendation: do not buy the CME data.** Finding 158 REJECTED. The AuclairsDad book stays in the ledger as finding 157, OPEN — UNRESOLVED (no observable mechanism found; no further spend), not as a candidate.

Kept: `data_1m_delta/` — 14 months of true taker delta on 18 perps is the dataset for any future order-flow question (and finally lets doc 23's volume findings be tested with aggressor side).
