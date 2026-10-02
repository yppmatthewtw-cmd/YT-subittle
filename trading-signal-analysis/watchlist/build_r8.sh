#!/bin/bash
# r8 報表重建：HTML + CSV + XLSX（基準 09-21 完整 OHLC、快照 09-23）
set -e
S=/tmp/claude-0/-home-user-YT-subittle/0bd65ef0-0bef-5829-9a6f-f0a46d2d96cd/scratchpad
W=/home/user/YT-subittle/trading-signal-analysis/watchlist
B="${B:-R7_six_criteria_scan_r8 (09_24; 09.32)}"
cp $S/base_r8.csv $S/scan_r7_result.csv
python3 -c "
import json,pandas as pd; d=pd.read_csv('$S/base_r8.csv')
json.dump({'missing': [], 'n': len(d), 'lastday': str(d.date.max())}, open('$S/scan_r7_meta.json','w'))"
(cd $S && python3 notes_r8.py >/dev/null)
source $S/notes_r8.env
export VER=r8 BASE_DAY=09-21 SNAP_DAY=09-23 PANEL_N=3,097
export UNIVERSE_CSV=$S/universe_r8.csv UPDATE_CSV=$S/update_r8.csv CHATHITS_CSV=$S/chat_hits_r8.csv SRC_ROWS=$S/src_rows_r8.csv
export REMAP_NOTE="3 檔重對應：BRK-A→BRK/A、BRK-B→BRK/B、BF.B→BF/B；20MA 鏡像另有一份寫成 BF.B 的相同資料，同根數時固定取斜線寫法（Nasdaq 快照的寫法）"
export SRC_NOTE="來源：三個 session 的最新成品（榜單本身仍是 09-16／09-17 基準的 R22／R20／R12／R13／R2，三個 repo 自 09-18 起沒有新成品；價格資料已於 2026-09-24 01:21–01:25 UTC 由各 repo 的 GitHub Actions 重新抓取：完整 OHLC 至 09-21，09-22、09-23 為 Nasdaq 官方收盤快照）。"
cd $W
rm -f "$W"/R7_six_criteria_scan_r8*
python3 build_r7_scan_html.py >/dev/null
H=$(ls R7_six_criteria_scan_r8*.html | head -1); B="${H%.html}"
cp "$S/universe_r8.csv" "${B}_加掃.csv"; cp "$S/chat_hits_r8_both.json" "${B}_chat1-3命中_both.json"
# 交付用 CSV：把內部沿用的 _16 / _17 欄名換成實際日期（09-21 基準、09-23 快照）
python3 - "$S/update_r8.csv" "${B}_0923更新.csv" "$S/chat_hits_r8.csv" "${B}_chat1-3命中.csv" <<'PY2'
import sys, pandas as pd
ren = {"close_16": "close_0921", "close_17": "close_0923", "chg1d_pct": "chg_0921_0923_pct"}
for a in ("c1", "c4", "c5", "c6", "clock", "four", "c5_days", "still_light"):
    ren[f"{a}_17"] = f"{a}_0923"
for src, dst in ((sys.argv[1], sys.argv[2]), (sys.argv[3], sys.argv[4])):
    pd.read_csv(src).rename(columns=ren).to_csv(dst, index=False, encoding="utf-8-sig")
PY2
python3 csv_to_xlsx.py "$B.csv" "$B.xlsx" >/dev/null
ls -la "$W"/R7_six_criteria_scan_r8*
