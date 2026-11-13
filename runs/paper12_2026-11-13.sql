CREATE TABLE IF NOT EXISTS pb12_equity (d TEXT PRIMARY KEY, equity REAL, shadow_equity REAL, open_positions INTEGER, closed_total INTEGER, closed_shadow INTEGER);
CREATE TABLE IF NOT EXISTS pb12_trades (d TEXT, sym TEXT, kind TEXT, opened TEXT, closed TEXT, entry REAL, stop REAL, target REAL, r_mult REAL, how TEXT, shadow INTEGER);
INSERT OR REPLACE INTO pb12_equity VALUES ('2026-11-13', 1913.1810, 1913.0471, 1, 4, 4);
INSERT INTO pb12_trades VALUES ('2026-11-13', 'EMB', 'etf', '2026-11-04', '2026-11-12', 92.44, 91.3953, 95.45, -1.0885, 'stop', 0);
INSERT INTO pb12_trades VALUES ('2026-11-13', 'HYG', 'etf', '2026-11-11', '2026-11-12', 77.35, 76.9927, 79.97, -1.2165, 'stop', 0);
INSERT INTO pb12_trades VALUES ('2026-11-13', 'BND', 'etf', '2026-11-11', '2026-11-12', 71.1, 70.8371, 72.68, -1.2705, 'stop', 1);