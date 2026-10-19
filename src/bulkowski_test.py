"""
BULKOWSKI AGAINST SOMETHING REAL — and every shape cut by our own indicators (DK, 19 Oct 19:06).

Detectors built to his identification guidelines, scored doc 39's way (the pattern's OWN target
before its OWN stop, against a random entry with the SAME reward:risk in the same instrument):
  rectangle bottom     >= 2 touches of each of two horizontal lines (tol), price inside, after a
                       decline; up-breakout = close above the top; target = top + height; stop = below bottom
  descending triangle  flat support (>= 2 touches), descending highs (>= 2); UP-breakout = close above the
                       last high; target = breakout + height at the first high; stop = below support
  triple bottom        three pivot lows within tol, up-breakout above the highest intervening high
  flag, half-mast      Bulkowski's measure: flagpole (trend start -> flag start) ADDED TO THE FLAG LOW,
                       not projected from the breakout (doc 39's flag used the harsher projection)
  + the three kept from doc 39 (double bottom, inverse H&S, ascending triangle) and doc 39's flag
Panels: crypto hourly (33 perps, 15 months), crypto daily (54), ETF daily (60 clean), US stocks daily (69).

Then EVERY resolved pattern is cut by our indicators at the signal bar:
  contain   the range book's containment switch (RD.detectors), ON/OFF
  trend     EMA20 vs EMA50 on the panel's bars (HTF: 4h for hourly, 5-bar for daily), with/against
  btc       BTC above / below its EMA200 (crypto panels only)
  height    pattern height / ATR14, tall (top half) vs short
  volume    volume trend into the pattern: last 10 bars vs prior 10, receding vs rising (his finding)
  throwback price returned to within 0.25 ATR of the breakout within 10 bars (his "throwbacks hurt")
  yearly    breakout in the lower third of the trailing 250-bar range (his "near the yearly low")
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob, sys
import numpy as np, pandas as pd
sys.path.insert(0, "/home/claude/qlab/src")
import patterns_proper as PP, structure as ST, regime_detect as RD
from levels_general import load_universe, CLEAN_ETF
RNG = np.random.default_rng(2026)


# ------------------------------------------------------------ new detectors (Bulkowski rules)
def d_rectangle_bottom(df, lows, highs, tol=0.03, min_touch=2):
    C, H, L = df.close.values, df.high.values, df.low.values; out = []
    for a in range(len(lows) - 1):
        i1, _ = lows[a]
        # window of pivots within 80 bars
        wl = [(i, k) for i, k in lows if i1 <= i <= i1 + 80]; wh = [(i, k) for i, k in highs if i1 < i <= i1 + 80]
        if len(wl) < min_touch or len(wh) < min_touch: continue
        bot = np.median([L[i] for i, _ in wl]); top = np.median([H[i] for i, _ in wh])
        if top <= bot or (top - bot)/bot < 0.01: continue
        if any(abs(L[i]/bot - 1) > tol for i, _ in wl) or any(abs(H[i]/top - 1) > tol for i, _ in wh): continue
        # "bottom": price fell into it — the 40 bars before i1 were higher
        pre = C[max(0, i1-40):i1]
        if len(pre) < 20 or pre.mean() < top: continue
        last_k = max(k for _, k in wl + wh); last_i = max(i for i, _ in wl + wh)
        for j in range(max(last_k, last_i + 1), min(last_i + 60, len(C))):
            if L[j] < bot*(1 - tol): break
            if C[j] > top:
                out.append(dict(bar=j, entry=C[j], stop=bot*(1 - 0.002), target=top + (top - bot), name="rectangle_bottom", height=top-bot, line=top)); break
    return dedup(out)


def d_desc_triangle_up(df, lows, highs, tol=0.03):
    C, H, L = df.close.values, df.high.values, df.low.values; out = []
    for a in range(len(lows) - 1):
        i1, _ = lows[a]
        wl = [(i, k) for i, k in lows if i1 <= i <= i1 + 80]
        if len(wl) < 2: continue
        sup = np.median([L[i] for i, _ in wl])
        if any(abs(L[i]/sup - 1) > tol for i, _ in wl): continue
        wh = [(i, k) for i, k in highs if i1 < i <= wl[-1][0]]
        if len(wh) < 2 or not all(H[wh[m+1][0]] < H[wh[m][0]] for m in range(len(wh)-1)): continue   # descending highs
        first_h = H[wh[0][0]]; last_h = H[wh[-1][0]]
        if first_h <= sup: continue
        last_k = max(k for _, k in wl + wh); last_i = max(i for i, _ in wl + wh)
        for j in range(max(last_k, last_i + 1), min(last_i + 60, len(C))):
            if L[j] < sup*(1 - tol): break
            if C[j] > last_h:
                out.append(dict(bar=j, entry=C[j], stop=sup*(1 - 0.002), target=C[j] + (first_h - sup), name="desc_triangle_up", height=first_h-sup, line=last_h)); break
    return dedup(out)


def d_triple_bottom(df, lows, highs, tol=0.04):
    C, H, L = df.close.values, df.high.values, df.low.values; out = []
    for a in range(len(lows) - 2):
        (i1, _), (i2, _), (i3, k3) = lows[a], lows[a+1], lows[a+2]
        if i3 - i1 < 20: continue
        y = [L[i1], L[i2], L[i3]]; base = min(y)
        if base <= 0 or max(y)/base - 1 > tol: continue
        mids = [h for h, _ in highs if i1 < h < i3]
        if not mids: continue
        neck = max(H[h] for h in mids)
        for j in range(max(k3, i3 + 1), min(i3 + 100, len(C))):
            if C[j] > neck:
                out.append(dict(bar=j, entry=C[j], stop=base*(1 - 0.002), target=neck + (neck - base), name="triple_bottom", height=neck-base, line=neck)); break
    return dedup(out)


def d_flag_halfmast(df, lows, highs, pole=2.0, maxcons=25):
    """doc 39's flag detection with Bulkowski's measure rule: pole added to the FLAG LOW."""
    sigs = PP.d_flag(df, lows, highs, pole=pole, maxcons=maxcons)
    out = []
    for g in sigs:
        pole_h = g["target"] - g["entry"]          # doc 39 projected the pole from the breakout
        flag_low = g["stop"]
        out.append(dict(bar=g["bar"], entry=g["entry"], stop=g["stop"], target=flag_low + pole_h, name="flag_halfmast", height=pole_h, line=g["entry"]))
    return out


def dedup(out):
    seen = set(); keep = []
    for g in out:
        if g["bar"] in seen: continue
        seen.add(g["bar"]); keep.append(g)
    return keep


def with_height(fn):
    def f(df, lows, highs):
        out = fn(df, lows, highs); H = df.high.values
        for g in out:
            if g["name"] in ("double_bottom", "inv_hs"): g["line"] = (g["target"] + g["stop"])/2
            else: g["line"] = float(H[max(0, g["bar"]-40):g["bar"]].max())      # resistance / flag high
            g["height"] = g["target"] - g["line"] if g["name"] != "flag" else g["target"] - g["entry"]
        return out
    return f


DETS = [with_height(PP.d_double_bottom), with_height(PP.d_inv_hs), with_height(PP.d_asc_triangle), with_height(PP.d_flag),
        d_flag_halfmast, d_rectangle_bottom, d_desc_triangle_up, d_triple_bottom]


# ------------------------------------------------------------ our indicators at the signal bar
def indicators(df, which, btc=None):
    d = df.copy()
    a = ST.atr(d, 14) if hasattr(ST, "atr") else (d.high - d.low).rolling(14).mean()
    d["atr"] = np.asarray(a)
    try:
        Dd, ema, lo_b, hi_b, aa = RD.detectors(d[["open","high","low","close","volume"]].astype(float))
        v = pd.Series(Dd["contain"], index=d.index); d["contain_on"] = (v > v.expanding(300).median()).values
    except Exception:
        d["contain_on"] = np.nan
    k = 4 if which == "crypto_hourly" else 5
    ck = d.close.rolling(k).mean()
    d["trend_up"] = (ck.ewm(span=20, adjust=False).mean() > ck.ewm(span=50, adjust=False).mean()).shift(1)
    d["vol_recede"] = d.volume.rolling(10).mean() < d.volume.shift(10).rolling(10).mean()
    rng_lo = d.low.rolling(250, min_periods=100).min(); rng_hi = d.high.rolling(250, min_periods=100).max()
    d["yearly_low_third"] = (d.close - rng_lo)/(rng_hi - rng_lo).replace(0, np.nan) < 1/3
    if btc is not None:
        b = btc.close.ewm(span=200, adjust=False).mean(); d["btc_bull"] = (btc.close > b).reindex(d.index, method="ffill").values
    else: d["btc_bull"] = np.nan
    return d


def throwback(df, bar, line, atr, n=10):
    H, L = df.high.values, df.low.values; away = False
    for j in range(bar + 1, min(bar + 1 + n, len(df))):
        if H[j] >= line + 0.5*atr: away = True
        if away and L[j] <= line: return True
    return False


def run(which):
    panel = load_universe(which) if which != "stocks" else {os.path.basename(p)[:-4]: pd.read_csv(p, parse_dates=["date"]).set_index("date").sort_index() for p in sorted(glob.glob("/home/claude/qlab/data_wide/*.csv")) if os.path.basename(p)[:-4] not in CLEAN_ETF}
    btc = None
    for key in ("BTCUSDT", "BTCUSD", "BTC"):
        if key in panel: btc = panel[key]; break
    real, ctrl, tb_entry = [], [], []
    for s, df in panel.items():
        if len(df) < 500 or "volume" not in df: continue
        try: lows, highs = PP.confirmed_pivots(df)
        except Exception: continue
        if len(lows) < 4 or len(highs) < 4: continue
        ind = indicators(df, which, btc if s not in ("BTCUSDT", "BTCUSD", "BTC") else None)
        sigs = []
        for det in DETS:
            try: sigs += det(df, lows, highs)
            except Exception: continue
        keep = []
        for g in sigs:
            r = PP.resolve(df, g["bar"], g["entry"], g["stop"], g["target"])
            if not r: continue
            b = g["bar"]; row = ind.iloc[b]
            r.update(name=g["name"], sym=s, contain_on=row.contain_on, trend_up=row.trend_up, btc_bull=row.btc_bull, vol_recede=row.vol_recede,
                     yearly_low=row.yearly_low_third, height_atr=g["height"]/row.atr if row.atr and row.atr > 0 else np.nan,
                     throwback=throwback(df, b, g["line"], row.atr if row.atr and row.atr > 0 else 0))
            real.append(r); keep.append(g)
        if keep:
            C = df.close.values; lo, hi = 150, len(C) - PP.MAXBARS - 2
            if hi > lo:
                bars_ = RNG.choice(np.arange(lo, hi), size=min(len(keep), hi - lo), replace=False)
                for j, si in zip(bars_, RNG.choice(len(keep), size=len(bars_))):
                    ref = keep[int(si)]; sd = 1 - ref["stop"]/ref["entry"]; td = ref["target"]/ref["entry"] - 1; e = C[int(j)]
                    r = PP.resolve(df, int(j), e, e*(1 - sd), e*(1 + td))
                    if not r: continue
                    row = ind.iloc[int(j)]
                    r.update(name=ref["name"], sym=s, contain_on=row.contain_on, trend_up=row.trend_up, btc_bull=row.btc_bull, vol_recede=row.vol_recede, yearly_low=row.yearly_low_third,
                             height_atr=ref["height"]/row.atr if row.atr and row.atr > 0 else np.nan)
                    ctrl.append(r)
            # THROWBACK ENTRY: wait for price to come back to the line within 10 bars, enter there, same stop/target
            H, L = df.high.values, df.low.values
            for g in keep:
                b = g["bar"]; line = g["line"]; atr = ind.atr.iloc[b]; away = False
                if not (atr and atr > 0): continue
                for j in range(b + 1, min(b + 11, len(df))):
                    if L[j] <= line:          # resting limit at the line, valid 10 bars, first touch fills
                        r = PP.resolve(df, j, line, g["stop"], g["target"])
                        if r: r.update(name=g["name"], sym=s); tb_entry.append(r)
                        break
    return pd.DataFrame(real), pd.DataFrame(ctrl), pd.DataFrame(tb_entry)


def exp(T):
    return np.where(T.resolved == 0, 0.0, np.where(T.win == 1.0, T.rr, -1.0))


def line(lbl, T, Cc=None):
    if len(T) < 30: print(f"  {lbl:<44}{len(T):>6} too few"); return
    R = exp(T); res = T[T.resolved == 1]; hit = res.win.mean() if len(res) else np.nan
    s = f"  {lbl:<44}{len(T):>6,}{hit*100:>6.1f}%{T.rr.mean():>6.2f}{R.mean():>+8.3f}R{R.mean()/(R.std(ddof=1)/np.sqrt(len(R))):>+6.1f}"
    if Cc is not None and len(Cc) >= 30:
        Rc = exp(Cc); s += f"{Rc.mean():>+8.3f}R{(R.mean()-Rc.mean()):>+8.3f}"
    print(s, flush=True)


if __name__ == "__main__":
    panels = sys.argv[1:] or ["crypto_hourly", "crypto_daily", "etf", "stocks"]
    for which in panels:
        T, Cc, TB = run(which)
        if not len(T): print(f"\n== {which}: nothing"); continue
        T.to_pickle(f"/home/claude/qlab/runs/bulk_{which}_T.pkl"); Cc.to_pickle(f"/home/claude/qlab/runs/bulk_{which}_C.pkl")
        print(f"\n== {which}: {len(T):,} resolved patterns, {T.sym.nunique()} instruments")
        print(f"  {'pattern / cut':<44}{'n':>6}{'hit':>7}{'R:R':>6}{'exp':>9}{'t':>6}{'ctrl':>9}{'edge':>8}")
        for name in T.name.unique():
            X = T[T.name == name]; Xc = Cc[Cc.name == name] if len(Cc) else None
            line(name, X, Xc)
        print("  --- cuts by our indicators (all patterns pooled, excluding the two flags):")
        P = T[~T.name.isin(["flag", "flag_halfmast"])]
        for col, (a, b) in {"contain_on": ("range switch ON", "range switch OFF"), "trend_up": ("HTF trend UP", "HTF trend DOWN"), "btc_bull": ("BTC > EMA200", "BTC < EMA200"),
                            "vol_recede": ("volume receding into pattern", "volume rising into pattern"), "throwback": ("THROWBACK within 10 bars", "no throwback"),
                            "yearly_low": ("breakout in lower third of 1y range", "upper two thirds")}.items():
            if P[col].isna().all(): continue
            Pc = Cc[~Cc.name.isin(["flag", "flag_halfmast"])] if len(Cc) else None
            line(f"   {a}", P[P[col] == True], Pc[Pc[col] == True] if Pc is not None and col in Pc else None)
            line(f"   {b}", P[P[col] == False], Pc[Pc[col] == False] if Pc is not None and col in Pc else None)
        med = P.height_atr.median()
        line(f"   TALL (height > {med:.1f} ATR)", P[P.height_atr > med], Pc[Pc.height_atr > med]); line("   SHORT", P[P.height_atr <= med], Pc[Pc.height_atr <= med])
        print("  --- POLICY: limit order at the pattern line for 10 bars (fills or misses) vs buy every breakout close. total R over ALL signals:")
        for name in T.name.unique():
            X = TB[TB.name == name] if len(TB) else TB; Xb = T[T.name == name]
            if len(Xb) < 30: continue
            Rb = exp(Xb); Rt = exp(X) if len(X) else np.array([0.0])
            print(f"   {name:<20} breakout: n {len(Xb):>6,} {Rb.mean():>+7.3f}R total {Rb.sum():>+8.0f}R | limit-at-line: n {len(X):>6,} ({len(X)/len(Xb)*100:.0f}% fill) {Rt.mean():>+7.3f}R total {Rt.sum():>+8.0f}R", flush=True)
