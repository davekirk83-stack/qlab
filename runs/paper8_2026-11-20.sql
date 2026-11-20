CREATE TABLE IF NOT EXISTS pb8_equity (d TEXT PRIMARY KEY, equity REAL, shadow_equity REAL, open_positions INTEGER, closed_total INTEGER, closed_shadow INTEGER);
CREATE TABLE IF NOT EXISTS pb8_trades (id INTEGER PRIMARY KEY AUTOINCREMENT, d TEXT, sym TEXT, side TEXT, opened TEXT, closed TEXT, ret REAL, how TEXT);
INSERT OR REPLACE INTO pb8_equity (d, equity, shadow_equity, open_positions, closed_total, closed_shadow) VALUES ('2026-11-20', 2001.7148, 2000.0134, 0, 98, 485);
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-20', 'WALLST', 'S', '2026-11-19 08:00:00+00:00', '2026-11-19 09:15:00+00:00', 0.001353, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-20', 'WALLST', 'L', '2026-11-19 14:15:00+00:00', '2026-11-19 14:30:00+00:00', 0.001326, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-20', 'DAX', 'L', '2026-11-19 12:15:00+00:00', '2026-11-19 16:15:00+00:00', -0.008083, 'regime');
