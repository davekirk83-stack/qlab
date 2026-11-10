# 226: Linda Raschke's OD/ID breakout (10 Nov 2026)

DK, 18:41, sent her post: "my all time favorite breakout formation… still pays better than any other".

**Rules.**
- **Setup:** an outside day followed by an inside day.
- **Entry:** a stop order through the inside day's high (buy) or low (sell), live for 3 days. Gaps fill at the open, and a same-day trigger of both sides counts as a loss.
- **Stop:** the other side of the inside day.
- **Exit:** after 5 or 10 days, at the next open.
- **Markets and costs:** 11 IG markets (indices, gold, T-note, FX, oil) at IG's real costs. Standard test v3. Variants were fixed in advance.

| Variant | n (per year) | Mean R | Last 5y | Last 12m | Verdict |
|---|---|---|---|---|---|
| Both sides, 5 days | 1,423 (53) | +0.066 | −0.103 | −0.133 | FAIL |
| Long only, 5 days | 893 (33) | −0.038 | −0.119 | −0.226 | FAIL |
| Both sides, 10 days | 1,357 (50) | +0.045 | −0.138 | −0.191 | FAIL |

**Reading.**
- The pattern had an edge in the early years: 2000–2015 was positive.
- **Since 2016 it has lost money** (−0.07 R per trade, 37% winners).
- Bonds, her example, were among the worst: −0.23 R on the T-note.
- Gold, the Dow and FTSE were positive, but picking markets after the fact is selection.

The book does not add to the portfolio. It goes on the narrow-fail list as **OD/ID on gold only**. That has to be confirmed on data it wasn't chosen from before it means anything.

Script: `src/odid_test.py`. Output: `runs/gate/odid_test.txt`.
