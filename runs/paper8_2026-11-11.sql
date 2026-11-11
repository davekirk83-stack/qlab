CREATE TABLE IF NOT EXISTS pb8_equity (d TEXT PRIMARY KEY, equity REAL, shadow_equity REAL, open_positions INTEGER, closed_total INTEGER, closed_shadow INTEGER);
CREATE TABLE IF NOT EXISTS pb8_trades (id INTEGER PRIMARY KEY AUTOINCREMENT, d TEXT, sym TEXT, side TEXT, opened TEXT, closed TEXT, ret REAL, how TEXT);
INSERT OR REPLACE INTO pb8_equity (d, equity, shadow_equity, open_positions, closed_total, closed_shadow) VALUES ('2026-11-11', 2009.9254, 1998.0495, 1, 64, 320);
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-11', 'DAX', 'L', '2026-11-10 14:30:00+00:00', '2026-11-10 18:30:00+00:00', -0.000398, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-11', 'NQ', 'L', '2026-11-10 14:00:00+00:00', '2026-11-10 14:30:00+00:00', 0.005038, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-11', 'NQ', 'S', '2026-11-10 15:00:00+00:00', '2026-11-10 15:15:00+00:00', 0.005835, 'sold');
