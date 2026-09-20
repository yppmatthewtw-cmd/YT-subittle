# -*- coding: utf-8 -*-
"""R7_six_criteria_scan CSV → Excel：Ticker 帶 TradingView 超連結；分頁：六項全中(淺紅 1/2/3 根) / 差一項 / 全部 / 說明。"""
import sys, glob, os
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

TV = "https://www.tradingview.com/chart/Q1c5VWwD/?symbol="
src = sys.argv[1] if len(sys.argv) > 1 else sorted(glob.glob(os.path.join(os.path.dirname(__file__), "R7_six_criteria_scan_r5 (*).csv")))[-1]
d = pd.read_csv(src)
NC = 6
SRC_NOTE = os.environ.get("SRC_NOTE", "來源：三個 watchlist repo 的最新成品。")
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
if "ai_group" in d.columns:   # AI Sector watchlist 版：加小群組欄
    COLS[2:2] = [("ai_cat", "AI 大分類", "txt"), ("ai_group", "AI 小群組", "txt"), ("ai_rank", "小群組資金流排名", "int"), ("ai_flow5", "個股 5 日資金流向", "txt")]
    if "ai_chg5" in d.columns:
        COLS[6:6] = [("ai_chg5", "個股 5 日漲跌 %", "num2")]
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
        ws.column_dimensions[get_column_letter(j)].width = 9 if f in ("tick", "num1", "num2", "num3", "int") else (34 if k == "ai_group" else max(8, min(26, len(h) * 1.6 + 2)))
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
if "ai_group" in d.columns:
    sheet(wb, "按 AI 小群組", d.sort_values(["ai_rank", "score", "volidx"], ascending=[True, False, False]), "依 AI 小群組資金流排名 → 命中數 → 波動指數排列。")
# 全市場（可選）：把合併面板裡所有流動性達標的股票也跑一次，找出 watchlist 以外的命中
UNI = os.environ.get("UNIVERSE_CSV", "")
if UNI and os.path.exists(UNI):
    u = pd.read_csv(UNI)
    u["c5_cat"] = u.apply(lambda r: ("第 %d 根" % (int(r.c5_days) + 1)) if (pd.notna(r.c5_days) and r.still_light) else ("已中斷" if pd.notna(r.c5_days) else "—"), axis=1)
    inwl = set(d.ticker)
    uf = u[u.score == NC].copy()
    uf["lists"] = uf.ticker.map(lambda t: "watchlist 內" if t in inwl else "watchlist 外")
    uf = uf.sort_values(["c5_days", "volidx"], ascending=[True, False])
    sheet(wb, "全市場 六項全中", uf, "合併面板 %d 檔流動性達標股票中，六項全中 %d 檔（其中 %d 檔不在三個 watchlist 內）。" % (len(u), len(uf), (uf.lists == "watchlist 外").sum()))

# 來源分頁（可選）：三個 session 的最新成品出處
SRC_ROWS = os.environ.get("SRC_ROWS", "")
if SRC_ROWS and os.path.exists(SRC_ROWS):
    srcs = pd.read_csv(SRC_ROWS)
    wsx = wb.create_sheet("來源")
    hdr = list(srcs.columns)
    for j, h in enumerate(hdr, 1):
        c = wsx.cell(1, j, h); c.font = Font(bold=True); c.fill = HEAD_FILL
    for i, (_, r) in enumerate(srcs.iterrows(), 2):
        for j, h in enumerate(hdr, 1):
            wsx.cell(i, j, "" if pd.isna(r[h]) else (int(r[h]) if h.endswith("檔數") else str(r[h])))
    for j, h in enumerate(hdr, 1):
        wsx.column_dimensions[get_column_letter(j)].width = 14 if h.endswith(("檔數", "基準日")) else 46

ws = wb.create_sheet("說明")
for i, t in enumerate([
    "R7 A–H 六項條件掃描 r5 — 日線，數據基準 2026-09-16 官方收盤（10MA / VCP / SubSector 三個 repo 的 Yahoo 鏡像合併，3,097 檔；09-17 官方收盤只有 202 檔、其餘為盤中快照，整天不採用；09-18 三個鏡像都沒有）",
    "① 重心線向上：r7e_gravity（滾動 VWAP 30，hlc3）最新一根斜率 > 0",
    "② 波動指數向上：r7h_volidx（0–100，高 = 平靜）最新一根斜率 > 0",
    "③ 波動指數 ≥ 75",
    "④ 時鐘 6–10 點：r7b_macd_clock 指針 180°–300°",
    "⑤ 淺紅第 1–3 根：MACD 柱狀圖 < 0 且回升，連續 1–3 根、未中斷",
    "⑥ 貼近重心線：收盤距重心線 ≤ 1.0 × ATR14 或 ≤ 3%",
    "VCP / 結構 / 最低阻力線 只作參考，不計分。MA20 與 EMA21 已刪除。",
    "Ticker 欄為 TradingView 圖表超連結（Q1c5VWwD 版面）。",
    "10MA R20 的 109 檔 = 89 檔在榜 + 20 檔本版跌出（新上榜同跌出 分頁），兩者都掃。BRK-A / BRK-B 無鏡像資料，未計入。",
    "「全市場 六項全中」分頁：合併面板中收盤 ≥ $2、60 日均量 ≥ 10 萬股、歷史 ≥ 80 根的 2,826 檔全掃一次的結果，含 watchlist 以外的名字。",
    SRC_NOTE,
], 1):
    ws.cell(i, 1, t).font = Font(bold=(i == 1))
ws.column_dimensions["A"].width = 110
out = sys.argv[2] if len(sys.argv) > 2 else src[:-4] + ".xlsx"
wb.save(out); print(out)
