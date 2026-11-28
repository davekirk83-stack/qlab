"""DK 28 Nov 08:20: "we do need to finally and definitively crack some day trading methods. We can't only trade stock market corrections".
Systematic intraday search (same anti-luck design as indicator_search2.py, doc 282):
DATA: Alpaca 15-min bars 2021-26, US regular session only (09:30-16:00 New York): index ETFs SPY / QQQ / IWM (what we trade as US500 /
      NQ / Russell on IG), 13 large stocks, commodity ETFs, COIN / MSTR. Confirmation: IG-traded NQ (Dukascopy 5m -> 15m, Oct 2025-Nov 2026).
CONDITIONS (~50, all known at the signal bar's close): time of day; opening range (first 30 min) breaks; prior-day high / low / close; gap
      up / down; session VWAP side and stretch; 15-min RSI(2) / RSI(14); big / narrow / inside bars; volume spikes; day move so far;
      3 bars the same way; 20-bar EMA side; daily context (above / below the daily 20-day mean, prior day up / down, daily RSI(2) < 10);
      SPY's own day so far (for every symbol); Monday / Friday.
TRADES: entry at the NEXT bar's open; always flat by the close (day trading). Exits: H2 (30 min), H4 (1 h), H8 (2 h), EOD (last bar's close),
      VWAP (first close back across the session VWAP in the trade's favour, else EOD). Long and short.
COSTS per side: index ETFs / IG indices 0.02% (IG NQ spread ~1 pt = 0.005% + slippage, conservative), stocks / commodity ETFs 0.03%.
JUDGED: edge = net return minus the unconditional average of the same exit for that symbol group in the train years. Per-day averaging,
      month-clustered t. SELECT on the 3 index ETFs 2021-23 (t >= 3); TEST: index ETFs 2024-26 (unseen), stocks 2021-26, IG NQ.
      Triples: each top pair + every third condition (t >= 3.5)."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, glob, itertools, numpy as np, pandas as pd
IDXE = ("SPY", "QQQ", "IWM"); COMM = ("GLD", "SLV", "USO", "UNG", "CPER", "DBA", "GDX")
EXITS = ("H2", "H4", "H8", "EOD", "VWAP")

def rth(f):
    d = pd.read_csv(f, index_col=0, parse_dates=True); d.index = pd.to_datetime(d.index, utc=True).tz_convert("America/New_York")
    m = d.index.hour * 60 + d.index.minute; d = d[(m >= 570) & (m < 960)].copy()
    if "vol" not in d: d["vol"] = np.nan
    return d[["open", "high", "low", "close", "vol"]].astype(float)

def features(d, spy_day):
    d = d.copy(); day = d.index.normalize(); d["day"] = day; g = d.groupby("day", sort=False)
    d["b"] = g.cumcount(); d["nb"] = g.close.transform("size")
    dopen = g.open.transform("first"); tp = (d.high + d.low + d.close) / 3; v = d.vol.fillna(1.0).replace(0, 1.0)
    d["vwap"] = (tp * v).groupby(day).cumsum() / v.groupby(day).cumsum()
    D = g.agg(o=("open", "first"), h=("high", "max"), l=("low", "min"), c=("close", "last"))
    pdh, pdl, pdc = D.h.shift(1), D.l.shift(1), D.c.shift(1); ma20d = D.c.rolling(20).mean().shift(1); pdc2 = D.c.shift(2)
    dd = D.c.diff(); u = dd.clip(lower=0).ewm(alpha=0.5, adjust=False).mean(); dn = (-dd.clip(upper=0)).ewm(alpha=0.5, adjust=False).mean(); drsi2 = (100 - 100 / (1 + u / dn.replace(0, np.nan))).shift(1)
    for k, s in (("pdh", pdh), ("pdl", pdl), ("pdc", pdc), ("ma20d", ma20d), ("pdc2", pdc2), ("drsi2", drsi2)): d[k] = s.reindex(day).values
    orh = d.high.where(d.b < 2).groupby(day).transform("max"); orl = d.low.where(d.b < 2).groupby(day).transform("min")
    c = d.close; rng = d.high - d.low; ar = rng.rolling(20).mean().shift(1); atr = ar
    dlt = c.diff(); up = dlt.clip(lower=0); dn_ = -dlt.clip(upper=0)
    r2 = 100 - 100 / (1 + up.ewm(alpha=0.5, adjust=False).mean() / dn_.ewm(alpha=0.5, adjust=False).mean().replace(0, np.nan))
    r14 = 100 - 100 / (1 + up.ewm(alpha=1 / 14, adjust=False).mean() / dn_.ewm(alpha=1 / 14, adjust=False).mean().replace(0, np.nan))
    ema20 = c.ewm(span=20).mean(); av = d.vol.rolling(20).mean().shift(1); dayret = c / dopen - 1
    F = {}
    F["first_hour"] = d.b < 4; F["midday"] = (d.b >= 4) & (d.b < 18); F["last_hour"] = d.b >= 22; F["bar0"] = d.b == 0; F["bar1"] = d.b == 1
    first_up = (c > orh) & (d.b >= 2); F["orb_up"] = first_up & ~first_up.groupby(day).shift(1, fill_value=False).groupby(day).cummax()
    first_dn = (c < orl) & (d.b >= 2); F["orb_dn"] = first_dn & ~first_dn.groupby(day).shift(1, fill_value=False).groupby(day).cummax()
    F["above_or"] = (c > orh) & (d.b >= 2); F["below_or"] = (c < orl) & (d.b >= 2); F["inside_or"] = (c <= orh) & (c >= orl) & (d.b >= 2)
    F["above_pdh"] = c > d.pdh; F["below_pdl"] = c < d.pdl; F["above_pdc"] = c > d.pdc; F["below_pdc"] = c < d.pdc
    F["gap_up"] = dopen > d.pdc * 1.005; F["gap_dn"] = dopen < d.pdc * 0.995
    F["gap_filled_up"] = F["gap_up"] & (d.low.groupby(day).cummin() <= d.pdc); F["gap_filled_dn"] = F["gap_dn"] & (d.high.groupby(day).cummax() >= d.pdc)
    F["above_vwap"] = c > d.vwap; F["below_vwap"] = c < d.vwap; F["stretch_up"] = c > d.vwap + 1.5 * atr; F["stretch_dn"] = c < d.vwap - 1.5 * atr
    F["rsi2<10"] = r2 < 10; F["rsi2>90"] = r2 > 90; F["rsi14<30"] = r14 < 30; F["rsi14>70"] = r14 > 70
    F["big_up_bar"] = (rng > 2 * ar) & (c > d.open); F["big_dn_bar"] = (rng > 2 * ar) & (c < d.open); F["nr7"] = rng <= rng.rolling(7).min()
    F["inside_bar"] = (d.high < d.high.shift()) & (d.low > d.low.shift())
    if d.vol.notna().mean() > 0.9: F["vol>2x"] = d.vol > 2 * av; F["vol<0.5x"] = d.vol < 0.5 * av
    F["day_up1%"] = dayret > 0.01; F["day_dn1%"] = dayret < -0.01; F["day_up"] = dayret > 0; F["day_dn"] = dayret < 0
    F["3up"] = (dlt > 0) & (dlt.shift() > 0) & (dlt.shift(2) > 0); F["3dn"] = (dlt < 0) & (dlt.shift() < 0) & (dlt.shift(2) < 0)
    F["above_ema20"] = c > ema20; F["below_ema20"] = c < ema20
    F["d_above_20d"] = d.pdc > d.ma20d; F["d_below_20d"] = d.pdc < d.ma20d; F["prev_day_up"] = d.pdc > d.pdc2; F["prev_day_dn"] = d.pdc < d.pdc2
    F["d_rsi2<10"] = d.drsi2 < 10; F["d_rsi2>90"] = d.drsi2 > 90
    sd = spy_day.reindex(d.index).values; F["spy_day_up"] = sd > 0; F["spy_day_dn"] = sd < 0
    F["mon"] = d.index.dayofweek == 0; F["fri"] = d.index.dayofweek == 4
    C = pd.DataFrame({k: np.asarray(v, dtype=bool) if not hasattr(v, "fillna") else v.fillna(False).astype(bool).values for k, v in F.items()}, index=d.index)
    return d, C

def exits(d):
    """gross return of each exit, entering at the next bar's open, long direction (shorts = minus)."""
    o, c, vw = d.open.values, d.close.values, d.vwap.values; b, nb = d.b.values, d.nb.values; n = len(c)
    idx = np.arange(n); last = idx + (nb - 1 - b)                 # index of the day's last bar
    ok = (b < nb - 1); e = np.where(ok, o[np.minimum(idx + 1, n - 1)], np.nan)
    out = {}
    for h in (2, 4, 8):
        j = np.minimum(idx + h, last); out[f"H{h}"] = c[j] / e - 1
    out["EOD"] = c[last] / e - 1
    # VWAP revert: long side = first close at/above VWAP after entry; short side = first close at/below VWAP
    for side, nm in ((1, "VWAPL"), (-1, "VWAPS")):
        hit = (c >= vw) if side == 1 else (c <= vw); r = np.full(n, np.nan)
        days = np.split(idx, np.where(np.diff(b) < 0)[0] + 1)
        for dd in days:
            hh = hit[dd]; cc = c[dd]; L = len(dd); first = np.full(L, L - 1); pos = L - 1
            for i in range(L - 1, -1, -1):                 # first[i] = next hit strictly after i (else the last bar)
                first[i] = pos
                if hh[i]: pos = i
            jj = np.empty(L, int)
            for i in range(L):                              # signal i, entry at i+1's open: exit at the first close at index >= i+1
                k = min(i + 1, L - 1); jj[i] = k if hh[k] else first[k]
            r[dd] = cc[jj]
        out[nm] = r / e - 1
    X = pd.DataFrame(out, index=d.index); X[~ok] = np.nan; return X

def build():
    spy = rth("data_alpaca/SPY_15m.csv.gz"); spy_day = spy.close / spy.groupby(spy.index.normalize()).open.transform("first") - 1
    rows = []
    for f in sorted(glob.glob("data_alpaca/*_15m.csv.gz")):
        s = os.path.basename(f).split("_")[0]; d = rth(f)
        if len(d) < 5000: continue
        d, C = features(d, spy_day); X = exits(d)
        grp = "index" if s in IDXE else ("commodity" if s in COMM else "stock")
        C["_sym"] = s; C["_grp"] = grp; C["_t"] = d.index; C["_day"] = d["day"].values
        for k in X: C[f"_g{k}"] = X[k].values
        rows.append(C.reset_index(drop=True))
    # IG NQ (Dukascopy) for confirmation, same session window
    q = pd.read_csv("data_nq_cache/nq_5m.csv", index_col=0, parse_dates=True); q.index = pd.to_datetime(q.index, utc=True)
    q = q.resample("15min").agg({"open": "first", "high": "max", "low": "min", "close": "last", "vol": "sum"}).dropna(subset=["close"])
    q.to_csv("/tmp/claude-0/-home-claude/6103913e-5d93-5930-ba67-b97312457994/scratchpad/nq15.csv")
    d = rth("/tmp/claude-0/-home-claude/6103913e-5d93-5930-ba67-b97312457994/scratchpad/nq15.csv"); d, C = features(d, spy_day); X = exits(d)
    C["_sym"] = "IG_NQ"; C["_grp"] = "ig_nq"; C["_t"] = d.index; C["_day"] = d["day"].values
    for k in X: C[f"_g{k}"] = X[k].values
    rows.append(C.reset_index(drop=True))
    M = pd.concat(rows, ignore_index=True)
    M["_cost"] = M._grp.map({"index": 0.000075, "ig_nq": 0.000075}).fillna(0.0003)   # 28 Nov: IG index cost ~0.005% spread + slippage per side (was 0.02%, 3-4x too high)
    return M

def gcol(ex, side): return f"_g{ex}" if ex != "VWAP" else ("_gVWAPL" if side == 1 else "_gVWAPS")

def evaluate(M, mask, ex, side, base):
    """28 Nov fix (per-day averaging hid the losing trend days - vwap_fade.py showed the 'best' survivor loses as real trades):
    PER TRADE. Only the FIRST bar of each run of consecutive signals (same symbol and day) is a trade - what a trader would take.
    Mean per trade; t-stat from MONTHLY SUMS of trade P&L (clustering by month)."""
    g = M[gcol(ex, side)].values; m = mask & np.isfinite(g)
    prev = np.r_[False, m[:-1]] & np.r_[False, (M._sym.values[1:] == M._sym.values[:-1]) & (M._day.values[1:] == M._day.values[:-1])]
    m = m & ~prev
    if m.sum() < 40: return None
    net = side * g[m] - 2 * M._cost.values[m]; edge = net - side * base[(ex, side)].reindex(M._grp.values[m]).values
    mo_key = pd.to_datetime(M._day.values[m]).to_period("M")
    ms = pd.Series(edge, index=mo_key).groupby(level=0).sum(); cnt = pd.Series(1, index=mo_key).groupby(level=0).sum()
    t = ms.mean() / (ms.std() / np.sqrt(len(ms))) if len(ms) > 3 and ms.std() > 0 else 0
    return dict(edge=100 * edge.mean(), t=t, net=100 * net.mean(), days=int(pd.Series(M._day.values[m]).nunique()), n=int(m.sum()), win=float((net > 0).mean()))

if __name__ == "__main__":
    M = build(); print("rows", len(M), M._grp.value_counts().to_dict(), flush=True)
    yr = pd.to_datetime(M._t, utc=True).dt.year.values
    base = {}
    for ex in EXITS:
        for side in (1, -1):
            g = M[gcol(ex, side)]; base[(ex, side)] = g[yr <= 2023].groupby(M._grp[yr <= 2023]).mean()
    names = [c for c in M.columns if not c.startswith("_")]; B = {k: M[k].values.astype(bool) for k in names}
    grp = M._grp.values
    TRAIN = (grp == "index") & (yr <= 2023); TEST = (grp == "index") & (yr >= 2024)
    OTH = {"stocks": grp == "stock", "commodities": grp == "commodity", "IG_NQ": grp == "ig_nq"}
    def mask(cb):
        m = B[cb[0]].copy()
        for k in cb[1:]: m = m & B[k]
        return m
    def search(cands, thr):
        res = []
        for cb in cands:
            mk = mask(cb); mt = mk & TRAIN
            if mt.sum() < 120: continue
            for ex in EXITS:
                for side in (1, -1):
                    e = evaluate(M, mt, ex, side, base)
                    if e and e["t"] >= thr and e["edge"] > 0 and e["net"] > 0:
                        res.append(dict(combo=" + ".join(cb), k=len(cb), exit=ex, side="long" if side == 1 else "short", **{f"tr_{a}": b for a, b in e.items()}))
        return pd.DataFrame(res)
    cands = [(a,) for a in names] + list(itertools.combinations(names, 2))
    T = search(cands, 3.0); print("train survivors singles+pairs:", len(T), flush=True)
    T = T.sort_values("tr_t", ascending=False) if len(T) else T
    tops = T[T.k == 2].drop_duplicates("combo").head(25).combo.str.split(" \\+ ").tolist() if len(T) else []
    trip = sorted({tuple(sorted(p + [c])) for p in tops for c in names if c not in p}); T3 = search(trip, 3.5) if trip else pd.DataFrame()
    print("triples tested", len(trip), "survivors", len(T3), flush=True)
    T = pd.concat([T, T3]).sort_values("tr_t", ascending=False) if len(T3) else T
    out = []
    for _, r in T.head(400).iterrows():
        mk = mask(r.combo.split(" + ")); side = 1 if r.side == "long" else -1; row = dict(r)
        e = evaluate(M, mk & TEST, r.exit, side, base) or dict(edge=np.nan, t=np.nan, net=np.nan, days=0, n=0, win=np.nan); row.update({f"te_{a}": b for a, b in e.items()})
        for nm, om in OTH.items():
            e = evaluate(M, mk & om, r.exit, side, base); row[f"{nm}_net"] = e["net"] if e else np.nan; row[f"{nm}_t"] = e["t"] if e else np.nan; row[f"{nm}_n"] = e["n"] if e else 0
        out.append(row)
    O = pd.DataFrame(out); O.to_csv("runs/research/intraday_search_pertrade.csv", index=False)
    if len(O):
        O["oos_ok"] = (O.te_edge > 0) & (O.te_t >= 2) & (O.te_net > 0)
        pd.set_option("display.width", 320); pd.set_option("display.max_colwidth", 50)
        cols = ["combo", "exit", "side", "tr_edge", "tr_net", "tr_t", "tr_n", "te_edge", "te_net", "te_t", "te_n", "stocks_net", "stocks_t", "commodities_net", "IG_NQ_net", "IG_NQ_t", "IG_NQ_n"]
        print("\nTOP 30 by train t:"); print(O[cols].head(30).round(3).to_string(index=False))
        S = O[O.oos_ok]; print(f"\nOUT-OF-SAMPLE SURVIVORS (index ETFs 2024-26, t>=2, net>0): {len(S)}"); print(S.sort_values("te_t", ascending=False)[cols].head(50).round(3).to_string(index=False))
