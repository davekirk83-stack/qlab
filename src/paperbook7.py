"""
THE PAPER BOOK v7 — "Ignition v1" on Nasdaq-100 (registered 19 Oct 2026, doc 92, finding 157).
AuclairsDad's engine as read off his own panel (doc 90), the row that held on 12 months:
  IGNITION    5-min bar range >= 1.25 x the average of the prior 20 bars
  DELTA SHARE |bar delta| / bar activity >= 0.05, its sign is the direction (tick-rule delta from
              Dukascopy ticks; activity = tick count)
  HTF         EMA20 vs EMA50 on the 5-min bars (completed), direction must agree; candle agrees
  (no coil requirement — the coil only thinned it: doc 92)
EXIT (his stack): stop 45 pts -> breakeven at +15 -> trail 1 ATR(20) -> target 9 ATR, cap 36 bars.
GOVERNORS: max 8 trades/day, 3-bar cooloff after an exit, daily loss cap 200 pts, all sessions.
COST: half the quoted CFD spread each way (~1.1 pts round trip; his future ~0.5).
LEDGER: 1 MNQ-equivalent contract, $2 per point, $2,000 start. SIMULATED ONLY (CAP-021).
SHADOW: for every real entry, 5 random completed bars from the trailing 30 days, same side, same
exit stack. The verdict is REAL minus SHADOW (rule 161). PASS: real > shadow at 300 trades.

ANTI-LEAK (his step 11): the book is a FULL REPLAY from its start date over the committed 5-minute
cache every day — no incremental state can drift from what a recalc would give. Decisions use closed
bars only; the last 36 bars are left open (a trade still running is reported as open, not booked).
DATA: Dukascopy USATECHIDXUSD ticks -> data_nq_cache/nq_5m.csv (committed). Each run pulls the
missing days (yesterday's Globex day is complete by 07:23 London), appends, replays.
"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, json, glob
import numpy as np, pandas as pd
sys.path.insert(0, "/home/claude/qlab/src")
ROOT = os.environ.get("QLAB_ROOT", "/home/claude/qlab"); RUNS = f"{ROOT}/runs"; CACHE = f"{ROOT}/data_nq_cache"
if os.access(os.path.dirname(ROOT) if os.path.exists(os.path.dirname(ROOT)) else "/", os.W_OK): os.makedirs(CACHE, exist_ok=True); os.makedirs(RUNS, exist_ok=True)
STATE = f"{RUNS}/paper7_state.json"; BARS = f"{CACHE}/nq_5m.csv"
START_DATE = "2026-10-19"; START = 2000.0; PT = 2.0
IGN, DSHARE = 1.25, 0.05
STOP, BE, TRAIL_ATR, TGT_ATR, CAP = 45.0, 15.0, 1.0, 9.0, 36
MAXT, COOL, LOSSCAP = 8, 3, 200.0
NCTRL = 5


def halted():
    try:
        h = json.load(open(f"{RUNS}/HALT.json"))
        if int(h.get("active", 0)) != 1: return None
        ra = h.get("resume_after")
        if ra and pd.Timestamp(ra) < pd.Timestamp.utcnow().tz_localize(None): return None
        return h
    except Exception: return None


def pull_missing(bars):
    """Fetch complete Globex days missing from the cache (Dukascopy, per hour, LZMA) and append 5-min bars."""
    import get_nq_ticks as G
    last = bars.index.max() if len(bars) else pd.Timestamp("2025-10-14", tz="UTC")
    today = pd.Timestamp.utcnow().normalize().tz_localize("UTC") if pd.Timestamp.utcnow().tz is None else pd.Timestamp.utcnow().normalize()
    days = [d.date() for d in pd.date_range((last + pd.Timedelta(days=1)).normalize(), today - pd.Timedelta(days=1)) if d.weekday() != 5]
    new = []
    for d in days:
        parts = [p for p in map(G.fetch_hour, [(d, h) for h in range(24)]) if p is not None]
        if not parts: continue
        t = pd.concat(parts).sort_values("ts"); t["mid"] = (t.ask + t.bid)/2
        sgn = np.sign(t.mid.diff().fillna(0).values)
        for i in range(1, len(sgn)):
            if sgn[i] == 0: sgn[i] = sgn[i-1]
        t["sgn"] = sgn; t = t.set_index("ts"); t.index = t.index.tz_localize("UTC")
        b = pd.DataFrame({"open": t.mid.resample("5min").first(), "high": t.mid.resample("5min").max(), "low": t.mid.resample("5min").min(), "close": t.mid.resample("5min").last(),
                          "vol": t.mid.resample("5min").count(), "delta": (t.sgn > 0).resample("5min").sum() - (t.sgn < 0).resample("5min").sum(),
                          "spread": (t.ask - t.bid).resample("5min").mean()}).dropna(subset=["close"])
        new.append(b); print(f"  pulled {d}: {len(b)} bars", flush=True)
    if new:
        bars = pd.concat([bars] + new); bars = bars[~bars.index.duplicated(keep="last")].sort_index(); bars.to_csv(BARS)
    return bars


def features(d):
    d = d.copy()
    tr = np.maximum(d.high - d.low, np.maximum((d.high - d.close.shift()).abs(), (d.low - d.close.shift()).abs()))
    d["atr"] = tr.rolling(20).mean().shift(1); d["rng"] = d.high - d.low
    d["ign"] = d.rng/d.rng.shift(1).rolling(20).mean(); d["dshare"] = d.delta/d.vol.replace(0, np.nan)
    d["ef"] = d.close.ewm(span=20, adjust=False).mean(); d["es"] = d.close.ewm(span=50, adjust=False).mean(); d["htf"] = np.sign(d.ef - d.es).shift(1)
    d["cost"] = d.spread/2; d["day"] = d.index.floor("D")
    d["sig"] = 0
    d.loc[(d.ign >= IGN) & (d.dshare >= DSHARE) & (d.close > d.open) & (d.htf == 1), "sig"] = 1
    d.loc[(d.ign >= IGN) & (d.dshare <= -DSHARE) & (d.close < d.open) & (d.htf == -1), "sig"] = -1
    return d


def manage(O, H, L, C, cost, atr, i, s, n):
    """Returns (pts, bars, how) or None if the trade is still open at the end of data."""
    e = O[i+1] + s*cost[i+1]; stop = e - s*STOP; tgt = e + s*TGT_ATR*atr[i]; best = e; be = False
    pts = lambda px: s*(px - e) - cost[i+1]
    for j in range(i+1, min(i+CAP+1, n)):
        fav = H[j] if s == 1 else L[j]; adv = L[j] if s == 1 else H[j]
        if (s == 1 and adv <= stop) or (s == -1 and adv >= stop): return pts(stop), j-i, "be" if be else "stop"
        if (s == 1 and fav >= tgt) or (s == -1 and fav <= tgt): return pts(tgt), j-i, "target"
        best = max(best, fav) if s == 1 else min(best, fav)
        if not be and s*(best - e) >= BE: be = True; stop = e + s*cost[i+1]*2
        if be:
            t = best - s*TRAIL_ATR*atr[i]
            if (s == 1 and t > stop) or (s == -1 and t < stop): stop = t
    if i + CAP + 1 <= n - 1: return pts(C[i+CAP]), CAP, "cap"
    return None


US_OPEN, US_CLOSE = 13*60+30, 20*60   # UTC minutes; the IG candidate (doc 100 Phase 0): entries only in US cash hours


def replay(d, start, flatten, us_hours=False):
    O, H, L, C, cost, atr, sig, day = d.open.values, d.high.values, d.low.values, d.close.values, d.cost.values, d.atr.values, d.sig.values, d.day.values
    n = len(C); idx = d.index; rng = np.random.default_rng(7)
    t0 = np.searchsorted(idx, pd.Timestamp(start, tz="UTC"))
    trades, shadow, open_tr = [], [], None; last_exit = -10**9; cur = None; ntr = 0; dpl = 0.0
    for i in range(max(t0, 300), n - 1):
        if day[i] != cur: cur = day[i]; ntr = 0; dpl = 0.0
        s = int(sig[i])
        if s == 0 or np.isnan(atr[i]) or i < last_exit + COOL or ntr >= MAXT or dpl <= -LOSSCAP: continue
        if flatten == 1 or (flatten == 2 and s == 1): continue
        if us_hours and not (US_OPEN <= idx[i].hour*60 + idx[i].minute < US_CLOSE): continue
        r = manage(O, H, L, C, cost, atr, i, s, n)
        if r is None: open_tr = {"opened": str(idx[i]), "side": s, "entry": float(O[i+1]), "bars_so_far": int(n-1-i)}; break
        pts, k, how = r; trades.append({"opened": str(idx[i]), "closed": str(idx[i+k]), "side": s, "pts": round(float(pts), 2), "bars": int(k), "how": how})
        last_exit = i + k; ntr += 1; dpl += pts
        lo = max(300, i - 30*288); cands = np.arange(lo, i - CAP - 1)
        for j in rng.choice(cands, size=min(NCTRL, len(cands)), replace=False):
            r2 = manage(O, H, L, C, cost, atr, int(j), s, n)
            if r2 is not None: shadow.append({"opened": str(idx[j]), "for": str(idx[i]), "side": s, "pts": round(float(r2[0]), 2), "how": r2[2]})
    return trades, shadow, open_tr


if __name__ == "__main__":
    today = pd.Timestamp.utcnow().strftime("%Y-%m-%d")
    st = {"started": START_DATE, "equity": START, "shadow_equity": START, "closed": 0, "closed_shadow": 0, "spec": "Ignition v1 (doc 92)"}
    if os.path.exists(STATE): st = json.load(open(STATE))
    bars = pd.read_csv(BARS, index_col=0) if os.path.exists(BARS) else pd.DataFrame()
    if len(bars): bars.index = pd.to_datetime(bars.index, utc=True)
    if "--no-pull" not in sys.argv: bars = pull_missing(bars)
    d = features(bars)
    H = halted(); flatten = int(H.get("flatten", 1)) if H else 0
    trades, shadow, open_tr = replay(d, st["started"], flatten)
    trades_us, shadow_us, open_us = replay(d, st["started"], flatten, us_hours=True)
    eq = START + PT*sum(t["pts"] for t in trades); seq = START + PT*sum(x["pts"] for x in shadow)/max(NCTRL, 1)
    eq_us = START + PT*sum(t["pts"] for t in trades_us); seq_us = START + PT*sum(x["pts"] for x in shadow_us)/max(NCTRL, 1)
    new_tr = [t for t in trades if t["closed"][:10] >= (st.get("last_booked") or "0000")]
    st.update({"equity": round(eq, 2), "shadow_equity": round(seq, 2), "closed": len(trades), "closed_shadow": len(shadow), "open": open_tr, "last_bar": str(d.index.max()), "last_booked": today, "halt": H,
               "us_hours": {"equity": round(eq_us, 2), "shadow_equity": round(seq_us, 2), "closed": len(trades_us), "open": open_us}})
    json.dump(st, open(STATE, "w"), indent=1)
    lines = [f"INSERT OR REPLACE INTO pb7_equity (d, equity, shadow_equity, open_positions, closed_total, closed_shadow, equity_us, shadow_us, closed_us) VALUES ('{today}', {eq:.2f}, {seq:.2f}, {1 if open_tr else 0}, {len(trades)}, {len(shadow)}, {eq_us:.2f}, {seq_us:.2f}, {len(trades_us)});"]
    for t in new_tr:
        lines.append(f"INSERT INTO pb7_trades (d, sym, opened, closed, ret, how, shadow) VALUES ('{today}', 'NQ', '{t['opened']}', '{t['closed']}', {t['pts']:.2f}, '{t['how']}', 0);")
    open(f"{RUNS}/paper7_{today}.sql", "w").write("\n".join(lines) + "\n")
    wins = sum(1 for t in trades if t["pts"] > 0)
    print(f"paper book v7 Ignition v1 — {today} — bars to {d.index.max()} — real ${eq:,.2f} ({len(trades)} closed, win {wins/len(trades)*100 if trades else 0:.0f}%) shadow ${seq:,.2f} — gap {eq-seq:+,.2f} — open: {open_tr}", flush=True)
    print(f"  US-hours variant (IG candidate): real ${eq_us:,.2f} ({len(trades_us)} closed) shadow ${seq_us:,.2f} — gap {eq_us-seq_us:+,.2f} — open: {open_us}", flush=True)
    print(f"  SQL -> {RUNS}/paper7_{today}.sql ({len(lines)} statements)")
