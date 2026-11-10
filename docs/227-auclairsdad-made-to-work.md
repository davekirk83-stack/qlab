# 227: AuclairsDad's system, made to work on the IG runner (10 Nov 2026, late)

DK, 22:35: "go back to auclair's dad's system and make it work. I already gave you the components."

**His components** (doc 90 and doc 198), all used as he gave them:
1. **Regime:** 16 × 15-minute regression. It is in trend when |t| > 2 and R² > 0.3, and released when |t| < 1.
2. **Coil:** the 20-bar range is no more than 4 ATR.
3. **Trigger:** the Ignition bar.
4. **Management:** his panel as Ignition v1.1.

**Test set-up.** US Tech 100, 5-minute bars, Oct 2025 to Nov 2026, at the data's spread plus 1 point outside US cash hours. The sample is split into a development period and a later hold-out period that was not used to choose settings. Script: `src/ad_stack_refine.py`. Output: `runs/gate/ad_stack_refine.txt`.

| Version | Trades/yr | Pts/trade | Win | Dev / hold-out | Months + | Worst month |
|---|---|---|---|---|---|---|
| **Full stack, all hours, Tue/Wed off** | 124 | **+6.33** | **70%** | +7.14 / **+5.13** | **10/14** | **−48** |
| Full stack, runner hours, Tue/Wed off | 62 | +6.74 | 62% | +11.81 / +1.67 | 7/13 | −88 |
| Full stack, runner hours | 101 | +1.81 | 57% | +8.89 / −6.72 | 5/13 | −156 |
| Full stack, US cash hours only | 22 | +4.50 | 65% | +19.43 / −6.99 | 7/9 | −94 |
| **Ignition v1.1 alone, runner hours** (London 08:00 to 17:00 NY, ex lunch) | **344** | **+4.57** | 62% | +6.41 / +1.91 | **11/14** | −190 |

## What this means
- **The complete stack works best around the clock with Tuesday and Wednesday off.** It is positive in both the development period and the hold-out, wins 70%, and its worst month is the smallest of any version. Running it needs 24-hour runner sessions; the runner is currently only up from London morning to the US close. That is the next build.
- **Live Ignition currently trades US cash hours only, about 87 trades a year.** Trading whenever the runner is up (London 08:00 to 17:00 New York, still skipping the US lunch) gives about 344 a year at +4.6 points each, with 11 of 14 months positive. This is the quickest way to more trades.

## Done tonight
- `src/ig_runner.py`:
  - new switch `IG_IGN_HOURS` (`us` by default, which is unchanged; `runner` = London 08:00 to 17:00 NY);
  - `IG_AD_STACK=1` turns on his regime and coil gate, with Tuesday and Wednesday off;
  - both were bench-tested.
- **Demo:** `IG_IGN_HOURS=runner` from tomorrow's 07:55 London session.
- **Live:** unchanged until DK decides. Live would also need the London-morning cron restored.
