"""Opening-range breakout and gap fade on IG index markets (task 12, 24 Oct 2026). 5-min Dukascopy bars Apr 15 - Oct 22 2026.
ORB: opening range = first N minutes after the cash open; enter on the first 5-min close beyond it (within 2 h); stop = other side of the
range; exit at target (1x range) or the cash close. Gap fade: open vs prior cash close; if |gap| >= g, fade it; stop 1x gap beyond the open;
exit at fill or after 2 h. Costs: IG spread (half each way) + half a spread slippage on market exits. Control: random entries, same hold."""
import numpy as np, pandas as pd
from scipy.stats import norm
INSTR = {"WALLST": ("data_ig_cache/USA30IDXUSD_5m.csv", 2.0, (13, 30), (20, 0)),
         "NQ":     ("data_nq_cache/nq_5m.csv", 1.0, (13, 30), (20, 0)),
         "DAX":    ("data_ig_cache/DEUIDXEUR_5m.csv", 1.2, (7, 0), (15, 30))}
rng = np.random.default_rng(7)

def load(f):
    d = pd.read_csv(f, index_col=0, parse_dates=True); d.index = pd.to_datetime(d.index, utc=True); return d[d.index >= "2026-04-15"]

def orb(d, spread, op, cl, n_min, target_mult):
    out = []; ctrl = []
    for day, g in d.groupby(d.index.date):
        t0 = pd.Timestamp(day, tz="UTC") + pd.Timedelta(hours=op[0], minutes=op[1]); tc = pd.Timestamp(day, tz="UTC") + pd.Timedelta(hours=cl[0], minutes=cl[1])
        s = g[(g.index >= t0) & (g.index < tc)]
        if len(s) < 60: continue
        orng = s[s.index < t0 + pd.Timedelta(minutes=n_min)]; rest = s[s.index >= t0 + pd.Timedelta(minutes=n_min)]
        hi, lo = orng.high.max(), orng.low.min(); R = hi - lo
        if R <= 0: continue
        win = rest[rest.index < t0 + pd.Timedelta(minutes=n_min + 120)]
        brk = win[(win.close > hi) | (win.close < lo)]
        if len(brk) == 0: continue
        i = rest.index.get_loc(brk.index[0]); side = 1 if brk.close.iloc[0] > hi else -1
        e = rest.close.iloc[i] + side*spread/2; stop = lo if side == 1 else hi; tgt = e + side*target_mult*R
        pnl = None
        for j in range(i+1, len(rest)):
            b = rest.iloc[j]
            if (side == 1 and b.low <= stop) or (side == -1 and b.high >= stop): pnl = side*(stop - e) - spread; break
            if target_mult and ((side == 1 and b.high >= tgt) or (side == -1 and b.low <= tgt)): pnl = side*(tgt - e) - spread/2; break
        if pnl is None: pnl = side*(rest.close.iloc[-1] - e) - spread
        out.append(pnl/R)   # in units of the opening range
        # control: random entry in the same window, random side, same stop distance (R) and exit rule
        k = rng.integers(i, max(i+1, len(rest)-12)); cs = rng.choice([1, -1]); ce = rest.close.iloc[k] + cs*spread/2; cstop = ce - cs*R; ctgt = ce + cs*target_mult*R; cp = None
        for j in range(k+1, len(rest)):
            b = rest.iloc[j]
            if (cs == 1 and b.low <= cstop) or (cs == -1 and b.high >= cstop): cp = cs*(cstop - ce) - spread; break
            if target_mult and ((cs == 1 and b.high >= ctgt) or (cs == -1 and b.low <= ctgt)): cp = cs*(ctgt - ce) - spread/2; break
        if cp is None: cp = cs*(rest.close.iloc[-1] - ce) - spread
        ctrl.append(cp/R)
    return np.array(out), np.array(ctrl)

def gapfade(d, spread, op, cl, gmin):
    out = []; prev_close = None
    for day, g in d.groupby(d.index.date):
        t0 = pd.Timestamp(day, tz="UTC") + pd.Timedelta(hours=op[0], minutes=op[1]); tc = pd.Timestamp(day, tz="UTC") + pd.Timedelta(hours=cl[0], minutes=cl[1])
        s = g[(g.index >= t0) & (g.index < tc)]
        if len(s) < 60: prev_close = None; continue
        o = s.open.iloc[0]
        if prev_close is not None:
            gap = (o - prev_close)/prev_close
            if abs(gap) >= gmin:
                side = -1 if gap > 0 else 1; e = o + side*spread/2; G = abs(o - prev_close); stop = e - side*G; tgt = prev_close
                pnl = None; win = s[s.index < t0 + pd.Timedelta(hours=2)]
                for j in range(1, len(win)):
                    b = win.iloc[j]
                    if (side == 1 and b.low <= stop) or (side == -1 and b.high >= stop): pnl = side*(stop - e) - spread; break
                    if (side == 1 and b.high >= tgt) or (side == -1 and b.low <= tgt): pnl = side*(tgt - e) - spread/2; break
                if pnl is None: pnl = side*(win.close.iloc[-1] - e) - spread
                out.append(pnl/G)
        prev_close = s.close.iloc[-1]
    return np.array(out)

def rep(name, x, c=None):
    if len(x) < 5: print(f"  {name}: n {len(x)} — too few"); return
    h = len(x)//2; t = x.mean()/x.std()*np.sqrt(len(x))
    line = f"  {name:34s} n {len(x):3d}  mean {x.mean():+.3f}R  t {t:+.1f}  win {100*(x>0).mean():.0f}%  H1 {x[:h].mean():+.3f} H2 {x[h:].mean():+.3f}"
    if c is not None and len(c): line += f"  | control {c.mean():+.3f}R  edge {x.mean()-c.mean():+.3f}"
    print(line)

if __name__ == "__main__":
    cuts = 0
    for name, (f, sp, op, cl) in INSTR.items():
        d = load(f); print(f"\n== {name} ({len(d)} bars, spread {sp})")
        for n_min in (15, 30):
            for tm in (0, 1.0):
                x, c = orb(d, sp, op, cl, n_min, tm); rep(f"ORB {n_min}m {'to close' if not tm else 'target 1R'}", x, c); cuts += 1
        for gmin in (0.002, 0.004):
            rep(f"gap fade |gap|>={gmin*100:.1f}%", gapfade(d, sp, op, cl, gmin)); cuts += 1
    print(f"\ncuts {cuts}: deflated bar t > {norm.ppf(1-0.05/cuts):.2f}   (R = opening range for ORB, gap size for the fade)")
