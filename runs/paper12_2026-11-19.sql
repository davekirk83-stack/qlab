CREATE TABLE IF NOT EXISTS pb12_equity (d TEXT PRIMARY KEY, equity REAL, shadow_equity REAL, open_positions INTEGER, closed_total INTEGER, closed_shadow INTEGER);
CREATE TABLE IF NOT EXISTS pb12_trades (d TEXT, sym TEXT, kind TEXT, opened TEXT, closed TEXT, entry REAL, stop REAL, target REAL, r_mult REAL, how TEXT, shadow INTEGER);
INSERT OR REPLACE INTO pb12_equity VALUES ('2026-11-19', 1891.1603, 1893.5337, 1, 5, 5);
INSERT INTO pb12_trades VALUES ('2026-11-19', 'EWZ', 'etf', '2026-11-04', '2026-11-18', 32.25, 30.6386, 43.9, -1.0200, 'stop', 1);