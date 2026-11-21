CREATE TABLE IF NOT EXISTS pb12_equity (d TEXT PRIMARY KEY, equity REAL, shadow_equity REAL, open_positions INTEGER, closed_total INTEGER, closed_shadow INTEGER);
CREATE TABLE IF NOT EXISTS pb12_trades (d TEXT, sym TEXT, kind TEXT, opened TEXT, closed TEXT, entry REAL, stop REAL, target REAL, r_mult REAL, how TEXT, shadow INTEGER);
INSERT OR REPLACE INTO pb12_equity VALUES ('2026-11-21', 1891.1603, 1873.7257, 2, 5, 6);
INSERT INTO pb12_trades VALUES ('2026-11-21', 'EWJ', 'etf', '2026-11-19', '2026-11-20', 87.01, 85.1221, 99.98, -1.0461, 'stop', 1);