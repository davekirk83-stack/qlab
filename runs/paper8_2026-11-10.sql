CREATE TABLE IF NOT EXISTS pb8_equity (d TEXT PRIMARY KEY, equity REAL, shadow_equity REAL, open_positions INTEGER, closed_total INTEGER, closed_shadow INTEGER);
CREATE TABLE IF NOT EXISTS pb8_trades (id INTEGER PRIMARY KEY AUTOINCREMENT, d TEXT, sym TEXT, side TEXT, opened TEXT, closed TEXT, ret REAL, how TEXT);
INSERT OR REPLACE INTO pb8_equity (d, equity, shadow_equity, open_positions, closed_total, closed_shadow) VALUES ('2026-11-10', 2004.6760, 1998.1232, 0, 61, 305);
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-10', 'WALLST', 'S', '2026-11-09 03:30:00+00:00', '2026-11-09 04:30:00+00:00', -0.000857, 'regime');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-10', 'WALLST', 'S', '2026-11-09 11:00:00+00:00', '2026-11-09 14:30:00+00:00', -0.000006, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-10', 'DAX', 'S', '2026-11-09 03:15:00+00:00', '2026-11-09 05:00:00+00:00', 0.001726, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-10', 'NQ', 'S', '2026-11-09 16:00:00+00:00', '2026-11-09 16:15:00+00:00', -0.013823, 'break');
