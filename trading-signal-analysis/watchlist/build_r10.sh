#!/bin/bash
# r9 報表重建：HTML + CSV + XLSX（基準 09-24 完整 OHLC；09-22 缺口以 Nasdaq 收盤補；附與 r8 對照）
set -e
S=/tmp/claude-0/-home-user-YT-subittle/0bd65ef0-0bef-5829-9a6f-f0a46d2d96cd/scratchpad
W=/home/user/YT-subittle/trading-signal-analysis/watchlist
cp $S/base_r10.csv $S/scan_r7_result.csv
python3 -c "
import json,pandas as pd; d=pd.read_csv('$S/base_r10.csv')
json.dump({'missing': [], 'n': len(d), 'lastday': str(d.date.max())}, open('$S/scan_r7_meta.json','w'))"
export PANEL_N="${PANEL_N:?set PANEL_N}"
(cd $S && python3 notes_r10.py >/dev/null)
source $S/notes_r10.env
export VER=r10 BASE_DAY=10-01 SNAP_DAY=10-01
export UNIVERSE_CSV=$S/universe_r10.csv CHATHITS_CSV=$S/chat_hits_r10.csv SRC_ROWS=$S/src_rows_r10.csv
unset UPDATE_CSV
export PREV_CSV=$S/r9keep/base_r9.csv PREV_VER=r9 PREV_DAY=09-24
# REMAP_NOTE 由 notes_r10.py 依資料算出
export SRC_NOTE="來源：三個 session 的最新成品 —— chat 1 R23 熱錢回落 20MA（09-30 收盤）、chat 2 Combined R22（09-16）、chat 3 SubSector R12 / AI R13 / 加息 R2（09-17）；價格資料已於 2026-10-01 23:18–23:23 UTC 由各 repo 的 GitHub Actions 重新抓取，完整 OHLC 至 10-01；Nasdaq 快照逐份與 Yahoo 收盤核對日期後才使用。"
cd $W
rm -f "$W"/R7_six_criteria_scan_r10*
python3 build_r7_scan_html.py >/dev/null
H=$(ls R7_six_criteria_scan_r10*.html | head -1); B="${H%.html}"
cp "$S/universe_r10.csv" "${B}_加掃.csv"; cp "$S/chat_hits_r10_both.json" "${B}_chat1-3命中_both.json"
python3 - "$S/chat_hits_r10.csv" "${B}_chat1-3命中.csv" <<'PY2'
import sys, pandas as pd
d = pd.read_csv(sys.argv[1])
d = d.drop(columns=[c for c in ("four_17", "close_17", "chg1d_pct", "clock_17") if c in d.columns and d[c].isna().all()])
d.to_csv(sys.argv[2], index=False, encoding="utf-8-sig")
PY2
python3 csv_to_xlsx.py "$B.csv" "$B.xlsx" >/dev/null
ls -la "$W"/R7_six_criteria_scan_r10*
