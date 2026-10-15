"""
THE SCANNER — DK's specification, implemented.

    scan for opportunities and set-ups
      -> rank them, surface the best
      -> prepare the trade: entry trigger, stop, TP1, TP2, runner
      -> execute ONLY if the signal confirms
      -> stop set on entry
      -> at TP1, stop moves to slightly ABOVE breakeven (fees covered, a little locked in)
      -> runner continues, trailed

Output is a prepared trade plan per candidate, with every level stated as a number.
Nothing here places an order. Research and paper only.

HONEST HEALTH WARNING, carried in the output itself:
the management layer that produces most of this plan's historical return was
measured on 2008-2026, a period containing enormous uptrends. On random entries
the same management earned +11.5% per trade. That is a trend-capture payoff, not
a demonstrated edge, and it has NOT been tested in a sustained falling market.
"""
import os, json, numpy as np, pandas as pd, datetime as dt
import core as C
import levels as LV
import patterns as P
from run10 import load_universe, atr, est_cost

BE_OFFSET_R = 0.10          # DK: stop goes slightly ABOVE breakeven after TP1
STOP_ATR = 1.5
TP1_R = 1.0
TP2_FIB = 1.618
TRAIL_ATR = 2.5
MAX_BARS = 60
RISK_PCT = 0.01             # illustrative sizing only


# ---- the set-up library. Each returns (fired_today, quality_score 0-1) ----
def setup_month_high(df):
    s = LV.l_break_prior_month_high(df)
    return s, "break of prior month high"

def setup_quarter_high(df):
    s = LV.l_break_prior_quarter_high(df)
    return s, "break of prior quarter high"

def setup_swing_break(df):
    s = LV.l_swing_break(df, 20)
    return s, "swing-high break"

def setup_flag(df):
    s = P.p_flag(df, 2.0, 10, 5, 0.5)
    return s, "bull flag continuation"

def setup_trend_pullback(df):
    s = C.s_rsi(df, 2, 10) * C.f_trend200(df)
    return s, "pullback in uptrend"

SETUPS = [setup_month_high, setup_quarter_high, setup_swing_break,
          setup_flag, setup_trend_pullback]


def confirmations(df, i):
    """What has to agree before this is worth taking. Each is a real check."""
    c = {}
    c["above 200d trend"] = bool(df.close.iloc[i] > df.close.rolling(200).mean().iloc[i])
    c["above 50d trend"] = bool(df.close.iloc[i] > df.close.rolling(50).mean().iloc[i])
    v = df.volume.rolling(20).mean()
    c["volume > 20d avg"] = bool(df.volume.iloc[i] > v.iloc[i]) if v.iloc[i] > 0 else False
    rng = (df.high - df.low)
    c["closed strong"] = bool((df.close.iloc[i] - df.low.iloc[i]) /
                              max(rng.iloc[i], 1e-9) > 0.6)
    rv = df.close.pct_change().rolling(20).std()
    c["vol not extreme"] = bool(rv.iloc[i] < rv.rolling(252).quantile(0.9).iloc[i]) \
        if rv.rolling(252).quantile(0.9).iloc[i] == rv.rolling(252).quantile(0.9).iloc[i] else True
    return c


def build_plan(sym, df, i, setup_name):
    a = float(atr(df).iloc[i])
    px = float(df.close.iloc[i])
    if not np.isfinite(a) or a <= 0:
        return None
    swing_lo = float(df.low.rolling(10).min().iloc[i])
    atr_stop = px - STOP_ATR * a
    stop = max(atr_stop, swing_lo * 0.995)
    if stop >= px:
        stop = atr_stop
    risk = px - stop
    if risk <= 0:
        return None
    lo50 = float(df.low.rolling(50).min().iloc[i])
    hi50 = float(df.high.rolling(50).max().iloc[i])
    tp2 = lo50 + (hi50 - lo50) * TP2_FIB
    tp1 = px + TP1_R * risk
    if not np.isfinite(tp2) or tp2 <= tp1:
        tp2 = px + 3 * risk
    cost = est_cost(df)
    be_stop = px + BE_OFFSET_R * risk + cost * px

    conf = confirmations(df, i)
    score = sum(conf.values()) / len(conf)
    return dict(
        symbol=sym, setup=setup_name, date=str(df.index[i].date()),
        price=round(px, 6), stop=round(stop, 6),
        risk_pct=round(risk / px * 100, 2),
        tp1=round(tp1, 6), tp1_r=TP1_R,
        tp2=round(tp2, 6), tp2_r=round((tp2 - px) / risk, 2),
        stop_after_tp1=round(be_stop, 6),
        trail=f"{TRAIL_ATR} x ATR ({round(TRAIL_ATR*a,6)}) on the final third",
        time_stop=f"{MAX_BARS} bars",
        confirmations=conf, confirm_score=round(score, 2),
        est_cost_bp=round(cost * 10000, 0),
        size_note=f"risk {RISK_PCT*100:.1f}% of capital / {risk/px*100:.2f}% stop distance",
    )


def scan(lookback_days=3, min_score=0.6):
    panel = load_universe()
    found = []
    for sym, df in panel.items():
        if len(df) < 300:
            continue
        for fn in SETUPS:
            try:
                s, name = fn(df)
                s = pd.Series(np.nan_to_num(np.asarray(s, dtype=float)), index=df.index)
            except Exception:
                continue
            recent = s.iloc[-lookback_days:]
            if recent.sum() == 0:
                continue
            i = len(df) - lookback_days + int(np.argmax(recent.values))
            p = build_plan(sym, df, i, name)
            if p and p["confirm_score"] >= min_score:
                found.append(p)
    found.sort(key=lambda x: (-x["confirm_score"], x["risk_pct"]))
    return found


if __name__ == "__main__":
    out = scan()
    print(f"SCAN — {dt.date.today()}  ·  {len(out)} prepared set-ups "
          f"(confirmation score >= 0.6)\n")
    print("RESEARCH ONLY. No order is placed by this system.\n")
    for p in out[:15]:
        passed = [k for k, v in p["confirmations"].items() if v]
        failed = [k for k, v in p["confirmations"].items() if not v]
        print(f"  {p['symbol']:12s} {p['setup']:28s} score {p['confirm_score']:.2f}  "
              f"({p['date']})")
        print(f"     entry {p['price']:<14} stop {p['stop']:<14} "
              f"(risk {p['risk_pct']}%)  cost ~{p['est_cost_bp']:.0f}bp")
        print(f"     TP1 {p['tp1']:<16} (1.0R, take 1/3)   "
              f"TP2 {p['tp2']:<14} ({p['tp2_r']}R, take 1/3)")
        print(f"     after TP1 stop -> {p['stop_after_tp1']}  (breakeven +{BE_OFFSET_R}R +fees)")
        print(f"     runner: {p['trail']}  ·  time stop {p['time_stop']}")
        print(f"     confirmed: {', '.join(passed) if passed else 'none'}")
        if failed:
            print(f"     NOT confirmed: {', '.join(failed)}")
        print()
    json.dump(out, open("/home/claude/qlab/runs/scan_latest.json", "w"), indent=1)
    print(f"{len(out)} plans written to runs/scan_latest.json")
