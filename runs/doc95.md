# 95 — The allocator, backtested: pooled-by-active beats reserved (19 Oct 2026)

DK, 19 Oct: *"Would it not make sense to allocate capital according to what is active at any moment in time?"* … *"allowing for maximum punch from our limited capital"* … *"If multiple are active they then share it accordingly."* Tested on the four books with twelve months of common history (15 Oct 2025 – 16 Oct 2026): Range v3 (doc 91), Ignition v1 (doc 92), Death-cross short v1 (doc 82), Golden-cross long v1 (doc 83). Code `src/allocator.py`; log `runs/allocator.log`; daily series `runs/allocator_daily.csv`, `runs/allocator_active.csv`.

## Method
Each book's daily return is its own registered paper book through the registered simulator ($2,000, 20 slots at 3× for the crypto books; 1 MNQ per $2,000 for Ignition), slot-capped. **Every book is then scaled to the same 1%/day volatility**, so the schemes differ only in allocation logic — otherwise the range book's backtest (doc 91: +1634% CAGR at 1×; at 3× it compounds to tens of millions, a capacity fantasy) swamps every comparison. A book is "active" on a day if it has an open position. Schemes: ALONE; RESERVED (fixed 1/N always); POOLED-ACTIVE (the day's budget split equally among active books, per-book ceiling 50%); POOLED-RISK (shares inverse to trailing 30-day volatility); POOLED-RISK + governors (budget halved while a book is >15% off its high; portfolio day stopped at −4%).

## Result (equal unit risk; CAGR comparable across rows, not a forecast)
| scheme | CAGR | maxDD | Sharpe | worst day | months >0 |
|---|---|---|---|---|---|
| alone: Range v3 | +836% | −4.1% | 11.8 | −2.1% | 100% |
| alone: Ignition | +64% | −7.4% | 2.7 | −4.5% | 77% |
| alone: Golden-cross | +41% | −7.1% | 1.9 | −2.3% | 31% |
| alone: Death-cross | +19% | −23.2% | 1.0 | −3.2% | 54% |
| RESERVED equal split | +129% | −1.6% | 9.0 | −1.0% | 92% |
| **POOLED-ACTIVE equal shares, ceiling 50%** | **+230%** | −2.7% | 8.7 | −1.8% | 92% |
| pooled-active, no ceiling | +235% | −2.7% | 8.8 | −1.8% | 92% |
| pooled, inverse-vol shares | +189% | −3.0% | 8.3 | −1.7% | 92% |
| pooled, inverse-vol + governors | +192% | −3.0% | 8.6 | −1.7% | 92% |

Pairwise daily correlations all within ±0.11. Active share of days: Range 100%, Death-cross 92%, Ignition 71%, Golden-cross 34%; no day with nothing active. **Diversification test (AuclairsDad's): 5.7% of days have two or more books each losing more than half a daily budget** (21 days; three or more on 2 days).

## Reading
1. **Pooling by what is active returns 1.8× the reserved split at the same risk-adjusted quality** (Sharpe 8.7 vs 9.0, within noise; drawdown −2.7% vs −1.6%). DK's instinct, measured: capital that follows the signal beats capital parked by book — the same thing doc 85's shared-slot result said.
2. **Equal shares beat inverse-volatility shares** (+230% vs +189%). The simpler rule wins; the clever one chases recent quiet and under-funds the book that is about to work.
3. **The 50% ceiling costs almost nothing** (+230% vs +235%) and is the brake against a one-regime month becoming a one-book portfolio. It stays.
4. **Governors add little here** (the drawdown halving rarely fires on the scaled series; the −4% day cap never binds). They stay for the live version because the day they matter is the day the backtest did not contain.
5. **Honest caveat:** the range book alone has a higher Sharpe than any pool (11.8 vs 8.7). The pool is not justified by this year's figure; it is justified by robustness — four uncorrelated engines versus one backtest that ran 1.7% below itself in its first live week.

## Decision
Allocator design fixed (finding 163): one shared risk pool; the day's budget split **equally among active books**; per-book ceiling 50% (to be revisited at five or more books); portfolio daily loss cap −4% of the stack; drawdown governor halving a book's budget past −15% until a new high; ceilings rebalanced monthly on the 1st with the profit allocation; lot sizes follow equity only at that rebalance. Goes onto the paper ledgers as a seventh "portfolio" line once two books have clean records (doc 93's tests), never before. Rule 171: allocation follows activity; shares are equal; ceilings and caps are the discipline.
