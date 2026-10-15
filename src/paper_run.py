"""
PAPER TRADING — the daily step.

Run once per trading day. It:
  1. refreshes daily bars for the universe
  2. advances every open position by one bar (both books)
  3. scans for new entries (LIVE) and draws frequency-matched random entries (SHADOW)
  4. applies SPEC screens and slot/heat/position caps
  5. marks both books to market and writes the journal

Places no orders. Holds no credentials. Writes JSON and nothing else.

The SHADOW book is the point. It takes random entries with identical management
on the same bars, so the market regime is controlled for by construction and the
measured quantity is LIVE minus SHADOW — whether the signals add anything —
rather than LIVE, which a rising market answers on its own.
"""
import os, json, time, datetime as dt
import numpy as np, pandas as pd
import requests
import SPEC, paper
from paper import load, save, plan_trade, step_position, mark, atr, report

WIDE = "/home/claude/qlab/data_wide"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
RNG = np.random.default_rng()

# Survivorship-clean ETFs only. The 69 single stocks in data_wide were selected
# by me knowing the outcome and must not be used for forward evidence (doc 28).
CLEAN = """SPY QQQ IWM DIA MDY IJR VTI VTV VUG MTUM QUAL USMV SPLV ACWI
XLK XLF XLE XLV XLI XLY XLP XLU XLB XLRE XLC
EFA EEM FXI EWJ EWZ EWG EWU INDA EWY EWT VGK
TLT IEF SHY LQD HYG AGG TIP BND EMB MUB
GLD SLV USO UNG DBA DBC CORN WEAT PPLT CPER URA
VNQ IYR VXX""".split()


def refresh(sym):
    """Pull the latest daily bars and merge into the local store."""
    try:
        r = requests.get(f"https://api.nasdaq.com/api/quote/{sym}/historical",
                         params=dict(assetclass="etf", fromdate="2006-01-01",
                                     todate=str(dt.date.today()), limit=99999),
                         headers={"User-Agent": UA, "Accept": "application/json"},
                         timeout=40)
        rows = r.json()["data"]["tradesTable"]["rows"]
    except Exception:
        return None

    def num(x):
        if x is None:
            return None
        x = str(x).replace("$", "").replace(",", "").strip()
        try:
            return float(x)
        except ValueError:
            return None
    df = pd.DataFrame([dict(date=q["date"], open=num(q.get("open")),
                            high=num(q.get("high")), low=num(q.get("low")),
                            close=num(q.get("close")),
                            volume=num(q.get("volume")) or 0.0) for q in rows])
    df["date"] = pd.to_datetime(df["date"], format="%m/%d/%Y", errors="coerce")
    df = df.dropna(subset=["date", "close"]).sort_values("date").drop_duplicates("date")
    return df if len(df) > 300 else None


def load_panel(do_refresh=True):
    panel = {}
    for s in CLEAN:
        p = f"{WIDE}/{s}.csv"
        df = None
        if do_refresh:
            df = refresh(s)
            if df is not None:
                df.to_csv(p, index=False)
                time.sleep(0.3)
        if df is None and os.path.exists(p):
            df = pd.read_csv(p, parse_dates=["date"])
        if df is None:
            continue
        df = df.set_index("date").sort_index()
        if len(df) > 300:
            panel[s] = df
    return panel


def est_cost(df):
    rng = ((df.high - df.low) / df.close).rolling(60).median().iloc[-1]
    return float(min(max(rng * 0.15, 0.0005), 0.01)) if rng == rng else 0.002


# ------------------------------------------------------------------- entries
def entry_signals(df):
    """SPEC.ENTRIES_KEPT only. Fires on the LAST bar or not at all."""
    out = []
    c, h, l = df.close, df.high, df.low
    i = len(df) - 1
    # month-high break
    pm = h.shift(1).rolling(21).max()
    if c.iloc[i] > pm.iloc[i] and c.iloc[i - 1] <= pm.iloc[i - 1]:
        out.append("month-high break")
    # pullback in uptrend
    ma200, ma50 = c.rolling(200).mean(), c.rolling(50).mean()
    d = c.diff()
    up = d.clip(lower=0).rolling(2).mean()
    dn = (-d.clip(upper=0)).rolling(2).mean()
    rsi2 = 100 - 100 / (1 + up / dn.replace(0, np.nan))
    if (c.iloc[i] > ma200.iloc[i]) and rsi2.iloc[i] < 10:
        out.append("pullback in uptrend")
    # flag: sharp rise, tight consolidation, break up
    rise = (c.iloc[i - 5] / c.iloc[i - 15] - 1) > 0.10 if i > 15 else False
    rngw = ((h.rolling(5).max() - l.rolling(5).min()) / c)
    tight = rngw.iloc[i - 1] < rngw.rolling(50).median().iloc[i - 1] * 0.8
    brk = c.iloc[i] > h.rolling(5).max().shift(1).iloc[i]
    if rise and tight and brk:
        out.append("flag")
    return out


def book_capacity(bk):
    heat = sum(p["risk_frac"] * p["notional_frac"] for p in bk["open"])
    return len(bk["open"]) < SPEC.MAX_OPEN and heat < SPEC.MAX_HEAT


def step(do_refresh=True):
    s = load()
    panel = load_panel(do_refresh)
    if not panel:
        print("no data — aborting, state untouched")
        return s
    today = max(df.index[-1] for df in panel.values())
    if s.get("last_bar") == str(today.date()):
        print(f"already processed {today.date()} — nothing to do")
        report(s)
        return s

    costs = {k: est_cost(v) for k, v in panel.items()}
    events = []

    # 1. advance open positions in both books
    for bname, bk in s["books"].items():
        still = []
        for p in bk["open"]:
            df = panel.get(p["sym"])
            if df is None or df.index[-1] <= pd.Timestamp(p["entry_date"]):
                still.append(p); continue
            bar = df.iloc[-1]
            done = step_position(p, dict(high=bar.high, low=bar.low,
                                         open=bar.open, close=bar.close))
            if done:
                net = p["pnl_r"] - p["cost"] * p["entry"] / (p["entry"] - p["stop"])
                bk["equity"] *= (1 + SPEC.RISK_PCT * net)
                bk["peak"] = max(bk["peak"], bk["equity"])
                p["exit_date"] = str(today.date())
                bk["closed"].append(p)
                events.append(f"{bname} CLOSE {p['sym']:6s} {net:+.2f}R  {p['exit_reason']}")
            else:
                still.append(p)
        bk["open"] = still

    # 2. LIVE entries
    live_fired = []
    for sym, df in panel.items():
        if len(df) < 250:
            continue
        for setup in entry_signals(df):
            live_fired.append((sym, setup))
    for sym, setup in live_fired:
        bk = s["books"]["LIVE"]
        if not book_capacity(bk):
            events.append(f"LIVE  SKIP  {sym:6s} {setup} — slots/heat full")
            continue
        if any(p["sym"] == sym for p in bk["open"]):
            continue
        p = plan_trade(sym, panel[sym], len(panel[sym]) - 1, setup,
                       bk["equity"], costs[sym])
        if p:
            bk["open"].append(p)
            events.append(f"LIVE  OPEN  {sym:6s} {setup} @ {p['entry']} "
                          f"stop {p['stop']} tp1 {p['tp1']}")

    # 3. SHADOW: frequency-matched random entries, same bar
    n = len(live_fired)
    if n:
        picks = RNG.choice(list(panel), size=min(n, len(panel)), replace=False)
        for sym in picks:
            bk = s["books"]["SHADOW"]
            if not book_capacity(bk):
                continue
            if any(p["sym"] == sym for p in bk["open"]):
                continue
            p = plan_trade(sym, panel[sym], len(panel[sym]) - 1, "RANDOM",
                           bk["equity"], costs[sym])
            if p:
                bk["open"].append(p)
                events.append(f"SHADOW OPEN {sym:6s} random @ {p['entry']}")

    # 4. mark to market
    for bname, bk in s["books"].items():
        unreal = sum(SPEC.RISK_PCT * mark(p, panel[p["sym"]].close.iloc[-1])
                     for p in bk["open"] if p["sym"] in panel)
        bk["marked_equity"] = bk["equity"] * (1 + unreal)

    s["last_bar"] = str(today.date())
    s["log"].append(dict(date=str(today.date()), events=events))
    s["log"] = s["log"][-120:]
    save(s)

    print(f"\nBAR {today.date()} — {len(events)} events")
    for e in events:
        print(f"  {e}")
    print()
    report(s)
    return s


if __name__ == "__main__":
    import sys
    step(do_refresh="--norefresh" not in sys.argv)
