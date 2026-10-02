# -*- coding: utf-8 -*-
"""
以 R7 六項條件 (r3) 掃描 AI Sector Watchlist 的全部成分股。
輸入：AI_Sector_watchlist_R*.xlsx（成分股資金流 Constituents + 總表 All 兩張表）
輸出：CSV（附 AI 小群組 / 大分類 / 組別名次 / 5 日強度 / 5 日漲跌），再交給 csv_to_xlsx.py 轉 Excel。
用法：python3 scan_ai_watchlist.py <AI_Sector_watchlist.xlsx> <out.csv>
"""
import sys, os, re
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_r7 import load, scan_one

src = sys.argv[1]
out = sys.argv[2]
xl = pd.ExcelFile(src)


def header_row(df, key):
    for i in range(min(15, len(df))):
        if any(str(v).strip() == key for v in df.iloc[i].values):
            return i
    raise SystemExit(f"找不到表頭 {key}")


# ── 成分股：組別名次 / 所屬群組 / 代號 / 5 日強度 tf5 / 5 日漲跌% ──
c = xl.parse("成分股資金流 Constituents", header=None)
h = header_row(c, "代號")
c.columns = [str(v).replace("\n", "") for v in c.iloc[h]]
c = c.iloc[h + 1:].dropna(subset=["代號"])
c["代號"] = c["代號"].astype(str).str.strip().str.upper()

# ── 總表：小群組 English 欄帶編號 (如 "E1 Server ODM/OEM…")、分類、名次 ──
a = xl.parse("總表 All", header=None)
ha = header_row(a, "名次")
a.columns = [str(v).replace("\n", "") for v in a.iloc[ha]]
a = a.iloc[ha + 1:].dropna(subset=["名次"])
gmap = {}
for _, r in a.iterrows():
    gmap[str(r["名稱"]).strip()] = dict(code=str(r["English"]).split()[0], cat=str(r["分類"]).strip(),
                                        rank=int(r["名次"]), gscore=r.get("5日分數"))

d = load()
d["symbol"] = d["symbol"].str.upper()
have = set(d.symbol.unique())
rows, missing = [], []
for _, r in c.iterrows():
    t = r["代號"]
    s = t if t in have else (t.replace(".", "-") if t.replace(".", "-") in have else None)
    if s is None:
        missing.append(t)
        continue
    res = scan_one(t, d[d.symbol == s])
    if res is None:
        missing.append(t)
        continue
    g = gmap.get(str(r["所屬群組"]).strip(), {})
    res["lists"] = "AI_Sector"
    res["ai_cat"] = g.get("cat", "")
    res["ai_group"] = (g.get("code", "") + " " + str(r["所屬群組"]).strip()).strip()
    res["ai_rank"] = g.get("rank", r.get("組別名次"))
    res["ai_flow5"] = f'{float(r["5日強度 tf5"]):+.4f}' if pd.notna(r.get("5日強度 tf5")) else ""
    res["ai_chg5"] = round(float(r["5日漲跌%"]) * 100, 2) if pd.notna(r.get("5日漲跌%")) else None
    rows.append(res)

df = pd.DataFrame(rows).sort_values(["score", "c5_days", "volidx"], ascending=[False, True, False])
df.to_csv(out, index=False, encoding="utf-8-sig")
print(f"scanned {len(df)} / {len(c)}  missing: {missing}")
print(df.score.value_counts().sort_index().to_dict())
print(df[df.score >= 5][["ticker", "score", "ai_group", "volidx", "clock", "c5_days"]].to_string())
