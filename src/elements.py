"""
THE ELEMENT LIBRARY — what the top indicators are actually MADE of.

DK: "Assess the top 100 indicators on TradingView to establish which elements
of these actually work the best, rather than telling me what doesn't work. If
there is a novel way to combine elements that would be interesting."

THE DESIGN
A hundred indicators are not a hundred ideas. They are a few dozen primitive
computations recombined. RSI, Stochastic, CCI, Williams %R and MFI are all
"where does price sit in its recent range" with different scaling. MACD is a
difference of two smoothers. Supertrend is an ATR band that ratchets. Bollinger
%B is distance from a volatility band.

So: decompose into PRIMITIVES, and score each primitive directly.

WHY INFORMATION COEFFICIENT, NOT A BACKTEST
A trade simulation throws away most of a signal's information by reducing it to
a binary threshold, and then the result depends on the exit rule you picked.
The IC — rank correlation between the element's value now and the return later
— measures predictive content continuously, with no exit, no stop, no threshold
to tune. Everything that has gone wrong in this programme came from the parts
IC does not have.

HOW IT IS KEPT HONEST
  per-symbol  IC is computed WITHIN each instrument, then averaged. A factor
              cannot win by sorting good coins from bad ones.
  demeaned    forward returns are demeaned per bar across the panel, which
              removes market-wide drift — the thing that has flattered half the
              results in this programme.
  split       first half vs second half, reported separately. An element that
              only works in one is not an element, it is a regime.
  horizons    1, 5, 20 bars. An element strong at one horizon and absent at the
              others is usually noise.
  no lookahead  every element uses trailing windows only.

Then the combination question: among elements that predict, which are
UNCORRELATED with each other? Two momentum elements agreeing is one element
counted twice. Momentum + structure + flow agreeing is three.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd


# --------------------------------------------------------------- primitives
def _ema(x, n): return pd.Series(x).ewm(span=n, adjust=False).mean().values
def _sma(x, n): return pd.Series(x).rolling(n).mean().values
def _std(x, n): return pd.Series(x).rolling(n).std().values


def atr(df, n=14):
    tr = pd.concat([df.high - df.low,
                    (df.high - df.close.shift()).abs(),
                    (df.low - df.close.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean().values


def build(df):
    """Every primitive element, as a dict of arrays. ~45 features."""
    C = df.close.values; H = df.high.values; L = df.low.values; O = df.open.values
    V = df.volume.values if "volume" in df.columns else np.full(len(C), np.nan)
    n = len(C); a = atr(df); a = np.where(a > 0, a, np.nan)
    f = {}

    # --- POSITION IN RANGE (RSI, Stoch, Williams %R, CCI all live here) ---
    for w in (14, 50, 200):
        lo = pd.Series(L).rolling(w).min().values
        hi = pd.Series(H).rolling(w).max().values
        f[f"range_pos_{w}"] = (C - lo) / np.where(hi > lo, hi - lo, np.nan)
    d = np.diff(C, prepend=C[0])
    for w in (14, 50):
        up = pd.Series(np.where(d > 0, d, 0)).ewm(alpha=1/w, adjust=False).mean().values
        dn = pd.Series(np.where(d < 0, -d, 0)).ewm(alpha=1/w, adjust=False).mean().values
        f[f"rsi_{w}"] = 100 - 100 / (1 + up / np.where(dn > 0, dn, 1e-9))

    # --- TREND / SMOOTHER DISTANCE (EMA, SMA, MACD, Ichimoku baseline) ---
    for w in (20, 50, 200):
        f[f"dist_ema_{w}"] = (C - _ema(C, w)) / a
    f["macd"] = (_ema(C, 12) - _ema(C, 26)) / a
    f["macd_hist"] = (_ema(C, 12) - _ema(C, 26) - _ema(_ema(C, 12) - _ema(C, 26), 9)) / a
    f["ema_spread"] = (_ema(C, 20) - _ema(C, 50)) / a

    # --- SLOPE and ACCELERATION ---
    for w in (10, 50):
        f[f"slope_{w}"] = (C - np.roll(C, w)) / a
        f[f"slope_{w}"][:w] = np.nan
    f["accel"] = f["slope_10"] - np.roll(f["slope_10"], 10)
    f["accel"][:20] = np.nan

    # --- VOLATILITY (Bollinger %B, BB width, ATR regime, Keltner) ---
    for w in (20, 50):
        m = _sma(C, w); s = _std(C, w)
        f[f"bb_pctb_{w}"] = (C - m) / np.where(s > 0, 2 * s, np.nan)
        f[f"bb_width_{w}"] = (2 * s) / np.where(m > 0, m, np.nan)
    f["atr_pct"] = a / C
    f["atr_regime"] = a / pd.Series(a).rolling(200).mean().values
    f["keltner_pos"] = (C - _ema(C, 20)) / np.where(a > 0, 2 * a, np.nan)

    # --- BAR SHAPE (candlesticks reduce to these three) ---
    rng = np.where(H > L, H - L, np.nan)
    f["close_in_bar"] = (C - L) / rng
    f["body_frac"] = np.abs(C - O) / rng
    f["upper_wick"] = (H - np.maximum(C, O)) / rng
    f["lower_wick"] = (np.minimum(C, O) - L) / rng
    f["gap"] = (O - np.roll(C, 1)) / a; f["gap"][0] = np.nan

    # --- VOLUME (OBV, CMF, MFI, Force Index reduce to these) ---
    if np.isfinite(V).any():
        vz = V / pd.Series(V).rolling(50).mean().values
        f["vol_rel"] = vz
        f["obv_slope"] = (pd.Series(np.sign(d) * V).rolling(20).sum().values
                          / pd.Series(V).rolling(20).sum().values)
        f["force"] = (d / a) * vz
        mfm = ((C - L) - (H - C)) / rng
        f["cmf"] = (pd.Series(mfm * V).rolling(20).sum().values
                    / pd.Series(V).rolling(20).sum().values)
        tp = (H + L + C) / 3
        vw = (pd.Series(tp * V).rolling(72).sum().values
              / pd.Series(V).rolling(72).sum().values)
        f["dist_vwap72"] = (C - vw) / a

    # --- STRUCTURE (distance to recent extremes; Donchian, S/R) ---
    for w in (50, 200):
        hi = pd.Series(H).rolling(w).max().values
        lo = pd.Series(L).rolling(w).min().values
        f[f"to_high_{w}"] = (hi - C) / a
        f[f"to_low_{w}"] = (C - lo) / a


    # --- ICHIMOKU, AS STATE (doc 58) -----------------------------------
    # Decomposed into components and scored individually. The CLOUD carries
    # real information as a position measure (IC 0.03-0.05, t in double
    # digits on crypto hourly); the TK CROSS everyone trades is worth -0.004.
    # So the cloud enters the library and the signals do not.
    # Causal throughout: the standard Ichimoku plots the cloud 26 bars AHEAD,
    # which is a lookahead bug if read naively. Here Span A and B are the
    # values computed from data available NOW, not shifted forward.
    def _mid(w):
        return (pd.Series(H).rolling(w).max().values
                + pd.Series(L).rolling(w).min().values) / 2
    tenkan = _mid(9); kijun = _mid(26)
    span_a = (tenkan + kijun) / 2
    span_b = _mid(52)
    ctop = np.maximum(span_a, span_b)
    cbot = np.minimum(span_a, span_b)
    f["ichi_cloud_bull"] = np.sign(span_a - span_b)
    f["ichi_above_cbot"] = (C - cbot) / a
    f["ichi_to_ctop"] = (ctop - C) / a
    f["ichi_vs_cloud"] = np.where(C > ctop, 1.0,
                                  np.where(C < cbot, -1.0, 0.0))
    f["ichi_tk_spread"] = (tenkan - kijun) / a
    f["ichi_thickness"] = (ctop - cbot) / a


    # --- FROM DK'S TRADINGVIEW SOURCES (2026-10-15) ---------------------
    # Five from the "top 10" lists that the library genuinely did not cover.
    # Each reduced to the computation underneath the plot.
    # WaveTrend (LazyBear): deviation of price from its EMA, normalised by
    # mean absolute deviation, then smoothed. A scaled distance-from-trend.
    _tp = (H + L + C) / 3
    _esa = _ema(_tp, 10)
    _d = _ema(np.abs(_tp - _esa), 10)
    _ci = (_tp - _esa) / np.where(_d > 0, 0.015 * _d, np.nan)
    f["wavetrend"] = _ema(_ci, 21)
    f["wavetrend_diff"] = f["wavetrend"] - _sma(f["wavetrend"], 4)
    # Pi Cycle: the 111-bar mean against twice the 350-bar mean. Built for
    # BTC daily tops; measured here as a continuous ratio, not a cross.
    f["pi_ratio"] = _sma(C, 111) / np.where(_sma(C, 350) > 0,
                                            2 * _sma(C, 350), np.nan)
    # RCI (Rank Correlation Index): Spearman correlation of price against
    # time over the window. A RANK-based trend measure, which is a different
    # object from every other trend element here and fits the IC method.
    for w in (26, 52):
        sr = pd.Series(C)
        f[f"rci_{w}"] = sr.rolling(w).apply(
            lambda v: 1 - 6 * np.sum((np.arange(len(v)) -
                        pd.Series(v).rank().values + 1) ** 2)
                        / (len(v) * (len(v) ** 2 - 1)), raw=False).values
    # True Strength Index: double-smoothed momentum over double-smoothed
    # absolute momentum. Not the same as MACD, which is a difference of means.
    _m = np.diff(C, prepend=C[0])
    f["tsi"] = (_ema(_ema(_m, 25), 13)
                / np.where(_ema(_ema(np.abs(_m), 25), 13) > 0,
                           _ema(_ema(np.abs(_m), 25), 13), np.nan))
    # Stochastic RSI: where RSI sits in ITS OWN recent range. A second-order
    # transform, not the same as range_pos of price.
    _r = f["rsi_14"]
    _rl = pd.Series(_r).rolling(14).min().values
    _rh = pd.Series(_r).rolling(14).max().values
    f["stoch_rsi"] = (_r - _rl) / np.where(_rh > _rl, _rh - _rl, np.nan)


    # --- FROM DK'S REDDIT TOP-10 (2026-10-15) --------------------------
    # Four the library genuinely lacked, each reduced to its computation.
    # %R TREND EXHAUSTION (upslidedown). The author's #1: "insane at catching
    # tops/bottoms and countertrend trading, 1m-1h". Williams %R alone is just
    # range position, which the library has. The NEW object is the AGREEMENT
    # of several %R lengths at an extreme — exhaustion is many lookbacks
    # calling the same thing at once, not one of them calling it.
    _wr = {}
    for w in (14, 21, 34, 55, 89):
        hi = pd.Series(H).rolling(w).max().values
        lo = pd.Series(L).rolling(w).min().values
        _wr[w] = (C - lo) / np.where(hi > lo, hi - lo, np.nan)
    _stack = np.vstack([_wr[w] for w in _wr])
    f["wr_exhaust_up"] = np.nanmean(_stack >= 0.8, axis=0)
    f["wr_exhaust_dn"] = np.nanmean(_stack <= 0.2, axis=0)
    f["wr_exhaust"] = f["wr_exhaust_up"] - f["wr_exhaust_dn"]
    f["wr_agree"] = np.nanstd(_stack, axis=0)        # low = all lengths agree
    # WILLIAMS VIX FIX (chrismoody) — a synthetic VIX from price alone:
    # how far below the recent high the current low sits. Built for bottoms.
    for w in (22, 50):
        hh = pd.Series(C).rolling(w).max().values
        f[f"vix_fix_{w}"] = (hh - L) / np.where(hh > 0, hh, np.nan) * 100
    # HULL MA — a low-lag smoother: WMA(2*WMA(n/2) - WMA(n), sqrt(n)).
    def _wma(x, n):
        w = np.arange(1, n + 1, dtype=float)
        return pd.Series(x).rolling(n).apply(
            lambda v: np.dot(v, w) / w.sum(), raw=True).values
    _h1 = _wma(C, 8); _h2 = _wma(C, 16)
    f["hull_dist"] = (C - _wma(2 * _h1 - _h2, 4)) / a
    # LAGUERRE FILTER (donovanwall) — a 4-pole recursive low-lag smoother.
    g = 0.7
    L0 = np.zeros(n); L1 = np.zeros(n); L2 = np.zeros(n); L3 = np.zeros(n)
    for t in range(1, n):
        L0[t] = (1 - g) * C[t] + g * L0[t - 1]
        L1[t] = -g * L0[t] + L0[t - 1] + g * L1[t - 1]
        L2[t] = -g * L1[t] + L1[t - 1] + g * L2[t - 1]
        L3[t] = -g * L2[t] + L2[t - 1] + g * L3[t - 1]
    f["laguerre_dist"] = (C - (L0 + 2 * L1 + 2 * L2 + L3) / 6) / a


    # --- FROM THE LUXALGO LIBRARY (2026-10-15) -------------------------
    # Two genuine gaps. Their "Churn" is our absorption measure and their
    # "Dead Cat Bounce" (a drop of >=3 ATR) is our cascade under Bulkowski's
    # name — both already covered. These two were not.
    # NR4 / NR7 — narrowest range in 4 or 7 bars. Doc 57 found COMPRESSION
    # (Bollinger width) the strongest element in the library; NR is a cleaner,
    # scale-free statement of the same thing and costs nothing to carry.
    _rng = H - L
    for w in (4, 7):
        f[f"nr{w}"] = (pd.Series(_rng).rolling(w).min().values
                       >= _rng - 1e-12).astype(float)
    f["range_pctile_50"] = pd.Series(_rng).rolling(50, min_periods=20)\
        .apply(lambda v: (v[-1] > v[:-1]).mean(), raw=True).values
    # VOLUME PROFILE — point of control and value area. These are the levels
    # institutions actually reference and the library had no volume-by-price
    # at all; every structure element so far has been time-based.
    if np.isfinite(V).any():
        _poc = np.full(n, np.nan); _vah = np.full(n, np.nan); _val = np.full(n, np.nan)
        W = 200
        for t in range(W, n):
            px = C[t - W:t]; vol = V[t - W:t]
            if not np.isfinite(vol).any() or px.max() <= px.min():
                continue
            bins = np.linspace(px.min(), px.max(), 25)
            idx = np.clip(np.digitize(px, bins) - 1, 0, 23)
            prof = np.bincount(idx, weights=np.nan_to_num(vol), minlength=24)
            k = int(np.argmax(prof))
            _poc[t] = (bins[k] + bins[min(k + 1, 24)]) / 2
            order = np.argsort(prof)[::-1]
            tot = prof.sum(); acc = 0.0; keep = []
            for o in order:
                acc += prof[o]; keep.append(o)
                if acc >= 0.7 * tot: break
            _vah[t] = bins[min(max(keep) + 1, 24)]
            _val[t] = bins[min(keep)]
        f["dist_poc"] = (C - _poc) / a
        f["vp_position"] = (C - _val) / np.where(_vah > _val, _vah - _val, np.nan)

    # --- MEAN-REVERSION PRESSURE ---
    for w in (5, 20):
        r = pd.Series(C).pct_change(w).values
        f[f"ret_{w}"] = r / (pd.Series(C).pct_change().rolling(100).std().values * np.sqrt(w))
    f["dd_from_high_200"] = (C / pd.Series(H).rolling(200).max().values - 1)

    # --- DIVERGENCE (price vs momentum, the one TGX is built on) ---
    r14 = f["rsi_14"]
    for w in (20, 50):
        pr = pd.Series(C).pct_change(w).values
        mr = pd.Series(r14).diff(w).values
        f[f"divergence_{w}"] = np.sign(pr) * (np.sign(pr) != np.sign(mr)) * np.abs(mr) / 10.0
    return f


FEATURE_FAMILY = {
    "range_pos": "momentum", "rsi": "momentum", "ret_": "momentum",
    "dist_ema": "trend", "macd": "trend", "ema_spread": "trend", "slope": "trend",
    "accel": "trend",
    "bb_pctb": "volatility", "bb_width": "volatility", "atr": "volatility",
    "keltner": "volatility",
    "close_in_bar": "bar_shape", "body_frac": "bar_shape", "upper_wick": "bar_shape",
    "lower_wick": "bar_shape", "gap": "bar_shape",
    "vol_rel": "volume", "obv": "volume", "force": "volume", "cmf": "volume",
    "dist_vwap": "volume",
    "to_high": "structure", "to_low": "structure", "dd_from_high": "structure",
    "divergence": "divergence",
    "ichi_": "ichimoku",
    "wavetrend": "oscillator", "pi_ratio": "trend", "rci_": "trend",
    "tsi": "momentum", "stoch_rsi": "momentum",
    "wr_exhaust": "exhaustion", "wr_agree": "exhaustion",
    "vix_fix": "volatility", "hull_dist": "trend", "laguerre_dist": "trend",
    "nr4": "volatility", "nr7": "volatility", "range_pctile": "volatility",
    "dist_poc": "volume_profile", "vp_position": "volume_profile",
    "liq_": "liquidation", "oi_": "liquidation", "taker_": "liquidation",
}


def family(name):
    for k, v in FEATURE_FAMILY.items():
        if name.startswith(k):
            return v
    return "other"
