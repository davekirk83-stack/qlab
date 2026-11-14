CREATE TABLE IF NOT EXISTS pb8_equity (d TEXT PRIMARY KEY, equity REAL, shadow_equity REAL, open_positions INTEGER, closed_total INTEGER, closed_shadow INTEGER);
CREATE TABLE IF NOT EXISTS pb8_trades (id INTEGER PRIMARY KEY AUTOINCREMENT, d TEXT, sym TEXT, side TEXT, opened TEXT, closed TEXT, ret REAL, how TEXT);
INSERT OR REPLACE INTO pb8_equity (d, equity, shadow_equity, open_positions, closed_total, closed_shadow) VALUES ('2026-11-14', 2006.4444, 2000.8618, 1, 80, 400);
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-14', 'WALLST', 'L', '2026-11-12 21:00:00+00:00', '2026-11-13 00:00:00+00:00', 0.002100, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-14', 'WALLST', 'L', '2026-11-13 06:00:00+00:00', '2026-11-13 06:15:00+00:00', -0.000851, 'regime');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-14', 'DAX', 'L', '2026-11-13 06:15:00+00:00', '2026-11-13 07:00:00+00:00', 0.001569, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-14', 'DAX', 'S', '2026-11-13 10:30:00+00:00', '2026-11-13 11:30:00+00:00', 0.001976, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-14', 'NQ', 'L', '2026-11-13 14:30:00+00:00', '2026-11-13 15:00:00+00:00', -0.014655, 'break');
