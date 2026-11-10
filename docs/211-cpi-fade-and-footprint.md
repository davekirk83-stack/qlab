# 211 — DK's screenshots 10 Nov 07:30: CPI-day fade, iceberg/absorption

## CPI-day fade (@MrMilkTrading): yesterday closed top half of range -> short into the CPI close; bottom half -> long
- The post's own chart: 2025-26 17/21 wins (81%), but 2022-24 17/36 (47%, a coin flip). Over all 57 releases about 34/57 (60%):
  a coin does that about 1 time in 10. Classic small-sample run, not yet an edge.
- Same rule on FOMC days (214 since 2000): 50% wins, t 0.77; 2022-26: 44%.
- Same rule on EVERY day (`src/close_position_fade.py`, 6 traded markets, 2000-26): gross S&P +5.7bp/day, but after IG spread + one night's
  funding: both sides −0.024 ATR (t −4.4); long-after-bottom-half +0.018 at IG spreads; long-after-bottom-20% +0.032 (t ~1). FAIL — the
  daily edge is the size of one night's funding.
- CPI release history 2001-2021 could not be fetched (BLS site not reachable from here), so the CPI-only version can't be tested on older
  data yet. Today's (10 Nov) call per the post: sell into CPI. Not traded; shadow only.

## Iceberg vs absorption (footprint)
- Needs exchange footprint data (traded volume at each price, bid vs ask). IG gives none for indices. Already tested on BTC with true taker
  delta (doc 191): generic absorption = within a few bp of the base rate, below costs, both halves. Only at stress 4h lows did it add
  (+44 to +56bp over 4h vs +26 to +35bp), n≈40 each period — too few to trade on its own.
