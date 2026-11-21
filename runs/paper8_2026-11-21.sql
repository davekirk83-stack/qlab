CREATE TABLE IF NOT EXISTS pb8_equity (d TEXT PRIMARY KEY, equity REAL, shadow_equity REAL, open_positions INTEGER, closed_total INTEGER, closed_shadow INTEGER);
CREATE TABLE IF NOT EXISTS pb8_trades (id INTEGER PRIMARY KEY AUTOINCREMENT, d TEXT, sym TEXT, side TEXT, opened TEXT, closed TEXT, ret REAL, how TEXT);
INSERT OR REPLACE INTO pb8_equity (d, equity, shadow_equity, open_positions, closed_total, closed_shadow) VALUES ('2026-11-21', 1994.3265, 1999.9864, 0, 101, 500);
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-21', 'WALLST', 'L', '2026-11-20 17:30:00+00:00', '2026-11-20 18:45:00+00:00', 0.003941, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-21', 'NQ', 'S', '2026-11-20 14:45:00+00:00', '2026-11-20 15:00:00+00:00', 0.006905, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-21', 'NQ', 'L', '2026-11-20 15:15:00+00:00', '2026-11-20 20:45:00+00:00', -0.025610, 'regime');
