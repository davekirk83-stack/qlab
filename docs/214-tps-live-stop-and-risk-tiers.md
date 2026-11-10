# 214 — TPS on live at the minimum stake, its £100 stop, and risk tiers (10 Nov 2026)

DK 08:22 "Yes" (TPS live with its own loss limit) · 08:22 "Set the TPS stop loss at £100 until the account has grown to £1000" ·
08:23 "We need to be aggressive at this early stage and decrease risk as the stack builds".

## Built (live daily runner + config/live_pot.json)
- TPS ladders may use IG's minimum stake (0.01/pt) even when that is above 2% risk (tier flag `tps_min_stake`).
- **TPS book stop**: realised + open TPS P&L <= −£100 (pot under £1,000) -> every TPS position is closed and no new ladders until DK restarts TPS.
  From £1,000 the stop is a share of the pot (10%, then 7.5%, then 5%).
- TPS P&L is kept out of the other books' −4% day stop and −15% floor (its own stop governs it); exposure cap (5x) still covers everything.
- **Risk tiers** (from pot size up): £0 2% per trade, TPS at minimum, stop £100 · £1,000 2%, TPS stop 10% · £2,500 1.5%, TPS stop 7.5% ·
  £5,000 1%, TPS sized normally (no minimum-stake exception), stop 5%.

## Replay Nov 2019 – Nov 2026 through the live runner (5x cap enforced on the whole account)
| | total | worst month | max drawdown | lowest balance |
|---|---|---|---|---|
| TPS at minimum, no stop | +£880 (TPS +£653) | −£176 | £216 | £312 |
| **TPS with the £100 stop (as built)** | **+£263** | −£125 | £150 | £382 |
| no TPS | +£367 | −£53 | £75 | £485 |
With the £100 stop, TPS stopped on 10 Mar 2020 (COVID crash) at −£103 and never restarted; TPS would have made +£817 after that date.
Open question for DK: restart rule after a TPS stop.
