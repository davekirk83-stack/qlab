UPDATE pb_positions SET status='closed', closed='2026-11-09', exit_px=0.04214811, exit_reason='stop', ret=-0.209683, pnl=-33.4 WHERE sym='MEUSD' AND opened='2026-11-02' AND status='open';
INSERT INTO pb_positions (sym,opened,entry,stop,target,atr,margin,lev,status) VALUES ('BOBAUSD','2026-11-09',0.0159,0.01300714,0.01638214,0.00096429,54.23,3.0,'open');
INSERT INTO pb_positions (sym,opened,entry,stop,target,atr,margin,lev,status) VALUES ('ETHUSD','2026-11-09',2090.49,1801.71857143,2138.61857143,96.25714286,54.23,3.0,'open');
INSERT INTO pb_positions (sym,opened,entry,stop,target,atr,margin,lev,status) VALUES ('GFIUSD','2026-11-09',0.0301,0.02437857,0.03105357,0.00190714,54.23,3.0,'open');
INSERT INTO pb_positions (sym,opened,entry,stop,target,atr,margin,lev,status) VALUES ('HNTUSD','2026-11-09',0.2748,0.17335714,0.29170714,0.03381429,54.23,3.0,'open');
INSERT INTO pb_positions (sym,opened,entry,stop,target,atr,margin,lev,status) VALUES ('HOPRUSD','2026-11-09',0.010262,0.0079415,0.01064875,0.0007735,54.23,3.0,'open');
INSERT INTO pb_positions (sym,opened,entry,stop,target,atr,margin,lev,status) VALUES ('KRLUSD','2026-11-09',0.1313,0.12652143,0.13209643,0.00159286,54.23,3.0,'open');
INSERT INTO pb_positions (sym,opened,entry,stop,target,atr,margin,lev,status) VALUES ('TOSHIUSD','2026-11-09',9.053e-05,7.233e-05,9.356e-05,6.07e-06,54.23,3.0,'open');
INSERT OR REPLACE INTO pb_equity (d,equity,open_pos,gate,signals_seen,taken,dropped,note) VALUES ('2026-11-09',2169.14,22,1,7,7,0,'7 signals, 7 taken, 0 dropped, 1 closed, 22 open');