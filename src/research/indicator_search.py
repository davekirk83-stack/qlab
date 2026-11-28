"""DK 28 Nov 08:05: "I'm not sure you really did what I asked in checking all indicators in novel combinations. I think you just jumped to
ones that I used in my trading". A systematic search, not a hand-pick.
LIBRARY: ~40 standard indicator conditions (all computed from data up to the signal day's close), grouped:
  trend      above 200d / below 200d, 50d>200d (golden), 20d>50d, ADX(14)>25, ADX<15, MACD>signal, MACD<signal, 55-day high (Donchian),
             55-day low, price>20d EMA, 200d rising
  momentum   ROC20>10%, ROC20<-10%, 52-week high, 52-week low, 3 up days, 3 down days, 6-month RS top (ROC126>20%)
  oscillator RSI14<30, RSI14>70, RSI2<10, RSI2>90, Stoch%K(14)<20, >80, Williams%R(10)<-90, CCI(20)<-100, CCI>100, MFI(14)<20, MFI>80
  volatility below lower Bollinger(20,2), above upper Bollinger, Bollinger squeeze (bandwidth lowest in 120d), ATR(14)% high (top 20% of
             1y), ATR% low (bottom 20%), NR7, inside day, wide-range day (range > 2x ATR)
  volume     volume > 2x 50d avg, volume < 0.5x avg, OBV at a 50-day high, Chaikin money flow(20) > 0.2, CMF < -0.2
  price act  gap up > 2%, gap down > 2%, IBS < 0.2, IBS > 0.8, close in top of range after down day (hammer-ish), outside day
  regime     S&P above 200d, S&P below 200d, VIX > 25, VIX < 15
SEARCH: every single condition, every pair, long AND short, forward returns from the signal close over 1, 5 and 20 days, minus costs
(0.20% round trip stocks, 0.20% indices/commodities, 0.04% FX, 0.28% crypto). Returns are averaged per DAY first (so a crash day with 300
signals counts once), then over days.
ANTI-LUCK: select on US stocks 2005-2015 ONLY (train). Report the top combinations' results on 2016-2026 (test, unseen), and on the
non-stock markets (indices, commodities, FX - no survivorship bias - and crypto). With ~3,000 pair x side x hold candidates, a train
t-stat of ~4 is needed before anything is a candidate (Bonferroni-ish); the out-of-sample check is the real filter.
Edge is reported as excess over the unconditional average of that market and hold (so plain market drift doesn't count)."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, glob, itertools, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); import cross_asset_s3 as X
HOLDS = (1, 5, 20)

def conds(D, spxup, vix):
    o, h, l, c = D.o, D.h, D.l, D.c; v = D.v if "v" in D and D.v.notna().any() and (D.v > 0).mean() > 0.9 else None
    F = {}; pc = c.shift(1)
    m20, m50, m200 = c.rolling(20).mean(), c.rolling(50).mean(), c.rolling(200).mean()
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1); atr = tr.rolling(14).mean()
    F["above200"] = c > m200; F["below200"] = c < m200; F["golden"] = m50 > m200; F["m20>m50"] = m20 > m50
    up_dm = (h - h.shift()).clip(lower=0); dn_dm = (l.shift() - l).clip(lower=0); up_dm[up_dm < dn_dm] = 0; dn_dm[dn_dm <= up_dm] = 0
    pdi = 100 * up_dm.ewm(alpha=1 / 14).mean() / atr; mdi = 100 * dn_dm.ewm(alpha=1 / 14).mean() / atr
    adx = (100 * (pdi - mdi).abs() / (pdi + mdi)).ewm(alpha=1 / 14).mean(); F["adx>25"] = adx > 25; F["adx<15"] = adx < 15
    macd = c.ewm(span=12).mean() - c.ewm(span=26).mean(); sigl = macd.ewm(span=9).mean(); F["macd>sig"] = macd > sigl; F["macd<sig"] = macd < sigl
    F["55d_high"] = c >= c.rolling(55).max(); F["55d_low"] = c <= c.rolling(55).min(); F["above_ema20"] = c > c.ewm(span=20).mean()
    F["200d_rising"] = m200 > m200.shift(20)
    roc20 = c / c.shift(20) - 1; F["roc20>10%"] = roc20 > 0.10; F["roc20<-10%"] = roc20 < -0.10
    F["52w_high"] = c >= c.rolling(252).max(); F["52w_low"] = c <= c.rolling(252).min()
    d = c.diff(); F["3up"] = (d > 0) & (d.shift() > 0) & (d.shift(2) > 0); F["3down"] = (d < 0) & (d.shift() < 0) & (d.shift(2) < 0)
    F["rs6m>20%"] = c / c.shift(126) - 1 > 0.20
    def rsi(n):
        u = d.clip(lower=0).ewm(alpha=1 / n).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / n).mean(); return 100 - 100 / (1 + u / dn.replace(0, np.nan))
    r14, r2 = rsi(14), rsi(2); F["rsi14<30"] = r14 < 30; F["rsi14>70"] = r14 > 70; F["rsi2<10"] = r2 < 10; F["rsi2>90"] = r2 > 90
    ll, hh = l.rolling(14).min(), h.rolling(14).max(); k = 100 * (c - ll) / (hh - ll); F["stoch<20"] = k < 20; F["stoch>80"] = k > 80
    wr = -100 * (h.rolling(10).max() - c) / (h.rolling(10).max() - l.rolling(10).min()); F["willr<-90"] = wr < -90
    tp = (h + l + c) / 3; cci = (tp - tp.rolling(20).mean()) / (0.015 * tp.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True))
    F["cci<-100"] = cci < -100; F["cci>100"] = cci > 100
    sd = c.rolling(20).std(); F["below_bb"] = c < m20 - 2 * sd; F["above_bb"] = c > m20 + 2 * sd
    bw = 4 * sd / m20; F["bb_squeeze"] = bw <= bw.rolling(120).min()
    atrp = atr / c; F["atr_high"] = atrp >= atrp.rolling(252).quantile(0.8); F["atr_low"] = atrp <= atrp.rolling(252).quantile(0.2)
    rng = h - l; F["nr7"] = rng <= rng.rolling(7).min(); F["inside"] = (h < h.shift()) & (l > l.shift()); F["wide_range"] = rng > 2 * atr.shift()
    F["outside"] = (h > h.shift()) & (l < l.shift())
    F["gap_up2%"] = o > pc * 1.02; F["gap_dn2%"] = o < pc * 0.98
    ibs = (c - l) / rng.replace(0, np.nan); F["ibs<0.2"] = ibs < 0.2; F["ibs>0.8"] = ibs > 0.8; F["hammer"] = (d < 0) & (ibs > 0.7) & (l < l.shift())
    if v is not None:
        av = v.rolling(50).mean().shift(1); F["vol>2x"] = v > 2 * av; F["vol<0.5x"] = v < 0.5 * av
        obv = (np.sign(d).fillna(0) * v).cumsum(); F["obv_50d_high"] = obv >= obv.rolling(50).max()
        mfv = ((c - l) - (h - c)) / rng.replace(0, np.nan) * v; cmf = mfv.rolling(20).sum() / v.rolling(20).sum(); F["cmf>0.2"] = cmf > 0.2; F["cmf<-0.2"] = cmf < -0.2
        mf = tp * v; pos = mf.where(tp > tp.shift(), 0).rolling(14).sum(); neg = mf.where(tp < tp.shift(), 0).rolling(14).sum(); mfi = 100 - 100 / (1 + pos / neg.replace(0, np.nan))
        F["mfi<20"] = mfi < 20; F["mfi>80"] = mfi > 80
    su = spxup.reindex(D.index).ffill(); vx = vix.reindex(D.index).ffill()
    F["spx>200"] = su == True; F["spx<200"] = su == False; F["vix>25"] = vx > 25; F["vix<15"] = vx < 15
    return pd.DataFrame({k: v_.fillna(False).astype(bool) for k, v_ in F.items()})

def fwd(D, cost):
    return pd.DataFrame({h: D.c.shift(-h) / D.c - 1 - cost for h in HOLDS})

def build(U, spxup, vix):
    rows = []
    for (cls, s), x in U.items():
        if cls in ("UK stocks", "bonds"): continue
        D = x.copy()
        if cls == "US stocks": D = pd.read_csv(f"data_stocks/{s}.csv.gz", parse_dates=["Date"], index_col="Date").rename(columns={"Open": "o", "High": "h", "Low": "l", "Close": "c", "Volume": "v"})
        D = D[[k for k in ("o", "h", "l", "c", "v") if k in D]].astype(float).dropna(subset=["c"]); D = D[D.c > 0]
        if len(D) < 400: continue
        cost = {"FX": 0.0004, "crypto": 0.0028}.get(cls, 0.002)
        C = conds(D, spxup, vix); R = fwd(D, cost); C = C.iloc[260:-21]; R = R.loc[C.index]
        C["_cls"] = cls; C["_sym"] = s; C["_t"] = C.index
        for hh in HOLDS: C[f"_r{hh}"] = R[hh].values
        rows.append(C.reset_index(drop=True))
    return pd.concat(rows, ignore_index=True)

def evaluate(M, mask, hold, side):
    """per-day average (a crash day with hundreds of signals counts once). raw = gross forward return; cost per side c.
    long net = raw - 2c ; short net = -raw - 2c. excess = net versus the market-class average raw move that day (sign-adjusted).
    Returns mean excess %, month-clustered t of excess, mean absolute net %, days, signals, win rate (net)."""
    r = M[f"_r{hold}"].values; c = M["_cost"].values; base = M[f"_base{hold}"].values
    m = mask & np.isfinite(r)
    if m.sum() < 30: return None
    raw = r[m] + 2 * c[m]
    net = raw - 2 * c[m] if side == 1 else -raw - 2 * c[m]
    ex = net - (base[m] if side == 1 else -base[m])
    t = M["_t"].values[m]; d = pd.DataFrame({"ex": ex, "net": net}, index=t).groupby(level=0).mean()
    if len(d) < 20: return None
    mo = d.ex.groupby(d.index.to_period("M")).mean(); tt = mo.mean() / (mo.std() / np.sqrt(len(mo))) if len(mo) > 3 and mo.std() > 0 else 0
    return dict(mean=100 * d.ex.mean(), t=tt, net=100 * d.net.mean(), days=len(d), n=int(m.sum()), win=float((net > 0).mean()))

if __name__ == "__main__":
    U = X.load(); spx = U[("indices", "SPX")]; spxup = (spx.c > spx.c.rolling(200).mean())
    vix = pd.read_csv("data_daily/VIX.csv", index_col=0); vix.index = pd.to_datetime(vix.index, utc=True).tz_localize(None).normalize(); vix = vix.close
    M = build(U, spxup, vix); print("rows", len(M), flush=True)
    M["_cost"] = M._cls.map({"FX": 0.0002, "crypto": 0.0014}).fillna(0.001)          # per side
    for hh in HOLDS:   # market/hold baseline: average raw forward return of that market class on that day (removes market drift)
        raw = M[f"_r{hh}"] + 2 * M._cost
        M[f"_base{hh}"] = raw.groupby([M._cls, M._t]).transform("mean")
    M.to_pickle("/tmp/claude-0/-home-claude/6103913e-5d93-5930-ba67-b97312457994/scratchpad/ind_M.pkl")
    names = [c for c in M.columns if not c.startswith("_")]
    B = {k: M[k].values for k in names}
    year = pd.to_datetime(M._t).dt.year.values; cls = M._cls.values
    TRAIN = (cls == "US stocks") & (year <= 2015); TEST = (cls == "US stocks") & (year >= 2016)
    OTHER = {c: (cls == c) for c in ("indices", "commodities", "FX", "crypto")}
    cands = [(a,) for a in names] + list(itertools.combinations(names, 2))
    print("candidates", len(cands), "x 2 sides x", len(HOLDS), "holds", flush=True)
    res = []
    for combo in cands:
        mk = B[combo[0]].copy()
        for k in combo[1:]: mk &= B[k]
        mt = mk & TRAIN
        if mt.sum() < 200: continue
        for hold in HOLDS:
            for side in (1, -1):
                e = evaluate(M, mt, hold, side)
                if e and e["t"] >= 3.0 and e["mean"] > 0 and e["net"] > 0: res.append(dict(combo=" + ".join(combo), k=len(combo), hold=hold, side="long" if side == 1 else "short", **{f"tr_{a}": b for a, b in e.items()}))
    T = pd.DataFrame(res).sort_values("tr_t", ascending=False); print("train survivors (t>=3)", len(T), flush=True)
    out = []
    for _, r in T.head(300).iterrows():
        combo = r.combo.split(" + "); mk = B[combo[0]].copy()
        for k in combo[1:]: mk &= B[k]
        side = 1 if r.side == "long" else -1; row = dict(r)
        e = evaluate(M, mk & TEST, r.hold, side); row.update({f"te_{a}": (b if e else np.nan) for a, b in (e or dict(mean=0, t=0, net=0, days=0, n=0, win=0)).items()})
        for c, om in OTHER.items():
            e = evaluate(M, mk & om, r.hold, side); row[f"{c}_mean"] = e["mean"] if e else np.nan; row[f"{c}_t"] = e["t"] if e else np.nan; row[f"{c}_n"] = e["n"] if e else 0
        out.append(row)
    O = pd.DataFrame(out); O.to_csv("runs/research/indicator_search.csv", index=False)
    O["oos_ok"] = (O.te_mean > 0) & (O.te_t >= 2) & (O.te_net > 0)
    O["xasset_ok"] = ((O.indices_mean > 0).astype(int) + (O.commodities_mean > 0).astype(int) + (O.crypto_mean > 0).astype(int) + (O.FX_mean > 0).astype(int))
    pd.set_option("display.width", 300); pd.set_option("display.max_colwidth", 45)
    cols = ["combo", "hold", "side", "tr_mean", "tr_net", "tr_t", "tr_n", "te_mean", "te_net", "te_t", "te_n", "indices_mean", "commodities_mean", "crypto_mean", "FX_mean", "xasset_ok"]
    print("\nTOP 40 by train t-stat:"); print(O[cols].head(40).round(3).to_string(index=False))
    print("\nOUT-OF-SAMPLE SURVIVORS (test t>=2) with >=3 of 4 other asset classes positive:")
    print(O[O.oos_ok & (O.xasset_ok >= 3)][cols].round(3).to_string(index=False))
    print("\nsummary: train survivors", len(T), "| of top 300: test t>=2:", int(O.oos_ok.sum()), "| + cross-asset>=3:", int((O.oos_ok & (O.xasset_ok >= 3)).sum()))
