# 213 — Getting the skipped trades onto the £500 book (10 Nov 2026)

DK 08:12–08:14: "Can any of those last books operate within our £500 limit at present … aside from the in-house 2% rule, can we not make money
from those books now already while the stack builds?"

## 2 ATR stop fallback (live, within 2%) — `src/fit_500.py`, runs/gate/fit_500.txt
- A tighter stop barely changes the edge: RSI(4) on US Tech 100 + Wall St +0.288 ATR at 2 ATR vs +0.290 at 3 ATR; TOM +0.180 at 2 ATR vs +0.175 at 5 ATR.
- So when IG's minimum stake (0.01/pt) would push a trade over 2% at its normal stop, the live runner now retries with a 2 ATR stop and takes
  the minimum stake if that fits under `max_risk_at_min_stake` (config/live_pot.json, 2% = no exception).
- 400-day replay: 128 trades (was 99), £500 -> £688 (was £652), 18/20 months positive, worst month −£36, max drawdown £38.
- Allowing 3% instead: £690 — no real gain. Taking US Tech 100 / Wall St signals on the US 500 instead: no edge on the extra days (t 0.5–0.7).

## TPS at the minimum stake — the one book the 2% rule really blocks
Replay Nov 2019 – Nov 2026 through the live runner with TPS rungs at IG's minimum stake (other books as above):
| | total | by year | worst month | max drawdown | lowest balance |
|---|---|---|---|---|---|
| all books | +£1,118 | 2020 −6, 2021 +249, 2022 −18, 2023 +118, 2024 +84, 2025 +289, 2026 +403 | −£134 | £229 | £374 |
| TPS alone | +£902 | 2020 −31, 2021 +214, 2022 −1, 2023 +103, 2024 +63, 2025 +219, 2026 +331 | −£122 | £196 | £382 |
| without TPS | +£215 | | −£29 | £68 | £486 |
TPS at minimum stakes is most of the money, but its worst stretch (−£196, ~40% of £500) would trip the −15% floor and many −4% day stops.
Running it would need DK to set its own loss limit for that book. DK's decision.

## US Tech 100 exception (DK 10 Nov 09:58: "make an exception for the US Tech 100 up to 3.5%")
`min_stake_exception: {"NQ": 0.035}` in config/live_pot.json. When IG's minimum stake is more than 2% at the normal stop, the US Tech 100
trade takes the 2 ATR stop (same edge) and may risk up to 3.5% (today ~2.6%: 0.01/pt x 2 x 640-pt ATR = £12.80). Other markets stay at 2%.
400-day replay, all live books incl. TPS at minimum: US Tech 100 50 trades +£186; all markets +£719.
