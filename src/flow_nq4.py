"""
AUCLAIRSDAD v2 — built from HIS blueprint (thread sent by DK, 19 Oct 14:06), not from my guess.

His thesis: "markets store energy in COMPRESSION and release it in EXPANSION". Layers, each a
gate: REGIME (statistical trend on clock buckets: slope t-stat, R², variance ratio, with
hysteresis) -> SETUP score 0-100 (compression: bar-time behaviour, order-flow flattening, range
stability, channel tightness, activity decay) -> TRIGGER score 0-100 (activity surge, one-sided
flow, range expansion, close location) + directional agreement (flow, candle, structure) ->
GOVERNORS (max trades, daily loss cap, cooloff, session, forced flat) -> EXITS (hard stop ->
breakeven ratchet -> trail). Multi-path: clean breakout OR raw-conviction continuation.

Our data: NQ 1-minute from Dukascopy ticks with n_ticks (activity) and tick-rule delta (flow).
Everything on closed bars; HTF stats on completed 15-minute buckets only (his anti-leak rule).
Judged his way too: fills by hour, loss-size distribution, exit-reason mix; and ours: matched
random controls with the identical exit stack, exit-free barrier race, ablations per layer.
"""
import warnings; warnings.filterwarnings("ignore")
import sys, glob
import numpy as np, pandas as pd
RNG = np.random.default_rng(17)
F = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/qlab/data_nq/nq_1m.csv"
STOP, BE_AT, TRAIL, CAP = 50.0, 20.0, 30.0, 180
W = 30            # compression window, minutes
LOOK = 1440       # percentile reference, one day


def pct_rank(x, look=LOOK):
    """Rolling percentile of the last value within the trailing window, 0-100."""
    return x.rolling(look, min_periods=look//4).rank(pct=True)*100


def build(F):
    b = pd.read_csv(F, index_col=0); b.index = pd.to_datetime(b.index, utc=True)
    b = b[b.n_ticks > 0].copy()
    b["rng"] = b.high - b.low
    b["atr"] = b.rng.rolling(60).mean()
    b["hour"] = b.index.hour + b.index.minute/60
    b["gday"] = (b.index - pd.Timedelta(hours=22)).floor("D")
    # ---- SETUP (compression) components, each inverted so 100 = most compressed
    rs = b.rng.rolling(W).std()                                    # range stability
    ch = (b.high.rolling(W).max() - b.low.rolling(W).min())/b.atr  # channel tightness
    act = b.n_ticks.rolling(W).sum()                               # activity (decay)
    flat = b.delta.rolling(W).sum().abs()/b.delta.abs().rolling(W).sum().replace(0, np.nan)   # flow flattening
    quiet = (b.rng < 0.25*b.atr).rolling(W).mean()                  # bar-time behaviour proxy: share of dead minutes
    b["s_rs"] = 100 - pct_rank(rs); b["s_ch"] = 100 - pct_rank(ch); b["s_act"] = 100 - pct_rank(act)
    b["s_flat"] = 100 - pct_rank(flat); b["s_quiet"] = pct_rank(quiet)
    b["setup"] = b[["s_rs", "s_ch", "s_act", "s_flat", "s_quiet"]].mean(axis=1)
    # ---- TRIGGER components at the bar
    b["t_act"] = pct_rank(b.n_ticks, 240)                            # activity surge vs last 4h
    side_share = b.delta.abs()/b.n_ticks                             # one-sided flow
    b["t_flow"] = pct_rank(side_share, 240)
    b["t_rng"] = pct_rank(b.rng, 240)                                # range expansion
    cl = (b.close - b.low)/b.rng.replace(0, np.nan)                  # close location 0..1
    b["cl"] = cl
    b["trig_up"] = b[["t_act", "t_flow", "t_rng"]].mean(axis=1)*0.75 + cl.fillna(0.5)*100*0.25
    b["trig_dn"] = b[["t_act", "t_flow", "t_rng"]].mean(axis=1)*0.75 + (1 - cl.fillna(0.5))*100*0.25
    # structure: close breaks the W-channel (prior bars)
    b["brk_up"] = b.close > b.high.shift(1).rolling(W).max(); b["brk_dn"] = b.close < b.low.shift(1).rolling(W).min()
    b["cand_up"] = b.close > b.open; b["cand_dn"] = b.close < b.open
    b["flow_up"] = b.delta > 0; b["flow_dn"] = b.delta < 0
    # ---- REGIME on completed 15-minute buckets: regression slope t, R², variance ratio over 16 buckets (4h)
    c15 = b.close.resample("15min").last().dropna()
    n = 16; x = np.arange(n); xm = x - x.mean()
    def reg(v):
        y = v - v.mean(); beta = (xm*y).sum()/(xm**2).sum(); res = y - beta*xm
        se = np.sqrt((res**2).sum()/(n-2)/(xm**2).sum()) if (res**2).sum() > 0 else 1e-9
        r2 = 1 - (res**2).sum()/(y**2).sum() if (y**2).sum() > 0 else 0
        return beta/se, r2
    tt = c15.rolling(n).apply(lambda v: reg(v)[0], raw=True); r2 = c15.rolling(n).apply(lambda v: reg(v)[1], raw=True)
    r1 = c15.diff(); r4 = c15.diff(4)
    vr = (r4.rolling(n).var()/(4*r1.rolling(n).var()))
    reg15 = pd.DataFrame({"tt": tt, "r2": r2, "vr": vr}).shift(1)        # completed buckets only
    b = b.join(reg15.reindex(b.index, method="ffill"))
    # hysteresis: enter trend when |t|>2 & r2>0.3, release when |t|<1
    st = np.zeros(len(b)); cur = 0
    T, R2, = b.tt.values, b.r2.values
    for i in range(len(b)):
        t_ = T[i]
        if np.isnan(t_): st[i] = cur; continue
        if cur == 0 and abs(t_) > 2.0 and R2[i] > 0.3: cur = int(np.sign(t_))
        elif cur != 0 and (abs(t_) < 1.0 or np.sign(t_) != cur): cur = 0
        st[i] = cur
    b["regime"] = st
    b["overnight"] = (b.hour >= 22) | (b.hour < 13.5)
    b["cost"] = b.spread/2
    return b.dropna(subset=["setup", "trig_up", "atr", "tt"])


def manage(O, H, L, C, cost, i, s):
    e = O[i+1] + s*cost[i+1]; stop = e - s*STOP; best = e; be = False
    pts = lambda px: s*(px - e) - cost[i+1]
    for j in range(i+1, min(i+CAP+1, len(C))):
        fav = H[j] if s == 1 else L[j]; adv = L[j] if s == 1 else H[j]
        if (s == 1 and adv <= stop) or (s == -1 and adv >= stop): return pts(stop), j-i, "be" if be else "stop"
        best = max(best, fav) if s == 1 else min(best, fav)
        if not be and s*(best - e) >= BE_AT: be = True; stop = e + s*cost[i+1]*2
        if be:
            t = best - s*TRAIL
            if (s == 1 and t > stop) or (s == -1 and t < stop): stop = t
    j = min(i+CAP, len(C)-1); return pts(C[j]), j-i, "cap"


def race(H, L, C, i, s, k=30, horizon=180):
    e = C[i]
    for j in range(i+1, min(i+horizon+1, len(C))):
        up = (H[j] >= e+k) if s == 1 else (L[j] <= e-k); dn = (L[j] <= e-k) if s == 1 else (H[j] >= e+k)
        if up and dn: return 0.5
        if up: return 1.0
        if dn: return 0.0
    return np.nan


def run(b, sig_up, sig_dn, govern=True, max_trades=8, loss_cap=150.0, cooloff=15, nctrl=5):
    O, H, L, C, cost = b.open.values, b.high.values, b.low.values, b.close.values, b.cost.values
    gd = b.gday.values; rows, ctrl = [], []
    su, sd = sig_up.values, sig_dn.values
    last_exit = -10**9; day = None; ntr = 0; dpl = 0.0
    for i in range(1500, len(C)-CAP-2):
        if gd[i] != day: day = gd[i]; ntr = 0; dpl = 0.0
        s = 1 if su[i] else (-1 if sd[i] else 0)
        if s == 0: continue
        if govern and (i < last_exit + cooloff or ntr >= max_trades or dpl <= -loss_cap): continue
        r, k, how = manage(O, H, L, C, cost, i, s); rows.append((s, b.index[i], r, k, how, race(H, L, C, i, s)))
        last_exit = i + k; ntr += 1; dpl += r
        for _ in range(nctrl):
            j = int(RNG.integers(1500, len(C)-CAP-2)); r2, k2, _ = manage(O, H, L, C, cost, j, s); ctrl.append((s, b.index[j], r2, k2, "", race(H, L, C, j, s)))
    cols = ["side", "ts", "pts", "bars", "how", "race"]
    return pd.DataFrame(rows, columns=cols), pd.DataFrame(ctrl, columns=cols)


def line(lbl, R, Cc):
    if len(R) < 30: print(f"  {lbl:<46}{len(R):>5} too few", flush=True); return
    t = R.pts.mean()/(R.pts.std(ddof=1)/np.sqrt(len(R)))
    gw = R.pts[R.pts > 0].sum(); gl = -R.pts[R.pts < 0].sum(); pf = gw/gl if gl > 0 else float("inf")
    days = max((R.ts.max()-R.ts.min()).days, 1)
    print(f"  {lbl:<46}{len(R):>5,}{R.pts.mean():>+8.2f}{t:>+6.1f}{(R.pts>0).mean()*100:>5.0f}%{pf:>6.2f}{R.bars.median():>5.0f}"
          f"{Cc.pts.mean():>+8.2f}{(R.pts.mean()-Cc.pts.mean()):>+7.2f}{R.race.mean()*100:>6.0f}%{Cc.race.mean()*100:>5.0f}%{R.pts.sum()/days*30:>8.0f}{len(R)/days:>6.1f}", flush=True)


def hdr(): print(f"  {'variant':<46}{'n':>5}{'pts/tr':>8}{'t':>6}{'win':>6}{'PF':>6}{'hold':>5}{'ctrl':>8}{'edge':>7}{'race':>6}{'ctrl':>5}{'pts/mo':>8}{'/day':>6}")


if __name__ == "__main__":
    b = build(F)
    on = b.overnight
    print(f"NQ 1-min {b.index.min().date()}..{b.index.max().date()}, {len(b):,} bars. Regime up {((b.regime==1)).mean()*100:.0f}% / down {((b.regime==-1)).mean()*100:.0f}% of bars. Exit stack: stop {STOP:.0f} -> BE at +{BE_AT:.0f} -> trail {TRAIL:.0f}, cap {CAP}m.\n")
    hdr()
    S_TH, T_TH = 70, 70
    agree_up = b.flow_up & b.cand_up; agree_dn = b.flow_dn & b.cand_dn
    V = {
        # the full stack
        "FULL: regime + setup + trigger + agree + brk (ON)": (on & (b.regime == 1) & (b.setup >= S_TH) & (b.trig_up >= T_TH) & agree_up & b.brk_up,
                                                             on & (b.regime == -1) & (b.setup >= S_TH) & (b.trig_dn >= T_TH) & agree_dn & b.brk_dn),
        "FULL without regime (both ways)": (on & (b.setup >= S_TH) & (b.trig_up >= T_TH) & agree_up & b.brk_up,
                                            on & (b.setup >= S_TH) & (b.trig_dn >= T_TH) & agree_dn & b.brk_dn),
        "FULL, any session": ((b.regime == 1) & (b.setup >= S_TH) & (b.trig_up >= T_TH) & agree_up & b.brk_up,
                              (b.regime == -1) & (b.setup >= S_TH) & (b.trig_dn >= T_TH) & agree_dn & b.brk_dn),
        "setup>=60, trig>=60 (looser), regime, ON": (on & (b.regime == 1) & (b.setup >= 60) & (b.trig_up >= 60) & agree_up & b.brk_up,
                                                      on & (b.regime == -1) & (b.setup >= 60) & (b.trig_dn >= 60) & agree_dn & b.brk_dn),
        "setup>=80, trig>=80 (tighter), no regime, ON": (on & (b.setup >= 80) & (b.trig_up >= 80) & agree_up & b.brk_up,
                                                         on & (b.setup >= 80) & (b.trig_dn >= 80) & agree_dn & b.brk_dn),
        # paths
        "PATH breakout only: setup + brk + candle, ON": (on & (b.setup >= S_TH) & b.brk_up & b.cand_up, on & (b.setup >= S_TH) & b.brk_dn & b.cand_dn),
        "PATH continuation: regime + trig + agree, ON": (on & (b.regime == 1) & (b.trig_up >= T_TH) & agree_up, on & (b.regime == -1) & (b.trig_dn >= T_TH) & agree_dn),
        "PATH breakout COUNTER-regime, ON": (on & (b.regime == -1) & (b.setup >= S_TH) & (b.trig_up >= T_TH) & agree_up & b.brk_up,
                                             on & (b.regime == 1) & (b.setup >= S_TH) & (b.trig_dn >= T_TH) & agree_dn & b.brk_dn),
        # ablations
        "trigger + agree only, ON": (on & (b.trig_up >= T_TH) & agree_up, on & (b.trig_dn >= T_TH) & agree_dn),
        "setup only + candle, ON": (on & (b.setup >= S_TH) & b.cand_up, on & (b.setup >= S_TH) & b.cand_dn),
        "regime only + candle, ON": (on & (b.regime == 1) & b.cand_up, on & (b.regime == -1) & b.cand_dn),
        "channel break only, ON": (on & b.brk_up, on & b.brk_dn),
        "FADE the full-stack breakout, ON": (on & (b.setup >= S_TH) & (b.trig_dn >= T_TH) & agree_dn & b.brk_dn,
                                             on & (b.setup >= S_TH) & (b.trig_up >= T_TH) & agree_up & b.brk_up),
    }
    first = None
    for name, (su, sd) in V.items():
        R, Cc = run(b, su, sd); line(name, R, Cc)
        if first is None and len(R) >= 30:
            first = (name, R, Cc)
    # the FULL stack without governors, and his fill interrogation
    su, sd = V["FULL: regime + setup + trigger + agree + brk (ON)"]
    R, Cc = run(b, su, sd, govern=False); line("FULL, governors OFF", R, Cc)
    R, Cc = run(b, su, sd)
    if len(R) >= 30:
        print("\n  FILL INTERROGATION (his step 15), FULL stack:")
        for s, lbl in ((1, "longs"), (-1, "shorts")): line(f"   {lbl}", R[R.side == s], Cc[Cc.side == s])
        R["h"] = R.ts.dt.hour
        print("   win rate by hour:", " ".join(f"{h}:{(R[R.h==h].pts>0).mean()*100:.0f}%({int((R.h==h).sum())})" for h in sorted(R.h.unique())))
        print("   exit mix:", R.how.value_counts().to_dict())
        ls = R.pts[R.pts < 0]; print(f"   loss sizes: median {ls.median():+.1f}, mean {ls.mean():+.1f}, full-stop share {(ls <= -STOP*0.9).mean()*100:.0f}%; win sizes median {R.pts[R.pts>0].median():+.1f} mean {R.pts[R.pts>0].mean():+.1f}")
        R["m"] = R.ts.dt.to_period("M"); print("   by month (pts/trade, n):", " ".join(f"{m}:{R[R.m==m].pts.mean():+.1f}({int((R.m==m).sum())})" for m in sorted(R.m.unique())))
        nt = R.groupby(R.ts.dt.date).pts.sum(); print(f"   nights traded {len(nt)}, mean {nt.mean():+.1f} pts, >0 {(nt>0).mean()*100:.0f}%, best {nt.max():+.0f}, worst {nt.min():+.0f}")


# ---------------- EXIT STACK VARIANTS (his step 9: "my losers rode to the full stop") ----------------
def manage2(O, H, L, C, cost, i, s, stop_pts, be_at, trail, scratch_min=None, scratch_pts=5.0):
    e = O[i+1] + s*cost[i+1]; stop = e - s*stop_pts; best = e; be = False
    pts = lambda px: s*(px - e) - cost[i+1]
    for j in range(i+1, min(i+CAP+1, len(C))):
        fav = H[j] if s == 1 else L[j]; adv = L[j] if s == 1 else H[j]
        if (s == 1 and adv <= stop) or (s == -1 and adv >= stop): return pts(stop), j-i, "be" if be else "stop"
        best = max(best, fav) if s == 1 else min(best, fav)
        if not be and s*(best - e) >= be_at: be = True; stop = e + s*cost[i+1]*2
        if be:
            t = best - s*trail
            if (s == 1 and t > stop) or (s == -1 and t < stop): stop = t
        if scratch_min and not be and j - i >= scratch_min and s*(C[j] - e) < scratch_pts: return pts(C[j]), j-i, "scratch"
    j = min(i+CAP, len(C)-1); return pts(C[j]), j-i, "cap"


def run2(b, su, sd, exitf, nctrl=5, cooloff=15, max_trades=8, loss_cap=150.0):
    O, H, L, C, cost = b.open.values, b.high.values, b.low.values, b.close.values, b.cost.values
    chlo = b.low.shift(1).rolling(W).min().values; chhi = b.high.shift(1).rolling(W).max().values
    gd = b.gday.values; rows, ctrl = [], []; su, sd = su.values, sd.values
    last_exit = -10**9; day = None; ntr = 0; dpl = 0.0
    for i in range(1500, len(C)-CAP-2):
        if gd[i] != day: day = gd[i]; ntr = 0; dpl = 0.0
        s = 1 if su[i] else (-1 if sd[i] else 0)
        if s == 0 or i < last_exit + cooloff or ntr >= max_trades or dpl <= -loss_cap: continue
        struct = (O[i+1] - chlo[i]) if s == 1 else (chhi[i] - O[i+1])
        r, k, how = exitf(O, H, L, C, cost, i, s, struct); rows.append((s, b.index[i], r, k, how, race(H, L, C, i, s)))
        last_exit = i + k; ntr += 1; dpl += r
        for _ in range(nctrl):
            j = int(RNG.integers(1500, len(C)-CAP-2)); sj = (O[j+1] - chlo[j]) if s == 1 else (chhi[j] - O[j+1])
            r2, k2, _ = exitf(O, H, L, C, cost, j, s, sj); ctrl.append((s, b.index[j], r2, k2, "", race(H, L, C, j, s)))
    cols = ["side", "ts", "pts", "bars", "how", "race"]
    return pd.DataFrame(rows, columns=cols), pd.DataFrame(ctrl, columns=cols)


if __name__ == "__main__":
    print("\n  EXIT STACK VARIANTS on the two live rows (loose stack; breakout path):"); hdr()
    rows_ = {"loose stack": V["setup>=60, trig>=60 (looser), regime, ON"], "breakout path": V["PATH breakout only: setup + brk + candle, ON"]}
    EX = {
        "stop 50 / BE 20 / trail 30 (base)": lambda O,H,L,C,c,i,s,st: manage2(O,H,L,C,c,i,s,50,20,30),
        "stop 30 / BE 15 / trail 20": lambda O,H,L,C,c,i,s,st: manage2(O,H,L,C,c,i,s,30,15,20),
        "STRUCTURAL stop (channel +5, cap 50) / BE 15 / trail 25": lambda O,H,L,C,c,i,s,st: manage2(O,H,L,C,c,i,s,min(max(st+5,10),50),15,25),
        "stop 50 / BE 20 / trail 30 + SCRATCH 20m<+5": lambda O,H,L,C,c,i,s,st: manage2(O,H,L,C,c,i,s,50,20,30,20,5),
        "structural / BE 15 / trail 25 + scratch 20m": lambda O,H,L,C,c,i,s,st: manage2(O,H,L,C,c,i,s,min(max(st+5,10),50),15,25,20,5),
        "stop 50 / BE 10 / trail 20": lambda O,H,L,C,c,i,s,st: manage2(O,H,L,C,c,i,s,50,10,20),
    }
    for rn, (su, sd) in rows_.items():
        for en, ef in EX.items():
            R, Cc = run2(b, su, sd, ef); line(f"{rn}: {en}", R, Cc)
            if len(R) >= 30 and "SCRATCH" in en or "structural" in en:
                ls = R.pts[R.pts < 0]; print(f"      exits {R.how.value_counts().to_dict()}; loss median {ls.median():+.1f}, win median {R.pts[R.pts>0].median():+.1f}")


# ---------------- THE /CL ROOM GEOMETRY (DK, 14:10): scale IN at -12/-17 before the hard stop -26, target +32 ALL lots ----------------
def manage_scalein(O, H, L, C, cost, i, s, adds=(0.46, 0.65), stop_f=1.0, tgt_f=1.23, base=50.0):
    """Lots: 1 at entry, +1 at each add level (fraction of base stop). Hard stop and single target for all lots. Returns pts per 1 lot-equivalent of the FIRST lot (so sizes are comparable), plus max lots used."""
    e = O[i+1] + s*cost[i+1]; lvls = [e - s*a*base for a in adds]; stop = e - s*stop_f*base; tgt = e + s*tgt_f*base
    fills = [e]; k = 0
    for j in range(i+1, min(i+CAP+1, len(C))):
        fav = H[j] if s == 1 else L[j]; adv = L[j] if s == 1 else H[j]
        while k < len(lvls) and ((s == 1 and adv <= lvls[k]) or (s == -1 and adv >= lvls[k])): fills.append(lvls[k] + s*cost[j]); k += 1
        if (s == 1 and adv <= stop) or (s == -1 and adv >= stop):
            return sum(s*(stop - f) - cost[j] for f in fills), j-i, "stop", len(fills)
        if (s == 1 and fav >= tgt) or (s == -1 and fav <= tgt):
            return sum(s*(tgt - f) - cost[j] for f in fills), j-i, "tgt", len(fills)
    j = min(i+CAP, len(C)-1); return sum(s*(C[j] - f) - cost[j] for f in fills), j-i, "cap", len(fills)


def run3(b, su, sd, geo, nctrl=5, cooloff=15, max_trades=8):
    O, H, L, C, cost = b.open.values, b.high.values, b.low.values, b.close.values, b.cost.values
    gd = b.gday.values; rows, ctrl = [], []; su, sd = su.values, sd.values
    last_exit = -10**9; day = None; ntr = 0
    for i in range(1500, len(C)-CAP-2):
        if gd[i] != day: day = gd[i]; ntr = 0
        s = 1 if su[i] else (-1 if sd[i] else 0)
        if s == 0 or i < last_exit + cooloff or ntr >= max_trades: continue
        r, k, how, nl = manage_scalein(O, H, L, C, cost, i, s, **geo); rows.append((s, b.index[i], r, k, how, nl))
        last_exit = i + k; ntr += 1
        for _ in range(nctrl):
            j = int(RNG.integers(1500, len(C)-CAP-2)); r2, k2, h2, n2 = manage_scalein(O, H, L, C, cost, j, s, **geo); ctrl.append((s, b.index[j], r2, k2, h2, n2))
    cols = ["side", "ts", "pts", "bars", "how", "lots"]
    return pd.DataFrame(rows, columns=cols), pd.DataFrame(ctrl, columns=cols)


if __name__ == "__main__":
    print("\n  SCALE-IN GEOMETRY (the /CL room: adds before the stop, one target for all lots). pts = sum over lots per trade; 'lots' = mean lots used"); 
    print(f"  {'variant':<52}{'n':>5}{'pts/tr':>8}{'t':>6}{'win':>6}{'PF':>6}{'lots':>5}{'ctrl':>8}{'edge':>7}{'maxloss':>8}{'pts/mo':>8}")
    GEOS = {
        "CL ratio on 50-pt base: adds -23/-33, stop -50, tgt +62": dict(adds=(0.46, 0.65), stop_f=1.0, tgt_f=1.23, base=50.0),
        "CL ratio on 30-pt base: adds -14/-20, stop -30, tgt +37": dict(adds=(0.46, 0.65), stop_f=1.0, tgt_f=1.23, base=30.0),
        "no adds, stop -50, tgt +62 (control geometry)": dict(adds=(), stop_f=1.0, tgt_f=1.23, base=50.0),
        "one add at -25, stop -50, tgt +40": dict(adds=(0.5,), stop_f=1.0, tgt_f=0.8, base=50.0),
        "adds -23/-33, stop -50, tgt +30": dict(adds=(0.46, 0.65), stop_f=1.0, tgt_f=0.6, base=50.0),
    }
    for rn, (su, sd) in rows_.items():
        for gn, geo in GEOS.items():
            R, Cc = run3(b, su, sd, geo)
            if len(R) < 30: print(f"  {rn}: {gn} too few"); continue
            t = R.pts.mean()/(R.pts.std(ddof=1)/np.sqrt(len(R))); gw = R.pts[R.pts > 0].sum(); gl = -R.pts[R.pts < 0].sum()
            days = max((R.ts.max()-R.ts.min()).days, 1)
            print(f"  {rn+': '+gn:<52}{len(R):>5}{R.pts.mean():>+8.2f}{t:>+6.1f}{(R.pts>0).mean()*100:>5.0f}%{gw/gl if gl>0 else 99:>6.2f}{R.lots.mean():>5.1f}{Cc.pts.mean():>+8.2f}{R.pts.mean()-Cc.pts.mean():>+7.2f}{R.pts.min():>+8.0f}{R.pts.sum()/days*30:>8.0f}", flush=True)


# ---------------- HIS TWO NEWEST PATHS: divergence fade (weak-momentum break of a prior high) and mean reversion in no-trend ----------------
if __name__ == "__main__":
    print("\n  DIVERGENCE and MEAN-REVERSION paths (overnight), base exit stack and the CL scale-in:"); hdr()
    weak = (b.t_flow < 50) & (b.t_act < 50)                       # the break happens on LESS flow and LESS activity than the last 4h norm
    div_short = on & b.brk_up & weak; div_long = on & b.brk_dn & weak
    z60 = (b.close - b.close.rolling(60).mean())/b.close.rolling(60).std()
    mr_long = on & (b.regime == 0) & (z60 < -2.0) & (b.s_flat > 70); mr_short = on & (b.regime == 0) & (z60 > 2.0) & (b.s_flat > 70)
    mr_long_any = on & (z60 < -2.0) & (b.s_flat > 70); mr_short_any = on & (z60 > 2.0) & (b.s_flat > 70)
    P = {"DIVERGENCE: weak-flow break of W-high -> short / low -> long": (div_long, div_short),
         "  (control: STRONG-flow break, go with)": (on & b.brk_up & ~weak, on & b.brk_dn & ~weak),
         "MEAN REVERSION: no regime, z60 > 2, flow flat -> fade": (mr_long, mr_short),
         "  mean reversion, any regime": (mr_long_any, mr_short_any)}
    for name, (su, sd) in P.items():
        R, Cc = run(b, su, sd); line(name, R, Cc)
        R, Cc = run3(b, su, sd, GEOS["CL ratio on 50-pt base: adds -23/-33, stop -50, tgt +62"])
        if len(R) >= 30:
            t = R.pts.mean()/(R.pts.std(ddof=1)/np.sqrt(len(R))); gw = R.pts[R.pts > 0].sum(); gl = -R.pts[R.pts < 0].sum()
            print(f"     + CL scale-in: n {len(R)} pts/tr {R.pts.mean():+.2f} t {t:+.1f} win {(R.pts>0).mean()*100:.0f}% PF {gw/gl if gl>0 else 99:.2f} lots {R.lots.mean():.1f} ctrl {Cc.pts.mean():+.2f}")
