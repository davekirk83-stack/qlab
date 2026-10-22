"""Range v3 engine on IG-tradeable index/commodity 5-min data -> 15-min bars (doc 114/115).
Costs: IG spread bet = half the quoted spread each way + 0.5 spread slippage on market exits. Control: time-matched random
episodes (same side, same hold, same costs) drawn from the trailing 30 days, 5 per real episode."""
import sys, os, json, numpy as np, pandas as pd
sys.path.insert(0, "/home/claude/qlab/src"); import paperbook6 as P
def load(path):
    d = pd.read_csv(path, index_col=0, parse_dates=True); d.index = pd.to_datetime(d.index, utc=True)
    o = d.open.resample("15min").first(); h = d.high.resample("15min").max(); l = d.low.resample("15min").min(); c = d.close.resample("15min").last()
    s = d.spread.resample("15min").mean() if "spread" in d else None
    b = pd.DataFrame({"open": o, "high": h, "low": l, "close": c}).dropna()
    if s is not None: b["spread"] = s.reindex(b.index).ffill()
    return b
def run(name, b, spread_pts, us_hours=None, half=None):
    px = b.close.median(); half_spread = spread_pts/2/px
    P.MK = half_spread; P.TAKER = half_spread; P.SLIP = spread_pts*0.5/px
    P._MED = {}
    if half == 1: b = b[b.index < b.index[len(b)//2]]
    if half == 2: b = b[b.index >= b.index[len(b)//2]]
    if us_hours:  # restrict NEW episodes to the window by masking the switch outside it: emulate by trimming? keep simple: full session
        pass
    pos = {}; slots = [40]
    closed, _ = P.step(name, b, pos, str(b.index[250]), slots)
    if not closed: return None
    e = pd.DataFrame(closed, columns=["sym", "side", "open", "close", "ret", "how"]); e["open"] = pd.to_datetime(e.open); e["close"] = pd.to_datetime(e.close)
    e["bars"] = ((e.close - e.open) / pd.Timedelta(minutes=15)).astype(int).clip(lower=1)
    # control
    rng = np.random.default_rng(7); C = b.close.values; idx = b.index; ctrl = []
    for _, r in e.iterrows():
        i = idx.searchsorted(r.open); lo = max(250, i - 30*96); 
        if lo >= i - r.bars - 1: continue
        for j in rng.choice(np.arange(lo, i - r.bars), size=5, replace=False):
            k = min(j + r.bars, len(C) - 1); s = 1 if r.side == "L" else -1
            ctrl.append(s*(C[k]/C[j] - 1) - 2*half_spread - P.SLIP)
    e["month"] = e.close.dt.to_period("M")
    return dict(name=name, n=len(e), per_ep=e.ret.mean()*100, win=(e.ret > 0).mean(), median=e.ret.median()*100, t=e.ret.mean()/e.ret.std()*np.sqrt(len(e)) if len(e) > 1 else 0,
                ctrl=np.mean(ctrl)*100 if ctrl else np.nan, months_pos=(e.groupby("month").ret.sum() > 0).mean(), nmonths=e.month.nunique(),
                hows=e.how.value_counts().to_dict(), eps_per_week=len(e)/max((b.index[-1]-b.index[0]).days/7, 1), total=e.ret.sum()*100)
if __name__ == "__main__":
    specs = [("US Tech 100 (NQ)", "/home/claude/qlab/data_nq_cache/nq_5m.csv", 1.0)]
    for instr, sp, label in (("USA30IDXUSD", 2.0, "Wall Street"), ("DEUIDXEUR", 1.2, "Germany 40"), ("XAUUSD", 0.3, "Gold")):
        p = f"/home/claude/qlab/data_ig_cache/{instr}_5m.csv"
        if os.path.exists(p): specs.append((label, p, sp))
    rows = []
    for label, path, sp in specs:
        b = load(path); print(f"\n{label}: {len(b)} 15m bars {b.index[0].date()} -> {b.index[-1].date()}, spread {sp} pts = {sp/b.close.median()*1e4:.1f} bps")
        for half in (None, 1, 2):
            r = run(label, b, sp, half=half)
            if r: print(f"  {'full' if half is None else 'H'+str(half):4s} n{r['n']:4d} per-ep {r['per_ep']:+.3f}% (ctrl {r['ctrl']:+.3f}%) win {r['win']:.0%} med {r['median']:+.2f}% t {r['t']:+.1f} months+ {r['months_pos']:.0%}/{r['nmonths']} eps/wk {r['eps_per_week']:.1f} total {r['total']:+.1f}% exits {r['hows']}")
            if half is None: rows.append(r)
    json.dump(rows, open("/home/claude/qlab/runs/range_index_test.json", "w"), indent=1, default=str)
