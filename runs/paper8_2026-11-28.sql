CREATE TABLE IF NOT EXISTS pb8_equity (d TEXT PRIMARY KEY, equity REAL, shadow_equity REAL, open_positions INTEGER, closed_total INTEGER, closed_shadow INTEGER);
CREATE TABLE IF NOT EXISTS pb8_trades (id INTEGER PRIMARY KEY AUTOINCREMENT, d TEXT, sym TEXT, side TEXT, opened TEXT, closed TEXT, ret REAL, how TEXT);
INSERT OR REPLACE INTO pb8_equity (d, equity, shadow_equity, open_positions, closed_total, closed_shadow) VALUES ('2026-11-28', 1983.8366, 2000.6220, 0, 118, 585);
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-28', 'WALLST', 'S', '2026-11-27 00:00:00+00:00', '2026-11-27 01:00:00+00:00', 0.001317, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-28', 'DAX', 'S', '2026-11-27 00:00:00+00:00', '2026-11-27 00:15:00+00:00', 0.001020, 'sold');
