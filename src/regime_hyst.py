"""
THE SWITCH AT THE LINE — flicker, hysteresis and hold-through.

DK, 16 Oct: "I want it to be a very clear assessment which 'engages' or
'disengages' as and when the conditions appear or change ... That would
increase the safety of the range trading book."

The registered switch (containment above its own expanding median) flips a
median 12 times a week per coin, and 29% of its engaged spells last under
four hours - shorter than the ladder's median hold. In the simulator and the
paper book an 'off' closes every open rung at the worst tick, so each false
'on' is a round trip paid for nothing. Five ways to run the same switch:

  registered   on above p50, off below p50; off closes positions
  deadband     on above p55, off below p45 (both expanding percentiles)
  dwell        on only after 8 consecutive bars (2h) above p50
  persist      off only after 8 consecutive bars below p50
  hold-through on/off as registered, but 'off' only blocks NEW entries;
               open rungs run to their own exits (target, break, cap)

Judged on the things that matter for safety: flips, total P&L, worst
episode, drawdown of the equity curve. Optimistic fills, registered ladder.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob, inspect
import numpy as np, pandas as pd
import clean_portfolio as CP
import regime_detect as RD

# a copy of CP.episodes where a gate going off does not shut the episode
_src = inspect.getsource(CP.episodes).replace(
    "def episodes(", "def episodes_hold(").replace(
    "if oi is not None and (i-oi >= CAP or broke or not ok):",
    "if oi is not None and (i-oi >= CAP or broke):")
exec(_src, CP.__dict__)
STABLE = {"USDTUSD","USDCUSD","DAIUSD","PYUSDUSD","USDSUSD","RLUSDUSD"}


def load():
    out = {}
    for f in sorted(glob.glob("/home/claude/qlab/data_15m/*USD.csv")):
        s = os.path.basename(f)[:-4]
        if s in STABLE: continue
        d = pd.read_csv(f, index_col=0)
        d.index = pd.to_datetime(d.index, utc=True, format="ISO8601")
        d = d[~d.index.duplicated(keep="last")].sort_index()
        if len(d) > 60000: out[s] = d
    return out


def gates(v):
    v = pd.Series(v)
    p50 = v.expanding(500).median()
    base = (v > p50)
    p55 = v.expanding(500).quantile(0.55); p45 = v.expanding(500).quantile(0.45)
    db = np.zeros(len(v), dtype=bool); on = False
    hi = (v > p55).values; lo = (v < p45).values
    for i in range(len(v)):
        if on and lo[i]: on = False
        elif not on and hi[i]: on = True
        db[i] = on
    run_on = base.groupby((base != base.shift()).cumsum()).cumcount()+1
    dwell = base & (run_on >= 8)
    nb = ~base
    run_off = nb.groupby((nb != nb.shift()).cumsum()).cumcount()+1
    persist = ~(nb & (run_off >= 8))
    return {"registered": base.values, "deadband 55/45": db,
            "dwell 2h before on": dwell.values, "persist 2h before off": persist.values,
            "hold-through (off blocks entries only)": base.values}


if __name__ == "__main__":
    data = load()
    print(f"{len(data)} coins, 15-minute bars.\n")
    P = {}
    for s, d in data.items():
        D, ema, lo, hi, a = RD.detectors(d)
        P[s] = (d, ema, lo, hi, a, gates(D["contain"]))
    print(f"  {'variant':<40}{'flips/wk':>9}{'episodes':>10}{'per ep':>10}{'t':>7}"
          f"{'total':>9}{'worst':>8}{'CAGR 1x':>9}{'maxDD':>8}{'Sharpe':>8}")
    for name in ["registered", "deadband 55/45", "dwell 2h before on",
                 "persist 2h before off", "hold-through (off blocks entries only)"]:
        rows = []; flips = []
        fn = CP.episodes_hold if name.startswith("hold") else CP.episodes
        for s, (d, ema, lo, hi, a, G) in P.items():
            al = G[name]
            x = pd.Series(al).fillna(False).astype(bool)
            flips.append((x != x.shift()).sum()/(len(x)/(96*7)))
            for side in ("L", "S"):
                rows += fn(d, al, ema, lo, hi, a, None, "optimistic", side, s)
        S = pd.DataFrame(rows, columns=["sym","entry","exit","ret","side"])
        S = S[np.isfinite(S.ret)]
        t = S.ret.mean()/(S.ret.std(ddof=1)/np.sqrt(len(S)))
        r, _, _ = CP.simulate(S, 40, 1)
        print(f"  {name:<40}{np.median(flips):>9.1f}{len(S):>10,}{S.ret.mean()*100:>+9.3f}%"
              f"{t:>+7.1f}{S.ret.sum()*100:>+8.0f}%{S.ret.min()*100:>+7.1f}%"
              f"{(r['cagr']*100 if r else float('nan')):>8.1f}%{(r['dd']*100 if r else float('nan')):>7.1f}%"
              f"{(r['sharpe'] if r else float('nan')):>8.2f}", flush=True)
