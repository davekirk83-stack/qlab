CREATE TABLE IF NOT EXISTS pb8_equity (d TEXT PRIMARY KEY, equity REAL, shadow_equity REAL, open_positions INTEGER, closed_total INTEGER, closed_shadow INTEGER);
CREATE TABLE IF NOT EXISTS pb8_trades (id INTEGER PRIMARY KEY AUTOINCREMENT, d TEXT, sym TEXT, side TEXT, opened TEXT, closed TEXT, ret REAL, how TEXT);
INSERT OR REPLACE INTO pb8_equity (d, equity, shadow_equity, open_positions, closed_total, closed_shadow) VALUES ('2026-11-04', 2017.5593, 1998.0667, 0, 50, 250);
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-04', 'WALLST', 'L', '2026-11-02 20:30:00+00:00', '2026-11-03 01:00:00+00:00', -0.001524, 'regime');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-04', 'DAX', 'L', '2026-11-02 19:30:00+00:00', '2026-11-03 03:00:00+00:00', -0.002210, 'regime');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-04', 'DAX', 'L', '2026-11-03 19:45:00+00:00', '2026-11-03 23:00:00+00:00', 0.001093, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-04', 'DAX', 'S', '2026-11-03 23:15:00+00:00', '2026-11-03 23:30:00+00:00', 0.001449, 'sold');
