CREATE TABLE IF NOT EXISTS pb8_equity (d TEXT PRIMARY KEY, equity REAL, shadow_equity REAL, open_positions INTEGER, closed_total INTEGER, closed_shadow INTEGER);
CREATE TABLE IF NOT EXISTS pb8_trades (id INTEGER PRIMARY KEY AUTOINCREMENT, d TEXT, sym TEXT, side TEXT, opened TEXT, closed TEXT, ret REAL, how TEXT);
INSERT OR REPLACE INTO pb8_equity (d, equity, shadow_equity, open_positions, closed_total, closed_shadow) VALUES ('2026-10-29', 2017.4585, 1999.8173, 0, 30, 150);
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-10-29', 'WALLST', 'L', '2026-10-28 01:00:00+00:00', '2026-10-28 06:30:00+00:00', -0.001920, 'regime');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-10-29', 'WALLST', 'S', '2026-10-28 14:15:00+00:00', '2026-10-28 18:00:00+00:00', 0.001329, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-10-29', 'DAX', 'S', '2026-10-28 16:45:00+00:00', '2026-10-28 18:15:00+00:00', 0.001953, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-10-29', 'NQ', 'L', '2026-10-28 13:45:00+00:00', '2026-10-28 16:45:00+00:00', 0.001500, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-10-29', 'NQ', 'S', '2026-10-28 18:30:00+00:00', '2026-10-28 18:45:00+00:00', 0.003418, 'sold');
