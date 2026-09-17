# -*- coding: utf-8 -*-
"""R7_six_criteria_scan CSV → Excel：Ticker 帶 TradingView 超連結；分頁：六項全中(淺紅 1/2/3 根) / 差一項 / 全部 / 說明。"""
import sys, glob, os
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

TV = "https://www.tradingview.com/chart/Q1c5VWwD/?symbol="
src = sys.argv[1] if len(sys.argv) > 1 else sorted(glob.glob(os.path.join(os.path.dirname(__file__), "R7_six_criteria_scan_r3 (*).csv")))[-1]
d = pd.read_csv(src)
NC = 6
COLS = [  # (csv 欄, Excel 標題, 格式)
    ("ticker", "Ticker", "link"), ("lists", "來源榜單", "txt"), ("date", "數據日", "txt"), ("close", "收盤", "num2"), ("score", "命中 /6", "int"),
    ("c1", "① 重心線向上", "tick"), ("grav", "重心線", "num2"), ("grav_slope", "重心斜率", "num3"), ("grav_shift5atr", "重心 5 根位移 (ATR)", "num2"),
    ("c2", "② 波動指數向上", "tick"), ("volidx", "波動指數", "num1"), ("volidx_slope", "波動指數斜率", "num2"), ("volidx_prev", "波動指數前值", "num1"),
    ("c3", "③ 波動指數 ≥75", "tick"), ("atr_pct", "ATR14 %", "num2"), ("sd60_pct", "60 日日波動 %", "num2"),
    ("c4", "④ 時鐘 6–10 點", "tick"), ("clock", "時鐘", "txt"), ("theta", "角度°", "num1"), ("cycle", "周期", "txt"), ("cyc_days", "周期第 N 日", "int"), ("cyc_prog", "周期進度 %", "int"),
    ("c5", "⑤ 淺紅第 1–3 根", "tick"), ("c5_cat", "淺紅第幾根", "txt"), ("hist", "Hist 今日", "num3"), ("hist_prev", "Hist 昨日", "num3"), ("hist_trough", "Hist 谷底", "num3"),
    ("c6", "⑥ 貼近重心線", "tick"), ("dist_grav_pct", "距重心 %", "num2"), ("dist_grav_atr", "距重心 (ATR)", "num2"),
    ("vcp", "VCP 指數 (參考)", "num1"), ("vcp_grade", "VCP 等級", "txt"), ("struct", "結構", "txt"), ("mk", "Market Key", "txt"), ("lr_line", "最低阻力線", "num2"), ("dist_lr_pct", "距阻力線 %", "num2"),
]
d["c5_cat"] = d.apply(lambda r: ("第 %d 根" % (int(r.c5_days) + 1)) if (pd.notna(r.c5_days) and r.still_light) else ("已中斷" if pd.notna(r.c5_days) else "—"), axis=1)
FMT = {"num1": "0.0", "num2": "0.00", "num3": "0.000", "int": "0"}
HEAD_FILL = PatternFill("solid", fgColor="EEF1ED"); OK = Font(color="16A34A", bold=True); NO = Font(color="DC2626", bold=True)
LINK = Font(color="0563C1", underline="single", bold=True); thin = Side(style="thin", color="E2E6E3")

def sheet(wb, name, df, note=None):
    ws = wb.create_sheet(name)
    r0 = 1
    if note:
        ws.cell(1, 1, note).font = Font(italic=True, color="64748B"); r0 = 2
    for j, (_, h, _) in enumerate(COLS, 1):
        c = ws.cell(r0, j, h); c.font = Font(bold=True); c.fill = HEAD_FILL; c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for i, (_, r) in enumerate(df.iterrows(), r0 + 1):
        for j, (k, _, f) in enumerate(COLS, 1):
            v = r[k]
            if f == "link":
                c = ws.cell(i, j, str(v)); c.hyperlink = TV + str(v); c.font = LINK
            elif f == "tick":
                c = ws.cell(i, j, "✓" if bool(v) else "✗"); c.font = OK if bool(v) else NO; c.alignment = Alignment(horizontal="center")
            elif f in FMT:
                c = ws.cell(i, j, None if pd.isna(v) else float(v)); c.number_format = FMT[f]
            else:
                c = ws.cell(i, j, "" if pd.isna(v) else str(v).replace("+", " · "))
            c.border = Border(bottom=thin)
    ws.freeze_panes = ws.cell(r0 + 1, 2)
    ws.auto_filter.ref = f"A{r0}:{get_column_letter(len(COLS))}{max(r0 + 1, r0 + len(df))}"
    for j, (k, h, f) in enumerate(COLS, 1):
        ws.column_dimensions[get_column_letter(j)].width = 9 if f in ("tick", "num1", "num2", "num3", "int") else max(8, min(26, len(h) * 1.6 + 2))
    ws.row_dimensions[r0].height = 32
    return ws

wb = Workbook(); wb.remove(wb.active)
full = d[d.score == NC].sort_values(["c5_days", "volidx"], ascending=[True, False])
sheet(wb, "六項全中", full, "六項全中 %d 檔；按 ⑤ 淺紅第 1 / 2 / 3 根排列，類內依波動指數由高至低。Ticker 可點擊開 TradingView。" % len(full))
for k in (0, 1, 2):
    g = full[full.c5_days == k]
    sheet(wb, f"淺紅第 {k + 1} 根", g, f"六項全中 · 淺紅第 {k + 1} 根：{len(g)} 檔")
five = d[d.score == NC - 1].copy()
five["fail"] = five.apply(lambda r: [c for c in ("c1", "c2", "c3", "c4", "c5", "c6") if not r[c]][0], axis=1)
five = five.sort_values(["fail", "volidx"], ascending=[True, False])
sheet(wb, "差一項", five, "五中一 %d 檔；按缺少的條件分組（看 ✗ 在哪一欄）。" % len(five))
sheet(wb, "全部", d.sort_values(["score", "c5_days", "volidx"], ascending=[False, True, False]), "全部 %d 檔；用「命中 /6」欄篩選。" % len(d))
ws = wb.create_sheet("說明")
for i, t in enumerate([
    "R7 A–H 六項條件掃描 r3 — 日線，數據基準 2026-09-16 收盤（vcp-watchlist repo Yahoo 日線鏡像）",
    "① 重心線向上：r7e_gravity（滾動 VWAP 30，hlc3）最新一根斜率 > 0",
    "② 波動指數向上：r7h_volidx（0–100，高 = 平靜）最新一根斜率 > 0",
    "③ 波動指數 ≥ 75",
    "④ 時鐘 6–10 點：r7b_macd_clock 指針 180°–300°",
    "⑤ 淺紅第 1–3 根：MACD 柱狀圖 < 0 且回升，連續 1–3 根、未中斷",
    "⑥ 貼近重心線：收盤距重心線 ≤ 1.0 × ATR14 或 ≤ 3%",
    "VCP / 結構 / 最低阻力線 只作參考，不計分。MA20 與 EMA21 已刪除。",
    "Ticker 欄為 TradingView 圖表超連結（Q1c5VWwD 版面）。",
], 1):
    ws.cell(i, 1, t).font = Font(bold=(i == 1))
ws.column_dimensions["A"].width = 110
out = src[:-4] + ".xlsx"
wb.save(out); print(out)
