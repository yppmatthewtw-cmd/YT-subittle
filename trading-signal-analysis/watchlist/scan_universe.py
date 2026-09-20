# -*- coding: utf-8 -*-
"""把合併面板裡的每一檔都跑一次 R7 六項條件（不只 watchlist 內的）。
流動性門檻用「20 日均額」而不是股數：BRK/A 每天只成交 200 股，但金額 1.45 億美元。
用法：python3 scan_universe.py out.csv [min_price] [min_turnover_usd]"""
import sys, os
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_r7 import load, scan_one

out = sys.argv[1]
MINP = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
MINT = float(sys.argv[3]) if len(sys.argv) > 3 else 3_000_000   # 20 日均額 (美元)

d = load()
rows, skipped = [], 0
for s, g in d.groupby("symbol", sort=True):
    if len(g) < 80 or g.close.iloc[-1] < MINP or g.close.iloc[-1] * g.volume.tail(20).mean() < MINT:
        skipped += 1
        continue
    r = scan_one(s, g)
    if r is None:
        skipped += 1
        continue
    r["lists"] = "universe"
    rows.append(r)
df = pd.DataFrame(rows).sort_values(["score", "c5_days", "volidx"], ascending=[False, True, False])
df.to_csv(out, index=False, encoding="utf-8-sig")
print(f"scanned {len(df)}  skipped {skipped}")
print(df.score.value_counts().sort_index().to_dict())
print(df[df.score == 6][["ticker", "volidx", "clock", "c5_days", "dist_grav_pct"]].to_string())
