# 191 — Sunday research: spikes, snap-backs, order flow and stress (8 Nov 2026)

DK asked (6 Nov) for a Sunday session on the tools we lack for trending, spiking and reverting markets, under the standing rule
"solve, don't kill" (docs/STANDING-RULE-solve-dont-kill.md). Saturday's posts added: long/short crowding, capitulation-day
signs, order flow (delta, CVD, absorption, stacked imbalances, footprint), candlestick patterns, thesis-based exits and ICT
sweep/displacement. Every idea below was built to work first; where the plain version failed, it was rebuilt around the place it
should matter (usually: after a stress move), and only then judged on data it was not tuned on.

## Data added
- BTC: Binance spot 1-minute bars Jan 2020 – 7 Nov 2026 with **true taker delta** (taker-buy volume) — `data_long/btc_1m.parquet`.
- BTC: Binance aggTrades for stress days since 2022, reduced to taker orders >= 5 BTC — `data_long/bigorders_*.parquet`.
- US Tech 100: Dukascopy 1-minute Jan 2020 – Aug 2021 (`data_long/nq_5m_2020_21.csv`) as a second, independent period
  alongside the existing Nov 2025 – Nov 2026 cache. (Dukascopy throttled the download; 2021-08 → 2025-10 is still missing.)
- Daily NDX, S&P 500, Russell 2000, VIX since 1990 (Yahoo).

## What looks exploitable

### 1. Spike continuation engine (US Tech 100, US 500) — `src/spike_shape_test.py`, `src/spike_engine_iter.py`, `src/spike_cont_other.py`
Abnormal 15-min bar = range >= 3x the prior 5 sessions' mean 15-min range (cash session). The **next 15-min bar decides**:

| | 2020-21 | 2025-26 |
|---|---|---|
| next bar pulls back → retraces >= 50% of the spike within 2h | 86% | 86% |
| next bar extends > 0.25 range → extends >= 0.5 range more | 76% | 77% |
| spike closed with a wick → retraces >= 50% | 95% | 100% |

CONT engine (chosen on 2020-21 only): next bar extends > 0.25 range and closes beyond the spike's close → enter at that close
with the spike; stop at the next bar's opposite extreme; target 1x spike range; 2h / session-end exit.
- US Tech 100 dev 2020-21: n42, +0.38R, win 40%. **Holdout 2025-26: n40, +0.19R, +1,099 pts.**
- US 500 2025-26 (never tuned): n34, +0.27R. FTSE 100 2025-26: n15, flat.
This is the missing trending-day tool: it fires exactly on the days the ladder should be standing aside.

The SNAP (fade) side is real descriptively but entering after the confirming bar leaves too little: best grid −0.04R holdout.
The snap-back is better caught by the existing range ladder's rungs once the shock pause (doc 190 S1) lifts.

### 2. Big-day forecast at 10:00 NY — `src/vol_forecast.py`
First-30-minute range vs its 20-day mean is the forecaster (both periods):
- <= 0.8x normal → big day (range >= 1.5x mean) only 2%;
- 1.6–2.2x → 50–66%; > 2.2x → 94–100%.
- A big yesterday raises the odds (30–56%). Five-day **compression does not** predict expansion (expansion follows expansion).
Rule "first 30 min >= 1.6x normal OR gap >= 0.5x range" flags ~40% of sessions and catches ~80% of big days.
Use: a 10:00 NY **mode switch** — big-day mode: ladder rungs off (or shock pause), CONT + Ignition on; quiet mode: ladder on.

### 3. BTC stress snap-back ladder (spot, long only) — `src/btc_orderflow_stress.py`, `src/btc_stress_ladder.py`
The edge is the **location**: a new 4h low after a 24h fall >= 3x the 30-day median 24h move → +26 to +35bp over 4h in both
halves (ordinary 4h lows: +2 to +6bp). Shorting new highs after up-stress does NOT work (asymmetric).
Ladder: arm on stress, a rung at each new 4h low >= 0.5% apart, max 4; exit at average entry +3%, or 48h, or −8% stop; 0.10% costs.
- dev 2020-23: n385 episodes, +0.15% per episode (of budget), win 76%, worst −7.2%
- hold 2024-26: n231, +0.10%, win 69%; random non-stress control in the holdout: −0.07% to −0.13%.
- With DK's 99-day smoothed MA as the regime filter: above the line dev +0.26% / hold +0.12% per episode; below the line ≈ 0.
  → trade it only above the line. **BTC is currently just below the line (~$76.5k), so it would be standing aside.**
- Crowd: works better when the Binance account long share is in its lowest third (+0.16%) than its highest (+0.06%) — 2024+.
Fits the Revolut X range-long book (spot, long only); the Revolut X runner is not built yet.

### 4. Capitulation-day retest ladder (indices, daily) — `src/capitulation_retest.py`
Trigger: index −3% on the day with VIX +25%. Rungs at the day's low, −3%, −6% for 20 days; exit +8%/40 days; stop 15% under the low.
- NDX 1990-2009: n10, +1.0%/episode, win 70%; **2010-2026: n16, +2.4%, win 81%**, worst −14%. Russell similar; S&P mixed.
- The tighter "−4% & VIX +40%" trigger: 10 of 10 winners but small (+1–1.5%).
- Thursday 5 Nov qualifies (NDX −6.4%, VIX +70%). Rungs: **26,606 / 25,808 / 25,010**, stop ~22,615.
- Not live-compatible as built: at IG's £0.01/pt minimum, a 15% stop is ~£40 per rung (> the 2% rule). Paper/demo, or DK's own
  discretionary use; a tighter-stop version needs testing.

## Useful but small

- **Thesis stops on Ignition** (`src/thesis_stop_test.py`): exit if after 2 bars there's < 0.25 ATR follow-through and the close is
  back through the signal bar's midpoint. Average loss −47 → −36 pts (dev), −59 → −46 (hold); total roughly unchanged (dev +17,
  hold −105 pts over a year). Ignition's break-even move already does most of this job. Worth it for live only as a variance cut.
- **Absorption** only means something at stress lows: delta z <= −2.5 with a close in the top 40% at a stress 4h low → +44 to +56bp
  over 4h (n46 dev / n36 hold) vs +26 to +35bp for the stress lows themselves. Too few cases to double size on (tested: no gain).
- **Long/short crowding**: see 3; and the 7 Nov study (>= 74% long: higher 30 days later 6/9, but median −9% first).

## Tested and not useful on their own (kept as context, not triggers)
- Generic order-flow triggers on BTC 2020-26 (absorption, CVD divergence, 1-min climax wicks, stacked one-sided delta): all within a
  few bp of the base rate, below costs, in both halves (`runs/btc_orderflow_test.txt`). Delta exhaustion inside stress: good in dev
  (+31bp vs +14bp at 1h), gone in holdout.
- 61 candlestick patterns on BTC 1h (`runs/candles_test.txt`): 5 of 33 positive in both halves — what chance alone gives; 0 in the
  stress context. The location does the work, not the candle.
- Stop raid / liquidity sweep as an entry (`runs/sweep_displacement_test.txt`): ~0R gross, negative after costs. Displacement raises
  the win rate from 37% to 43% (BTC) — consistent with the spike study — but not to a standalone edge.
- Big orders "trapped in wicks" (`runs/big_order_wick_test.txt`): see the addendum.

## Proposed next steps (DK to decide)
1. Demo: add the CONT spike engine on US Tech 100 and US 500 (own 8-trade allowance), and the 10:00 big-day switch.
2. Demo: switch on the shock pause (doc 190 S1) for the ladders.
3. Revolut X: build the runner with the stress snap-back ladder + 99-line filter, dry-run first.
4. Fill the 2021-25 Dukascopy gap slowly in the background to recheck 1 and 2 on a third period.
5. Hyperliquid forward recorder for big orders and net positioning (no history available).

## Addendum — big orders "trapped in the wicks" (`src/big_order_wick_test2.py`, `runs/big_order_wick_test.txt`)
490 BTC stress days 2022 – Oct 2026, 32,910 taker orders >= 20 BTC (Binance spot). Wick bars at 4h lows that contain big sell orders
in the bottom 30% of the bar, versus the same wick bars without them, forward 4h (bp, long side):
- >= 20 BTC: 2022-23 −34 vs −10 (big sellers were RIGHT — price kept falling); 2024-26 −8 vs −16 (slightly better than without).
- >= 50 BTC: 2022-23 −31 vs −14; 2024-26 −24 vs −15.
- Mirror (big buyers in upper wicks at highs, short): >= 50 BTC 2022-23 +57 vs +14, 2024-26 +13 vs +16.
No consistent exhaustion signal on Binance spot: more often the big aggressor was informed, not trapped. The Hyperliquid version
(who is opening vs closing, net positioning) can't be tested on history; a forward recorder is the only way to check it.
