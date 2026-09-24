# -*- coding: utf-8 -*-
"""r8 的版本敘述：寫成 env 檔給 csv_to_xlsx.py / build_r7_scan_html.py 讀。"""
import pandas as pd, json, sys
S = "/tmp/claude-0/-home-user-YT-subittle/0bd65ef0-0bef-5829-9a6f-f0a46d2d96cd/scratchpad"
b = pd.read_csv(f"{S}/base_r8.csv"); u = pd.read_csv(f"{S}/universe_r8.csv"); up = pd.read_csv(f"{S}/update_r8.csv")
n6 = int((b.score == 6).sum())
# Yahoo 已出的 09-22 / 09-23 日線 vs Nasdaq 官方收盤快照（逐檔）
y = pd.concat([pd.read_csv(f"{S}/eod2/vcp_eod_2025-09-01_2026-09-24.csv.gz"),
               pd.read_csv(f"{S}/eod/eod_10ma_2025-12-26_2026-09-24.csv.gz"),
               pd.read_csv(f"{S}/eod/eod_20ma_2025-09-01_2026-09-24.csv.gz")]).drop_duplicates(["symbol", "date"])
chk = {}
for dt in ("2026-09-22", "2026-09-23"):
    sn = pd.read_csv(f"/home/user/yppmatthewtw-cmd/10ma-watchlist/data/snapshots/{dt}.csv")
    sn["px"] = pd.to_numeric(sn.lastsale.astype(str).str.replace(r"[$,]", "", regex=True), errors="coerce")
    sn["symbol"] = sn.symbol.astype(str).str.upper().str.strip()
    m = y[y.date == dt].merge(sn[["symbol", "px"]], on="symbol")
    dc = (m.close / m.px - 1).abs() * 100
    chk[dt] = (int((y.date == dt).sum()), len(m), float(dc.max()), int((dc > 0.05).sum()))
print("yahoo vs nasdaq:", chk)
yv = {dt: y[y.date == dt].symbol.nunique() for dt in ("2026-09-22", "2026-09-23")}
still = up[(up.score == 6) & up.four_17]; fresh = up[(up.score != 6) & up.four_17 & up.c2 & up.c3]
data = ("本版資料：再次觸發三個 repo 的 GitHub Actions（fetch_yahoo_eod ×3、fetch_eod_snapshot）抓到 09-24 01:25 UTC（美東 09-23 收盤後約 5.5 小時）。"
        f"Yahoo 的 09-22 日線三鏡像合計仍只出了 {yv['2026-09-22']} 檔（09-23 {yv['2026-09-23']} 檔；完整交易日約 3,040 檔），連 20MA repo 的 tail 路線（5 日相對期間 / 小時線）也只補到 65 檔 09-22 日線，"
        "所以完整 OHLC 的最新交易日仍是 09-21，六項條件的基準與 r7 相同；09-22、09-23 兩天用 10MA repo 的 Nasdaq 官方收盤快照（各 3,078 檔、760/760 全覆蓋）更新 ①④⑤⑥。"
        f"Yahoo 已出的 09-22（{chk['2026-09-22'][1]} 檔）與 09-23（{chk['2026-09-23'][1]} 檔）收盤和 Nasdaq 快照逐檔比對，"
        f"最大差異 {max(chk['2026-09-22'][2], chk['2026-09-23'][2]):.3f}%，差 >0.05% 的 {chk['2026-09-22'][3] + chk['2026-09-23'][3]} 檔。")
panel = ("面板修正：同一檔同一天在多份鏡像都有資料時，改取抓取窗口較新的那份（r7 以前取檔名排序在前的舊檔，舊檔裡的當日值可能是收盤前的半日值）。"
         f"重算後 760 檔的六項命中數與 r7 逐檔相同，只有 84 檔的重心線或波動指數有 ≤0.3% / ≤0.7 點的小幅變動（Yahoo 事後修訂的成交量與高低價）。"
         "760 檔最後一根全部落在 09-21，0 檔停在舊日期。")
html = ("r8：條件與 r3–r7 相同。" + data + " " + panel +
        f" 本版真正的新資訊是 <b>09-23 收盤</b>：{n6} 檔全中裡 {len(still)} 檔在 09-23 收盤下 ①④⑤⑥ 仍成立，另有 {len(fresh)} 檔新符合。")
env = {"DATA_NOTE": data, "PANEL_NOTE": panel, "HTML_NOTE": html}
with open(f"{S}/notes_r8.env", "w") as f:
    for k, v in env.items():
        f.write(f"export {k}={json.dumps(v, ensure_ascii=False)}\n")
# 來源分頁：加掃一列改由資料算出（r7 的這一列沿用了 r5 的 09-16 / 2,584）
src = pd.read_csv(f"{S}/src_rows.csv")
src.loc[src.Session == "加掃", ["Repo / 取得方式", "成品基準日", "取用檔數"]] = [
    "三個 repo 的 Yahoo 鏡像併集 3,097 檔", "2026-09-21", str(len(u))]
src.loc[len(src)] = ["價格資料", "三個 repo 的 fetch_yahoo_eod（09-24 01:21–01:25 UTC）＋ 10MA fetch_eod_snapshot（09-22、09-23）",
                     "完整 OHLC 至 09-21；09-22 / 09-23 為 Nasdaq 官方收盤快照", "2026-09-23", "3,097"]
src.to_csv(f"{S}/src_rows_r8.csv", index=False, encoding="utf-8-sig")
print(open(f"{S}/notes_r8.env").read()[:600]); print(src.tail(3).to_string())
