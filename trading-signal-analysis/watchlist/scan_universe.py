# -*- coding: utf-8 -*-
"""把合併面板裡的每一檔都跑一次 R7 六項條件（不只 watchlist 內的）。
流動性門檻用「20 日均額」= 最近 20 根 (收盤 × 成交量) 的平均，而不是股數：BRK/A 每天只成交 200 股，但金額 1.45 億美元。
（r8 以前誤用「最後收盤 × 20 日均量」，股價在窗口內大幅跳動時會高估或低估。）
另外：最後一根不在面板最新交易日的不掃；同一證券的點／槓／斜線寫法（BF.B 與 BF/B）只留資料最長的一個。
用法：python3 scan_universe.py out.csv [min_price] [min_turnover_usd]"""
import sys, os
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_r7 import load, scan_one

out = sys.argv[1]
MINP = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
MINT = float(sys.argv[3]) if len(sys.argv) > 3 else 3_000_000   # 20 日均額 (美元)

d = load()
last = d.date.max()
counts = d.groupby("symbol").size()
# 同一證券不同寫法：以「去掉分隔符」的鍵分組，取根數最多者；同根數優先斜線（Nasdaq 快照的寫法）
key = {s: s.replace(".", "/").replace("-", "/") for s in counts.index}
best = {}
for s in sorted(counts.index):
    k = key[s]
    if k not in best or (counts[s], "/" in s) > (counts[best[k]], "/" in best[k]):
        best[k] = s
keep = set(best.values())
dup = len(counts) - len(keep)

rows, skipped, stale = [], 0, 0
for s, g in d.groupby("symbol", sort=True):
    if s not in keep:
        continue
    if g.date.iloc[-1] != last:
        stale += 1
        continue
    if len(g) < 80 or g.close.iloc[-1] < MINP or (g.close * g.volume).tail(20).mean() < MINT:
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
print(f"scanned {len(df)}  skipped {skipped}  stale {stale}  alias-dups {dup}")
print(df.score.value_counts().sort_index().to_dict())
print(df[df.score == 6][["ticker", "volidx", "clock", "c5_days", "dist_grav_pct"]].to_string())
