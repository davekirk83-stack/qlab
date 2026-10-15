"""
KELTNER RANGE BOOK, REBUILT FOR FREQUENCY.

DK's mandate: "I'd much rather we earned $10 five to twenty times a day than
trying to get $200 wins a few times a week." ~$2,000 stack, 2-5x leverage.

WHY THE EXISTING BOOK CANNOT SERVE THAT
Doc 66's Keltner book is hourly with a 120-bar hold. That is a five-day swing
trade. Tuning it harder cannot make it fire 50 times a month; the horizon is
the constraint, not the parameters. So this is a rebuild on 15-MINUTE bars with
holds measured in hours, not days.

WHAT CARRIES OVER (all of it earned, none of it assumed)
  doc 66  wide stop. The stop sweep rose monotonically to 6 ATR and was still
          improving. A band touch is a volatility event; a tight stop sits
          inside the noise that produced the signal.
  doc 66  range regime only. Buying the lower band in a downtrend is not
          reversion, it is catching a falling knife - there is nothing to
          revert to because the mid is falling toward price.
  doc 63  tapered exit. Half at the mid, half at the opposing band. The mid is
          the high-probability target and the wrong one to use alone.
  doc 65  laddered entry, weight increasing toward the extreme.
  doc 50  the control must be drawn from the SAME regime.

WHAT IS NEW
  frequency is a reported column, not an afterthought. A cell that prints a
  beautiful edge on 40 trades a year is a failure against this mandate.
  dollar P&L on a $2,000 stack at 3x is printed next to the percentage, because
  "+0.3%/trade" and "$1.80 a trade" are different conversations.

Costs: maker in on every rung, maker out on targets, taker + slippage on stops.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob, sys
import numpy as np, pandas as pd

MAKER, TAKER, SLIP = 2/10000, 5/10000, 10/10000
RNG = np.random.default_rng(20261015)
BAR = "15min"; BARS_PER_DAY = 96
STACK, LEV = 2000.0, 3.0


def atr_np(H, L, C, n=14):
    pc = np.roll(C, 1); pc[0] = C[0]
    tr = np.maximum(H-L, np.maximum(np.abs(H-pc), np.abs(L-pc)))
    return pd.Series(tr).rolling(n).mean().bfill().values


def efficiency(C, w=100):
    net = np.abs(pd.Series(C).diff(w)).values
    gross = pd.Series(np.abs(np.diff(C, prepend=C[0]))).rolling(w).sum().values
    return net / np.where(gross > 0, gross, np.nan)


def load(folder):
    out = {}
    for f in sorted(glob.glob(f"{folder}/*.csv")):
        s = os.path.basename(f)[:-4]
        d = pd.read_csv(f)
        d.index = pd.to_datetime(d.t, unit="ms", utc=True)
        b = d.resample(BAR).agg(open=("open","first"), high=("high","max"),
                                low=("low","min"), close=("close","last"),
                                volume=("volume","sum")).dropna()
        if len(b) > 3000:
            out[s] = b
    return out


def play(C, H, L, i, stop, t1, t2, maxh, rungs):
    """Ladder down from C[i] toward the stop; half out at t1, rest at t2."""
    n = len(C); top = C[i]
    if stop >= top*0.9995: return None
    px = [top] if rungs == 1 else list(np.linspace(top, stop*1.0015, rungs))
    w = np.arange(1, len(px)+1, dtype=float); w /= w.sum()   # heavier at the extreme
    filled = []; half = False; pnl = 0.0
    for q in range(i+1, min(i+1+maxh, n)):
        for k, (p, ww) in enumerate(zip(px, w)):
            if L[q] <= p and k not in [f[0] for f in filled]:
                filled.append((k, p, ww))
        if not filled: continue
        dep = sum(x for _,_,x in filled)
        e = (sum(p*x for _,p,x in filled)/dep)*(1+MAKER)
        if L[q] <= stop:
            rest = 1.0 if not half else 0.5
            return pnl + rest*((stop*(1-SLIP-TAKER))/e - 1)*dep, dep, q-i
        if not half and H[q] >= t1:
            pnl += 0.5*((t1*(1-MAKER))/e - 1)*dep; half = True; continue
        if half and H[q] >= t2:
            return pnl + 0.5*((t2*(1-MAKER))/e - 1)*dep, dep, q-i
    if not filled: return 0.0, 0.0, maxh
    dep = sum(x for _,_,x in filled)
    e = (sum(p*x for _,p,x in filled)/dep)*(1+MAKER)
    q = min(i+maxh, n-1); rest = 1.0 if not half else 0.5
    return pnl + rest*((C[q]*(1-MAKER))/e - 1)*dep, dep, maxh


def run(data, katr, maxh, rungs, eff_cut, taper=True, cool=None):
    cool = cool if cool is not None else maxh
    real=[]; ctrl=[]; dep=[]; hold=[]; span_days=0.0
    for s, d in data.items():
        C,H,L = d.close.values, d.high.values, d.low.values
        n=len(C); a=atr_np(H,L,C)
        ema = pd.Series(C).ewm(span=20, adjust=False).mean().values
        lower = ema - 2*a; upper = ema + 2*a
        eff = efficiency(C)
        rng_ok = eff < eff_cut
        trig = (C <= lower) & (np.roll(C,1) > np.roll(lower,1)) & rng_ok
        span_days += (d.index[-1]-d.index[0]).total_seconds()/86400
        last = -10**9
        elig = np.flatnonzero(rng_ok & np.isfinite(a) & (np.arange(n)>150))
        for i in np.flatnonzero(trig):
            if i < 150 or i > n-maxh-2 or i-last < cool: continue
            last = i
            st = lower[i] - katr*a[i]
            t1 = ema[i]; t2 = upper[i] if taper else ema[i]
            r = play(C,H,L,i,st,t1,t2,maxh,rungs)
            if r is None: continue
            real.append(r[0]); dep.append(r[1]); hold.append(r[2])
            # control: same regime, random time, same geometry
            pool = elig[(elig>150)&(elig<n-maxh-2)]
            if len(pool)==0: continue
            q = int(RNG.choice(pool))
            c = play(C,H,L,q, C[q]-(C[i]-st), C[q]+(t1-C[i]), C[q]+(t2-C[i]),
                     maxh, rungs)
            if c: ctrl.append(c[0])
    return (np.array(real), np.array(ctrl), np.array(dep),
            np.array(hold), span_days/max(len(data),1))


def show(tag, data):
    print(f"\n{'='*104}\n{tag}   {len(data)} symbols, {BAR} bars\n{'='*104}")
    print(f"{'stop':>5}{'hold':>6}{'eff':>6}{'rung':>5}{'n':>6}{'/mo':>7}"
          f"{'net%':>9}{'t':>7}{'ctrl%':>8}{'EDGE':>8}{'win%':>6}"
          f"{'medh':>6}{'$/trd':>7}{'$/mo':>8}")
    cells=[]
    for katr in (3,5,8):
        for maxh in (16,32,64):
            for eff_cut in (0.20,0.30):
                for rungs in (1,4):
                    r,c,dp,hd,days = run(data,katr,maxh,rungs,eff_cut)
                    if len(r)<120 or len(c)<120: continue
                    months = days/30.44
                    per_mo = len(r)/months/len(data)*len(data)   # total book
                    t = r.mean()/(r.std(ddof=1)/np.sqrt(len(r)))
                    edge = r.mean()-c.mean()
                    dollars = r.mean()*STACK*LEV
                    cells.append(dict(katr=katr,maxh=maxh,eff=eff_cut,rungs=rungs,
                        n=len(r),per_mo=per_mo,mean=r.mean(),t=t,edge=edge,
                        win=(r>0).mean(),dollars=dollars,r=r,c=c))
                    print(f"{katr:>5}{maxh:>6}{eff_cut:>6.2f}{rungs:>5}{len(r):>6}"
                          f"{per_mo:>7.0f}{r.mean()*100:>+8.3f}%{t:>+7.2f}"
                          f"{c.mean()*100:>+7.3f}%{edge*100:>+7.3f}%"
                          f"{(r>0).mean()*100:>5.0f}%{np.median(hd):>6.0f}"
                          f"{dollars:>7.2f}{dollars*per_mo:>8.0f}")
    if not cells: print("  no cell met the minimum sample"); return None
    beat = sum(1 for x in cells if x["edge"]>0)
    t_req = float(np.sqrt(2*np.log(max(len(cells),2))))
    print(f"\n  {sum(1 for x in cells if x['mean']>0)}/{len(cells)} cells net positive"
          f" | {beat}/{len(cells)} beat their control"
          f" | corrected t bar for {len(cells)} cells: {t_req:.2f}")
    b = max(cells, key=lambda x: x["mean"])
    print(f"  BEST BY RETURN: stop {b['katr']}A hold {b['maxh']}b eff<{b['eff']} "
          f"rungs {b['rungs']} -> {b['mean']*100:+.3f}%/trade t={b['t']:+.2f} "
          f"{'CLEARS' if b['t']>=t_req else 'BELOW'} the bar")
    f = max([x for x in cells if x["t"]>=t_req] or cells, key=lambda x: x["dollars"]*x["per_mo"])
    print(f"  BEST BY $ / MONTH: stop {f['katr']}A hold {f['maxh']}b eff<{f['eff']} "
          f"rungs {f['rungs']} -> {f['per_mo']:.0f} trades/mo, "
          f"${f['dollars']:.2f}/trade, ${f['dollars']*f['per_mo']:.0f}/mo on "
          f"${STACK:,.0f} at {LEV:.0f}x")
    return cells


if __name__ == "__main__":
    IS = load("/home/claude/qlab/data_1m")
    show("IN SAMPLE (18 symbols)", IS)
