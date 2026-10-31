CREATE TABLE IF NOT EXISTS pb11_equity (d TEXT, book TEXT, equity REAL, shadow_equity REAL, open_positions INTEGER, closed_total INTEGER, closed_shadow INTEGER, PRIMARY KEY (d, book));
CREATE TABLE IF NOT EXISTS pb11_trades (d TEXT, book TEXT, sym TEXT, opened TEXT, closed TEXT, ret REAL, r_mult REAL, how TEXT, shadow INTEGER);
INSERT OR REPLACE INTO pb11_equity VALUES ('2026-10-31', 'MV', 2000.0000, 2000.0000, 0, 0, 0);
INSERT OR REPLACE INTO pb11_equity VALUES ('2026-10-31', 'EP', 2000.0000, 2000.0000, 0, 0, 0);
CREATE TABLE IF NOT EXISTS pb11_cloud (d TEXT, book TEXT, cloud_equity REAL, closed_cloud INTEGER, PRIMARY KEY (d, book));
CREATE TABLE IF NOT EXISTS pb11_trade_cloud (book TEXT, sym TEXT, opened TEXT, cloud INTEGER, PRIMARY KEY (book, sym, opened));
INSERT OR REPLACE INTO pb11_cloud VALUES ('2026-10-31', 'MV', 2000.0000, 0);
INSERT OR REPLACE INTO pb11_cloud VALUES ('2026-10-31', 'EP', 2000.0000, 0);