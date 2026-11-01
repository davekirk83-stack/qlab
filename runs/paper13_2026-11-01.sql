CREATE TABLE IF NOT EXISTS pb13_equity (d TEXT PRIMARY KEY, equity REAL, ignition_alone REAL, max_dd REAL, closed_total INTEGER);
CREATE TABLE IF NOT EXISTS pb13_trades (d TEXT, eng TEXT, opened TEXT, closed TEXT, pnl REAL, margin REAL);
INSERT OR REPLACE INTO pb13_equity VALUES ('2026-11-01', 500.0000, 500.0000, 0.0000, 0);
DELETE FROM pb13_trades;