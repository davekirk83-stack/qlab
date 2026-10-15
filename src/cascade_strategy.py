"""
CASCADE STRATEGY — turning the liquidation finding into a tradeable spec.

The finding (doc 33): in thin alts, an extreme liquidation cascade is followed by
~+1.8% over 72h, t=+5.07, monotonic in intensity, holding in both halves of the
sample. The open question — the one most likely to kill it — is EXECUTION, because
spreads blow out during a cascade in precisely the illiquid names where the effect
lives.

So this file does not ask "is there an effect". It asks "is there a TRADE", and it
is deliberately hostile to the answer:

  PESSIMISTIC FILLS       entry at the HIGH of the entry bar, not the close —
                          i.e. assume you got the worst price available in the
                          hour you were buying
  SLIPPAGE SWEEP          0 / 10 / 25 / 50 / 100bp, so the breakeven slippage is
                          visible rather than assumed
  ENTRY TIMING            four variants, because buying into the cascade itself
                          is a falling-knife trade and may be unexecutable
  STRUCTURAL STOP         below the cascade low, which is where the forced selling
                          actually stopped
  BTC/ETH EXCLUDED        the effect is absent there (t=+0.50) and including them
                          would flatter nothing

If the edge does not survive entry-at-the-high plus 50bp, it is not a strategy.
"""
import warnings; warnings.filterwarnings("ignore")
import os
import numpy as np, pandas as pd

OI = "/home/claude/qlab/data_oi"
PX = "/home/claude/qlab/data_1h_33"
EXCLUDE = {"BTCUSDT", "ETHUSDT"}          # effect absent in majors (doc 33)
Z_CASCADE = 4.0


def load(sym):
    """Join open-interest metrics to real hourly OHLC."""
    d = pd.read_csv(f"{OI}/{sym}.csv", parse_dates=["create_time"]).set_index("create_time")
    d = d[~d.index.duplicated()].sort_index()
    oi = d.sum_open_interest.resample("1h").last()

    k = pd.read_csv(f"{PX}/{sym}.csv", parse_dates=["date"]).set_index("date").sort_index()
    k = k[~k.index.duplicated()]

    h = pd.DataFrame(dict(open=k.open, high=k.high, low=k.low, close=k.close,
                          volume=k.volume, oi=oi)).dropna()
    h["ret"] = h.close.pct_change()
    h["d_oi"] = h.oi.pct_change()
    h["range_pct"] = (h.high - h.low) / h.close          # proxy for execution pain
    return h.dropna()


def cascades(h, z=Z_CASCADE):
    """Hours where price fell and open interest was destroyed, in the extreme tail."""
    m = (h.ret < 0) & (h.d_oi < 0)
    flush = (-h.d_oi).where(m)
    zz = (flush - flush.mean()) / flush.std()
    return zz > z


def backtest(h, sig, entry_mode, slip_bp, stop_atr=1.5, tp_pct=None,
             max_bars=72, pessimistic=True):
    """One trade per cascade. Returns a list of net returns."""
    atr = (h.high - h.low).rolling(24).mean()
    H, L, C, O = h.high.values, h.low.values, h.close.values, h.open.values
    idx = np.flatnonzero(sig.values)
    slip = slip_bp / 10000.0
    out, last = [], -1
    for i in idx:
        if i <= last:
            continue
        # ---- when do we actually get in? ----
        if entry_mode == "same bar close":
            e = i
        elif entry_mode == "next bar":
            e = i + 1
        elif entry_mode == "wait 3 bars":
            e = i + 3
        elif entry_mode == "first green bar":
            e = None
            for j in range(i + 1, min(i + 7, len(h))):
                if C[j] > O[j]:
                    e = j; break
            if e is None:
                continue
        else:
            raise ValueError(entry_mode)
        if e is None or e + 1 >= len(h):
            continue
        # PESSIMISTIC: you paid the high of the entry bar, plus slippage
        px = (H[e] if pessimistic else C[e]) * (1 + slip)
        a = atr.iloc[e]
        if not np.isfinite(a) or a <= 0 or px <= 0:
            continue
        casc_low = L[i:e + 1].min()
        stop = min(casc_low * 0.998, px - stop_atr * a)
        risk = px - stop
        if risk <= 0:
            continue
        tp = px * (1 + tp_pct) if tp_pct else None
        ex, ret = None, None
        for j in range(e + 1, min(e + 1 + max_bars, len(h))):
            if L[j] <= stop:
                ret = (min(stop, O[j]) * (1 - slip)) / px - 1; ex = j; break
            if tp and H[j] >= tp:
                ret = (tp * (1 - slip)) / px - 1; ex = j; break
        if ex is None:
            j = min(e + max_bars, len(h) - 1)
            ret = (C[j] * (1 - slip)) / px - 1; ex = j
        out.append(dict(ret=ret, bars=ex - e, entry_range=h.range_pct.iloc[e]))
        last = ex
    return out


def summarise(rows):
    if len(rows) < 30:
        return None
    r = np.array([x["ret"] for x in rows])
    se = r.std() / np.sqrt(len(r))
    return dict(n=len(r), mean=r.mean(), t=r.mean() / se if se > 0 else 0,
                win=(r > 0).mean(), med=np.median(r),
                bars=np.mean([x["bars"] for x in rows]))


def main():
    syms = [f[:-4] for f in sorted(os.listdir(OI)) if f.endswith(".csv")]
    syms = [s for s in syms if s not in EXCLUDE and os.path.exists(f"{PX}/{s}.csv")]
    frames = {}
    for s in syms:
        try:
            h = load(s)
            if len(h) > 2000:
                frames[s] = h
        except Exception:
            pass
    sigs = {s: cascades(h) for s, h in frames.items()}
    tot = sum(int(v.sum()) for v in sigs.values())
    print("CASCADE STRATEGY — hostile execution assumptions\n")
    print(f"  {len(frames)} alt perps (BTC/ETH excluded), {tot} cascade events")
    print(f"  entry at the HIGH of the entry bar + slippage. Stop below the cascade low.")
    print(f"  72-bar limit, one trade per cascade.\n")

    # how bad is the bar you are buying into?
    rng = np.concatenate([frames[s].range_pct[sigs[s]].values for s in frames])
    print(f"  EXECUTION PAIN: the cascade bar's high-low range averages "
          f"{np.nanmean(rng)*100:.2f}% of price")
    print(f"  (median {np.nanmedian(rng)*100:.2f}%, 90th pct "
          f"{np.nanpercentile(rng,90)*100:.2f}%) — this is the spread you fight.\n")

    print("=" * 94)
    print("  ENTRY TIMING x SLIPPAGE — does any version survive?")
    print("=" * 94)
    print(f"  {'entry':18s} {'slip':>6} {'n':>6} {'mean':>9} {'median':>9} "
          f"{'win':>7} {'t':>7} {'bars':>6}")
    best = None
    for mode in ("same bar close", "next bar", "wait 3 bars", "first green bar"):
        for slip in (0, 10, 25, 50, 100):
            rows = []
            for s, h in frames.items():
                rows += backtest(h, sigs[s], mode, slip)
            d = summarise(rows)
            if not d:
                continue
            flag = ""
            if d["t"] > 2 and d["mean"] > 0:
                flag = "  <-- survives"
                if best is None or d["mean"] > best[1]["mean"]:
                    best = (mode, d, slip)
            print(f"  {mode:18s} {slip:5d}bp {d['n']:6d} {d['mean']*100:+8.3f}% "
                  f"{d['med']*100:+8.3f}% {d['win']*100:6.1f}% {d['t']:+7.2f} "
                  f"{d['bars']:6.1f}{flag}")
        print()

    if best:
        print("=" * 94)
        print(f"  BEST SURVIVING CONFIG: {best[0]} @ {best[2]}bp slippage")
        print("=" * 94)
        print(f"    mean {best[1]['mean']*100:+.3f}%  median {best[1]['med']*100:+.3f}%  "
              f"win {best[1]['win']*100:.1f}%  t={best[1]['t']:+.2f}  n={best[1]['n']}")
    else:
        print("  NOTHING SURVIVES. The effect is real but not tradeable at these costs.")


if __name__ == "__main__":
    main()
