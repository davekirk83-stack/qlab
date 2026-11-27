"""DK 27 Nov 17:20: "Does my longing method work on other/all charts?" - DK book v2 LONGS (doc 272) as a stand-alone engine run on every
market with 15-min history: 10 coins (Binance spot 2021-26) and the IG index/gold caches (5-min -> 15-min; NQ / US500 ~1 year,
Wall St / DAX / FTSE / gold ~7 months).
Two ports:
  'as tested'  = the BTC rules in % (deep flush 15% under the 20-day high, a third off at +1.5%, target +3%)
  'vol-scaled' = the same rules in units of each market's daily ATR% (BTC's ATR ~3% -> deep 5 ATR, partial 0.5 ATR, target 1 ATR),
                 because a 15% flush on the S&P is a once-a-decade event, not a trading signal.
Rules otherwise as v2: resting bids each London morning just under the 24h low (only when price is within 3% / 1 ATR above it), in a
deep flush or an uptrend (above the 50- and 200-day); 4 rungs 10/20/30/40 spaced 0.3 x ATR% (clipped 0.6-3%); stop one step under
the deepest; 2-day fill window; 7-day limit; flat before US CPI. Costs: coins maker 0 / taker 0.09% + 0.05% slip (Revolut X);
IG markets = the data's spread + 0.018%/day overnight funding. Result = % of the ladder budget per campaign."""
import warnings; warnings.filterwarnings("ignore")
import glob, os, sys, io, contextlib, numpy as np, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
with contextlib.redirect_stdout(io.StringIO()): import liq_book as LB
CPI_T = pd.DatetimeIndex(LB.CPI_T)
CO = "/tmp/claude-0/-home-claude/6103913e-5d93-5930-ba67-b97312457994/scratchpad/coins15"

def coin(sym):
    xs = []
    for f in sorted(glob.glob(f"{CO}/{sym}-15m-*.csv")):
        x = pd.read_csv(f, header=None).iloc[:, :5]; x.columns = "t open high low close".split()
        x["t"] = pd.to_datetime(x.t // 1000 if x.t.iloc[0] > 1e14 else x.t, unit="ms", utc=True); xs.append(x.set_index("t"))
    d = pd.concat(xs).sort_index(); return d[~d.index.duplicated()].astype(float)
def ig(f):
    d = pd.read_csv(f, index_col=0); d.index = pd.to_datetime(d.index, utc=True)
    sp = (d.spread / d.close).median() if "spread" in d else 0.0002
    q = d.resample("15min").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna(); return q, float(sp)

def run(d, mode, venue, spread=0.0):
    O, H, L, C = d.open.values, d.high.values, d.low.values, d.close.values; U = d.index; N = len(C)
    dl = pd.DataFrame({"h": d.high.resample("1D").max(), "l": d.low.resample("1D").min(), "c": d.close.resample("1D").last()}).dropna()
    tr = np.maximum(dl.h - dl.l, np.maximum((dl.h - dl.c.shift()).abs(), (dl.l - dl.c.shift()).abs()))
    day = U.floor("1D")
    ATRP = (tr.rolling(14).mean() / dl.c).shift(1).reindex(day).values
    UP = ((dl.c > dl.c.rolling(50).mean()) & (dl.c > dl.c.rolling(200, min_periods=120).mean())).shift(1).reindex(day).fillna(False).values
    HI20 = dl.h.rolling(20).max().shift(1).reindex(day).values
    cpi = np.searchsorted(U.values, CPI_T.values)
    taker = 0.0009 + 0.0005 if venue == "coin" else spread / 2; maker = 0.0 if venue == "coin" else spread / 2; fund = 0.0 if venue == "coin" else 0.00018
    out = []; busy = -1
    starts = np.where((U.hour == 7) & (U.minute == 0))[0]
    for j in starts:
        if j < 96 * 30 or j >= N - 96 * 8 or j <= busy or not np.isfinite(ATRP[j]) or not np.isfinite(HI20[j]): continue
        a = ATRP[j]; lvl = L[j - 96:j].min() * (1 - 0.1 * a if mode == "vol-scaled" else 0.997)
        if C[j - 1] > lvl * (1 + (a if mode == "vol-scaled" else 0.03)): continue
        deep = C[j] <= HI20[j] * (1 - (5 * a if mode == "vol-scaled" else 0.15))
        if not (deep or UP[j]): continue
        step = float(np.clip(0.3 * a, 0.006 if mode == "as tested" else 0.1 * a, 0.03))
        rungs = [lvl * (1 - step * r) for r in range(4)]; wts = (0.1, 0.2, 0.3, 0.4); stop = rungs[-1] * (1 - step)
        p_lvl, t_lvl = (0.5 * a, 1.0 * a) if mode == "vol-scaled" else (0.015, 0.03)
        nc = cpi[np.searchsorted(cpi, j + 1)] if np.searchsorted(cpi, j + 1) < len(cpi) else 10 ** 9
        qty = cost = pnl = 0.0; part = False; done = [False] * 4; k1 = None; res = None; kend = min(N - 1, j + 96 * 7)
        for k in range(j, kend + 1):
            for r in range(4):
                if not done[r] and k <= j + 192 and L[k] <= rungs[r]: done[r] = True; qty += wts[r]; cost += wts[r] * rungs[r] * (1 + maker); k1 = k1 if k1 is not None else k
            if qty <= 0:
                if k > j + 192: break
                continue
            avg = cost / qty; hold = (k - k1) / 96 * fund
            if L[k] <= stop: res = pnl + qty * (stop * (1 - taker) - avg * (1 + hold)); break
            if k >= nc - 1: res = pnl + qty * (C[k] * (1 - taker) - avg * (1 + hold)); break
            if not part and k > k1 and H[k] >= avg * (1 + p_lvl): q = qty / 3; pnl += q * (avg * (1 + p_lvl) * (1 - maker) - avg * (1 + hold)); qty -= q; cost = avg * qty; part = True
            if k > k1 and H[k] >= avg * (1 + t_lvl): res = pnl + qty * (avg * (1 + t_lvl) * (1 - maker) - avg * (1 + hold)); break
        if qty <= 0 and res is None: continue
        if res is None: avg = cost / qty; res = pnl + qty * (C[kend] * (1 - taker) - avg * (1 + (kend - k1) / 96 * fund)); k = kend
        out.append((U[j], res / lvl * 100)); busy = max(k, j + 96)
    t = pd.Series([v for _, v in out], index=pd.DatetimeIndex([a for a, _ in out]))
    return t

def summ(t, m, mode, since):
    if len(t) < 8: return dict(mkt=m, port=mode, n=len(t), since=since)
    h = len(t) // 2; y = t.groupby(t.index.year).sum(); eq = t.cumsum()
    return dict(mkt=m, port=mode, n=len(t), since=since, win=round((t > 0).mean(), 2), mean=round(t.mean(), 3), h1=round(t[:h].mean(), 3), h2=round(t[h:].mean(), 3),
                last12m=round(t[t.index >= t.index[-1] - pd.Timedelta("365D")].mean(), 3), yrs_pos=f"{(y > 0).sum()}/{len(y)}", total=round(t.sum(), 1), max_dd=round((eq - eq.cummax()).min(), 1))

if __name__ == "__main__":
    rows = []; allt = {}
    for s in ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT", "DOGEUSDT", "ADAUSDT", "LINKUSDT", "AVAXUSDT", "LTCUSDT"):
        d = coin(s)
        for mode in ("as tested", "vol-scaled"):
            t = run(d, mode, "coin"); allt[(s, mode)] = t; rows.append(summ(t, s, mode, str(d.index[0].date()))); print(rows[-1], flush=True)
    for m, f in (("NQ", "data_nq_cache/nq_5m.csv"), ("US500", "data_ig_cache/USA500IDXUSD_5m.csv"), ("WALLST", "data_ig_cache/USA30IDXUSD_5m.csv"),
                 ("DAX", "data_ig_cache/DEUIDXEUR_5m.csv"), ("FTSE", "data_ig_cache/GBRIDXGBP_5m.csv"), ("GOLD", "data_ig_cache/XAUUSD_5m.csv")):
        d, sp = ig(f)
        for mode in ("as tested", "vol-scaled"):
            t = run(d, mode, "ig", sp); allt[(m, mode)] = t; rows.append(summ(t, m, mode, str(d.index[0].date()))); print(rows[-1], flush=True)
    R = pd.DataFrame(rows); R.to_csv("runs/research/dk_v2_all_charts.csv", index=False)
    for mode in ("as tested", "vol-scaled"):
        alts = pd.concat([allt[(s, mode)] for s in ("ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT", "DOGEUSDT", "ADAUSDT", "LINKUSDT", "AVAXUSDT", "LTCUSDT")]).sort_index()
        r = summ(alts, "ALL 9 ALTCOINS pooled", mode, "2021"); print(r); R = pd.concat([R, pd.DataFrame([r])])
    R.to_csv("runs/research/dk_v2_all_charts.csv", index=False); pd.set_option("display.width", 250); print(R.to_string(index=False))
