"""Phase 0 (doc 100): the daily long-only books at Coinbase Advanced base-tier fees — 0.60% taker each way, no leverage.
GOLDEN-CROSS v1 (paperbook5 logic, BTC>EMA200 gate) and the Bulkowski pattern engine on crypto daily (doc 98 gates)."""
import warnings; warnings.filterwarnings("ignore")
import sys, numpy as np, pandas as pd
sys.path.insert(0, "/home/claude/qlab/src")
import paperbook4 as P4, paperbook5 as P5
from range_scalein import load_all
FEE = 0.006
def golden(cost):
    P5.COST = cost
    B = load_all(); btc = B["BTCUSD"][0]; b4 = P4.bars4h(btc[["open","high","low","close","volume"]].astype(float)); C_,H_,L_,a_,s_,e200 = P5.indicators(b4); bull = pd.Series(C_ > e200, index=b4.index)
    rows = []
    for sym,(d,*_) in B.items():
        d4 = P4.bars4h(d[["open","high","low","close","volume"]].astype(float)); idx = d4.index; C,H,L,a,sig,_ = P5.indicators(d4)
        for i in np.where(sig)[0]:
            if i+1 >= len(C) or not bull.reindex([idx[i]], method="ffill").iloc[0]: continue
            pos = {"entry": C[i]*(1+cost), "atr": a[i], "bars": 0, "sym": sym, "opened": str(idx[i]), "shadow": 0}
            for j in range(i+1, len(C)):
                r = P5.manage(pos, H, L, C, j, idx)
                if r: rows.append((sym, idx[i], idx[j], r[3])); break
    R = pd.DataFrame(rows, columns=["sym","entry","exit","ret"])
    t = R.ret.mean()/(R.ret.std(ddof=1)/np.sqrt(len(R)))
    print(f"  GOLDEN-CROSS v1 at {cost*1e4:.0f} bps/side: {len(R):,} eps, per ep {R.ret.mean()*100:+.3f}% (t {t:+.1f}), win {(R.ret>0).mean()*100:.0f}%, median {R.ret.median()*100:+.3f}%, coins>0 {(R.groupby('sym').ret.mean()>0).mean()*100:.0f}%; unlevered 20 slots on $2,000 over {(R.exit.max()-R.entry.min()).days} days ≈ ${2000*R.ret.sum()/20:+,.0f}", flush=True)
def patterns(cost):
    T = pd.read_pickle("/home/claude/qlab/runs/bulk_crypto_daily_T.pkl"); T = T[~T.name.isin(["flag","flag_halfmast"])]
    net = np.where(T.resolved==0, 0.0, np.where(T.win==1.0, T.tgt_pct, -T.stop_pct)) - 2*cost
    T = T.assign(net=net)
    for lbl, m in [("all shapes", np.ones(len(T),bool)), ("BTC>EMA200", (T.btc_bull==True).values), ("BTC>EMA200 + lower third of year", ((T.btc_bull==True)&(T.yearly_low==True)).values)]:
        X = T[m]; t = X.net.mean()/(X.net.std(ddof=1)/np.sqrt(len(X)))
        print(f"  PATTERNS daily {lbl:<34} n {len(X):>5,}  net/trade {X.net.mean()*100:+.2f}% (t {t:+.1f}) win {(X.net>0).mean()*100:.0f}%  median {X.net.median()*100:+.2f}%  avg stop {X.stop_pct.mean()*100:.1f}%", flush=True)
if __name__ == "__main__":
    print("At the books' own assumption (4.5 bps):"); golden(4.5/1e4); patterns(4.5/1e4)
    print("At Coinbase Advanced base tier (60 bps taker each way):"); golden(FEE); patterns(FEE)
