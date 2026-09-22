# -*- coding: utf-8 -*-
"""R7_six_criteria_scan CSV → Excel：Ticker 帶 TradingView 超連結；分頁：六項全中(淺紅 1/2/3 根) / 差一項 / 全部 / 說明。"""
import sys, glob, os
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

TV = "https://www.tradingview.com/chart/Q1c5VWwD/?symbol="
src = sys.argv[1] if len(sys.argv) > 1 else sorted(glob.glob(os.path.join(os.path.dirname(__file__), "R7_six_criteria_scan_r*.csv")))[-1]
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
    ("turnover20_m", "20 日均額 (百萬)", "num1"), ("bars", "歷史根數", "int"), ("hist_ok", "歷史足夠 ≥250", "tick"),
    ("vcp", "VCP 指數 (參考)", "num1"), ("vcp_grade", "VCP 等級", "txt"), ("struct", "結構", "txt"), ("mk", "Market Key", "txt"), ("lr_line", "最低阻力線", "num2"), ("dist_lr_pct", "距阻力線 %", "num2"),
]
if "ai_group" in d.columns:   # AI Sector watchlist 版：加小群組欄
    COLS[2:2] = [("ai_cat", "AI 大分類", "txt"), ("ai_group", "AI 小群組", "txt"), ("ai_rank", "小群組資金流排名", "int"), ("ai_flow5", "個股 5 日資金流向", "txt")]
    if "ai_chg5" in d.columns:
        COLS[6:6] = [("ai_chg5", "個股 5 日漲跌 %", "num2")]
d["hist_ok"] = d["bars"] >= 250
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
    u["hist_ok"] = u["bars"] >= 250
    u["c5_cat"] = u.apply(lambda r: ("第 %d 根" % (int(r.c5_days) + 1)) if (pd.notna(r.c5_days) and r.still_light) else ("已中斷" if pd.notna(r.c5_days) else "—"), axis=1)
    inwl = set(d.ticker)
    uf = u[u.score == NC].copy()
    uf["lists"] = uf.ticker.map(lambda t: "榜內" if t in inwl else "榜外")
    uf = uf.sort_values(["c5_days", "volidx"], ascending=[True, False])
    sheet(wb, "加掃 六項全中", uf, "三鏡像併集 3,097 檔中、收盤 ≥ $2 且 20 日均額 ≥ 300 萬美元的 %d 檔，六項全中 %d 檔（其中 %d 檔不在四張榜單內）。這不是全市場：10MA 自己的漏斗算出美股可報價名單約 5,065 檔。" % (len(u), len(uf), (uf.lists == "榜外").sum()))

# chat 1–3 命中但未過六項（可選）：三個 session 各自用自己那套準則選中、但六項條件未全中的名字
CH = os.environ.get("CHATHITS_CSV", "")
if CH and os.path.exists(CH):
    ch = pd.read_csv(CH)
    CHCOLS = [("ticker", "Ticker", "link"), ("name", "公司", "txt"),
              ("n_hit", "命中系統數", "int"), ("hits", "命中哪幾套", "txt"), ("detail", "命中內容（來源原話）", "txt"),
              ("avoid", "反向標註", "txt"), ("catalyst", "催化", "txt"),
              ("score", "六項命中 /6", "int"), ("miss", "欠缺條件", "txt"),
              ("close", "09-16 收盤", "num2"), ("volidx", "波動指數", "num1"), ("volidx_slope", "指數斜率", "num2"),
              ("grav_slope", "重心斜率", "num3"), ("clock", "時鐘", "txt"), ("c5_cat", "淺紅第幾根", "txt"),
              ("dist_grav_pct", "距重心 %", "num2"),
              ("c1_grade", "chat1 VCP/Wein/Pre", "txt"), ("c1_up", "chat1 上升分數", "num1"), ("c1_sure", "chat1 確定性", "num1"),
              ("ss_name", "chat2 子板塊", "txt"), ("ss_rank", "子板塊名次", "int"), ("ss_score", "子板塊 5 日分", "num1"),
              ("ai_group", "chat2 AI 小群組", "txt"), ("ai_rank", "AI 群組名次", "int"), ("ai_tf5", "AI 個股 5 日強度", "num3"),
              ("ma_rank", "chat3 10MA 排名", "int"), ("ma_tf", "通過時間框", "int"), ("ma_vcp", "10MA VCP 分", "num1"),
              ("ma_flag", "10MA 審視標記", "txt"), ("rh", "加息 R2", "txt"),
              ("four_17", "09-17 ①④⑤⑥", "tick"), ("close_17", "09-17 收盤", "num2"), ("chg1d_pct", "當日 %", "num2"),
              ("turnover20_m", "20 日均額 (百萬)", "num1"), ("bars", "歷史根數", "int"), ("hist_ok", "歷史足夠 ≥250", "tick"),
              ("vcp", "VCP 指數 (參考)", "num1"), ("struct", "結構", "txt"), ("lists", "來源榜單", "txt")]

    def chsheet(name, df, note):
        w = wb.create_sheet(name)
        w.cell(1, 1, note).font = Font(italic=True, color="64748B")
        for j, (_, h, _) in enumerate(CHCOLS, 1):
            c = w.cell(2, j, h); c.font = Font(bold=True); c.fill = HEAD_FILL
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        for i, (_, r) in enumerate(df.iterrows(), 3):
            for j, (k, _, f) in enumerate(CHCOLS, 1):
                v = r[k]
                if f == "link":
                    c = w.cell(i, j, str(v)); c.hyperlink = TV + str(v); c.font = LINK
                elif f == "tick":
                    c = w.cell(i, j, "" if pd.isna(v) else ("✓" if bool(v) else "✗"))
                    c.font = OK if bool(v) else NO; c.alignment = Alignment(horizontal="center")
                elif f in FMT:
                    c = w.cell(i, j, None if pd.isna(v) else float(v)); c.number_format = FMT[f]
                else:
                    c = w.cell(i, j, "" if pd.isna(v) else str(v).replace("+", " · "))
                c.border = Border(bottom=thin)
        w.freeze_panes = w.cell(3, 2)
        w.auto_filter.ref = f"A2:{get_column_letter(len(CHCOLS))}{max(3, 2 + len(df))}"
        for j, (k, h, f) in enumerate(CHCOLS, 1):
            w.column_dimensions[get_column_letter(j)].width = (
                58 if k == "detail" else 30 if k in ("hits", "ai_group", "catalyst", "ma_flag", "lists") else
                20 if k in ("name", "ss_name", "c1_grade") else
                9 if f in ("tick", "num1", "num2", "num3", "int") else 12)
        w.row_dimensions[2].height = 32
        return w

    chsheet("Chat1-3 命中 未過六項", ch,
            "三個 session 各自用自己那套準則選中、但 R7 六項條件未全中的 %d 檔。命中規則（一律採用來源成品自己的通過標記）："
            "chat1 Combined R22 = 線上 ≥1 且三榜有頂級（VCP A/B、Weinstein 2A、Pre-breakout A）；"
            "chat2 SubSector R12 = 所屬子板塊 5 日分 ≥70 且斜率 >0；"
            "chat2 AI Sector R13 = 所屬小群組 5 日分 ≥70 且個股 5 日強度 >0；"
            "chat3 10MA R20 = 在總表（本版跌出 20 檔不算）；chat3 加息 R2 = 受惠名單。"
            "按「六項命中 /6」→「命中系統數」→ 波動指數排序。" % len(ch))
    for k in (3, 2, 1):
        g = ch[ch.n_hit == k]
        if len(g):
            chsheet(f"Chat 命中 {k} 套", g, f"同時命中 {k} 套 chat 準則、但六項未全中：{len(g)} 檔。")

# 09-17 收盤快照更新（可選）：快照沒有盤中高低，②③（波動指數）不可信，只看 ①④⑤⑥
UPD = os.environ.get("UPDATE_CSV", "")
if UPD and os.path.exists(UPD):
    m = pd.read_csv(UPD)
    UCOLS = [("ticker", "Ticker", "link"), ("lists", "來源榜單", "txt"), ("close_16", "09-16 收盤", "num2"),
             ("close_17", "09-17 收盤", "num2"), ("chg1d_pct", "當日 %", "num2"),
             ("c1_17", "① 重心線向上", "tick"), ("c4_17", "④ 時鐘 6–10 點", "tick"), ("c5_17", "⑤ 淺紅 1–3 根", "tick"),
             ("c6_17", "⑥ 貼近重心線", "tick"), ("clock_17", "09-17 時鐘", "txt"), ("dist_grav_pct", "距重心 %", "num2"),
             ("volidx", "波動指數 (09-16)", "num1"), ("c2", "② 09-16 指數向上", "tick"), ("c3", "③ 09-16 ≥75", "tick")]

    def usheet(name, df, note):
        ws2 = wb.create_sheet(name)
        ws2.cell(1, 1, note).font = Font(italic=True, color="64748B")
        for j, (_, h, _) in enumerate(UCOLS, 1):
            c = ws2.cell(2, j, h); c.font = Font(bold=True); c.fill = HEAD_FILL
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        for i, (_, r) in enumerate(df.iterrows(), 3):
            for j, (k, _, f) in enumerate(UCOLS, 1):
                v = r[k]
                if f == "link":
                    c = ws2.cell(i, j, str(v)); c.hyperlink = TV + str(v); c.font = LINK
                elif f == "tick":
                    c = ws2.cell(i, j, "✓" if bool(v) else "✗"); c.font = OK if bool(v) else NO
                    c.alignment = Alignment(horizontal="center")
                elif f in FMT:
                    c = ws2.cell(i, j, None if pd.isna(v) else float(v)); c.number_format = FMT[f]
                else:
                    c = ws2.cell(i, j, "" if pd.isna(v) else str(v).replace("+", " · "))
                c.border = Border(bottom=thin)
        ws2.freeze_panes = ws2.cell(3, 2)
        for j, (k, h, f) in enumerate(UCOLS, 1):
            ws2.column_dimensions[get_column_letter(j)].width = 10 if f in ("tick", "num1", "num2") else 22
        ws2.row_dimensions[2].height = 30

    still = m[(m.score == NC) & m.four_17]
    lost = m[(m.score == NC) & (~m.four_17)]
    fresh = m[(m.score != NC) & m.four_17 & m.c2 & m.c3].sort_values("volidx", ascending=False)
    usheet("09-17 仍成立", still, "09-16 六項全中、且在 09-17 收盤下 ①④⑤⑥ 仍全部成立：%d / %d 檔。" % (len(still), len(still) + len(lost)))
    usheet("09-17 已失效", lost, "09-16 六項全中、但 09-17 收盤已有一項不成立（多數是 ⑤ 淺紅中斷）：%d 檔。" % len(lost))
    usheet("09-17 新符合", fresh, "09-17 收盤下 ①④⑤⑥ 成立、且 09-16 的 ②③（波動指數）也通過的候補：%d 檔。快照無盤中高低，②③ 用 09-16 值。" % len(fresh))

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
            v = r[h]
            if pd.isna(v):
                cell = ""
            else:
                cell = int(v) if (h.endswith("檔數") and str(v).strip().isdigit()) else str(v)
            wsx.cell(i, j, cell)
    for j, h in enumerate(hdr, 1):
        wsx.column_dimensions[get_column_letter(j)].width = 14 if h.endswith(("檔數", "基準日")) else 46

ws = wb.create_sheet("說明")
for i, t in enumerate([
    "R7 A–H 六項條件掃描 r6 — 六項條件的基準是 2026-09-16 官方收盤（完整 OHLC，三個 repo 的 Yahoo 鏡像合併 3,097 檔）。另有三個 09-17 分頁，用 10MA repo 的 Nasdaq 收盤快照（753/758 檔）更新 ①④⑤⑥；快照沒有盤中高低，②③（波動指數）不能重算，沿用 09-16 值。09-18／09-21 收盤三個 repo 都還沒有：三個鏡像最後一次更新是 09-18 01–04 UTC，本次已重新 fetch 確認無新 commit，掃描結果與 r5 逐格相同。本版新增「Chat1-3 命中 未過六項」分頁。",
    "① 重心線向上：r7e_gravity（滾動 VWAP 30，hlc3）最新一根斜率 > 0",
    "② 波動指數向上：r7h_volidx（0–100，高 = 平靜）最新一根斜率 > 0",
    "③ 波動指數 ≥ 75",
    "④ 時鐘 6–10 點：r7b_macd_clock 指針 180°–300°",
    "⑤ 淺紅第 1–3 根：MACD 柱狀圖 < 0 且回升，連續 1–3 根、未中斷",
    "⑥ 貼近重心線：收盤距重心線 ≤ 1.0 × ATR14 或 ≤ 3%",
    "VCP / 結構 / 最低阻力線 只作參考，不計分。MA20 與 EMA21 已刪除。",
    "Ticker 欄為 TradingView 圖表超連結（Q1c5VWwD 版面）。",
    "來源榜單欄會標明名字的身分：10MA_R20（在榜 89）· 10MA_R20_跌出（本版被剔除 20）· RateHike_R2_受惠 / _迴避（同一 session 09-18 的加息與地緣政治 3 日清單）。六項全中裡若出現「跌出」或「迴避」標籤，代表原榜單本身不推薦，請自行判斷。",
    "歷史足夠 ≥250：鏡像只給 42 檔 75 根（2026-06-01 起），這些名字的 60 日波動與週期平均值樣本太短，時鐘與波動指數不可靠。",
    "10MA R20 的 109 檔 = 89 檔在榜 + 20 檔本版跌出（新上榜同跌出 分頁），兩者都掃；758 檔全部掃到，0 檔缺資料。",
    "「Chat1-3 命中 未過六項」分頁：三個 session 各自的成品用自己那套準則選中、但本掃描六項未全中的名字，另按命中 1 / 2 / 3 套拆成子分頁。命中規則寫在該分頁第一行。六項全中的 17 檔裡有 6 檔同時是 chat 命中（MRK、JNJ、DHR、LH、NWSA、RNR），其餘 11 檔是本掃描獨有。",
    "「全市場 六項全中」分頁：合併面板中收盤 ≥ $2、20 日均額 ≥ 300 萬美元、歷史 ≥ 80 根的 2,584 檔全掃一次的結果，含 watchlist 以外的名字。",
    "① 用的是「重心線 1 根斜率 > 0」（六項條件的原文）。R7-E 自己把線塗綠的條件較嚴：5 根位移 ≥ 0.8 ATR；表中已附「重心 5 根位移 (ATR)」欄，可自行加嚴。",
    "③ 門檻用 75（六項條件原文）。R7-H 圖上那條綠色分隔線預設在 80，所以有些通過 ③ 的名字在圖上仍在線下。",
    "④ 時鐘：MACD 柱狀圖在 Pine 的前 33 根是 na（EMA 要等 SMA 種子），本掃描已照做並丟掉每個方向的第一段，避免暖機假週期污染平均週期長度。歷史根數 < 150 的名字，時鐘與進度仍不夠可靠，請以「歷史根數」欄判斷。",
    "代號對齊：鏡像用 BRK/A、BRK/B、BF/B 等斜線寫法，watchlist 用 BRK-A、BF.B；掃描會自動試點/槓/斜線並取資料最長者（本次 3 檔重對應）。",
    SRC_NOTE,
], 1):
    ws.cell(i, 1, t).font = Font(bold=(i == 1))
ws.column_dimensions["A"].width = 110
out = sys.argv[2] if len(sys.argv) > 2 else src[:-4] + ".xlsx"
wb.save(out); print(out)
