"""
PUMP CHASE v2 — built the way a trader would, not the way a tester would (DK, 19 Oct 14:01:
"if I was doing this, how would I make it work?").

v1 (doc 89) showed continuation is real (race 51-56% vs random 48-50%) but buying the spike bar
at market and trailing off the high loses the median trade. v2 changes the three things a trader
would change:

  1. THE SPIKE PICKS THE COIN, THE PULLBACK IS THE ENTRY. After close up >= X% in N minutes,
     wait for a pullback of at least P% of the spike (measured spike low -> spike high), then
     buy the first bar whose low holds above the prior bar's low (the cascade's own trigger).
     Give up if no pullback within W bars or if the pullback retraces > 100% (the spike failed).
  2. STRUCTURE EXITS. Stop under the pullback low (minus 0.1 ATR). TP1 at the spike high: take
     half, stop to breakeven. Runner: target spike high + 1x spike height (the measured move),
     or the DELTA EXIT: leave when the 5-minute true taker delta turns against (z < -1), or the cap.
  3. REGIME. Reported for every entry: all hours / Asia 00-08 / coin containment switch OFF
     (the range book's own regime detector, so the two books partition the day).

Panel: 18 perps, 1-minute bars with true taker delta (data_1m_delta), 2025-09..2026-09.
Costs: entry is a limit at the trigger bar's close -> maker 2bp; exits taker 4.5bp (stop) or
maker 2bp (targets). Matched random control: random pullback-shaped entry (random bar whose low
held above the prior bar's low), same exits, 3 per trade. Barrier race +-1 spike-height.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob, json
import numpy as np, pandas as pd
RNG = np.random.default_rng(8)
D = "/home/claude/qlab/data_1m_delta"; D15 = "/home/claude/qlab/data_15m"
MAKER, TAKER = 2e-4, 4.5e-4
MED = json.load(open("/home/claude/qlab/runs/contain_median.json")) if os.path.exists("/home/claude/qlab/runs/contain_median.json") else {}


def load(c):
    d = pd.read_csv(f"{D}/{c}.csv"); d.index = pd.to_datetime(d.t, unit="ms", utc=True)
    d = d[["open", "high", "low", "close", "vol", "delta"]]; d = d[~d.index.duplicated()].asfreq("1min")
    d[["open","high","low","close"]] = d[["open","high","low","close"]].ffill(); d[["vol","delta"]] = d[["vol","delta"]].fillna(0)
    tr = np.maximum(d.high - d.low, np.maximum((d.high - d.close.shift()).abs(), (d.low - d.close.shift()).abs()))
    d["atr"] = tr.rolling(60).mean()
    d5 = d.delta.rolling(5).sum(); d["dz"] = (d5 - d5.rolling(1440).mean())/d5.rolling(1440).std()
    d["hour"] = d.index.hour
    # containment switch from the 15m panel (range book v2.2): contain > frozen median
    try:
        import regime_detect as RD
        f15 = f"{D15}/{c[:-4]}USD.csv"
        if os.path.exists(f15):
            q = pd.read_csv(f15, index_col=0); q.index = pd.to_datetime(q.index, utc=True, format="ISO8601"); q = q[~q.index.duplicated(keep="last")].sort_index()
            Dd, *_ = RD.detectors(q); v = pd.Series(Dd["contain"], index=q.index)
            thr = MED.get(f"{c[:-4]}USD", {}).get("median"); allow = v > (thr if thr is not None else v.expanding(500).median())
            d["range_on"] = allow.shift(1).reindex(d.index, method="ffill").fillna(True).values
        else: d["range_on"] = np.nan
    except Exception as e:
        d["range_on"] = np.nan
    return d.dropna(subset=["atr", "dz"])


def episodes(d, N, X, P, W, cap, exit_mode):
    O, H, L, C, A, DZ = d.open.values, d.high.values, d.low.values, d.close.values, d.atr.values, d.dz.values
    n = len(C); mv = np.full(n, np.nan); mv[N:] = C[N:]/C[:-N] - 1
    out = []; last = -10**9
    for i in np.flatnonzero(mv >= X/100):
        if i < last or i + W + cap + 2 >= n: continue
        lo0 = L[i-N:i+1].min(); hi0 = H[i-N:i+1].max(); spike = hi0 - lo0
        if spike <= 0: continue
        # walk forward: track the spike high (may extend), wait for pullback >= P of spike, then first higher-low bar
        hi, pulled, trig = hi0, False, None
        for q in range(i+1, i+1+W):
            hi = max(hi, H[q])
            if L[q] <= hi - P*(hi - lo0): pulled = True
            if L[q] < lo0: break                               # spike failed
            if pulled and L[q] > L[q-1] and C[q] > O[q]: trig = q; break
        if trig is None: last = i + N; continue
        last = trig + cap
        e = C[trig]*(1 + MAKER); pl = L[trig-1] if L[trig-1] < L[trig] else L[trig]
        stop = pl - 0.1*A[trig]; tp1 = hi; tp2 = hi + (hi - lo0)
        if stop >= e or tp1 <= e: continue
        rem, pnl, be = 1.0, 0.0, False
        how = "cap"
        for q in range(trig+1, min(trig+1+cap, n)):
            if L[q] <= stop:
                pnl += rem*((stop*(1-TAKER))/e - 1); rem = 0; how = "be" if be else "stop"; break
            if not be and H[q] >= tp1:
                pnl += 0.5*((tp1*(1-MAKER))/e - 1); rem = 0.5; be = True; stop = e*(1 + 2*TAKER)
            if be:
                if exit_mode == "measured" and H[q] >= tp2: pnl += rem*((tp2*(1-MAKER))/e - 1); rem = 0; how = "tp2"; break
                if exit_mode == "delta" and DZ[q] < -1.0: pnl += rem*((C[q]*(1-TAKER))/e - 1); rem = 0; how = "delta"; break
                if exit_mode == "trail":
                    t = H[trig:q+1].max() - 1.0*A[trig]
                    if t > stop: stop = t
        if rem > 0: q = min(trig+cap, n-1); pnl += rem*((C[q]*(1-TAKER))/e - 1)
        race = np.nan
        for q in range(trig+1, min(trig+1+cap, n)):
            up = H[q] >= e + spike; dn = L[q] <= e - spike
            if up and dn: race = 0.5; break
            if up: race = 1.0; break
            if dn: race = 0.0; break
        out.append((d.index[trig], pnl, q - trig, how, race, d.hour.values[trig], d.range_on.values[trig], spike/A[trig], (hi-lo0)/lo0*100))
    return out


def control(d, k, cap, exit_mode):
    """Random higher-low bars with the same exit geometry scaled by a random spike height."""
    O, H, L, C, A, DZ = d.open.values, d.high.values, d.low.values, d.close.values, d.atr.values, d.dz.values
    n = len(C); out = []
    cand = np.flatnonzero((L[1:] > L[:-1]) & (C[1:] > O[1:])) + 1; cand = cand[(cand > 1500) & (cand < n - cap - 2)]
    for trig in RNG.choice(cand, size=min(k, len(cand)), replace=False):
        spike = A[trig]*RNG.uniform(3, 8)                      # same order as real spikes (reported below)
        e = C[trig]*(1 + MAKER); stop = L[trig-1] - 0.1*A[trig]; tp1 = e + spike*RNG.uniform(0.3, 0.7); tp2 = tp1 + spike
        if stop >= e: continue
        rem, pnl, be = 1.0, 0.0, False
        for q in range(trig+1, min(trig+1+cap, n)):
            if L[q] <= stop: pnl += rem*((stop*(1-TAKER))/e - 1); rem = 0; break
            if not be and H[q] >= tp1: pnl += 0.5*((tp1*(1-MAKER))/e - 1); rem = 0.5; be = True; stop = e*(1 + 2*TAKER)
            if be:
                if exit_mode == "measured" and H[q] >= tp2: pnl += rem*((tp2*(1-MAKER))/e - 1); rem = 0; break
                if exit_mode == "delta" and DZ[q] < -1.0: pnl += rem*((C[q]*(1-TAKER))/e - 1); rem = 0; break
                if exit_mode == "trail":
                    t = H[trig:q+1].max() - 1.0*A[trig]
                    if t > stop: stop = t
        if rem > 0: q = min(trig+cap, n-1); pnl += rem*((C[q]*(1-TAKER))/e - 1)
        out.append(pnl)
    return out


def line(lbl, R, ctrl):
    if len(R) < 60: print(f"  {lbl:<44}{len(R):>6} too few", flush=True); return
    t = R.ret.mean()/(R.ret.std(ddof=1)/np.sqrt(len(R)))
    top = R.ret.sort_values(ascending=False); fat = top.iloc[:max(1, len(R)//20)].sum()/R.ret.sum()*100 if R.ret.sum() > 0 else float("nan")
    m = R.ts.dt.to_period("M"); g = R.groupby(m).ret.sum(); mon = (R.groupby(m).ret.mean() > 0).mean()*100; big = g.max()/R.ret.sum()*100 if R.ret.sum() > 0 else float("nan")
    print(f"  {lbl:<44}{len(R):>6,}{R.ret.mean()*100:>+8.3f}%{t:>+6.1f}{(R.ret>0).mean()*100:>5.0f}%{R.ret.median()*100:>+7.2f}%{R.bars.median():>5.0f}"
          f"{np.mean(ctrl)*100:>+8.3f}%{(R.ret.mean()-np.mean(ctrl))*100:>+7.3f}{(R.groupby('sym').ret.mean()>0).mean()*100:>6.0f}%{R.race.mean()*100:>6.0f}%{mon:>5.0f}%{big:>5.0f}%{fat:>6.0f}%", flush=True)


def hdr(): print(f"  {'variant':<44}{'n':>6}{'per ep':>9}{'t':>6}{'win':>6}{'median':>8}{'hold':>5}{'ctrl':>9}{'edge':>7}{'coins':>7}{'race':>6}{'mo>0':>6}{'bigmo':>6}{'top5%':>6}")


if __name__ == "__main__":
    import sys; sys.path.insert(0, "/home/claude/qlab/src")
    B = {os.path.basename(f)[:-4]: load(os.path.basename(f)[:-4]) for f in sorted(glob.glob(f"{D}/*.csv"))}
    print(f"{len(B)} perps, 1-minute with true taker delta, {min(b.index.min() for b in B.values()).date()}..{max(b.index.max() for b in B.values()).date()}; range switch available for {sum(int(b.range_on.notna().any()) for b in B.values())} coins.\n")
    hdr()
    for (N, X, P, W, cap) in ((5, 2.0, 0.38, 60, 240), (15, 3.0, 0.38, 90, 240), (15, 3.0, 0.5, 90, 240), (60, 5.0, 0.38, 180, 480)):
        for em in ("measured", "delta", "trail"):
            rows, ctrl = [], []
            for sym, d in B.items():
                ep = episodes(d, N, X, P, W, cap, em); rows += [(sym,)+r for r in ep]
                ctrl += control(d, 3*len(ep), cap, em)
            R = pd.DataFrame(rows, columns=["sym","ts","ret","bars","how","race","hour","range_on","spike_atr","spike_pct"])
            tag = f"+{X:.0f}%/{N}m, pullback {P:.2f}, exit={em}"
            line(tag, R, ctrl)
            if em == "measured" and len(R) >= 60:
                print(f"     spikes: median {R.spike_pct.median():.1f}% = {R.spike_atr.median():.1f} ATR; exits {R.how.value_counts().to_dict()}")
                line("   Asia 00-08 UTC", R[R.hour < 8], ctrl)
                line("   US 13-21 UTC", R[(R.hour >= 13) & (R.hour < 21)], ctrl)
                rr = R[R.range_on.notna()]
                line("   range switch OFF (trend state)", rr[rr.range_on == False], ctrl)
                line("   range switch ON", rr[rr.range_on == True], ctrl)
                m = R.ts.dt.to_period("M")
                print("     by month:", " ".join(f"{k}:{v*100:+.2f}" for k, v in R.groupby(m).ret.mean().items()))
            elif em == "delta" and len(R) >= 60:
                print(f"     exits {R.how.value_counts().to_dict()}")
                line("   Asia 00-08 UTC", R[R.hour < 8], ctrl)
                rr = R[R.range_on.notna()]; line("   range switch OFF", rr[rr.range_on == False], ctrl)
