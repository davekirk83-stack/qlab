"""Kronos-small (github.com/shiyu-coder/Kronos, code frozen April 2026) vs naive baselines, out of sample (May 1 - Oct 23 2026).
Every 4 hours, feed the last 512 15-min bars, forecast the next 4 (1 hour), average of 5 samples. Saved incrementally per instrument.
Run: python kronos_test.py SYMBOL   (BTC, ETH -> Coinbase 15-min; NQ -> Dukascopy 5-min resampled)"""
import sys, os, time, numpy as np, pandas as pd, torch
sys.path.insert(0, "/home/claude/kronos_src/Kronos"); from model import Kronos, KronosTokenizer, KronosPredictor
torch.set_num_threads(2)
SYM = sys.argv[1]; OUT = f"/home/claude/qlab/runs/kronos/{SYM}.csv"
if SYM in ("BTC", "ETH"):
    d = pd.read_csv(f"/home/claude/qlab/data_15m/{SYM}USD.csv", index_col=0); d.index = pd.to_datetime(d.index, utc=True)
else:
    r = pd.read_csv("/home/claude/qlab/data_nq_cache/nq_5m.csv", index_col=0); r.index = pd.to_datetime(r.index, utc=True)
    d = pd.DataFrame({"open": r.open.resample("15min").first(), "high": r.high.resample("15min").max(), "low": r.low.resample("15min").min(),
                      "close": r.close.resample("15min").last(), "volume": r.vol.resample("15min").sum()}).dropna()
d["amount"] = d.volume*d.close; d = d[["open", "high", "low", "close", "volume", "amount"]]
tok = KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-base"); m = Kronos.from_pretrained("NeoQuasar/Kronos-small")
pred = KronosPredictor(m, tok, device="cpu", max_context=512)
done = set(pd.read_csv(OUT).t0) if os.path.exists(OUT) else set()
pts = [i for i in range(512, len(d) - 4) if d.index[i] >= pd.Timestamp("2026-05-01", tz="UTC") and d.index[i].hour % 4 == 0 and d.index[i].minute == 0]
pts = [i for i in pts if str(d.index[i]) not in done]
print(SYM, "points to do", len(pts), flush=True)
B = 8; t0 = time.time()
for k in range(0, len(pts), B):
    chunk = pts[k:k+B]
    xs = [d.iloc[i-512:i].reset_index(drop=True) for i in chunk]
    xts = [pd.Series(d.index[i-512:i]).dt.tz_localize(None) for i in chunk]
    yts = [pd.Series(d.index[i:i+4]).dt.tz_localize(None) for i in chunk]
    try: preds = pred.predict_batch(df_list=xs, x_timestamp_list=xts, y_timestamp_list=yts, pred_len=4, T=1.0, top_p=0.9, sample_count=5, verbose=False)
    except Exception as e: print("batch error", e, flush=True); continue
    rows = []
    for i, p in zip(chunk, preds):
        last = d.close.iloc[i-1]
        rows.append(dict(t0=str(d.index[i]), last=last, pred1=float(p.close.iloc[0]), pred4=float(p.close.iloc[-1]),
                         act1=float(d.close.iloc[i]), act4=float(d.close.iloc[i+3]), prev4=float(d.close.iloc[i-5])))
    pd.DataFrame(rows).to_csv(OUT, mode="a", header=not os.path.exists(OUT), index=False)
    if (k//B) % 10 == 0: print(f"{SYM} {k+len(chunk)}/{len(pts)} {time.time()-t0:.0f}s", flush=True)
print(SYM, "done", flush=True)
