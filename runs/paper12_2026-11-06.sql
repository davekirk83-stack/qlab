CREATE TABLE IF NOT EXISTS pb12_equity (d TEXT PRIMARY KEY, equity REAL, shadow_equity REAL, open_positions INTEGER, closed_total INTEGER, closed_shadow INTEGER);
CREATE TABLE IF NOT EXISTS pb12_trades (d TEXT, sym TEXT, kind TEXT, opened TEXT, closed TEXT, entry REAL, stop REAL, target REAL, r_mult REAL, how TEXT, shadow INTEGER);
INSERT OR REPLACE INTO pb12_equity VALUES ('2026-11-06', 1979.3436, 1959.1446, 3, 1, 2);
INSERT INTO pb12_trades VALUES ('2026-11-06', 'XLI', 'etf', '2026-11-03', '2026-11-05', 171.32, 166.1, 188.19, -1.0328, 'stop', 0);
INSERT INTO pb12_trades VALUES ('2026-11-06', 'MDY', 'etf', '2026-11-03', '2026-11-05', 676.25, 653.781, 717.35, -1.0301, 'stop', 1);
INSERT INTO pb12_trades VALUES ('2026-11-06', 'EWY', 'etf', '2026-11-04', '2026-11-05', 152.12, 145.567, 193.93, -1.0232, 'stop', 1);