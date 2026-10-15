# qlab — DK Operations, Section 1 (Trading)

Research code for the trading programme run under the "Personal Manager & PA"
project. **Research and paper trading only.** No live order, brokerage or
exchange account, credential, authentication, or committed capital of any size,
on any signal, under any circumstance (CAP-021).

## Layout

    src/            the lab: element library, harness, book trackers, studies
    runs/paper/     forward paper-trading journals (JSON, synced to D1)

Market data is deliberately not committed — see `.gitignore`. What data exists,
where it came from and what period it covers is recorded in the `data_assets`
table of the `dk-capital` Cloudflare D1 database.

## Where the knowledge lives

| thing | home |
|---|---|
| code | this repository |
| results, element scores, book registry, method rules | `dk-capital` D1 database |
| narrative findings (numbered docs) | the claude.ai project |

## Key modules

| file | what it does |
|---|---|
| `elements.py` | 66 primitive elements across 11 families, IC-scored |
| `harness.py` | one graded evaluation path for every candidate |
| `structure.py` | levels, trendlines, pivots |
| `cascade_v3.py` / `cascade_v3k.py` | registered book and its tapered-exit variant |
| `retest_paper.py`, `vwap_paper.py`, `pattern_paper.py`, `carry_paper.py` | the other registered books |
| `execcost.py` | slippage and capacity measured from real order-book depth |
| `keltner_regime.py` | the range-regime reversion candidate |
| `condition.py` | conditioning a book on the element library |
| `db_sync.py` | emits SQL to push paper trades into D1 |

## Standing method rules

Twenty rules are recorded in the `rules` table of the database, each with the
error that produced it. The two that have caught the most mistakes:

- **State measures predict; signal measures do not.** Crossovers, divergences
  and candlestick patterns carry almost nothing.
- **Count independent observations, not bars.** Overlapping forward windows are
  not a sample.
