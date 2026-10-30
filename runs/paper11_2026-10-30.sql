CREATE TABLE IF NOT EXISTS pb11_equity (d TEXT, book TEXT, equity REAL, shadow_equity REAL, open_positions INTEGER, closed_total INTEGER, closed_shadow INTEGER, PRIMARY KEY (d, book));
CREATE TABLE IF NOT EXISTS pb11_trades (d TEXT, book TEXT, sym TEXT, opened TEXT, closed TEXT, ret REAL, r_mult REAL, how TEXT, shadow INTEGER);
INSERT OR REPLACE INTO pb11_equity VALUES ('2026-10-30', 'MV', 2000.0000, 2000.0000, 0, 0, 0);
INSERT OR REPLACE INTO pb11_equity VALUES ('2026-10-30', 'EP', 2000.0000, 2000.0000, 0, 0, 0);