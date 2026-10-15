"""Live structure check: opening 30-min 'first move is the wrong move' + descending
trendline reclaim. Research/observation only. Places nothing."""
import json,urllib.request,time,sys
import numpy as np

def candles(coin,interval,hours):
    now=int(time.time()*1000)
    req=urllib.request.Request('https://api.hyperliquid.xyz/info',
      data=json.dumps({'type':'candleSnapshot','req':{'coin':coin,'interval':interval,
        'startTime':now-hours*3600*1000,'endTime':now}}).encode(),
      headers={'Content-Type':'application/json'})
    c=json.load(urllib.request.urlopen(req,timeout=30))
    return [dict(t=k['t'],o=float(k['o']),h=float(k['h']),l=float(k['l']),c=float(k['c'])) for k in c]

def hhmm(t): return time.strftime('%H:%M',time.gmtime(t/1000))

def swing_highs(ks,k=3):
    out=[]
    for i in range(k,len(ks)-k):
        if ks[i]['h']==max(x['h'] for x in ks[i-k:i+k+1]): out.append(i)
    return out

def upper_hull(pts):
    """Monotone chain upper hull -> the descending resistance line touches these."""
    pts=sorted(pts)
    hull=[]
    for p in pts:
        while len(hull)>=2:
            (x1,y1),(x2,y2)=hull[-2],hull[-1]
            if (x2-x1)*(p[1]-y1)-(y2-y1)*(p[0]-x1) >= 0: hull.pop()
            else: break
        hull.append(p)
    return hull

coin=sys.argv[1] if len(sys.argv)>1 else 'BTC'
m5=candles(coin,'5m',30)
m15=candles(coin,'15m',96)
px=m5[-1]['c']
print(f"{coin}  now {hhmm(int(time.time()*1000))}Z  last {hhmm(m5[-1]['t'])}Z  px {px:,.0f}\n")

# --- opening 30 minutes of the US cash open (13:30Z) ---
day=time.strftime('%Y-%m-%d',time.gmtime())
def ymd(t): return time.strftime('%Y-%m-%d',time.gmtime(t/1000))
op=[k for k in m5 if ymd(k['t'])==day and '13:30'<=hhmm(k['t'])<'14:00']
if op:
    o=op[0]['o']; hi=max(k['h'] for k in op); lo=min(k['l'] for k in op)
    hi_t=hhmm([k for k in op if k['h']==hi][0]['t']); lo_t=hhmm([k for k in op if k['l']==lo][0]['t'])
    first = 'UP' if hi_t<lo_t else 'DOWN'
    print("US OPEN 13:30Z, first 30 min")
    print(f"  open {o:,.0f}  high {hi:,.0f} @{hi_t}  low {lo:,.0f} @{lo_t}")
    print(f"  first move      {first}  ({'high' if first=='UP' else 'low'} printed first)")
    print(f"  excursion up    {(hi/o-1)*100:+.2f}%   down {(lo/o-1)*100:+.2f}%")
    print(f"  since open      {(px/o-1)*100:+.2f}%")
    print(f"  wrong-move test the first move was {first}; it is "
          f"{'CONFIRMED' if ((first=='UP' and px>hi) or (first=='DOWN' and px<lo)) else 'FADED'} so far")
    print(f"  retrace of the dump  {(px-lo)/(hi-lo)*100:.0f}% of the open range reclaimed\n")

# --- descending trendline from recent 15m swing highs ---
sw=swing_highs(m15,3)
# only highs from the leg down: from the highest swing high onward
if sw:
    top=max(sw,key=lambda i:m15[i]['h'])
    pts=[(i,m15[i]['h']) for i in sw if i>=top]
    hull=upper_hull(pts)
    if len(hull)>=2:
        (x1,y1),(x2,y2)=hull[0],hull[-1]
        slope=(y2-y1)/(x2-x1) if x2!=x1 else 0.0
        n=len(m15)-1
        line=y1+slope*(n-x1)
        print("DESCENDING TRENDLINE (15m swing highs, upper hull)")
        print(f"  anchor A {hhmm(m15[x1]['t'])}Z @ {y1:,.0f}")
        print(f"  anchor B {hhmm(m15[x2]['t'])}Z @ {y2:,.0f}")
        print(f"  slope    {slope*4:+,.0f} per hour")
        print(f"  line now {line:,.0f}")
        print(f"  price is {(px/line-1)*100:+.2f}% vs line -> "
              f"{'RECLAIMED (above)' if px>line else 'still BELOW'}")
        # when was it lost?
        lost=None
        for i in range(len(m15)-1,x2,-1):
            if m15[i]['c'] > y1+slope*(i-x1): lost=i; break
        if lost is not None and lost<len(m15)-1:
            print(f"  last close above it: {hhmm(m15[lost]['t'])}Z "
                  f"({(len(m15)-1-lost)*15} min ago)")
        print(f"  reclaim needs a 15m close above {line:,.0f} "
              f"({(line/px-1)*100:+.2f}% from here)")
