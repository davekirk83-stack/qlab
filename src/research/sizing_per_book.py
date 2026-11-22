import sys, runpy
sys.argv=["x"]; sys.path.insert(0,"src"); sys.path.insert(0,"src/research")
src=open("src/research/sizing_study.py").read().split("out = [")[0]
src=src.replace('BOOKS = {"RSI4L"','BOOKS = {"RSI4": (lambda d: (up(d) & (r4(d) < 25), r4(d) > 55, 10, 3.0, "C"), 3.0), "RSI4L"')
g={}; exec(src, g)
T=g["T"]
for b in ("RSI4","RSI4L","TPS","TOM"):
    g["T"]=T[T.book==b].reset_index(drop=True)
    for risk,cap in ((0.02,None),(0.03,0.06),(0.05,0.10)):
        cg,md,wm,c5,_=g["sim"](risk, cap=cap, B=True)
        print(f"{b:6} n{len(g['T'])} meanR {g['T'].R.mean():+.3f} | risk {risk:.0%} cap {cap} DDladder: CAGR {cg:+.1%} maxDD {md:.0%} worst month {wm:+.1%} last5y {c5:+.1%}")
