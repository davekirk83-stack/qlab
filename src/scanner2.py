"""
THE SCANNER v2 — spec v1.1.

Changes from v1, each forced by a measured result rather than an opinion:

  1. TWO CONFIRMATION BLOCKS, not one. Doc 24 found every confirmation sign flips
     between momentum and mean-reversion setups. A single block applied to both
     was actively costing money on one of them.

  2. VOLATILITY FILTERS REMOVED FROM MOMENTUM. "vol not extreme" was the single
     most expensive item in the scanner: -159pp to -348pp annualised across the
     three breakout entries. Breakouts earn in violent conditions; screening
     those out removes the trades that pay. "in squeeze" likewise.

  3. NO GLOBAL VOLUME RULE. The pending instruction was to invert the volume
     check. Tested across four setups it runs -97pp to +40pp — there is no
     universal sign. It is now declared per setup, and where unmeasured it is
     reported but NOT scored.

  4. OPEN-INTEREST GATE (doc 23). A high-volume rally with OI RISING is fresh
     leveraged longs: -0.572% over 72h, 39.5% up. With OI FALLING it is short
     covering: +0.847%. Same-looking candle either way — only OI separates them.
     Longs are blocked on the first and favoured on the second.

  5. CAPACITY FILTER. The median trade implies ~11% of the account in a single
     name; in thin names that is unfillable. Position is now checked against
     median daily turnover and the plan is rejected or sized down.

  6. SQUEEZE AS A WATCHLIST STATE (doc 25), not a trigger. Bandwidth in its
     bottom decile forecasts a volatility expansion in 94% of instruments and
     says nothing about direction, so it flags "a move is coming" and the
     direction must come from the setup.

  7. SIZING 0.5% / max 4 open. Sharpe is flat ~1.9-2.1 across every sizing
     setting, so sizing is a leverage dial, not an edge. 1% / 8 open implies a
     70% drawdown, which nobody holds through.

Nothing here places an order. Research and paper only.
"""
import os, json, numpy as np, pandas as pd, datetime as dt
import core as C
import levels as LV
import patterns as P
from run10 import load_universe, atr, est_cost

# ---- spec v1.1 ----
BE_OFFSET_R = 0.10
STOP_ATR = 1.5
TP1_R = 1.0
TP2_FIB = 1.618
TRAIL_ATR = 2.5
MEAT_BARS = 5
RUNNER_BARS = 60
RISK_PCT = 0.005
MAX_OPEN = 4
MAX_CAPACITY = 0.05          # position may not exceed 5% of median daily turnover
OI_DIR = "/home/claude/qlab/data_oi"


# ------------------------------------------------------------------ setups
def setup_month_high(df):
    return LV.l_break_prior_month_high(df), "break of prior month high", "momentum"

def setup_quarter_high(df):
    return LV.l_break_prior_quarter_high(df), "break of prior quarter high", "momentum"

def setup_swing_break(df):
    return LV.l_swing_break(df, 20), "swing-high break", "momentum"

def setup_flag(df):
    return P.p_flag(df, 2.0, 10, 5, 0.5), "bull flag continuation", "momentum"

def setup_trend_pullback(df):
    return C.s_rsi(df, 2, 10) * C.f_trend200(df), "pullback in uptrend", "momentum"

def setup_pb_cross(df):
    ma = df.close.rolling(20).mean(); sd = df.close.rolling(20).std()
    up, lo = ma + 2 * sd, ma - 2 * sd
    pb = (df.close - lo) / (up - lo).replace(0, np.nan)
    return ((pb > 0.5) & (pb.shift(1) <= 0.5)).astype(float), "%B cross 0.5", "meanrev"

def setup_band_reversion(df):
    ma = df.close.rolling(20).mean(); sd = df.close.rolling(20).std()
    lo = ma - 2 * sd
    below = df.close < lo
    return (below.shift(1).fillna(False) & ~below).astype(float), \
           "lower-band reversion", "meanrev"

SETUPS = [setup_month_high, setup_quarter_high, setup_swing_break, setup_flag,
          setup_trend_pullback, setup_pb_cross, setup_band_reversion]

# measured per-setup volume sign (doc 24). None = unmeasured, report but do not score.
VOLUME_SIGN = {
    "break of prior month high": +1,
    "swing-high break":          -1,
    "%B cross 0.5":              +1,
    "lower-band reversion":      None,
    "break of prior quarter high": None,
    "bull flag continuation":    None,
    "pullback in uptrend":       None,
}


# ----------------------------------------------------------- indicators
def bandwidth(df, n=20, k=2.0):
    ma = df.close.rolling(n).mean(); sd = df.close.rolling(n).std()
    return ((ma + k * sd) - (ma - k * sd)) / ma.replace(0, np.nan)


def confirmations(df, i, setup_name, family):
    """Two blocks. Which checks apply, and their sign, depends on the family."""
    c, scored = {}, {}
    close, ma200 = df.close.iloc[i], df.close.rolling(200).mean().iloc[i]
    ma50 = df.close.rolling(50).mean().iloc[i]
    v20 = df.volume.rolling(20).mean().iloc[i]
    rng = max(df.high.iloc[i] - df.low.iloc[i], 1e-9)
    strong = (df.close.iloc[i] - df.low.iloc[i]) / rng > 0.6
    bw = bandwidth(df)
    sq = bool(bw.iloc[i] <= bw.rolling(252).quantile(0.25).iloc[i]) \
        if bw.rolling(252).quantile(0.25).iloc[i] == bw.rolling(252).quantile(0.25).iloc[i] else False
    rv = df.close.pct_change().rolling(20).std()
    calm = bool(rv.iloc[i] < rv.rolling(252).quantile(0.90).iloc[i]) \
        if rv.rolling(252).quantile(0.90).iloc[i] == rv.rolling(252).quantile(0.90).iloc[i] else True

    if family == "momentum":
        # trend filters earn +42 to +255pp. Volatility filters are REMOVED.
        scored["above 200d trend"] = bool(close > ma200)
        scored["above 50d trend"] = bool(close > ma50)
        scored["closed strong"] = bool(strong)
        c["(not scored) calm market"] = calm       # removed: -159 to -348pp
        c["(not scored) in squeeze"] = sq          # removed: -100 to -240pp
    else:
        # mean reversion: every sign flips. Trend filters HURT; vol filters HELP.
        scored["calm market"] = calm               # +63pp
        scored["in squeeze"] = sq                  # +58pp
        scored["closed strong"] = bool(strong)     # +33pp
        c["(not scored) above 200d"] = bool(close > ma200)   # -53pp if required

    sign = VOLUME_SIGN.get(setup_name)
    heavy = bool(df.volume.iloc[i] > v20) if v20 > 0 else False
    if sign == +1:
        scored["volume > 20d avg"] = heavy
    elif sign == -1:
        scored["volume BELOW 20d avg"] = not heavy
    else:
        c["(not scored, unmeasured) volume > 20d avg"] = heavy

    c.update(scored)
    score = sum(scored.values()) / max(len(scored), 1)
    return c, round(score, 2)


# ------------------------------------------------------------------- OI gate
_OI_CACHE = {}

def oi_state(sym):
    """Doc 23. Returns (verdict, note) from the most recent 24h of OI and price.
    Only the 8 symbols with archive OI are covered; everything else is 'no data'."""
    base = sym.replace("USD", "USDT") if sym.endswith("USD") else sym
    path = f"{OI_DIR}/{base}.csv"
    if base not in _OI_CACHE:
        if not os.path.exists(path):
            _OI_CACHE[base] = None
        else:
            d = pd.read_csv(path, parse_dates=["create_time"]).set_index("create_time")
            _OI_CACHE[base] = d.sort_index()
    d = _OI_CACHE[base]
    if d is None or len(d) < 600:
        return "no data", "no open-interest feed for this symbol"
    w = d.iloc[-288:]                       # last 24h at 5-min
    oi0, oi1 = w.sum_open_interest.iloc[0], w.sum_open_interest.iloc[-1]
    if not (oi0 > 0):
        return "no data", "bad OI values"
    oi_chg = oi1 / oi0 - 1
    px = w.sum_open_interest_value / w.sum_open_interest.replace(0, np.nan)
    px_chg = px.iloc[-1] / px.iloc[0] - 1
    if px_chg > 0 and oi_chg > 0.02:
        return "BLOCK", (f"price +{px_chg*100:.1f}% with OI +{oi_chg*100:.1f}% — fresh "
                         f"leveraged longs; this cell runs -0.572% / 72h")
    if px_chg > 0 and oi_chg < -0.02:
        return "FAVOUR", (f"price +{px_chg*100:.1f}% with OI {oi_chg*100:.1f}% — short "
                          f"covering; this cell runs +0.847% / 72h")
    if px_chg < 0 and oi_chg < -0.02:
        return "CAUTION", (f"price {px_chg*100:.1f}% with OI {oi_chg*100:.1f}% — long "
                           f"liquidation; this cell runs -0.478% / 72h")
    return "neutral", f"price {px_chg*100:+.1f}%, OI {oi_chg*100:+.1f}%"


# ------------------------------------------------------------------ the plan
def build_plan(sym, df, i, setup_name, family, equity=100_000.0):
    a = float(atr(df).iloc[i]); px = float(df.close.iloc[i])
    if not np.isfinite(a) or a <= 0 or px <= 0:
        return None
    swing_lo = float(df.low.rolling(10).min().iloc[i])
    stop = max(px - STOP_ATR * a, swing_lo * 0.995)
    if stop >= px:
        stop = px - STOP_ATR * a
    risk = px - stop
    if risk <= 0:
        return None
    lo50, hi50 = float(df.low.rolling(50).min().iloc[i]), float(df.high.rolling(50).max().iloc[i])
    tp2 = lo50 + (hi50 - lo50) * TP2_FIB
    tp1 = px + TP1_R * risk
    if not np.isfinite(tp2) or tp2 <= tp1:
        tp2 = px + 3 * risk
    cost = est_cost(df)

    conf, score = confirmations(df, i, setup_name, family)
    oi_verdict, oi_note = oi_state(sym)

    # ---- capacity ----
    notional = equity * RISK_PCT / (risk / px)
    turnover = float((df.close * df.volume).rolling(20).median().iloc[i])
    cap_share = notional / turnover if turnover and turnover > 0 else np.nan
    if np.isfinite(cap_share) and cap_share > MAX_CAPACITY:
        cap_ok, cap_note = False, (f"position £{notional:,.0f} = {cap_share*100:.1f}% of "
                                   f"median daily turnover (limit {MAX_CAPACITY*100:.0f}%) "
                                   f"— REJECTED, unfillable")
    elif not np.isfinite(cap_share):
        cap_ok, cap_note = True, "no volume data — capacity unverified"
    else:
        cap_ok, cap_note = True, (f"position £{notional:,.0f} = {cap_share*100:.2f}% of "
                                  f"median daily turnover — fillable")

    bw = bandwidth(df)
    q = bw.rolling(252).quantile(0.10).iloc[i]
    watch = bool(bw.iloc[i] <= q) if q == q else False

    return dict(
        symbol=sym, setup=setup_name, family=family, date=str(df.index[i].date()),
        price=round(px, 6), stop=round(stop, 6), risk_pct=round(risk / px * 100, 2),
        tp1=round(tp1, 6), tp1_r=TP1_R, tp2=round(tp2, 6), tp2_r=round((tp2 - px) / risk, 2),
        stop_after_tp1=round(px + BE_OFFSET_R * risk + cost * px, 6),
        trail=f"{TRAIL_ATR} x ATR ({round(TRAIL_ATR*a,6)}) on the final third",
        meat_time_stop=f"{MEAT_BARS} bars", runner_time_stop=f"{RUNNER_BARS} bars",
        confirmations=conf, confirm_score=score,
        oi_verdict=oi_verdict, oi_note=oi_note,
        capacity_ok=cap_ok, capacity_note=cap_note,
        squeeze_watch=watch,
        est_cost_bp=round(cost * 10000, 0),
        size_note=f"risk {RISK_PCT*100:.2f}% of capital, max {MAX_OPEN} open",
    )


def scan(lookback_days=3, min_score=0.6, equity=100_000.0):
    panel = load_universe()
    found, blocked = [], []
    for sym, df in panel.items():
        if len(df) < 300:
            continue
        for fn in SETUPS:
            try:
                s, name, fam = fn(df)
                s = pd.Series(np.nan_to_num(np.asarray(s, dtype=float)), index=df.index)
            except Exception:
                continue
            recent = s.iloc[-lookback_days:]
            if recent.sum() == 0:
                continue
            i = len(df) - lookback_days + int(np.argmax(recent.values))
            p = build_plan(sym, df, i, name, fam, equity)
            if not p:
                continue
            if p["confirm_score"] < min_score:
                continue
            if not p["capacity_ok"]:
                blocked.append(p); continue
            if p["oi_verdict"] == "BLOCK":
                blocked.append(p); continue
            found.append(p)
    rank = {"FAVOUR": 0, "neutral": 1, "no data": 2, "CAUTION": 3}
    found.sort(key=lambda x: (rank.get(x["oi_verdict"], 2), -x["confirm_score"], x["risk_pct"]))
    return found, blocked


if __name__ == "__main__":
    out, blocked = scan()
    print(f"SCAN v2 — {dt.date.today()}  ·  spec v1.1")
    print(f"  {len(out)} prepared set-ups, {len(blocked)} rejected by the OI gate "
          f"or capacity filter")
    print("  RESEARCH ONLY. No order is placed by this system.\n")
    for p in out[:12]:
        passed = [k for k, v in p["confirmations"].items() if v and not k.startswith("(")]
        failed = [k for k, v in p["confirmations"].items() if not v and not k.startswith("(")]
        print(f"  {p['symbol']:12s} {p['setup']:28s} [{p['family']}] "
              f"score {p['confirm_score']:.2f}  ({p['date']})")
        print(f"     entry {p['price']:<13} stop {p['stop']:<13} "
              f"(risk {p['risk_pct']}%)  cost ~{p['est_cost_bp']:.0f}bp")
        print(f"     TP1 {p['tp1']:<15} (1.0R, 1/3)   TP2 {p['tp2']:<13} ({p['tp2_r']}R, 1/3)")
        print(f"     after TP1 stop -> {p['stop_after_tp1']}   runner: {p['trail']}")
        print(f"     time stops: meat {p['meat_time_stop']}, runner {p['runner_time_stop']}")
        print(f"     OI: {p['oi_verdict']} — {p['oi_note']}")
        print(f"     capacity: {p['capacity_note']}")
        if p["squeeze_watch"]:
            print(f"     SQUEEZE: bandwidth in bottom decile — expansion approaching")
        print(f"     confirmed: {', '.join(passed) if passed else 'none'}")
        if failed:
            print(f"     not confirmed: {', '.join(failed)}")
        print()
    if blocked:
        print(f"  REJECTED ({len(blocked)}):")
        for p in blocked[:8]:
            why = p["oi_note"] if p["oi_verdict"] == "BLOCK" else p["capacity_note"]
            print(f"    {p['symbol']:12s} {p['setup']:26s} — {why}")
    os.makedirs("/home/claude/qlab/runs", exist_ok=True)
    json.dump(dict(taken=out, rejected=blocked),
              open("/home/claude/qlab/runs/scan_v2.json", "w"), indent=1)
    print(f"\n{len(out)} plans + {len(blocked)} rejections -> runs/scan_v2.json")
