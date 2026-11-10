# 212 — Live money rules that scale with the pot and the number of books (10 Nov 2026)

DK 07:51: "These rules need to be able to scale as the number of books and pot size increase" — 07:53: "Because I may add funding where possible".

## One place: `config/live_pot.json` (read by `src/live_limits.py`, used by BOTH live runners)
pot_gbp 500 · risk_per_trade 2% · exposure 5x · day stop 4% · floor 15% · equity-index risk cap 6% · compound on · deposits_raise_pot on ·
books: intraday (Ignition, spike) and daily (RSI4, TPS, TOM, Santa), each with a sizing `share` (1.0 now).

## How it scales
- Every limit is a share of the pot, never a £ figure in code.
- Pot used for sizing and caps = pot_gbp + DK's net deposits + all books' trading P&L since live started (whole IG account).
- **Deposits and withdrawals** (IG DEPOSIT / WITHDRAWAL transactions) are never counted as profit or loss: a deposit raises the pot and every
  limit with it at the next run; a withdrawal lowers it; neither can trip the day stop or floor.
  Test: £500 pot, −£20 trading → £480; deposit £1,000 → £1,480 (change still −£20); a further −£100 that day = −£120 → day stop.
- Exposure cap, day stop and floor are measured on the WHOLE account, so adding a book never multiplies the risk.
- A bigger pot automatically un-skips trades: at £500 the IG minimum stake rules out TPS, most US Tech 100 and Wall Street trades;
  from roughly £1,500–2,500 they fit inside 2% and start trading with no code change.
- Adding a book = one entry under "books" (DK's decision, CAP-021); a share below 1.0 gives it a smaller slice of the pot.
