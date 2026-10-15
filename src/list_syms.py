import re, json, urllib.request, urllib.parse
B="https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
out, tok = [], None
for _ in range(40):
    q={"delimiter":"/","prefix":"data/spot/monthly/klines/"}
    if tok: q["marker"]=tok
    with urllib.request.urlopen(f"{B}?{urllib.parse.urlencode(q)}",timeout=60) as r:
        x=r.read().decode()
    p=re.findall(r'<Prefix>data/spot/monthly/klines/([A-Z0-9]+)/</Prefix>',x)
    if not p: break
    out+=p
    if '<IsTruncated>true' not in x: break
    tok=f"data/spot/monthly/klines/{p[-1]}/"
usdt=sorted(set(s for s in out if s.endswith("USDT")
            and not any(k in s for k in ("UPUSDT","DOWNUSDT","BULL","BEAR"))))
json.dump(usdt,open("/home/claude/qlab/syms_usdt.json","w"))
print(f"{len(out)} prefixes, {len(usdt)} clean USDT spot pairs")
