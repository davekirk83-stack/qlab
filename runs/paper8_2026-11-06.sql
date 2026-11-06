CREATE TABLE IF NOT EXISTS pb8_equity (d TEXT PRIMARY KEY, equity REAL, shadow_equity REAL, open_positions INTEGER, closed_total INTEGER, closed_shadow INTEGER);
CREATE TABLE IF NOT EXISTS pb8_trades (id INTEGER PRIMARY KEY AUTOINCREMENT, d TEXT, sym TEXT, side TEXT, opened TEXT, closed TEXT, ret REAL, how TEXT);
INSERT OR REPLACE INTO pb8_equity (d, equity, shadow_equity, open_positions, closed_total, closed_shadow) VALUES ('2026-11-06', 2007.5344, 1997.8127, 0, 55, 275);
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-06', 'WALLST', 'S', '2026-11-05 13:00:00+00:00', '2026-11-05 14:00:00+00:00', 0.001542, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-06', 'WALLST', 'L', '2026-11-05 14:30:00+00:00', '2026-11-05 14:45:00+00:00', -0.008355, 'break');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-06', 'DAX', 'L', '2026-11-05 14:30:00+00:00', '2026-11-05 16:00:00+00:00', -0.009067, 'regime');
