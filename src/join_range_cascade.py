"""
THE RANGE–CASCADE JOIN — item 2 of doc 75 (DK: "Great idea ... potentially";
the join goes in only if it beats the two books run unjoined).

One machine per coin: the range book trades while its containment switch is ON;
when the switch goes OFF the coin is handed to the cascade (base-then-bid, v3);
the range book re-engages when containment returns.

Built from the registered pieces, unchanged:
  range    clean_portfolio.episodes on 15-minute bars, both sides, chase fills,
           switch = containment > the coin's frozen full-history median
           (runs/contain_median.json, as paperbook2 v2.2)
  cascade  cascade_v3 scan (3% in 5 min -> lift 0.8% -> 10-minute base -> bid
           0.4% below -> structural stop -> +1.5% / 60-minute cap) on 1-minute
           bars, with v3 costs
Coins = those with both panels (18). Period = the overlap of the two panels.

FOUR BOOKS through the same simulator (40 slots, 1x):
  range alone · cascade alone · UNJOINED (both, sharing the slots) ·
  JOINED (range + cascade only while the range switch is OFF)
plus the diagnostic that decides it: cascade trades during range-ON vs range-OFF.
"""
import warnings; warnings.filterwarnings("ignore")
import json, os
import numpy as np, pandas as pd
import clean_portfolio as CP, regime_detect as RD, cascade_v3 as CV

MED = json.load(open("/home/claude/qlab/runs/contain_median.json"))
D1M = "/home/claude/qlab/data_1m"; D15 = "/home/claude/qlab/data_15m"
MAXH, MAKER, TAKER, SLIP, DEPTH, TP = CV.MAXH, CV.MAKER, CV.TAKER, CV.SLIP, CV.DEPTH, CV.TP


def cascade_episodes(sym, m):
    C, L, H = m.close.values, m.low.values, m.high.values; n = len(C)
    mv = np.full(n, np.nan); mv[CV.WIN:] = C[CV.WIN:]/C[:-CV.WIN] - 1
    out = []; last = -10**9
    for i in np.flatnonzero(mv <= -CV.DROP):
        if i <= last or i + 2*MAXH >= n: continue
        r = CV.find_base(C, L, i, n); last = i + MAXH
        if r is None: continue
        base_k, lo = r
        bid = max(C[base_k]*(1-DEPTH), lo*1.0002); fill = None
        for q in range(base_k+1, min(base_k+1+MAXH, n)):
            if L[q] < lo: break
            if L[q] <= bid: fill = q; break
        if fill is None: continue
        px = bid*(1+MAKER); stop = lo*(1-0.0005); tgt = px*(1+TP)
        if stop >= px: continue
        ret = None
        for q in range(fill+1, min(fill+1+MAXH, n)):
            if L[q] <= stop: ret = (stop*(1-SLIP-TAKER))/px - 1; break
            if H[q] >= tgt: ret = (tgt*(1-MAKER))/px - 1; break
        if ret is None: q = min(fill+MAXH, n-1); ret = (C[q]*(1-MAKER))/px - 1
        out.append((sym, m.index[i], m.index[fill], m.index[q], ret))
    return pd.DataFrame(out, columns=["sym", "signal", "entry", "exit", "ret"])


def main():
    syms = [f[:-4] for f in sorted(os.listdir(D1M)) if os.path.exists(f"{D15}/{f[:-8]}USD.csv")]
    R_rows, C_rows, C_off, C_on = [], [], [], []
    t0, t1 = None, None
    for s in syms:
        m = pd.read_csv(f"{D1M}/{s}.csv"); m.index = pd.to_datetime(m.t, unit="ms", utc=True); m = m[["open","high","low","close","volume"]].astype(float)
        d = pd.read_csv(f"{D15}/{s[:-4]}USD.csv", index_col=0); d.index = pd.to_datetime(d.index, utc=True, format="ISO8601")
        d = d[~d.index.duplicated(keep="last")].sort_index()
        lo_t, hi_t = max(m.index.min(), d.index.min()), min(m.index.max(), d.index.max())
        t0 = lo_t if t0 is None else max(t0, lo_t); t1 = hi_t if t1 is None else min(t1, hi_t)
        d = d[d.index <= hi_t]                                  # full history for the detectors
        D, ema, lo_b, hi_b, a = RD.detectors(d)
        thr = MED.get(f"{s[:-4]}USD", {}).get("median")
        v = pd.Series(D["contain"]); allow = (v > (thr if thr is not None else v.expanding(500).median())).values
        rows = []
        for side in ("L", "S"):
            rows += CP.episodes(d, allow, ema, lo_b, hi_b, a, None, "chase", side, f"{s[:-4]}USD")
        R = pd.DataFrame(rows, columns=["sym", "entry", "exit", "ret", "side"]); R = R[np.isfinite(R.ret)]
        R = R[(R.entry >= lo_t)]; R_rows.append(R)
        Cc = cascade_episodes(s, m[m.index >= lo_t])
        sw = pd.Series(allow, index=d.index)
        state = sw.reindex(Cc.signal, method="ffill").values if len(Cc) else np.array([])
        Cc["range_on"] = state.astype(bool); C_rows.append(Cc)
        print(f"  {s:<9} range eps {len(R):>5}  cascade eps {len(Cc):>4}  (range on {int(Cc.range_on.sum()):>3} / off {int((~Cc.range_on).sum()):>3})", flush=True)
    R = pd.concat(R_rows); Cc = pd.concat(C_rows)
    R["book"] = "range"; Cc["book"] = "cascade"
    print(f"\nOverlap {t0.date()} to {t1.date()}, {len(syms)} coins.")

    def stats(lbl, S):
        if len(S) < 20: print(f"  {lbl:<36} n={len(S)} too few"); return
        t = S.ret.mean()/(S.ret.std(ddof=1)/np.sqrt(len(S)))
        print(f"  {lbl:<36}{len(S):>6,}{S.ret.mean()*100:>+8.3f}%{t:>+6.1f}{(S.ret>0).mean()*100:>5.0f}%", flush=True)
    print("\nPer-episode (the diagnostic that decides the join):")
    stats("range episodes", R)
    stats("cascade, all", Cc)
    stats("cascade while range switch ON", Cc[Cc.range_on])
    stats("cascade while range switch OFF", Cc[~Cc.range_on])
    for s in ("L", "S"): stats(f"range {s} side", R[R.side == s])

    def sim(lbl, S):
        S = S[["sym", "entry", "exit", "ret"]].copy()
        r, taken, skipped = CP.simulate(S, 40, 1)
        if r is None: print(f"  {lbl:<36} blew up"); return
        print(f"  {lbl:<36}{taken:>7}{skipped:>8}{S.ret.mean()*100:>+9.3f}%{r['cagr']*100:>+8.1f}%{r['dd']*100:>+8.1f}%{r['sharpe']:>8.2f}{r['final']:>11,.0f}", flush=True)
    print(f"\nBooks through the same simulator ($2,000, 40 slots, 1x), same coins and bars:")
    print(f"  {'book':<36}{'taken':>7}{'skipped':>8}{'per ep':>10}{'CAGR':>9}{'maxDD':>9}{'Sharpe':>8}{'final':>11}")
    sim("range alone", R)
    sim("cascade alone", Cc)
    sim("UNJOINED: range + cascade (all)", pd.concat([R, Cc]))
    sim("JOINED: range + cascade only when OFF", pd.concat([R, Cc[~Cc.range_on]]))
    sim("inverse: range + cascade only when ON", pd.concat([R, Cc[Cc.range_on]]))
    R.to_csv("/home/claude/qlab/runs/join_range_eps.csv", index=False); Cc.to_csv("/home/claude/qlab/runs/join_cascade_eps.csv", index=False)


if __name__ == "__main__":
    main()
