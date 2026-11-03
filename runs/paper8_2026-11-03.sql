CREATE TABLE IF NOT EXISTS pb8_equity (d TEXT PRIMARY KEY, equity REAL, shadow_equity REAL, open_positions INTEGER, closed_total INTEGER, closed_shadow INTEGER);
CREATE TABLE IF NOT EXISTS pb8_trades (id INTEGER PRIMARY KEY AUTOINCREMENT, d TEXT, sym TEXT, side TEXT, opened TEXT, closed TEXT, ret REAL, how TEXT);
INSERT OR REPLACE INTO pb8_equity (d, equity, shadow_equity, open_positions, closed_total, closed_shadow) VALUES ('2026-11-03', 2018.1607, 1996.6533, 2, 46, 230);
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-03', 'WALLST', 'S', '2026-11-02 09:30:00+00:00', '2026-11-02 12:00:00+00:00', 0.000515, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-03', 'WALLST', 'L', '2026-11-02 12:30:00+00:00', '2026-11-02 13:00:00+00:00', 0.001220, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-03', 'DAX', 'L', '2026-11-02 12:30:00+00:00', '2026-11-02 13:30:00+00:00', 0.001834, 'sold');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-03', 'DAX', 'S', '2026-11-02 13:30:00+00:00', '2026-11-02 15:15:00+00:00', -0.002040, 'regime');
INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('2026-11-03', 'NQ', 'L', '2026-11-02 17:30:00+00:00', '2026-11-02 19:30:00+00:00', -0.008281, 'break');
