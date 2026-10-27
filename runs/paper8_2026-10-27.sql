CREATE TABLE IF NOT EXISTS pb8_equity (d TEXT PRIMARY KEY, equity REAL, shadow_equity REAL, open_positions INTEGER, closed_total INTEGER, closed_shadow INTEGER);
CREATE TABLE IF NOT EXISTS pb8_trades (id INTEGER PRIMARY KEY AUTOINCREMENT, d TEXT, sym TEXT, side TEXT, opened TEXT, closed TEXT, ret REAL, how TEXT);
INSERT OR REPLACE INTO pb8_equity (d, equity, shadow_equity, open_positions, closed_total, closed_shadow) VALUES ('2026-10-27', 2008.7588, 1999.2166, 0, 18, 90);
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-10-27', 'WALLST', 'S', '2026-10-26 08:30:00+00:00', '2026-10-26 10:15:00+00:00', 0.000811, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-10-27', 'WALLST', 'L', '2026-10-26 23:00:00+00:00', '2026-10-26 23:15:00+00:00', 0.001155, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-10-27', 'DAX', 'S', '2026-10-25 23:00:00+00:00', '2026-10-25 23:15:00+00:00', 0.001772, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-10-27', 'DAX', 'S', '2026-10-26 07:00:00+00:00', '2026-10-26 08:00:00+00:00', 0.000808, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-10-27', 'NQ', 'S', '2026-10-26 13:00:00+00:00', '2026-10-26 13:30:00+00:00', 0.002948, 'sold');
