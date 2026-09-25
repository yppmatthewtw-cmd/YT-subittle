#!/bin/bash
# r9 報表重建：HTML + CSV + XLSX（基準 09-24 完整 OHLC；09-22 缺口以 Nasdaq 收盤補；附與 r8 對照）
set -e
S=/tmp/claude-0/-home-user-YT-subittle/0bd65ef0-0bef-5829-9a6f-f0a46d2d96cd/scratchpad
W=/home/user/YT-subittle/trading-signal-analysis/watchlist
cp $S/base_r9.csv $S/scan_r7_result.csv
python3 -c "
import json,pandas as pd; d=pd.read_csv('$S/base_r9.csv')
json.dump({'missing': [], 'n': len(d), 'lastday': str(d.date.max())}, open('$S/scan_r7_meta.json','w'))"
export PANEL_N="${PANEL_N:?set PANEL_N}"
(cd $S && python3 notes_r9.py >/dev/null)
source $S/notes_r9.env
export VER=r9 BASE_DAY=09-24 SNAP_DAY=09-24
export UNIVERSE_CSV=$S/universe_r9.csv CHATHITS_CSV=$S/chat_hits_r9.csv SRC_ROWS=$S/src_rows_r9.csv
unset UPDATE_CSV
export PREV_CSV=$S/r8keep/base_r8.csv PREV_VER=r8 PREV_DAY=09-21
# REMAP_NOTE 由 notes_r9.py 依資料算出
export SRC_NOTE="來源：三個 session 的最新成品 —— chat 1 R21 動能回調（09-23 收盤）、chat 2 Combined R22（09-16）、chat 3 SubSector R12 / AI R13 / 加息 R2（09-17）；價格資料已於 2026-09-25 01:3x UTC 由各 repo 的 GitHub Actions 重新抓取，完整 OHLC 至 09-24，09-22 缺口以 Nasdaq 官方收盤補。"
cd $W
rm -f "$W"/R7_six_criteria_scan_r9*
python3 build_r7_scan_html.py >/dev/null
H=$(ls R7_six_criteria_scan_r9*.html | head -1); B="${H%.html}"
cp "$S/universe_r9.csv" "${B}_加掃.csv"; cp "$S/chat_hits_r9_both.json" "${B}_chat1-3命中_both.json"
python3 - "$S/chat_hits_r9.csv" "${B}_chat1-3命中.csv" <<'PY2'
import sys, pandas as pd
d = pd.read_csv(sys.argv[1])
d = d.drop(columns=[c for c in ("four_17", "close_17", "chg1d_pct", "clock_17") if c in d.columns and d[c].isna().all()])
d.to_csv(sys.argv[2], index=False, encoding="utf-8-sig")
PY2
python3 csv_to_xlsx.py "$B.csv" "$B.xlsx" >/dev/null
ls -la "$W"/R7_six_criteria_scan_r9*
