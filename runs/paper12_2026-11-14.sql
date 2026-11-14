CREATE TABLE IF NOT EXISTS pb12_equity (d TEXT PRIMARY KEY, equity REAL, shadow_equity REAL, open_positions INTEGER, closed_total INTEGER, closed_shadow INTEGER);
CREATE TABLE IF NOT EXISTS pb12_trades (d TEXT, sym TEXT, kind TEXT, opened TEXT, closed TEXT, entry REAL, stop REAL, target REAL, r_mult REAL, how TEXT, shadow INTEGER);
INSERT OR REPLACE INTO pb12_equity VALUES ('2026-11-14', 1891.1603, 1913.0471, 0, 5, 4);
INSERT INTO pb12_trades VALUES ('2026-11-14', 'MUB', 'etf', '2026-11-04', '2026-11-13', 104.36, 103.669, 106.3, -1.1510, 'stop', 0);