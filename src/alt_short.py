"""
THE ALT SHORT — the cascade mirror, armed by positioning. Item 3 of doc 75.

The cascade earns because crypto leverage is net LONG: a sharp fall forces
liquidations that dump at market, and the first green bar after the flush is
the entry. Its mirror - short the vertical spike UP - fails overall (doc 35,
t = -6.80) because there is usually no crowd of shorts to be squeezed. The
standing prediction (capital-research) is that in a bear, when funding turns
negative and positioning flips, the mirror should start working.

TEST, on the 27 registered coins' 15-minute bars, 2021-2026, ALTS ONLY
(BTC and ETH excluded per DK, 16 Oct):
  signal   a 15m bar whose close is >= +X% above the close 2 bars earlier
           (a vertical spike up over 30 minutes), X = 4%
  entry    short at the open of the bar after the first bar whose high is
           below the prior bar's high (the spike has stalled)
  exit     TP -2.0%, SL +2.5%, abandon after 8 bars (2h) at the close
  costs    chase in (limit at the open +0.05 ATR premium, 1.5bp) and taker
           out 4.5bp + 5bp slip - as the cascade is costed
GATES (funding = the coin's own last 8h Binance perp funding before entry)
  ungated          every signal
  funding < 0      positioning net short at the time
  funding < -0.01% strongly negative
  market gate      median funding across the panel < 0
CONTROL  random entry, same coin, same TP/SL/abandon geometry, short.
Reported overall, 2022 alone (the bear), and ex-2022. One row per episode.
"""
import warnings; warnings.filterwarnings("ignore")
import json, glob, os
import numpy as np, pandas as pd

MK, TAKER, SLIP, PREM = 1.5/10000, 4.5/10000, 5/10000, 0.05
X, TP, SL, ABANDON = 0.04, 0.020, 0.025, 8
RNG = np.random.default_rng(33)
REG = json.load(open("/home/claude/qlab/runs/range_universe.json"))["registered_universe"]
ALTS = [s for s in REG if s not in ("BTCUSD", "ETHUSD")]


def load():
    out = {}
    for s in ALTS:
        f = f"/home/claude/qlab/data_15m/{s}.csv"; c = s[:-3]
        fp = f"/home/claude/qlab/data_funding_binance/{c}.csv"
        if not (os.path.exists(f) and os.path.exists(fp)): continue
        d = pd.read_csv(f, index_col=0); d.index = pd.to_datetime(d.index, utc=True, format="ISO8601")
        d = d[~d.index.duplicated(keep="last")].sort_index()
        fr = pd.read_csv(fp); fr["ts"] = pd.to_datetime(fr.ts, utc=True, format="ISO8601"); fr = fr.set_index("ts").rate.sort_index()
        d["fund"] = fr.reindex(d.index, method="ffill").values
        out[s] = d
    return out


def episodes(d, gate):
    C, H, L, O, F = d.close.values, d.high.values, d.low.values, d.open.values, d.fund.values
    pc = np.roll(C, 1); pc[0] = C[0]
    tr = np.maximum(H-L, np.maximum(np.abs(H-pc), np.abs(L-pc))); a = pd.Series(tr).rolling(14).mean().bfill().values
    spike = (C/np.roll(C, 2) - 1 >= X); spike[:2] = False
    rows = []; n = len(C); i = 250
    while i < n - ABANDON - 3:
        if not spike[i] or not gate(F[i], i): i += 1; continue
        # wait for the stall: first bar whose high is below the prior bar's high, within 4 bars
        j = i + 1; stalled = False
        while j < min(i + 5, n - ABANDON - 2):
            if H[j] < H[j-1]: stalled = True; break
            j += 1
        if not stalled: i = j; continue
        e = j + 1; px = O[e] + PREM*a[e]      # short at the next open, chase premium against us
        entry = px*(1 - MK)
        tp, sl = px*(1 - TP), px*(1 + SL); out = None
        for k in range(e, e + ABANDON):
            if H[k] >= sl: out = sl*(1 + TAKER + SLIP); how = "stop"; break
            if L[k] <= tp: out = tp*(1 + MK); how = "tp"; break
        if out is None: out = C[e + ABANDON - 1]*(1 + TAKER + SLIP); how = "time"; k = e + ABANDON - 1
        rows.append((d.index[e].year, entry/out - 1, how, F[i]))
        i = k + 1
    return rows


def control(d, nrows):
    C, H, L, O = d.close.values, d.high.values, d.low.values, d.open.values
    pc = np.roll(C, 1); pc[0] = C[0]
    tr = np.maximum(H-L, np.maximum(np.abs(H-pc), np.abs(L-pc))); a = pd.Series(tr).rolling(14).mean().bfill().values
    rows = []; n = len(C)
    for _ in range(nrows):
        e = int(RNG.integers(250, n - ABANDON - 2)); px = O[e] + PREM*a[e]; entry = px*(1 - MK)
        tp, sl = px*(1 - TP), px*(1 + SL); out = None
        for k in range(e, e + ABANDON):
            if H[k] >= sl: out = sl*(1 + TAKER + SLIP); break
            if L[k] <= tp: out = tp*(1 + MK); break
        if out is None: out = C[e + ABANDON - 1]*(1 + TAKER + SLIP)
        rows.append((d.index[e].year, entry/out - 1, "", np.nan))
    return rows


def line(lbl, R, Cc):
    if len(R) < 30: print(f"  {lbl:<34} n={len(R):<6} too few"); return
    t = R.ret.mean()/(R.ret.std(ddof=1)/np.sqrt(len(R)))
    print(f"  {lbl:<34}{len(R):>7,}{R.ret.mean()*100:>+8.3f}%{t:>+7.2f}{(R.ret>0).mean()*100:>6.0f}%"
          f"{(R.how=='tp').mean()*100:>6.0f}%{Cc.ret.mean()*100:>+9.3f}%{(R.ret.mean()-Cc.ret.mean())*100:>+8.3f}")


if __name__ == "__main__":
    data = load()
    allf = pd.concat([d.fund for d in data.values()], axis=1)
    mkt = allf.median(axis=1)
    print(f"{len(data)} alts, 15-minute bars, spike >= +{X*100:.0f}% in 30 min, short the stall; TP -{TP*100:.1f}% SL +{SL*100:.1f}% abandon {ABANDON} bars.\n")
    print(f"  {'variant':<34}{'n':>7}{'per ep':>9}{'t':>7}{'win':>7}{'TP hit':>7}{'control':>10}{'edge':>8}")
    GATES = {"ungated": lambda f, i: True,
             "funding < 0": lambda f, i: np.isfinite(f) and f < 0,
             "funding < -0.01%": lambda f, i: np.isfinite(f) and f < -0.0001,
             "funding > 0 (crowded long)": lambda f, i: np.isfinite(f) and f > 0}
    for gname, g in GATES.items():
        R, Cc = [], []
        for s, d in data.items():
            r = episodes(d, g); R += r; Cc += control(d, len(r))
        R = pd.DataFrame(R, columns=["y","ret","how","fund"]); Cc = pd.DataFrame(Cc, columns=["y","ret","how","fund"])
        print(f"\n{gname}")
        line("all years", R, Cc)
        line("2022 (the bear)", R[R.y == 2022], Cc[Cc.y == 2022])
        line("ex 2022", R[R.y != 2022], Cc[Cc.y != 2022])
        line("2025-2026", R[R.y >= 2025], Cc[Cc.y >= 2025])
    # market-wide gate
    R, Cc = [], []
    for s, d in data.items():
        m = mkt.reindex(d.index, method="ffill").values
        r = episodes(d, lambda f, i: np.isfinite(m[i]) and m[i] < 0); R += r; Cc += control(d, len(r))
    R = pd.DataFrame(R, columns=["y","ret","how","fund"]); Cc = pd.DataFrame(Cc, columns=["y","ret","how","fund"])
    print("\nmarket gate: panel median funding < 0")
    line("all years", R, Cc); line("2022 (the bear)", R[R.y == 2022], Cc[Cc.y == 2022]); line("ex 2022", R[R.y != 2022], Cc[Cc.y != 2022])
    print("\n  Reference: the long cascade (doc 56 base-then-bid) +0.378%/trade, win 65.8%, edge over control +0.316pp.")
