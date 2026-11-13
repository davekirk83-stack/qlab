CREATE TABLE IF NOT EXISTS pb8_equity (d TEXT PRIMARY KEY, equity REAL, shadow_equity REAL, open_positions INTEGER, closed_total INTEGER, closed_shadow INTEGER);
CREATE TABLE IF NOT EXISTS pb8_trades (id INTEGER PRIMARY KEY AUTOINCREMENT, d TEXT, sym TEXT, side TEXT, opened TEXT, closed TEXT, ret REAL, how TEXT);
INSERT OR REPLACE INTO pb8_equity (d, equity, shadow_equity, open_positions, closed_total, closed_shadow) VALUES ('2026-11-13', 2011.4025, 2000.1544, 1, 75, 375);
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-13', 'WALLST', 'L', '2026-11-12 07:00:00+00:00', '2026-11-12 07:45:00+00:00', 0.001049, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-13', 'WALLST', 'L', '2026-11-12 13:45:00+00:00', '2026-11-12 15:00:00+00:00', 0.002899, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-13', 'WALLST', 'S', '2026-11-12 16:00:00+00:00', '2026-11-12 18:00:00+00:00', 0.002346, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-13', 'DAX', 'L', '2026-11-12 19:30:00+00:00', '2026-11-12 23:00:00+00:00', 0.001614, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-13', 'NQ', 'S', '2026-11-12 15:45:00+00:00', '2026-11-12 16:00:00+00:00', -0.004390, 'regime');
