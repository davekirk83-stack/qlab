"""
ROUND NUMBERS — where retail actually puts its orders.

DK, 2026-10-15:
  "Retail traders tend to either set the stop loss at the major break point of
   a move, or relatively arbitrary points below that. Sometimes in BTC they
   would set it at say 82800 or 82850 (a touch below the nearest thousand
   barrier). Inversely they would tend to set TP targets at either around the
   even 83,000 or a bit greedier at 83050, 83100, or 83200. They wouldn't tend
   to take profit at 83500 unless there was a very good reason."

WHY THIS IS THE TEST THE LAST THREE MISSED
magnet.py, sweep.py and liqmap.py all placed barriers at FIXED PERCENTAGE
distances from the current price. If orders cluster at round numbers, a fixed
percentage test is structurally blind to it: the cluster sits at a different
percentage distance on every single bar, so averaging across bars smears it
into nothing. Three nulls in a row may have been a measurement artefact rather
than an absence, and this geometry is the way to find out.

THE PREDICTION, which is falsifiable and asymmetric
DK's description is not "orders cluster at round numbers". It is sharper than
that, and the asymmetry is what makes it testable:

    STOPS      sit a touch BELOW the round number   (82,800 / 82,850)
    TARGETS    sit AT or a touch ABOVE it           (83,000 / 83,050 / 83,200)
    and NOT    at the halfway mark                  (83,500 is avoided)

Orders are where price reverses, because an order getting filled in size IS
the reversal. So:

    swing LOWS  should concentrate JUST BELOW round numbers
    swing HIGHS should concentrate AT or JUST ABOVE them
    NEITHER     should concentrate at the midpoint of the interval

THE NULL
Position within the round-number interval, as a fraction of the interval.
Under the null that round numbers mean nothing, swing extremes are UNIFORM
across that fraction — every part of the interval equally likely. There is no
model to fit, no drift to correct, no distance geometry to argue about. It is
a flat line, and any shape at all is the finding.

THE GRID
"Round" must scale with price: 1,000 is round for BTC at 83,000 and absurd for
DOGE at 0.20. The grid step is snapped to the 1-2-5 sequence nearest 1% of
price, which puts BTC on 1,000s and keeps every symbol on a humanly round
increment of comparable relative size. The grid is recomputed from a trailing
price so it never uses future information.

CONTROL FOR THE OBVIOUS OBJECTION
A swing low is by construction a local minimum, so lows sit low in any local
range. That says nothing about ROUND numbers unless the reference grid matters.
So the whole test is re-run against a DESHIFTED grid -- the same spacing,
offset by half a cell -- which destroys roundness while preserving every other
property. If the shape survives the shift, it is geometry, not psychology.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd

M1 = "/home/claude/qlab/data_1m"
PIV = 30          # bars either side to qualify as a swing extreme
NBIN = 20
RNG = np.random.default_rng(8308)


def grid_step(px):
    """Nearest 1-2-5 increment to 1% of price."""
    tgt = px * 0.01
    e = np.floor(np.log10(tgt))
    m = tgt / 10 ** e
    snap = np.where(m < 1.5, 1.0, np.where(m < 3.5, 2.0, np.where(m < 7.5, 5.0, 10.0)))
    return snap * 10 ** e


def swings(H, L, w=PIV):
    """Indices of confirmed swing highs and lows."""
    sh = pd.Series(H); sl = pd.Series(L)
    hi = sh.rolling(2 * w + 1, center=True).max()
    lo = sl.rolling(2 * w + 1, center=True).min()
    return np.flatnonzero(sh.values == hi.values), np.flatnonzero(sl.values == lo.values)


def frac_in_cell(price, step, offset=0.0):
    """Where in the round-number interval does this price sit? 0 = on the
    round number, 0.5 = halfway to the next one."""
    return ((price / step) + offset) % 1.0


def collect(offset=0.0):
    hi_f, lo_f, syms = [], [], []
    for f in sorted(glob.glob(f"{M1}/*.csv")):
        s = os.path.basename(f)[:-4]
        d = pd.read_csv(f)
        if len(d) < 50000:
            continue
        H, L, C = d.high.values, d.low.values, d.close.values
        # trailing reference price -> the grid cannot use future information
        ref = pd.Series(C).rolling(1440).median().bfill().values
        step = grid_step(ref)
        ih, il = swings(H, L)
        ih = ih[ih > 1440]; il = il[il > 1440]
        if len(ih) < 50 or len(il) < 50:
            continue
        hi_f.append(frac_in_cell(H[ih], step[ih], offset))
        lo_f.append(frac_in_cell(L[il], step[il], offset))
        syms.append(s)
    return np.concatenate(hi_f), np.concatenate(lo_f), syms


def report(hf, lf, label):
    print(f"\n  {label}   swing highs n={len(hf):,}   swing lows n={len(lf):,}")
    edges = np.linspace(0, 1, NBIN + 1)
    hh, _ = np.histogram(hf, edges); ll, _ = np.histogram(lf, edges)
    hp = hh / hh.sum() * 100; lp = ll / ll.sum() * 100
    exp = 100 / NBIN
    print(f"    {'position in interval':<24}{'highs':>9}{'lows':>9}"
          f"{'  (uniform = %.2f%%)' % exp}")
    for i in range(NBIN):
        a, b = edges[i], edges[i + 1]
        tag = ""
        if i == 0: tag = "  <- ON the round number"
        if i == NBIN - 1: tag = "  <- just BELOW the next one"
        if abs(a - 0.5) < 1e-9: tag = "  <- the halfway mark"
        bar_h = "#" * int(round((hp[i] - exp) * 6)) if hp[i] > exp else ""
        bar_l = "#" * int(round((lp[i] - exp) * 6)) if lp[i] > exp else ""
        print(f"    {a:>5.2f}-{b:<18.2f}{hp[i]:>8.2f}%{lp[i]:>8.2f}%"
              f"  {bar_h:<10}{bar_l:<10}{tag}")
    # chi-square against uniform
    from scipy import stats
    ch = stats.chisquare(hh)[1]; cl = stats.chisquare(ll)[1]
    print(f"    chi-square vs uniform:  highs p={ch:.2e}   lows p={cl:.2e}")
    return hp, lp


if __name__ == "__main__":
    print("ROUND NUMBERS — are swing extremes uniform within the interval?")
    print("Null is a flat line. Any shape is the finding.")
    hf, lf, syms = collect(0.0)
    print(f"\n  {len(syms)} symbols, 1-minute bars, {PIV}-bar confirmed swings")
    hp, lp = report(hf, lf, "TRUE ROUND-NUMBER GRID")

    hf2, lf2, _ = collect(0.5)
    hp2, lp2 = report(hf2, lf2, "CONTROL — grid shifted half a cell")

    print("\n" + "=" * 86)
    print("  THE ASYMMETRY DK PREDICTED")
    print("=" * 86)
    # just below = top 10% of the interval; at/just above = bottom 15%
    jb = lambda v: float((v >= 0.90).mean() * 100)
    ja = lambda v: float((v <= 0.15).mean() * 100)
    mid = lambda v: float(((v > 0.40) & (v < 0.60)).mean() * 100)
    print(f"  {'':34}{'true grid':>12}{'shifted':>12}{'uniform':>10}")
    print(f"  {'swing LOWS just below a round #':<34}{jb(lf):>11.2f}%"
          f"{jb(lf2):>11.2f}%{10.0:>9.1f}%")
    print(f"  {'swing HIGHS at/just above':<34}{ja(hf):>11.2f}%"
          f"{ja(hf2):>11.2f}%{15.0:>9.1f}%")
    print(f"  {'swing HIGHS at the midpoint':<34}{mid(hf):>11.2f}%"
          f"{mid(hf2):>11.2f}%{20.0:>9.1f}%")


# ----------------------------------------------- rn2
def rn2():
    from scipy import stats
    
    # ---- 1. proper control: an offset that does NOT map the quarter-grid onto itself
    print("CONTROL, DONE PROPERLY")
    print("A half-cell shift maps {0,.25,.5,.75} onto itself, so it destroyed nothing.")
    print("0.137 of a cell does destroy it while preserving everything else.\n")
    hf,lf,syms=R.collect(0.0)
    hf2,lf2,_=R.collect(0.137)
    def peaks(v):
        e=np.linspace(0,1,21); h,_=np.histogram(v,e); p=h/h.sum()*100
        q=[p[0],p[5],p[10],p[15]]            # the quarter bins
        o=[p[i] for i in range(20) if i not in (0,5,10,15)]
        return np.mean(q),np.mean(o)
    for lab,(a,b) in (("TRUE grid",(hf,lf)),("SHIFTED 0.137",(hf2,lf2))):
        qh,oh=peaks(a); ql,ol=peaks(b)
        print(f"  {lab:<16} highs: quarter-bins {qh:5.2f}% vs other {oh:5.2f}%"
              f"  ratio {qh/oh:4.2f}x   |  lows: {ql:5.2f}% vs {ol:5.2f}%  ratio {ql/ol:4.2f}x")
    
    # ---- 2. fine resolution on BTC: where exactly, in thousands?
    print("\n\nBTC ONLY — swing extremes by position in the 1,000 interval (50-unit bins)")
    d=pd.read_csv("/home/claude/qlab/data_1m/BTCUSDT.csv")
    H,L,C=d.high.values,d.low.values,d.close.values
    ih,il=R.swings(H,L)
    step=1000.0
    fh=(H[ih]%step); fl=(L[il]%step)
    e=np.arange(0,1050,50); 
    hh,_=np.histogram(fh,e); ll,_=np.histogram(fl,e)
    hp=hh/hh.sum()*100; lp=ll/ll.sum()*100; exp=100/20
    print(f"  {'level':<12}{'highs':>8}{'lows':>8}   (uniform {exp:.1f}%)")
    for i in range(20):
        tag=""
        if e[i]==0: tag="  <- the round thousand"
        if e[i]==800: tag="  <- DK's 800 (stops)"
        if e[i]==250: tag="  <- DK's 250 (overshoot)"
        if e[i]==500: tag="  <- the half"
        b1="#"*int(max(0,round((hp[i]-exp)*8))); b2="#"*int(max(0,round((lp[i]-exp)*8)))
        print(f"  +{int(e[i]):<11}{hp[i]:>7.2f}%{lp[i]:>7.2f}%  {b1:<8}{b2:<8}{tag}")
    
    # ---- 3. the sequence: what happens on crossing a new thousand upward?
    print("\n\nTHE THOUSAND-CROSSING SEQUENCE (BTC, 1-min)")
    print("DK: 'hits first the reject to the 800, climb up and overshoot to about")
    print("250, then either accept or reject.'\n")
    n=len(C)
    k=np.floor(C/step)
    cross=np.flatnonzero((k[1:]>k[:-1]))+1          # first bar above a new thousand
    cross=cross[(cross>60)&(cross<n-720)]
    lvl=np.floor(C[cross]/step)*step
    res=[]
    for idx,L0 in zip(cross,lvl):
        w=slice(idx,min(idx+720,n))                  # 12 hours
        hi=H[w]; lo=L[w]
        res.append(dict(maxup=(hi.max()-L0), maxdn=(L0-lo.min()),
                        # did it dip back below before extending +250?
                        dip=float(L0-lo[:60].min())))
    T=pd.DataFrame(res)
    print(f"  n = {len(T)} upward thousand-crossings")
    print(f"  within the first hour, median dip back below the level: "
          f"{T.dip.median():+.0f}   (DK predicts ~ -200)")
    print(f"  share that dipped at least 150 below within the hour: "
          f"{(T.dip>=150).mean()*100:.1f}%")
    print(f"  share that dipped at least 200 below:                  "
          f"{(T.dip>=200).mean()*100:.1f}%")
    print(f"  median maximum extension above the level (12h): {T.maxup.median():+.0f}"
          f"   (DK predicts ~ +250)")
    for t in (100,250,500):
        print(f"    reached +{t:<4} {(T.maxup>=t).mean()*100:5.1f}%")


# ----------------------------------------------- rn3
def rn3():
    """Is the dip-back after a round-number crossing a STOP HUNT, or just volatility?
    Control: identical measurement at FAKE levels that are not round."""
    import warnings; warnings.filterwarnings("ignore")
    import numpy as np, pandas as pd, sys
    sys.path.insert(0,"/home/claude/qlab/src")
    
    d=pd.read_csv("/home/claude/qlab/data_1m/BTCUSDT.csv")
    H,L,C=d.high.values,d.low.values,d.close.values; n=len(C)
    STEP=1000.0
    
    def crossings(offset):
        """Upward crossings of a grid of spacing STEP, shifted by `offset`."""
        k=np.floor((C-offset)/STEP)
        idx=np.flatnonzero(k[1:]>k[:-1])+1
        idx=idx[(idx>60)&(idx<n-720)]
        lvl=np.floor((C[idx]-offset)/STEP)*STEP+offset
        return idx,lvl
    
    def study(idx,lvl,horizon=60):
        """After crossing up through `lvl`: how far back below, and how far above
        BEFORE the first meaningful retrace."""
        dip=[]; over=[]
        for i,L0 in zip(idx,lvl):
            w=slice(i,min(i+horizon,n))
            lo=L[w]; hi=H[w]
            dip.append(L0-lo.min())
            # initial overshoot: running max until price gives back 100
            run=0.0; best=0.0
            for j in range(i,min(i+horizon,n)):
                best=max(best,H[j]-L0)
                if best-(H[j]-L0)>100: break
            over.append(best)
        return np.array(dip),np.array(over)
    
    print("STOP HUNT OR JUST VOLATILITY? — BTC 1-min, 1,000-point grid\n")
    print(f"  {'grid':<26}{'n':>7}{'median dip below':>19}{'dip>=200':>11}"
          f"{'median overshoot':>19}")
    rows={}
    for lab,off in (("TRUE thousands",0.0),("fake: x500 (half)",500.0),
                    ("fake: x137",137.0),("fake: x380",380.0),("fake: x620",620.0)):
        idx,lvl=crossings(off)
        dip,over=study(idx,lvl)
        rows[lab]=(dip,over)
        print(f"  {lab:<26}{len(idx):>7}{np.median(dip):>18.0f}"
              f"{(dip>=200).mean()*100:>10.1f}%{np.median(over):>18.0f}")
    
    t=rows["TRUE thousands"][0]
    fakes=np.concatenate([rows[k][0] for k in rows if k!="TRUE thousands"])
    from scipy import stats
    u=stats.mannwhitneyu(t,fakes,alternative="greater")
    print(f"\n  true vs all fakes, dip magnitude: median {np.median(t):.0f} vs "
          f"{np.median(fakes):.0f}   Mann-Whitney p={u.pvalue:.3f}")
    
    print("\n\nTHE TRADE IF IT IS REAL — sweep below, then reclaim")
    print("After crossing up through a level, price dips back below it, then")
    print("reclaims. Does the reclaim pay, and does it pay more at TRUE levels?\n")
    def sweep_trade(idx,lvl,look=60,hold=240,stop_pts=250):
        out=[]
        for i,L0 in zip(idx,lvl):
            # find a dip at least 100 below the level within `look`
            w=range(i,min(i+look,n))
            swept=None
            for j in w:
                if L[j]<=L0-100: swept=j; break
            if swept is None: continue
            # reclaim: close back above the level
            ent=None
            for j in range(swept+1,min(swept+look,n)):
                if C[j]>L0: ent=j; break
            if ent is None or ent+hold>=n: continue
            e=C[ent]; st=e-stop_pts
            r=None
            for j in range(ent+1,ent+hold+1):
                if L[j]<=st: r=-1.0; break
            if r is None: r=(C[ent+hold]-e)/stop_pts
            out.append(r)
        return np.array(out)
    print(f"  {'grid':<26}{'n':>7}{'mean R':>10}{'win':>9}{'t':>8}")
    for lab,off in (("TRUE thousands",0.0),("fake: x500 (half)",500.0),
                    ("fake: x137",137.0),("fake: x380",380.0),("fake: x620",620.0)):
        idx,lvl=crossings(off)
        r=sweep_trade(idx,lvl)
        if len(r)<50: continue
        se=r.std(ddof=1)/np.sqrt(len(r))
        print(f"  {lab:<26}{len(r):>7}{r.mean():>+10.3f}{(r>0).mean()*100:>8.1f}%"
              f"{r.mean()/se:>+8.2f}")


# ----------------------------------------------- rn4
def rn4():
    """Reclaims of round numbers lose more than reclaims of fake levels.
    So test the inverse, with costs, and check it is not a stop-distance artefact."""
    import warnings; warnings.filterwarnings("ignore")
    import numpy as np, pandas as pd
    d=pd.read_csv("/home/claude/qlab/data_1m/BTCUSDT.csv")
    d["dt"]=pd.to_datetime(d.t,unit="ms")
    H,L,C=d.high.values,d.low.values,d.close.values; n=len(C); TS=d.dt.values
    STEP=1000.0
    COST=7/10000     # taker in, taker out, on BTC
    
    def crossings(off):
        k=np.floor((C-off)/STEP); idx=np.flatnonzero(k[1:]>k[:-1])+1
        idx=idx[(idx>60)&(idx<n-1000)]
        return idx, np.floor((C[idx]-off)/STEP)*STEP+off
    
    def trade(idx,lvl,short,stop_pts,hold):
        out=[]
        for i,L0 in zip(idx,lvl):
            sw=None
            for j in range(i,min(i+60,n)):
                if L[j]<=L0-100: sw=j; break
            if sw is None: continue
            ent=None
            for j in range(sw+1,min(sw+60,n)):
                if C[j]>L0: ent=j; break
            if ent is None or ent+hold>=n: continue
            e=C[ent]
            st=e+stop_pts if short else e-stop_pts
            r=None
            for j in range(ent+1,ent+hold+1):
                if (H[j]>=st) if short else (L[j]<=st): r=-1.0; break
            if r is None:
                dd=(e-C[ent+hold]) if short else (C[ent+hold]-e)
                r=dd/stop_pts
            out.append(r - COST*e/stop_pts)      # costs in R
        return np.array(out)
    
    print("FADING THE ROUND-NUMBER RECLAIM — short it instead, costs netted\n")
    print(f"  {'stop':>6}{'hold':>7}{'grid':<22}{'n':>7}{'mean R':>10}{'win':>8}{'t':>8}")
    for stop_pts,hold in ((250,240),(400,240),(250,60),(600,480)):
        for lab,off in (("TRUE thousands",0.0),("fakes (pooled)",None)):
            if off is None:
                r=np.concatenate([trade(*crossings(o),True,stop_pts,hold)
                                  for o in (137.0,380.0,620.0,500.0)])
            else:
                r=trade(*crossings(off),True,stop_pts,hold)
            if len(r)<50: continue
            se=r.std(ddof=1)/np.sqrt(len(r))
            print(f"  {stop_pts:>6}{hold:>7}  {lab:<20}{len(r):>7}{r.mean():>+10.3f}"
                  f"{(r>0).mean()*100:>7.1f}%{r.mean()/se:>+8.2f}")
        print()
    
    # split by year -- is it a regime?
    print("TRUE thousands, short, stop 250 / hold 240, by year:")
    idx,lvl=crossings(0.0)
    keep=[]
    for i,L0 in zip(idx,lvl):
        sw=None
        for j in range(i,min(i+60,n)):
            if L[j]<=L0-100: sw=j; break
        if sw is None: continue
        ent=None
        for j in range(sw+1,min(sw+60,n)):
            if C[j]>L0: ent=j; break
        if ent is None or ent+240>=n: continue
        e=C[ent]; st=e+250; r=None
        for j in range(ent+1,ent+241):
            if H[j]>=st: r=-1.0; break
        if r is None: r=(e-C[ent+240])/250
        keep.append((TS[ent], r-COST*e/250))
    K=pd.DataFrame(keep,columns=["ts","R"]); K["yr"]=pd.to_datetime(K.ts).dt.year
    for y,g in K.groupby("yr"):
        se=g.R.std(ddof=1)/np.sqrt(len(g))
        print(f"    {y}  n={len(g):5d}  {g.R.mean():+.3f}R  t={g.R.mean()/se:+.2f}")


# ----------------------------------------------- rn5_quarter_points
def rn5_quarter_points():
    RNG=np.random.default_rng(500)
    
    MAJ={"BTCUSDT":1000.0,"ETHUSDT":100.0,"SOLUSDT":10.0,"BNBUSDT":100.0,
         "LTCUSDT":10.0,"BCHUSDT":100.0}
    WIN=0.05     # +/-5% of the cell counts as "at" that point
    
    def analyse(sym,step):
        d=pd.read_csv(f"/home/claude/qlab/data_1m/{sym}.csv")
        H,L=d.high.values,d.low.values
        ih,il=R.swings(H,L)
        fh=(H[ih]%step)/step; fl=(L[il]%step)/step
        return fh,fl
    
    def at(v,c):
        dist=np.minimum(np.abs(v-c),1-np.abs(v-c))
        return dist<=WIN
    
    def boot_share(v,c,draws=1500):
        m=at(v,c); s=[]
        for _ in range(draws):
            k=RNG.integers(0,len(v),len(v)); s.append(m[k].mean()*100)
        return np.mean(s),np.percentile(s,2.5),np.percentile(s,97.5)
    
    print("IS THE HALF-WAY POINT THE LEAST USED?")
    print(f"Each quarter point +/-{WIN*100:.0f}% of the cell; uniform share = {WIN*2*100:.0f}%\n")
    pool_h=[];pool_l=[]
    for sym,step in MAJ.items():
        try: fh,fl=analyse(sym,step)
        except Exception: continue
        pool_h.append(fh); pool_l.append(fl)
        print(f"  {sym}  (grid {step:g})   swing HIGHS n={len(fh):,}")
        line=[]
        for c,lab in ((0.0,"x000"),(0.25,"x250"),(0.5,"x500"),(0.75,"x750")):
            m,lo,hi=boot_share(fh,c)
            line.append((lab,m,lo,hi))
        best=min(line,key=lambda t:t[1])
        for lab,m,lo,hi in line:
            tag="  <- LEAST USED" if lab==best[0] else ""
            print(f"      {lab}  {m:5.2f}%  [{lo:5.2f},{hi:5.2f}]{tag}")
    PH=np.concatenate(pool_h); PL=np.concatenate(pool_l)
    print(f"\n  POOLED MAJORS   highs n={len(PH):,}   lows n={len(PL):,}")
    for nm,V in (("swing HIGHS (where longs take profit)",PH),
                 ("swing LOWS  (where stops sit)",PL)):
        print(f"    {nm}")
        res=[]
        for c,lab in ((0.0,"x000"),(0.25,"x250"),(0.5,"x500"),(0.75,"x750")):
            m,lo,hi=boot_share(V,c); res.append((lab,m,lo,hi))
        best=min(res,key=lambda t:t[1])
        for lab,m,lo,hi in res:
            tag="  <- LEAST USED" if lab==best[0] else ""
            print(f"      {lab}  {m:5.2f}%  [{lo:5.2f},{hi:5.2f}]{tag}")
        a=dict((l,m) for l,m,_,_ in res)
        print(f"      x000 vs x500: {a['x000']-a['x500']:+.2f}pp")


# ----------------------------------------------- rn6_per_symbol
def rn6_per_symbol():
    def conc(v):
        e=np.linspace(0,1,21); h,_=np.histogram(v,e); p=h/h.sum()*100
        q=np.mean([p[0],p[5],p[10],p[15]]); o=np.mean([p[i] for i in range(20)
                                                       if i not in (0,5,10,15)])
        return q/o
    
    print("PER-SYMBOL: concentration at quarter points, true grid vs shifted control\n")
    print(f"  {'symbol':<12}{'median px':>11}{'grid':>11}{'true':>8}{'ctrl':>8}{'excess':>9}")
    rows=[]
    for f in sorted(glob.glob("/home/claude/qlab/data_1m/*.csv")):
        s=os.path.basename(f)[:-4]
        d=pd.read_csv(f)
        if len(d)<50000: continue
        H,L,C=d.high.values,d.low.values,d.close.values
        ref=pd.Series(C).rolling(1440).median().bfill().values
        step=R.grid_step(ref)
        ih,il=R.swings(H,L); ih=ih[ih>1440]; il=il[il>1440]
        if len(ih)<50: continue
        v=np.concatenate([R.frac_in_cell(H[ih],step[ih]),R.frac_in_cell(L[il],step[il])])
        v2=np.concatenate([R.frac_in_cell(H[ih],step[ih],0.137),
                           R.frac_in_cell(L[il],step[il],0.137)])
        t,c=conc(v),conc(v2)
        rows.append(dict(sym=s,px=np.median(C),step=np.median(step),true=t,ctrl=c))
        print(f"  {s:<12}{np.median(C):>11.4g}{np.median(step):>11.4g}"
              f"{t:>8.2f}{c:>8.2f}{t-c:>+9.2f}")
    D=pd.DataFrame(rows)
    print(f"\n  median excess across {len(D)} symbols: {(D.true-D.ctrl).median():+.2f}")
    print(f"  symbols with excess > 0.10: {(D.true-D.ctrl>0.10).sum()}/{len(D)}")
    # does the artefact scale with how badly the snap fits?
    D["fit"]=np.abs(np.log10(D.step/(D.px*0.01)))
    print(f"\n  correlation between excess and grid-snap misfit: "
          f"{D[['fit']].assign(e=D.true-D.ctrl).corr().iloc[0,1]:+.2f}")
    print("  (a strong positive correlation would mean the effect IS the artefact)")
    print("\n  BTC specifically — the one grid that is unambiguous:")
    b=D[D.sym=="BTCUSDT"]
    if len(b): print(f"    true {b.true.iloc[0]:.2f}  control {b.ctrl.iloc[0]:.2f}"
                     f"  excess {b.true.iloc[0]-b.ctrl.iloc[0]:+.2f}")
