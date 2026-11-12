CREATE TABLE IF NOT EXISTS pb8_equity (d TEXT PRIMARY KEY, equity REAL, shadow_equity REAL, open_positions INTEGER, closed_total INTEGER, closed_shadow INTEGER);
CREATE TABLE IF NOT EXISTS pb8_trades (id INTEGER PRIMARY KEY AUTOINCREMENT, d TEXT, sym TEXT, side TEXT, opened TEXT, closed TEXT, ret REAL, how TEXT);
INSERT OR REPLACE INTO pb8_equity (d, equity, shadow_equity, open_positions, closed_total, closed_shadow) VALUES ('2026-11-12', 2009.6351, 1999.6080, 0, 70, 350);
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-12', 'WALLST', 'S', '2026-11-11 05:00:00+00:00', '2026-11-11 05:30:00+00:00', 0.000740, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-12', 'WALLST', 'L', '2026-11-11 09:30:00+00:00', '2026-11-11 12:00:00+00:00', 0.000974, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-12', 'WALLST', 'S', '2026-11-11 13:15:00+00:00', '2026-11-11 14:15:00+00:00', 0.001201, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-12', 'WALLST', 'S', '2026-11-11 20:15:00+00:00', '2026-11-11 23:00:00+00:00', 0.001078, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-12', 'DAX', 'S', '2026-11-10 19:00:00+00:00', '2026-11-11 00:30:00+00:00', -0.002044, 'regime');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-12', 'DAX', 'S', '2026-11-11 16:00:00+00:00', '2026-11-11 18:00:00+00:00', -0.002527, 'regime');
