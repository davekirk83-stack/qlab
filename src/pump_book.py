"""
PUMP IGNITION as a BOOK — the robust row from doc 89 (hourly +5%/4 bars with volume, scale-out
half at +1 ATR -> breakeven, trail 1 ATR, cap) and its 15-minute cousin (+5%/16 bars), run
through the range book's own portfolio simulator ($2,000, 20 slots, 3x, as paperbook2) so it is
judged on the equity curve (rule 155), not the per-episode mean. Also the ignition trade WITHOUT
a pullback on the 15-minute 5-year panel, since v2 showed the continuation is in the first bars.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd
import clean_portfolio as CP
import pump_chase as PC

def eps(panel, N, X, k, scale, side=1, volf=True):
    p = PC.PANELS[panel]; rows = []
    for f in sorted(glob.glob(f"{p['d']}/*.csv")):
        d = PC.load(p, f)
        if d is None: continue
        sym = os.path.basename(f)[:-4]
        if side == -1 and (sym.startswith("BTC") or sym.startswith("ETH")): continue
        S = PC.signals(d, N, X, p); sig = S["pump" if volf else "pump (no volume filter)"] if side == 1 else S["dump"]
        O, H, L, C, a = d.open.values, d.high.values, d.low.values, d.close.values, d.atr.values
        idx = np.where(sig.values)[0]; idx = idx[(idx > 100) & (idx < len(C)-p["cap"]-2)]; last = -10**9
        for i in idx:
            if i - last < N: continue
            last = i
            r, n = PC.trail_exit(O, H, L, C, a, i, side, k, p["cap"], p["cost"], scale)
            rows.append((sym, d.index[i+1], d.index[min(i+1+n, len(C)-1)], r))
    return pd.DataFrame(rows, columns=["sym", "entry", "exit", "ret"])

def sim(lbl, S, slots=20, lev=3):
    r, taken, skipped = CP.simulate(S[["sym","entry","exit","ret"]], slots, lev)
    yrs = (S.exit.max() - S.entry.min()).days/365.25
    m = S.set_index("entry").ret.resample("ME").sum(); mon = (m > 0).mean()*100
    if r is None: print(f"  {lbl:<44} BLEW UP (taken {taken})"); return
    print(f"  {lbl:<44}{len(S):>6}{taken:>7}{S.ret.mean()*100:>+8.3f}%{r['cagr']*100:>+8.1f}%{r['dd']*100:>+8.1f}%{r['sharpe']:>7.2f}{r['final']:>10,.0f}{mon:>7.0f}%{len(S)/yrs/365:>7.1f}", flush=True)

if __name__ == "__main__":
    print(f"  {'book ($2,000, 20 slots, 3x)':<44}{'eps':>6}{'taken':>7}{'per ep':>9}{'CAGR':>9}{'maxDD':>9}{'Sharpe':>7}{'final':>10}{'mo>0':>8}{'/day':>7}")
    S = eps("1h", 4, 5.0, 1.0, True); sim("1h +5%/4b vol, scale-out + trail 1 (15 mo)", S)
    S = eps("1h", 4, 5.0, 1.0, False); sim("1h +5%/4b vol, trail 1 only", S)
    S = eps("1h", 4, 5.0, 2.0, True); sim("1h +5%/4b vol, scale-out + trail 2", S)
    S = eps("1h", 4, 5.0, 1.0, True, volf=False); sim("1h +5%/4b NO vol, scale-out + trail 1", S)
    S15 = eps("15m", 16, 5.0, 1.0, True); sim("15m +5%/16b vol, scale-out + trail 1 (5 yrs)", S15)
    for y in sorted(set(S15.entry.dt.year)):
        sim(f"   {y}", S15[S15.entry.dt.year == y])
    S = eps("15m", 16, 5.0, 1.0, False); sim("15m +5%/16b vol, trail 1 only (5 yrs)", S)
    S = eps("15m", 4, 3.0, 1.0, True); sim("15m +3%/4b vol, scale-out + trail 1 (5 yrs)", S)
    S = eps("15m", 16, 5.0, 3.0, True); sim("15m +5%/16b vol, scale-out + trail 3 (5 yrs)", S)

    # ---- bull-regime gate: BTC above its 4h EMA200 (the golden-cross book's gate), applied to the 5-year 15m ignition trade
    q = pd.read_csv("/home/claude/qlab/data_15m/BTCUSD.csv", index_col=0); q.index = pd.to_datetime(q.index, utc=True, format="ISO8601"); q = q[~q.index.duplicated(keep="last")].sort_index()
    c4 = q.close.resample("4h").last().dropna(); gate = (c4 > c4.ewm(span=200, adjust=False).mean()).shift(1)
    S = eps("15m", 16, 5.0, 1.0, False); g = gate.reindex(S.entry, method="ffill").fillna(False).astype(bool).values
    print(f"\n  BTC 4h EMA200 gate on the 15m ignition trade (trail 1): bull bars {gate.mean()*100:.0f}%")
    sim("15m +5%/16b, trail 1, BULL only (5 yrs)", S[g]); sim("15m +5%/16b, trail 1, BEAR only (5 yrs)", S[~g])
    S = eps("15m", 16, 5.0, 1.0, True); g = gate.reindex(S.entry, method="ffill").fillna(False).astype(bool).values
    sim("15m +5%/16b, scale-out+trail 1, BULL only", S[g]); sim("15m +5%/16b, scale-out+trail 1, BEAR only", S[~g])
    Sb = S[g]
    for y in sorted(set(Sb.entry.dt.year)): sim(f"   bull {y}", Sb[Sb.entry.dt.year == y])
