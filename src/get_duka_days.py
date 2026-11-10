"""Fetch Dukascopy 1-min days for a given list of dates only (doc 209: USCL entry-timing test). Usage: get_duka_days.py INSTR dates.txt"""
import sys, os, time, datetime as dt
from concurrent.futures import ThreadPoolExecutor
INSTR, LIST = sys.argv[1], sys.argv[2]; sys.argv = [sys.argv[0], INSTR, "2000-01-01", "2000-01-01"]
import importlib.util; spec = importlib.util.spec_from_file_location("g", os.path.join(os.path.dirname(os.path.abspath(__file__)), "get_duka_1m.py"))
src = open(spec.origin).read().split("days = [x.date()")[0]; g = {}; exec(src, g)
days = [dt.date.fromisoformat(x.strip()) for x in open(LIST) if x.strip()]
for p in range(30):
    with ThreadPoolExecutor(max_workers=6) as ex: fs = list(ex.map(g["day"], days))
    left = sum(f is None for f in fs); print(INSTR, f"pass {p}: {left} missing", flush=True)
    if not left: break
    time.sleep(90)
