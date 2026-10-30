CREATE TABLE IF NOT EXISTS pb8_equity (d TEXT PRIMARY KEY, equity REAL, shadow_equity REAL, open_positions INTEGER, closed_total INTEGER, closed_shadow INTEGER);
CREATE TABLE IF NOT EXISTS pb8_trades (id INTEGER PRIMARY KEY AUTOINCREMENT, d TEXT, sym TEXT, side TEXT, opened TEXT, closed TEXT, ret REAL, how TEXT);
INSERT OR REPLACE INTO pb8_equity (d, equity, shadow_equity, open_positions, closed_total, closed_shadow) VALUES ('2026-10-30', 2020.8879, 1999.6279, 0, 34, 170);
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-10-30', 'WALLST', 'S', '2026-10-29 01:00:00+00:00', '2026-10-29 06:30:00+00:00', -0.000628, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-10-30', 'DAX', 'S', '2026-10-29 05:00:00+00:00', '2026-10-29 06:00:00+00:00', 0.001340, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-10-30', 'DAX', 'L', '2026-10-29 07:45:00+00:00', '2026-10-29 08:00:00+00:00', 0.002073, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-10-30', 'NQ', 'L', '2026-10-29 13:30:00+00:00', '2026-10-29 14:00:00+00:00', 0.004014, 'sold');
