"""
BOLLINGER BANDS as setups, plus an audit of the scanner's confirmation checks.

Three jobs in one run:

  A. BOLLINGER SETUPS. DK's suggestion. Six variants, all event-driven with the
     spec-v1 trade management, judged on annualised return on deployed capital
     (the objective fixed in run 15 — per-trade expectancy converges on
     buy-and-hold, which is investing, not trading).

       squeeze break     bandwidth in its lowest decile, then close > upper band
       upper break       close crosses above the upper band
       band walk         3 consecutive closes above the upper band
       lower reversion   close below the lower band, then close back inside
       %B cross          %B crosses up through 0.5 from below
       squeeze + trend   squeeze break, but only above the 200d

     A squeeze is the low-volatility state. The run-12 finding was that QUIET
     breakouts beat heavy-volume ones by a wide margin, so a squeeze should be
     the better launchpad. That is a prediction this run can falsify.

  B. CONFIRMATION AUDIT. Each check in scanner.confirmations() is measured for
     its MARGINAL effect: same setup, same management, trades split by whether
     the check passed. A check that does not separate the two groups is noise
     dressed as rigour, and the volume check is suspected of being backwards.

  C. The volume check tested in BOTH directions, because the claim is not that
     volume does not matter but that the sign is wrong.
"""
import numpy as np, pandas as pd
import core as C
import levels as LV
from run10 import load_universe, atr, est_cost

PANEL = load_universe()
COSTS = {s: est_cost(d) for s, d in PANEL.items()}

MGMT = dict(stop_atr=1.0, tp1_r=1.0, tp2_r=3.0, trail_atr=2.5,
            max_bars=10, be_offset_r=0.10)


# ----------------------------------------------------------------- indicators
def bands(df, n=20, k=2.0):
    ma = df.close.rolling(n).mean()
    sd = df.close.rolling(n).std()
    up, lo = ma + k * sd, ma - k * sd
    bw = (up - lo) / ma.replace(0, np.nan)
    pb = (df.close - lo) / (up - lo).replace(0, np.nan)
    return ma, up, lo, bw, pb


def bb_setups(df):
    ma, up, lo, bw, pb = bands(df)
    c = df.close
    squeeze = bw <= bw.rolling(252).quantile(0.10)
    above = c > up
    below = c < lo
    out = {}
    out["squeeze break"] = (squeeze.shift(1) & above & ~above.shift(1).fillna(False))
    out["upper break"] = (above & ~above.shift(1).fillna(False))
    out["band walk"] = (above & above.shift(1).fillna(False) & above.shift(2).fillna(False)
                        & ~above.shift(3).fillna(False))
    out["lower reversion"] = (below.shift(1).fillna(False) & ~below)
    out["%B cross 0.5"] = ((pb > 0.5) & (pb.shift(1) <= 0.5))
    out["squeeze break + 200d"] = (out["squeeze break"]
                                   & (c > c.rolling(200).mean()))
    return {k: v.astype(float).fillna(0.0) for k, v in out.items()}


# ------------------------------------------------------------------- the trade
def trade(df, entries, cost, tags=None, stop_atr=1.0, tp1_r=1.0, tp2_r=3.0,
          trail_atr=2.5, max_bars=10, be_offset_r=0.10):
    """Event-driven. Returns (ret, bars, tagdict) per trade."""
    A = atr(df).values
    H, L, Cl, O = df.high.values, df.low.values, df.close.values, df.open.values
    SL = df.low.rolling(10).min().values
    idx = np.flatnonzero(np.nan_to_num(entries.values) > 0)
    out, last = [], -1
    for i in idx:
        if i <= last or i + 1 >= len(df):
            continue
        a = A[i]
        if not (a == a) or a <= 0:
            continue
        px = O[i + 1]
        if not (px == px) or px <= 0:
            continue
        atr_stop = px - stop_atr * a
        stop = max(atr_stop, SL[i] * 0.995) if SL[i] == SL[i] else atr_stop
        if stop >= px:
            stop = atr_stop
        risk = px - stop
        if risk <= 0:
            continue
        tp1, tp2 = px + tp1_r * risk, px + tp2_r * risk
        filled, pnl, peak, ex = 0.0, 0.0, px, None
        cur = stop
        for j in range(i + 1, min(i + 1 + max_bars, len(df))):
            if L[j] <= cur:
                pnl += (1 - filled) * (cur / px - 1); ex = j; break
            if filled < 0.34 and H[j] >= tp1:
                pnl += (1 / 3) * (tp1 / px - 1); filled = 1 / 3
                cur = max(cur, px + be_offset_r * risk + cost * px)
            if filled < 0.67 and H[j] >= tp2:
                pnl += (1 / 3) * (tp2 / px - 1); filled = 2 / 3
            if filled >= 0.66:
                tr = peak - trail_atr * a
                if L[j] <= tr and tr > cur:
                    pnl += (1 - filled) * (tr / px - 1); ex = j; break
            peak = max(peak, H[j])
        if ex is None:
            j = min(i + max_bars, len(df) - 1)
            pnl += (1 - filled) * (Cl[j] / px - 1); ex = j
        rec = dict(ret=pnl - cost, bars=max(ex - i, 1))
        if tags is not None:
            for k, v in tags.items():
                rec[k] = bool(v.iloc[i]) if i < len(v) else False
        out.append(rec)
        last = ex
    return out


def summarise(rows, label):
    if len(rows) < 80:
        return None
    r = np.array([x["ret"] for x in rows])
    b = np.array([x["bars"] for x in rows])
    exp, mb = float(r.mean()), float(b.mean())
    ann = (1 + exp) ** (252 / mb) - 1 if exp > -1 else -1
    se = r.std() / np.sqrt(len(r))
    return dict(label=label, n=len(r), exp=exp, bars=mb, ann=ann,
                win=float((r > 0).mean()), t=float(exp / se) if se > 0 else 0.0)


def line(d):
    print(f"  {d['label']:26s} n={d['n']:5d}  exp {d['exp']*100:+7.3f}%  "
          f"bars {d['bars']:5.1f}  ANN {d['ann']*100:+9.1f}%  "
          f"win {d['win']*100:5.1f}%  t={d['t']:+5.2f}")


# ------------------------------------------------------------------ tag frames
def tag_frame(df):
    """The scanner's confirmation checks, as boolean series."""
    v20 = df.volume.rolling(20).mean()
    rv = df.close.pct_change().rolling(20).std()
    rng = (df.high - df.low).replace(0, np.nan)
    ma, up, lo, bw, pb = bands(df)
    return {
        "above 200d":    df.close > df.close.rolling(200).mean(),
        "above 50d":     df.close > df.close.rolling(50).mean(),
        "vol > 20d avg": (df.volume > v20) & (v20 > 0),
        "closed strong": (df.close - df.low) / rng > 0.6,
        "vol not extreme": rv < rv.rolling(252).quantile(0.90),
        "in squeeze":    bw <= bw.rolling(252).quantile(0.25),
    }


def main():
    print("BOLLINGER SETUPS + CONFIRMATION AUDIT")
    print(f"  universe {len(PANEL)} instruments (majors + altcoins)")
    print(f"  management: {MGMT}")
    print("  objective: annualised return on DEPLOYED capital\n")

    # ---------------------------------------------------------------- part A
    print("=" * 96)
    print("A.  BOLLINGER SETUPS")
    print("=" * 96)
    allrows, res = {}, []
    names = None
    for s, df in PANEL.items():
        try:
            su = bb_setups(df)
        except Exception:
            continue
        names = names or list(su)
        for k, e in su.items():
            if e.sum() == 0:
                continue
            allrows.setdefault(k, []).extend(trade(df, e, COSTS[s], **MGMT))
    for k in names or []:
        d = summarise(allrows.get(k, []), k)
        if d:
            res.append(d); line(d)

    # benchmark: the incumbent entry from the spec
    inc = []
    for s, df in PANEL.items():
        try:
            e = LV.l_break_prior_month_high(df)
            e = pd.Series(np.nan_to_num(np.asarray(e, dtype=float)), index=df.index)
        except Exception:
            continue
        if e.sum():
            inc.extend(trade(df, e, COSTS[s], **MGMT))
    d = summarise(inc, "[incumbent] month high")
    print()
    if d:
        line(d)
        base_ann = d["ann"]
        better = [x for x in res if x["ann"] > base_ann]
        print(f"\n  Bollinger variants beating the incumbent: {len(better)} of {len(res)}")
        for x in sorted(better, key=lambda z: -z["ann"]):
            print(f"    {x['label']:26s} {(x['ann']-base_ann)*100:+9.1f}pp annualised")

    # ---------------------------------------------------------------- part B/C
    print()
    print("=" * 96)
    print("B/C.  CONFIRMATION AUDIT — does each check actually separate outcomes?")
    print("=" * 96)
    best = max(res, key=lambda z: z["ann"])["label"] if res else "squeeze break"
    print(f"  setup under test: {best}\n")
    rows = []
    for s, df in PANEL.items():
        try:
            su = bb_setups(df); tg = tag_frame(df)
        except Exception:
            continue
        e = su.get(best)
        if e is None or e.sum() == 0:
            continue
        rows.extend(trade(df, e, COSTS[s], tags=tg, **MGMT))
    if not rows:
        print("  no trades")
        return
    t = pd.DataFrame(rows)
    overall = summarise(rows, "ALL trades"); line(overall)
    print()
    print(f"  {'check':18s} {'PASS':>34s}   {'FAIL':>34s}   edge")
    for k in tag_frame(next(iter(PANEL.values()))).keys():
        if k not in t:
            continue
        a = summarise(t[t[k]].to_dict("records"), "pass")
        b = summarise(t[~t[k]].to_dict("records"), "fail")
        if not a or not b:
            continue
        gap = a["ann"] - b["ann"]
        verdict = "KEEP" if gap > 0.05 else ("INVERT" if gap < -0.05 else "noise")
        print(f"  {k:18s} n={a['n']:5d} ann {a['ann']*100:+9.1f}% exp {a['exp']*100:+6.3f}%"
              f"   n={b['n']:5d} ann {b['ann']*100:+9.1f}% exp {b['exp']*100:+6.3f}%"
              f"   {gap*100:+8.1f}pp  {verdict}")

    print()
    print("  KEEP   = the check earns its place")
    print("  INVERT = the check is BACKWARDS; requiring it costs money")
    print("  noise  = it separates nothing; drop it, it only adds false comfort")

    cum = C.ledger_bump(len(res) + 12, "bollinger setups + confirmation audit")
    print(f"\nLIFETIME TRIALS: {cum}")
    pd.DataFrame(res).to_csv("/home/claude/qlab/runs/bb.csv", index=False)


if __name__ == "__main__":
    main()
