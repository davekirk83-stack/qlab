# 140 — Fear & Greed and VIX: no usable signal (27 Oct 2026)
(Held in the repo because the claude.ai project is at its size limit.)

DK shared Crypto Tony's "FEAR 43 … Bottom not in" post: "Possibly useful … Along with VIX".
Data: alternative.me Fear & Greed 2018–2026 (reads 48 now; Tony's 43 is CoinMarketCap's index), Cboe VIX 1990–2026 (18.4 on 26 Oct).
Script `src/fng_vix_test.py`; output in `runs/fng_vix_test.txt`.

- **Fear & Greed vs BTC 30d forward (median):**
  - extreme fear +1.8%; fear −1.6%; 40–49 +5.6%; 50–59 0%; greed +2.2%; extreme greed +3.6%. All days +1.6%.
  - Not monotone; no edge.
  - Tony's situation (falling from greed into 40s, 33 episodes): ≥5% lower within 30 days 61% vs a 57% base rate. "Bottom not in" is the base rate.
- **VIX level vs BTC 30d:**
  - <15 +4.9%; 15–20 +0.4%; 20–25 +4.8%; 25–30 +4.1%; 30+ +7.9% (all days +3.2%).
  - The 15–20 band (where VIX sits now) is the weakest, but the pattern isn't monotone.
- **VIX 30+ vs QQQ:** day-weighted it looks great (21d +7.0%, 84% up), but that's clustered.
  - On the first day of each of 13 separate episodes since 2016: 8/13 up, median +3.6%, worst −9.9% (Feb 2020).
  - It's the known "buy the panic" tendency: real-ish but small-sample, and a long-term-investing idea rather than a trading book.
- **VIX 5-day spikes:** nothing for BTC or QQQ.
- **Combinations:** fear with calm VIX (<20) gives a BTC 30d of −0.2% (49% up), vs +3.3% with stressed VIX (≥25). Small edge, not significant.

**Verdict:** neither index is a trading signal for our books.
- Note for the investing side: first closes above VIX 30 have been decent long entries for indices (8/13).
