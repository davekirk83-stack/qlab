"""
FOUR FAMILIES TAKEN FROM DK'S MARKET ADVISORY V19.1 PANEL (2026-10-15).

DK shared the Pine script as a curiosity and then said take anything useful.
Most of the score is built from components the library has already measured as
negatively signed (EMA stack, MACD, RSI, ADX/DMI), so the scoring aggregation
is not worth importing. Four things in it ARE genuinely absent from our library:

1. SESSION STRUCTURE. We have 11 element families and not one of them knows
   what time it is. Findings 82 and 84 just showed the US cash open carries a
   real, regime-conditional effect, so session state is a measured gap, not a
   guess. Asia/London/NY ranges, where price sits in them, which extremes have
   been taken, and whether the prior session's range is still standing.

2. NADARAYA-WATSON ENVELOPE. A kernel-regression band. We carry Bollinger and
   Keltner but no kernel smoother, and reversion is the only thing that has
   ever worked for us, so another reversion band is worth a look.
   *** THE PINE VERSION REPAINTS. *** It recomputes the whole window on
   barstate.islast with a symmetric kernel, so the fitted value at any
   historical bar uses bars that came after it. Read as history that is
   lookahead, and it is the same class of error that produced the false +2.64
   Sharpe in doc 25. Implemented here ONE-SIDED (causal endpoint estimate):
   only bars at or before t contribute to the fit at t.

3. LELEDC EXHAUSTION. Count consecutive closes above/below close[4], then
   require a new N-bar extreme plus a reversal candle. Exhaustion is our best
   positively-signed family (wr_exhaust_dn +0.0383), so a second, structurally
   different exhaustion measure is worth carrying.

4. CALENDAR / TURN OF MONTH. The panel carries a long-only end-of-month boost.
   The turn-of-month effect is one of the oldest documented anomalies and we
   have no calendar family at all. Costs nothing to measure.

Method identical to the rest of the library: IC is Spearman rank correlation
computed WITHIN each symbol then averaged; forward returns are demeaned per bar
across the panel to strip market drift; first half vs second half reported
separately; 20-bar horizon on hourly bars; trailing windows only.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd
from scipy import stats

PX = "/home/claude/qlab/data_1h_33"
HORIZON = 20


def atr(df, n=14):
    tr = pd.concat([df.high - df.low,
                    (df.high - df.close.shift()).abs(),
                    (df.low - df.close.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean().values


def nwe_causal(C, window=300, h=8.0, mult=3.0):
    """One-sided Nadaraya-Watson. The fit at t uses only t, t-1, ... t-window+1.
    w_j = exp(-j^2 / (2 h^2)) with j = how many bars BACK, so the kernel is
    truncated at the present bar rather than centred on it. No repaint."""
    n = len(C)
    j = np.arange(window)
    w = np.exp(-(j ** 2) / (2.0 * h * h))
    w /= w.sum()
    fit = np.full(n, np.nan)
    for t in range(window, n):
        fit[t] = np.dot(C[t - window + 1:t + 1][::-1], w)
    mae = pd.Series(np.abs(C - fit)).rolling(window).mean().values * mult
    return fit, mae


def build(df):
    """Session, NWE, Leledc and calendar elements. df needs a UTC DatetimeIndex."""
    C = df.close.values; H = df.high.values; L = df.low.values; O = df.open.values
    n = len(C); a = atr(df); a = np.where(a > 0, a, np.nan)
    f = {}
    idx = df.index
    hour = idx.hour.values
    dom = idx.day.values
    dow = idx.dayofweek.values
    day_id = (idx.normalize().astype("int64") // 86_400_000_000_000).values

    # ---------------------------------------------------- 1. SESSION STRUCTURE
    # Asia 00:00-07:59Z, London 07:00-15:59Z, NY 13:00-19:59Z (whole hours).
    def running_extremes(mask):
        """High/low of the CURRENT day's session so far; NaN before it opens.
        Strictly causal: at bar t only bars <= t of the same day are used."""
        hi = np.full(n, np.nan); lo = np.full(n, np.nan)
        ch = -np.inf; cl = np.inf; cur = -1
        for t in range(n):
            if day_id[t] != cur:
                cur = day_id[t]; ch = -np.inf; cl = np.inf
            if mask[t]:
                ch = max(ch, H[t]); cl = min(cl, L[t])
            if np.isfinite(ch) and ch > -np.inf:
                hi[t] = ch; lo[t] = cl
        return hi, lo

    m_asia = (hour >= 0) & (hour < 8)
    m_ldn = (hour >= 7) & (hour < 16)
    m_ny = (hour >= 13) & (hour < 20)
    ah, al = running_extremes(m_asia)
    lh, ll = running_extremes(m_ldn)

    with np.errstate(invalid="ignore", divide="ignore"):
        f["sess_asia_pos"] = (C - al) / np.where(ah > al, ah - al, np.nan)
        f["sess_to_asia_hi"] = (ah - C) / a
        f["sess_to_asia_lo"] = (C - al) / a
        f["sess_ldn_pos"] = (C - ll) / np.where(lh > ll, lh - ll, np.nan)
        f["sess_to_ldn_hi"] = (lh - C) / a
        f["sess_to_ldn_lo"] = (C - ll) / a
        f["sess_asia_range"] = (ah - al) / a
        f["sess_ldn_range"] = (lh - ll) / a
    # which extremes have been taken, and is the prior range still standing
    f["sess_took_asia_hi"] = ((H > ah) & m_ldn).astype(float)
    f["sess_took_asia_lo"] = ((L < al) & m_ldn).astype(float)
    f["sess_took_ldn_hi"] = ((H > lh) & m_ny).astype(float)
    f["sess_took_ldn_lo"] = ((L < ll) & m_ny).astype(float)
    f["sess_ldn_standing"] = (m_ny & (H <= lh) & (L >= ll)).astype(float)
    # sweep-and-reclaim, as a STATE not a trade (the panel uses it as a promoter)
    f["sess_asia_lo_reclaim"] = ((L < al) & (C > al) & m_ldn).astype(float)
    f["sess_asia_hi_reclaim"] = ((H > ah) & (C < ah) & m_ldn).astype(float)
    f["sess_ldn_lo_reclaim"] = ((L < ll) & (C > ll) & m_ny).astype(float)
    f["sess_ldn_hi_reclaim"] = ((H > lh) & (C < lh) & m_ny).astype(float)
    # which session are we in, and how far through it
    f["sess_in_ny"] = m_ny.astype(float)
    f["sess_in_ldn"] = m_ldn.astype(float)
    f["sess_in_asia"] = m_asia.astype(float)
    # the panel's NY lean: opens below London mid -> lean low
    with np.errstate(invalid="ignore"):
        f["sess_ny_lean"] = np.where(m_ny, C - (lh + ll) / 2.0, np.nan) / a

    # ---------------------------------------------------- 2. NWE (CAUSAL)
    fit, mae = nwe_causal(C)
    with np.errstate(invalid="ignore", divide="ignore"):
        f["nwe_pos"] = (C - fit) / np.where(mae > 0, mae, np.nan)
        f["nwe_dist_atr"] = (C - fit) / a
        f["nwe_width"] = mae / a
    f["nwe_lo_touch"] = ((L <= fit - mae) & (C > fit - mae)).astype(float)
    f["nwe_hi_touch"] = ((H >= fit + mae) & (C < fit + mae)).astype(float)

    # ---------------------------------------------------- 3. LELEDC
    c4 = pd.Series(C).shift(4).values
    bindex = np.zeros(n); sindex = np.zeros(n)
    for t in range(1, n):
        if np.isfinite(c4[t]):
            bindex[t] = bindex[t - 1] + 1 if C[t] > c4[t] else 0
            sindex[t] = sindex[t - 1] + 1 if C[t] < c4[t] else 0
    LB, LL_ = 6, 30
    lowest = pd.Series(L).rolling(LL_).min().values
    highest = pd.Series(H).rolling(LL_).max().values
    f["lele_bull"] = ((sindex > LB) & (C > O) & (L <= lowest)).astype(float)
    f["lele_bear"] = ((bindex > LB) & (C < O) & (H >= highest)).astype(float)
    f["lele_bindex"] = bindex
    f["lele_sindex"] = sindex
    f["lele_persist"] = bindex - sindex
    # distance to the most recent level of each kind, carried forward
    for nm, flag, lvl in (("lele_to_bull", f["lele_bull"], L),
                          ("lele_to_bear", f["lele_bear"], H)):
        s = pd.Series(np.where(flag > 0, lvl, np.nan)).ffill(limit=40).values
        with np.errstate(invalid="ignore"):
            f[nm] = (C - s) / a

    # ---------------------------------------------------- 4. CALENDAR
    last_dom = pd.Series(dom, index=idx).groupby(idx.to_period("M")).transform("max").values
    f["cal_turn_of_month"] = ((dom <= 3) | (dom >= last_dom - 1)).astype(float)
    f["cal_dom_pos"] = dom / last_dom
    f["cal_is_weekend"] = (dow >= 5).astype(float)
    f["cal_hour_sin"] = np.sin(2 * np.pi * hour / 24.0)
    f["cal_hour_cos"] = np.cos(2 * np.pi * hour / 24.0)
    return f


FAMILY = {"sess_": "session", "nwe_": "kernel_band",
          "lele_": "exhaustion2", "cal_": "calendar"}


def run():
    frames = {}
    for p in sorted(glob.glob(f"{PX}/*.csv")):
        s = os.path.basename(p)[:-4]
        d = pd.read_csv(p)
        d["dt"] = pd.to_datetime(d.date, utc=True)
        d = d.set_index("dt").sort_index()
        if len(d) < 1500: continue
        d["fwd"] = d.close.shift(-HORIZON) / d.close - 1
        frames[s] = d
    print(f"panel: {len(frames)} symbols, {HORIZON}-bar horizon on hourly bars")

    # demean forward returns per timestamp across the panel (strip market drift)
    fwd = pd.DataFrame({s: d.fwd for s, d in frames.items()})
    fwd = fwd.sub(fwd.mean(axis=1), axis=0)

    feats = {s: build(d) for s, d in frames.items()}
    names = sorted(set().union(*[set(v) for v in feats.values()]))

    rows = []
    for name in names:
        ics = []; h1 = []; h2 = []
        for s, F in feats.items():
            if name not in F: continue
            x = pd.Series(F[name], index=frames[s].index)
            y = fwd[s].reindex(x.index)
            m = np.isfinite(x) & np.isfinite(y)
            if m.sum() < 400 or x[m].nunique() < 3: continue
            ics.append(stats.spearmanr(x[m], y[m]).statistic)
            half = m.sum() // 2
            xa, ya = x[m].iloc[:half], y[m].iloc[:half]
            xb, yb = x[m].iloc[half:], y[m].iloc[half:]
            if xa.nunique() > 2: h1.append(stats.spearmanr(xa, ya).statistic)
            if xb.nunique() > 2: h2.append(stats.spearmanr(xb, yb).statistic)
        if len(ics) < 10: continue
        ics = np.array(ics)
        ic = np.nanmean(ics)
        t = ic / (np.nanstd(ics, ddof=1) / np.sqrt(len(ics)))
        agree = int((np.sign(ics) == np.sign(ic)).sum())
        fam = next((v for k, v in FAMILY.items() if name.startswith(k)), "other")
        rows.append(dict(name=name, family=fam, ic=ic, t=t,
                         agree=agree, total=len(ics),
                         ic_h1=np.nanmean(h1) if h1 else np.nan,
                         ic_h2=np.nanmean(h2) if h2 else np.nan))
    T = pd.DataFrame(rows).sort_values("ic", key=abs, ascending=False)
    T["stable"] = (np.sign(T.ic_h1) == np.sign(T.ic_h2)).astype(int)
    pd.set_option("display.width", 150)
    print()
    print(T.to_string(index=False,
          float_format=lambda v: f"{v:+.4f}" if abs(v) < 1 else f"{v:+.2f}"))
    T.to_csv("/home/claude/qlab/runs/elements_mktadv.csv", index=False)
    print("\nBENCHMARK from the existing 66-element library (same panel/horizon):")
    print("  best positive  ichi_thickness +0.0489 (t=10.69, 33/33)")
    print("  best negative  dist_ema_200   -0.0516 (t=-8.66, 32/33)")
    print("  anything inside +-0.02 is not competitive with what we already carry.")
    return T


if __name__ == "__main__":
    run()
