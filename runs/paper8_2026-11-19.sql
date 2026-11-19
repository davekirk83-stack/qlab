CREATE TABLE IF NOT EXISTS pb8_equity (d TEXT PRIMARY KEY, equity REAL, shadow_equity REAL, open_positions INTEGER, closed_total INTEGER, closed_shadow INTEGER);
CREATE TABLE IF NOT EXISTS pb8_trades (id INTEGER PRIMARY KEY AUTOINCREMENT, d TEXT, sym TEXT, side TEXT, opened TEXT, closed TEXT, ret REAL, how TEXT);
INSERT OR REPLACE INTO pb8_equity (d, equity, shadow_equity, open_positions, closed_total, closed_shadow) VALUES ('2026-11-19', 2004.4230, 1998.7801, 0, 95, 470);
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-19', 'WALLST', 'L', '2026-11-18 12:30:00+00:00', '2026-11-18 13:30:00+00:00', 0.001889, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-19', 'DAX', 'S', '2026-11-18 08:00:00+00:00', '2026-11-18 09:00:00+00:00', 0.002029, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-19', 'DAX', 'L', '2026-11-18 12:30:00+00:00', '2026-11-18 15:45:00+00:00', -0.005616, 'regime');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-19', 'NQ', 'L', '2026-11-18 14:30:00+00:00', '2026-11-18 15:00:00+00:00', 0.005434, 'sold');
