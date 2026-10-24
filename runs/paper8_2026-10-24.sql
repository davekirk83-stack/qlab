CREATE TABLE IF NOT EXISTS pb8_equity (d TEXT PRIMARY KEY, equity REAL, shadow_equity REAL, open_positions INTEGER, closed_total INTEGER, closed_shadow INTEGER);
CREATE TABLE IF NOT EXISTS pb8_trades (id INTEGER PRIMARY KEY AUTOINCREMENT, d TEXT, sym TEXT, side TEXT, opened TEXT, closed TEXT, ret REAL, how TEXT);
INSERT OR REPLACE INTO pb8_equity (d, equity, shadow_equity, open_positions, closed_total, closed_shadow) VALUES ('2026-10-24', 2005.0023, 1999.2854, 0, 13, 65);
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-10-24', 'WALLST', 'S', '2026-10-22 20:00:00+00:00', '2026-10-23 00:15:00+00:00', 0.001052, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-10-24', 'WALLST', 'L', '2026-10-23 01:15:00+00:00', '2026-10-23 06:15:00+00:00', -0.000159, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-10-24', 'WALLST', 'L', '2026-10-23 12:15:00+00:00', '2026-10-23 13:30:00+00:00', -0.003887, 'regime');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-10-24', 'DAX', 'L', '2026-10-23 01:00:00+00:00', '2026-10-23 05:15:00+00:00', 0.000102, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-10-24', 'NQ', 'L', '2026-10-23 13:00:00+00:00', '2026-10-23 13:30:00+00:00', 0.002594, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-10-24', 'NQ', 'S', '2026-10-23 14:30:00+00:00', '2026-10-23 16:45:00+00:00', 0.002536, 'sold');
