# -*- coding: utf-8 -*-
"""把「最新完整 OHLC 收盤」的掃描結果，與「再後一日收盤快照」的掃描結果併成更新層。

快照只有收盤價與成交量，沒有盤中高低，真實波幅無法計算，所以 ②③（R7-H 波動指數）
一律沿用基準日的值，快照日只重算 ①④⑤⑥。

用法：python3 build_update.py <base_scan.csv> <snap_scan.csv> <out.csv>
"""
import sys
import pandas as pd

base = pd.read_csv(sys.argv[1])
snap = pd.read_csv(sys.argv[2])
out = sys.argv[3]

b = base.set_index("ticker")
s = snap.set_index("ticker")
common = [t for t in b.index if t in s.index]

rows = []
for t in common:
    rb, rs = b.loc[t], s.loc[t]
    if str(rs["date"]) == str(rb["date"]):
        continue                      # 快照日沒有這檔的新資料
    four = bool(rs["c1"]) and bool(rs["c4"]) and bool(rs["c5"]) and bool(rs["c6"])
    rows.append(dict(
        ticker=t, lists=rb["lists"], score=int(rb["score"]),
        c2=bool(rb["c2"]), c3=bool(rb["c3"]), volidx=rb["volidx"],
        close_16=rb["close"], close_17=rs["close"],
        chg1d_pct=round((rs["close"] / rb["close"] - 1) * 100, 2) if rb["close"] else None,
        c1_17=bool(rs["c1"]), c4_17=bool(rs["c4"]), c5_17=bool(rs["c5"]), c6_17=bool(rs["c6"]),
        clock_17=rs["clock"], dist_grav_pct=rs["dist_grav_pct"], four_17=four,
        c5_days_17=rs["c5_days"], still_light_17=rs["still_light"]))

d = pd.DataFrame(rows)
d.to_csv(out, index=False, encoding="utf-8-sig")
NC = 6
still = d[(d.score == NC) & d.four_17]
lost = d[(d.score == NC) & (~d.four_17)]
fresh = d[(d.score != NC) & d.four_17 & d.c2 & d.c3]
print(f"基準 {base.date.max()} → 快照 {snap.date.max()}：覆蓋 {len(d)} / {len(base)} 檔")
print(f"  仍成立 {len(still)}：{' '.join(still.ticker)}")
print(f"  已失效 {len(lost)}：{' '.join(lost.ticker)}")
print(f"  新符合 {len(fresh)}：{' '.join(fresh.sort_values('volidx', ascending=False).ticker)}")
