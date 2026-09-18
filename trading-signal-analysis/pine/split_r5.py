# -*- coding: utf-8 -*-
"""從 R4 拆出 R5 四件套：主圖策略 / MACD+時鐘 pane / VCP pane / 確定性 pane。

Pine 一個腳本只能佔一個 pane，故必須拆檔；四支腳本的計算邏輯逐字沿用 R4，
只改「畫在哪個 pane」與各自的呈現方式。
"""
import re, pathlib

P = pathlib.Path("/home/user/YT-subittle/trading-signal-analysis/pine")
src = (P / "combo_cycle_clock_ema9bw_r4.pine").read_text(encoding="utf-8")
L = src.split("\n")


def seg(a, b):
    """取 1-based 行號 [a, b) 的區塊。"""
    return "\n".join(L[a - 1:b - 1]).rstrip("\n")


# ── 由 R4 擷取共用區塊 ──
M1_PARAM = seg(63, 89)      # M1 參數
M1_ENGINE = seg(89, 131)    # f_cycle + security + 衍生變數
M1_DRAW = seg(131, 145)     # 主圖繪製 (背景/plot/label)
M1_CLOCK = seg(145, 207)    # 時鐘 table
M1_ALERT = seg(207, 213)    # 警報

M3_INPUT = seg(237, 245)
M3_FUNC = seg(248, 425)     # f_clamp01 / f_pos / f_bar / f_cert7 / f_vcp / f_gradeTxt / f_gradeCol
M3_CALC = seg(428, 441)
M3_ALERT = seg(505, 508)

M2_PARAM = seg(527, 566)
M2_BODY = seg(566, 704)     # 指標 + 訊號 + 下單 + 繪圖
M2_ALERT = seg(704, 709)


# ── R5-B 專用：改寫過的 M1 參數與時鐘 ──
M1_PARAM_B = (M1_PARAM
    .replace('posOpt = input.string("左上", "位置", options = ["左上", "右上", "左下", "右下"], group = grpK)',
             'posOpt = input.string("右中", "時鐘位置 (本 pane 內)", options = ["右上", "右中", "右下", "左上", "左中", "左下"], group = grpK)')
    .replace('grid   = input.int(13, "解析度 (格數, 建議奇數 11–17)", minval = 9, maxval = 21, group = grpK)',
             'grid   = input.int(11, "解析度 (格數, 建議奇數 9–13；pane 較矮用小值)", minval = 9, maxval = 21, group = grpK)')
    .replace('cellW  = input.float(0.9, "格寬 (% 圖表寬)", minval = 0.3, step = 0.1, group = grpK)',
             'cellW  = input.float(0.6, "格寬 (% 圖表寬)", minval = 0.2, step = 0.1, group = grpK)')
    .replace('cellH  = input.float(1.7, "格高 (% 圖表高)", minval = 0.5, step = 0.1, group = grpK)',
             'cellH  = input.float(1.1, "格高 (% 圖表高)", minval = 0.3, step = 0.1, group = grpK)')
    .replace('showBg  = input.bool(true, "主圖週期背景著色", group = grpK)',
             'showBg  = input.bool(true, "週期背景著色", group = grpK)'))

_old_tpos = ('tpos = posOpt == "左上" ? position.top_left : posOpt == "右上" ? position.top_right :\n'
             '       posOpt == "左下" ? position.bottom_left : position.bottom_right')
_new_tpos = ('tpos = posOpt == "右上" ? position.top_right : posOpt == "右中" ? position.middle_right :\n'
             '       posOpt == "右下" ? position.bottom_right : posOpt == "左上" ? position.top_left :\n'
             '       posOpt == "左中" ? position.middle_left : position.bottom_left')
_old_stat = '(timeframe.period != cycTF ? "\\n(日線週期 疊加於 " + timeframe.period + " 圖)" : "")'
_new_stat = ('(timeframe.period != cycTF ? "\\n(日線週期 疊加於 " + timeframe.period + " 圖)" : "") +\n'
             '         (not up and not na(extBar) ? "\\n距轉勢點 " + str.tostring(bar_index - extBar) + " 根" : "")')
M1_CLOCK_B = M1_CLOCK.replace(_old_tpos, _new_tpos).replace(_old_stat, _new_stat)
assert M1_CLOCK_B != M1_CLOCK, "clock replacements did not apply"
assert M1_PARAM_B != M1_PARAM, "param replacements did not apply"


# ── 各 pane 專屬的面板輸入（R4 的 showM3/m3Pos 只適用於單檔版）──
_grpW_old = ('grpW = "M3 ② 面板"\n'
             'showM3    = input.bool(true, "顯示 M3 資訊框 (3-B VCP 在上 / 3-A 確定性在下)", group = grpW)\n'
             'm3Pos     = input.string("右中", "M3 資訊框位置", options = ["左上", "左中", "左下", "右上", "右中", "右下"], group = grpW)\n'
             'certAlert = input.float(70, "確定性警報門檻 (≥)", minval = 0, maxval = 100, group = grpW)')
assert _grpW_old in M3_INPUT, "grpW block not found in M3_INPUT"
M3_INPUT_A = M3_INPUT.replace(_grpW_old,
    'grpW = "M3 ② 門檻"\n'
    'certAlert = input.float(70, "確定性警報門檻 (≥)", minval = 0, maxval = 100, group = grpW)')
M3_INPUT_C = M3_INPUT.replace(_grpW_old,
    'grpW = "② 面板"\n'
    'showVcp = input.bool(true, "顯示明細面板 (本 pane 右側)", group = grpW)')
M3_INPUT_D = M3_INPUT.replace(_grpW_old,
    'grpW = "② 面板"\n'
    'showCert  = input.bool(true, "顯示 7 分項面板 (本 pane 右側)", group = grpW)\n'
    'certAlert = input.float(70, "確定性警報門檻 (≥)", minval = 0, maxval = 100, group = grpW)')

# R5-A：沿用 M2 既有的右上狀態面板，只把模組代號改成對應的 pane 檔名
M2_BODY_A = (M2_BODY
    .replace('"日線週期 (M1)"', '"日線週期 (R5-B)"')
    .replace('"VCP 等級 (M3)"', '"VCP 等級 (R5-C)"')
    .replace('"確定性 (M3)"',  '"確定性 (R5-D)"'))
assert M2_BODY_A != M2_BODY, "M2 status-table labels not found"

HDR = """//@version=5
// ═══════════════════════════════════════════════════════════════════════════
//  {title}
//
//  R5 套件 —— Pine 一個腳本只能佔一個 pane，故 R4 的單檔拆成四支，各佔一個 pane：
//     R5-A  主圖 (overlay)   EMA9 帶寬策略 + 進出場 + 狀態面板        combo_r5a_main.pine
//     R5-B  下方 pane ①      MACD 柱狀圖 + 週期時鐘 (時鐘在最右邊)     combo_r5b_macd_clock.pine
//     R5-C  下方 pane ②      VCP 指數曲線 0–100 + 等級                combo_r5c_vcp.pine
//     R5-D  下方 pane ③      確定性指數曲線 0–100 + 7 分項            combo_r5d_cert.pine
//  四支的計算邏輯與 R4 逐字相同，只改「畫在哪個 pane」與各自的呈現方式。
//
{note}// ═══════════════════════════════════════════════════════════════════════════
"""

# ══════════════════════════════════════════════════════════════════════════
# R5-A  主圖：EMA9 帶寬策略（M2）
# ══════════════════════════════════════════════════════════════════════════
a_note = """//  本檔內容：MODULE 2（EMA9 中線 ± 帶寬、擠壓突破 / 回踩進場、風控出場）。
//  M1 的日線週期與 M3 的 VCP／確定性仍在此計算，供「⑥ 模組整合」過濾與右上狀態面板使用，
//  但它們的圖形改由 R5-B / R5-C / R5-D 在各自的 pane 呈現，本檔不再畫時鐘與資訊框。
"""
a = HDR.format(title="R5-A  主圖：EMA9 Band Width Strategy", note=a_note) + f'''
strategy("R5-A EMA9 BW (main)", shorttitle = "R5-A EMA9-BW",
     overlay = true, initial_capital = 10000,
     default_qty_type = strategy.percent_of_equity, default_qty_value = 20,
     commission_type = strategy.commission.percent, commission_value = 0.05,
     slippage = 1, pyramiding = 0, process_orders_on_close = true,
     max_labels_count = 500)


// ── M1 週期引擎（僅供過濾與面板；圖形在 R5-B）──
{M1_PARAM}

{M1_ENGINE}

bgcolor(showBg ? (up ? color.new(cUp, 94) : color.new(cDn, 94)) : na, title = "日線週期背景")


// ── M3 計算（僅供過濾與面板；曲線在 R5-C / R5-D）──
{M3_INPUT_A}

{M3_FUNC}

{M3_CALC}


// ── MODULE 2：策略本體 ──
{M2_PARAM}

{M2_BODY_A}

{M2_ALERT}
'''

# ══════════════════════════════════════════════════════════════════════════
# R5-B  下方 pane：MACD 柱狀圖 + 週期時鐘（時鐘置於 pane 最右邊）
# ══════════════════════════════════════════════════════════════════════════
b_note = """//  本檔內容：MODULE 1。MACD 柱狀圖以四色畫在本 pane（升加速／升減速／跌減弱／跌加速），
//  MACD 線與訊號線疊在同一 pane，週期背景與「上一段周期長度」標籤同時顯示，
//  週期時鐘 table 置於本 pane 的最右邊（預設 右中；可改右上／右下）。
//
//  ⚠ 時鐘是格子陣列，pane 太矮會被壓扁 —— 請把本 pane 往下拖高（約 250px 以上）
//     才會呈現正圓；或把「解析度」調小（9–11 格）。
"""
b = HDR.format(title="R5-B  下方 pane：MACD 柱狀圖 + 週期時鐘", note=b_note) + f'''
indicator("R5-B MACD + Cycle Clock", shorttitle = "R5-B MACD Clock",
     overlay = false, max_labels_count = 300)

{M1_PARAM_B}

{M1_ENGINE}

// ── 本 pane 繪圖：MACD 柱狀圖（四色）+ MACD/Signal 線 ──
histRising = hist > hist[1]
hcol = up ? (histRising ? color.new(cUp, 0) : color.new(cUp, 55))
          : (histRising ? color.new(cDn, 55) : color.new(cDn, 0))
plot(hist,    "MACD Histogram", style = plot.style_columns, color = hcol)
plot(macdL,   "MACD",   color = color.new(color.blue, 20),   linewidth = 2)
plot(sigLine, "Signal", color = color.new(color.orange, 20), linewidth = 2)
hline(0, "零軸", color = color.new(color.gray, 30), linestyle = hline.style_solid)
bgcolor(showBg ? (up ? color.new(cUp, 92) : color.new(cDn, 92)) : na, title = "週期背景")

// 週期切換處標註上一段長度（畫在零軸上／下）
if showLbl and flipEvt
    label.new(bar_index, 0, str.tostring(lastLen, "#") + "日",
         style = up[1] ? label.style_label_down : label.style_label_up,
         color = up[1] ? color.new(cUp, 20) : color.new(cDn, 20),
         textcolor = color.white, size = size.tiny)

// 轉勢點（本周期柱狀圖極值）標記 —— 時鐘 6 點鐘所對應的那一根
var float extVal = na
var int   extBar = na
if flip
    extVal := hist
    extBar := bar_index
else
    if (not up and hist < nz(extVal, hist)) or (up and hist > nz(extVal, hist))
        extVal := hist
        extBar := bar_index
plotshape(bar_index == extBar and not up, "轉勢點 (谷底)", shape.circle, location.absolute,
     color.new(#eab308, 20), size = size.tiny, offset = 0)

{M1_CLOCK_B}

{M1_ALERT}
'''

# ══════════════════════════════════════════════════════════════════════════
# R5-C  下方 pane：VCP 指數曲線
# ══════════════════════════════════════════════════════════════════════════
c_note = """//  本檔內容：MODULE 3-B。把 vcp_classify 的 0–100 分數畫成一條曲線，
//  背景依 A/B/C/D/E 等級著色，60 / 40 兩條參考線，右側面板列出構成分數的明細。
//  算法與 R4 的 MODULE 3 逐字相同（來源：VCP-watchlist repo，Combined Watchlist R17）。
"""
c = HDR.format(title="R5-C  下方 pane：VCP 指數曲線", note=c_note) + f'''
indicator("R5-C VCP Score", shorttitle = "R5-C VCP", overlay = false)

{M3_INPUT_C}

{M3_FUNC}

[vcpScore, vcpGrade, offHigh, aboveLow, chg1m, chg3m, rng21, volRatio, trendOK, tightB, extendedB, a50B, a200B, crossB] =
     request.security(syminfo.tickerid, m3TF, f_vcp(), lookahead = barmerge.lookahead_off)

// ── 曲線 ──
gCol = f_gradeCol(vcpGrade)
plot(vcpScore, "VCP 指數", color = color.new(gCol, 0), linewidth = 2)
plot(vcpGrade, "VCP 等級 (0=A…4=E)", color = color.gray, display = display.data_window)
hline(60, "60 強", color = color.new(#3FB68B, 45), linestyle = hline.style_dashed)
hline(40, "40 弱", color = color.new(#E0705F, 45), linestyle = hline.style_dashed)
bgcolor(color.new(gCol, 90), title = "等級背景 (綠A 藍B 灰C 深灰D 黃E)")

// 等級變動處標註
if vcpGrade != vcpGrade[1]
    label.new(bar_index, vcpScore, f_gradeTxt(vcpGrade), style = label.style_label_left,
         color = color.new(gCol, 15), textcolor = color.white, size = size.tiny)

// ── 明細面板（本 pane 右側）──
var table tV = table.new(position.middle_right, 2, 9, bgcolor = color.new(#ffffff, 5),
     frame_color = color.black, frame_width = 2, border_width = 1, border_color = color.new(color.black, 85))
var bool vInit = false
if showVcp and barstate.islast
    if not vInit
        for rj = 0 to 8
            table.cell(tV, 0, rj, "")
            table.cell(tV, 1, rj, "")
        vInit := true
    table.cell(tV, 0, 0, "VCP " + str.tostring(vcpScore, "#.#"), text_color = color.white,
         bgcolor = color.new(gCol, 10), text_size = size.small)
    table.cell(tV, 1, 0, f_gradeTxt(vcpGrade), text_color = color.white,
         bgcolor = color.new(gCol, 10), text_size = size.small)
    table.cell(tV, 0, 1, "距 52 週高", text_size = size.tiny)
    table.cell(tV, 1, 1, str.tostring(-offHigh, "#.#") + "%", text_size = size.tiny,
         text_color = offHigh <= 10 ? #3FB68B : color.gray)
    table.cell(tV, 0, 2, "距 52 週低", text_size = size.tiny)
    table.cell(tV, 1, 2, "+" + str.tostring(aboveLow, "#") + "%", text_size = size.tiny,
         text_color = aboveLow >= 30 ? #3FB68B : color.gray)
    table.cell(tV, 0, 3, "1 月 / 3 月", text_size = size.tiny)
    table.cell(tV, 1, 3, str.tostring(chg1m, "+#.#") + "% / " + str.tostring(chg3m, "+#.#") + "%",
         text_size = size.tiny, text_color = extendedB ? #E5B15C : color.gray)
    table.cell(tV, 0, 4, "21 日收盤區間", text_size = size.tiny)
    table.cell(tV, 1, 4, str.tostring(rng21, "#.#") + "%" + (tightB ? " 緊縮 ✓" : ""),
         text_size = size.tiny, text_color = tightB ? #3FB68B : color.gray)
    table.cell(tV, 0, 5, "量比 10d/50d", text_size = size.tiny)
    table.cell(tV, 1, 5, str.tostring(volRatio, "#.##") + (volRatio < 0.95 ? " 量縮 ✓" : ""),
         text_size = size.tiny, text_color = volRatio < 0.95 ? #3FB68B : color.gray)
    table.cell(tV, 0, 6, "趨勢模板", text_size = size.tiny)
    table.cell(tV, 1, 6, (trendOK ? "通過 ✓" : "未通過") + "  MA50" + (a50B ? "✓" : "✗") +
         " MA200" + (a200B ? "✓" : "✗") + " 50>200" + (crossB ? "✓" : "✗"),
         text_size = size.tiny, text_color = trendOK ? #3FB68B : #E0705F)
    table.cell(tV, 0, 7, "延伸判定", text_size = size.tiny)
    table.cell(tV, 1, 7, extendedB ? "21 日漲幅 >15% → E" : "否", text_size = size.tiny,
         text_color = extendedB ? #E5B15C : color.gray)
    table.cell(tV, 0, 8, "A=待突破 B=上升 C=修復", text_size = size.tiny, text_color = color.gray)
    table.cell(tV, 1, 8, "D=趨勢弱 E=延伸", text_size = size.tiny, text_color = color.gray)

alertcondition(vcpGrade == 0 and vcpGrade[1] != 0, "VCP 轉 A 級 (待突破)", "{{{{ticker}}}} VCP 等級轉為 A · VCP 待突破")
alertcondition(vcpGrade == 4 and vcpGrade[1] != 4, "VCP 轉 E 級 (延伸)", "{{{{ticker}}}} VCP 等級轉為 E · 突破延伸中，不追高")
'''

# ══════════════════════════════════════════════════════════════════════════
# R5-D  下方 pane：確定性指數曲線
# ══════════════════════════════════════════════════════════════════════════
d_note = """//  本檔內容：MODULE 3-A。把 7 項加權後的 0–100 確定性總分畫成一條曲線，
//  7 個分項各自可選顯示為細線，有「一底高於一底」結構時背景轉綠，
//  右側面板列出 7 項各自的進度條與分數。
//  算法與 R4 的 MODULE 3 逐字相同（來源：VCP-watchlist repo build_r17_data.py）。
"""
d = HDR.format(title="R5-D  下方 pane：確定性指數曲線", note=d_note) + f'''
indicator("R5-D Certainty 7", shorttitle = "R5-D Cert7", overlay = false)

{M3_INPUT_D}
showParts = input.bool(false, "同時畫出 7 個分項細線", group = grpW)

{M3_FUNC}

[cBreak, cRetr, cTime, cDv, cContr, cMa, hlOk, dvRatio, contrRatio, dHeld, brokeHi, ret21, nBot] =
     request.security(syminfo.tickerid, m3TF, f_cert7(), lookahead = barmerge.lookahead_off)
benchRet21 = request.security(bench, m3TF, bar_index >= 21 ? close / close[21] - 1 : 0.0,
     lookahead = barmerge.lookahead_off)
rs21 = ret21 - nz(benchRet21)
cRs  = f_clamp01(0.5 + rs21 / 0.2)
certTotal = 100 * (0.25 * cBreak + 0.10 * cRetr + 0.15 * cTime + 0.15 * cDv +
                   0.10 * cContr + 0.10 * cRs + 0.15 * cMa)

// ── 曲線 ──
certCol = certTotal >= certAlert ? #3FB68B : certTotal >= 50 ? #E5B15C : #8B98A5
plot(certTotal, "確定性總分", color = color.new(certCol, 0), linewidth = 2)
plot(showParts ? cBreak * 100 : na, "突破 25%", color = color.new(color.green, 45))
plot(showParts ? cRetr  * 100 : na, "回升 10%", color = color.new(color.lime, 45))
plot(showParts ? cTime  * 100 : na, "守底 15%", color = color.new(color.blue, 45))
plot(showParts ? cDv    * 100 : na, "量縮 15%", color = color.new(color.purple, 45))
plot(showParts ? cContr * 100 : na, "收縮 10%", color = color.new(color.orange, 45))
plot(showParts ? cRs    * 100 : na, "RS 10%",   color = color.new(color.red, 45))
plot(showParts ? cMa    * 100 : na, "均線 15%", color = color.new(color.gray, 45))
hline(certAlert, "警報門檻", color = color.new(#3FB68B, 45), linestyle = hline.style_dashed)
hline(50, "50", color = color.new(color.gray, 60))
bgcolor(hlOk ? color.new(#3FB68B, 92) : na, title = "一底高於一底 結構")

// ── 7 分項面板（本 pane 右側）──
var table tD = table.new(position.middle_right, 3, 9, bgcolor = color.new(#ffffff, 5),
     frame_color = color.black, frame_width = 2, border_width = 1, border_color = color.new(color.black, 85))
var bool dInit = false
if showCert and barstate.islast
    if not dInit
        for cc = 0 to 2
            for rj = 0 to 8
                table.cell(tD, cc, rj, "")
        dInit := true
    hdrCol = certTotal >= certAlert ? color.new(#3FB68B, 10) :
             certTotal >= 50 ? color.new(#E5B15C, 10) : color.new(#6B7885, 10)
    table.cell(tD, 0, 0, "確定性", text_color = color.white, bgcolor = hdrCol, text_size = size.small)
    table.cell(tD, 1, 0, str.tostring(certTotal, "#.#"), text_color = color.white, bgcolor = hdrCol, text_size = size.small)
    table.cell(tD, 2, 0, hlOk ? "HL ✓ " + str.tostring(nBot) + " 底" : "無 HL", text_color = color.white,
         bgcolor = hdrCol, text_size = size.tiny)
    names = array.from("突破 25%", "回升 10%", "守底 15%", "量縮 15%", "收縮 10%", "RS 10%", "均線 15%")
    vals  = array.from(cBreak, cRetr, cTime, cDv, cContr, cRs, cMa)
    for i = 0 to 6
        v = array.get(vals, i)
        table.cell(tD, 0, i + 1, array.get(names, i), text_size = size.tiny, text_halign = text.align_left)
        table.cell(tD, 1, i + 1, f_bar(v, 8), text_size = size.tiny,
             text_color = v >= 0.7 ? #3FB68B : v >= 0.4 ? #E5B15C : #8B98A5)
        table.cell(tD, 2, i + 1, str.tostring(v * 100, "#"), text_size = size.tiny, text_halign = text.align_right)
    table.cell(tD, 0, 8, "量比(跌/漲) " + str.tostring(dvRatio, "#.##"), text_size = size.tiny, text_color = color.gray)
    table.cell(tD, 1, 8, "RS21 " + str.tostring(rs21 * 100, "+#.#") + "%", text_size = size.tiny, text_color = color.gray)
    table.cell(tD, 2, 8, hlOk ? "守底 " + str.tostring(dHeld) + "日" : "–", text_size = size.tiny, text_color = color.gray)

alertcondition(certTotal >= certAlert and certTotal[1] < certAlert, "確定性達門檻",
     "{{{{ticker}}}} 確定性總分升至門檻以上")
'''

out = {
    "combo_r5a_main.pine": a,
    "combo_r5b_macd_clock.pine": b,
    "combo_r5c_vcp.pine": c,
    "combo_r5d_cert.pine": d,
}
for name, txt in out.items():
    (P / name).write_text(txt, encoding="utf-8")
    decl = [l for l in txt.split("\n") if re.search(r"(indicator|strategy|library)\s*\(", l)]
    risky = [l.strip()[:60] for l in txt.split("\n")
             if re.search(r"\?[^/]*array\.get", l) and not l.strip().startswith("//")]
    print(f"{name:28s} {len(txt.split(chr(10))):4d} lines | declarations {len(decl)} | risky {risky or 'none'}")
