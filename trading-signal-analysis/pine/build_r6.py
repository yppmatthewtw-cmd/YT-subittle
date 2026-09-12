# -*- coding: utf-8 -*-
"""
由 R5 四件套產生 R6 四件套（檔名尾綴 r6(mm.dd_hh.mm)，腳本標題內為 r6(mm:dd_hh:mm)）。

R6 變更：
  A  主圖底部加入成交量柱；「主力大單買入 / 賣出」交易日以另色標示 + 狀態框新增一列 + 警報
  B  MACD 加入頂背馳 / 底背馳（日線環境計算；日線圖上畫連線）；時鐘解析度提高 (預設 21 格)、
     環厚 / 指針寬隨解析度放大、已走過弧段亮色、12/3/6/9 刻度
  C  等級變動標籤字級加大一倍 (tiny → normal，可調)
  D  只有「高確定性」(≥ 門檻) 區段著色；其餘灰色無色；門檻線 + 區間填色 + 進入高確定性標記
用法：python3 build_r6.py            → 產生四個 combo_*_r6(mm.dd_hh.mm).pine
"""
import re, pathlib, datetime, zoneinfo, sys

P = pathlib.Path(__file__).parent
TZ = zoneinfo.ZoneInfo("Asia/Taipei")
now = datetime.datetime.now(TZ)
TS_TITLE = now.strftime("%m:%d_%H:%M")          # 腳本標題 / 檔頭用 (使用者指定格式)
TS_FILE  = now.strftime("%m.%d_%H.%M")          # 檔名用 (冒號不能出現在 Windows / macOS 檔名)

NAMES = {
    "a": (f"combo_a_main_r6({TS_FILE}).pine",       "combo_r5a_main.pine"),
    "b": (f"combo_b_macd_clock_r6({TS_FILE}).pine", "combo_r5b_macd_clock.pine"),
    "c": (f"combo_c_vcp_r6({TS_FILE}).pine",        "combo_r5c_vcp.pine"),
    "d": (f"combo_d_cert_r6({TS_FILE}).pine",       "combo_r5d_cert.pine"),
}


def common(src, key):
    """R5 → R6 標記、檔頭檔名、標題加版本尾綴。"""
    src = src.replace("R5", "R6")
    for k, (new, old) in NAMES.items():
        src = src.replace(old, new)
    # 標題加版本
    src = re.sub(r'^(strategy|indicator)\("([^"]+)"', lambda m: f'{m.group(1)}("{m.group(2)} r6({TS_TITLE})"', src, count=1, flags=re.M)
    # 檔頭加版本行
    src = src.replace("// ═══════════════════════════════════════════════════════════════════════════\n//  R6-",
                      f"// ═══════════════════════════════════════════════════════════════════════════\n//  版本 r6({TS_TITLE})\n//  R6-", 1)
    return src


def must(src, old, new, what, count=1):
    assert old in src, f"[{what}] 找不到要替換的片段：{old[:60]!r}"
    return src.replace(old, new, count)


# ═══════════════════════════════ R6-A ═══════════════════════════════
a = (P / NAMES["a"][1]).read_text(encoding="utf-8")
a = common(a, "a")

VOL_BLOCK = '''
// ── ⑧ 主圖底部成交量 + 主力大單日 ──
// 成交量柱以 plotcandle 畫在價格區間下方：柱底 = 最近 volWin 根最低價再往下 3%，
// 柱高按視窗內最大量等比縮放到價格區間的 volArea%。主力大單 = 量 ≥ bigX × 均量，
// 且收在當日區間上緣 (買入) / 下緣 (賣出)。
grpVol  = "⑧ 成交量 (主圖底部)"
showVol = input.bool(true, "顯示成交量柱", group = grpVol)
volLen  = input.int(50, "均量期數", minval = 5, group = grpVol)
bigX    = input.float(2.0, "主力大單門檻 (× 均量)", minval = 1.2, step = 0.1, group = grpVol)
bigPos  = input.float(0.6, "主力買入：收盤位於當日區間 ≥ (0.5–1)；賣出反之", minval = 0.5, maxval = 1, step = 0.05, group = grpVol)
volArea = input.float(18, "成交量區佔價格區間高度 %", minval = 5, maxval = 40, group = grpVol)
volWin  = input.int(150, "定位視窗 (根)", minval = 20, group = grpVol)
markBig = input.bool(true, "K 線旁另加 ◆ 標記", group = grpVol)
cBuy    = input.color(#2563eb, "主力買入色", group = grpVol)
cSell   = input.color(#f97316, "主力賣出色", group = grpVol)
cVolN   = input.color(color.new(color.gray, 65), "一般成交量色", group = grpVol)

vAvg    = ta.sma(volume, volLen)
rngPos  = high != low ? (close - low) / (high - low) : 0.5
bigVol  = volume >= vAvg * bigX
bigBuy  = bigVol and close > open and rngPos >= bigPos
bigSell = bigVol and close < open and rngPos <= 1 - bigPos
nBuy20  = math.sum(bigBuy  ? 1 : 0, 20)
nSell20 = math.sum(bigSell ? 1 : 0, 20)

winLo = ta.lowest(low, volWin)
winHi = ta.highest(high, volWin)
vMax  = ta.highest(volume, volWin)
vBase = winLo - (winHi - winLo) * 0.03
vTop  = vBase + (winHi - winLo) * volArea / 100 * (vMax > 0 ? volume / vMax : 0)
volCol = bigBuy ? cBuy : bigSell ? cSell : cVolN
plotcandle(showVol ? vBase : na, showVol ? vTop : na, showVol ? vBase : na, showVol ? vTop : na,
     "成交量 (主圖底部)", color = volCol, wickcolor = color.new(color.gray, 100), bordercolor = volCol)
plotshape(markBig and bigBuy,  "主力大單買入日", shape.diamond, location.belowbar, cBuy,  size = size.tiny)
plotshape(markBig and bigSell, "主力大單賣出日", shape.diamond, location.abovebar, cSell, size = size.tiny)
plot(volume, "成交量", color = volCol, display = display.data_window)
plot(vAvg,   "均量",   color = color.gray, display = display.data_window)

'''
a = must(a, "// M2 狀態面板 (貼右；", VOL_BLOCK.lstrip("\n") + "// M2 狀態面板 (貼右；", "A 插入成交量區塊")
# 狀態框 9 列 → 10 列，新增「主力大單」列
a = must(a, "table.new(f_boxPos(boxPos), 2, 9,", "table.new(f_boxPos(boxPos), 2, 10,", "A 表格列數")
a = a.replace("boxH / 9", "boxH / 10")
ROW9 = '''    table.cell(tbl, 0, 9, "主力大單 (20日)", width = boxW * 0.55, height = boxH / 10, text_size = size.small)
    table.cell(tbl, 1, 9, "買 " + str.tostring(nBuy20) + " · 賣 " + str.tostring(nSell20) + (bigBuy ? " ·今日主買" : bigSell ? " ·今日主賣" : ""),
         width = boxW * 0.45, height = boxH / 10, text_size = size.small,
         bgcolor = bigBuy ? color.new(cBuy, 60) : bigSell ? color.new(cSell, 60) : na)

// ── M2 警報 ──'''
a = must(a, "\n// ── M2 警報 ──", "\n" + ROW9, "A 表格新增列")
a = a.rstrip("\n") + '''
alertcondition(bigBuy,  "⑧ 主力大單買入日", "{{ticker}} 成交量 ≥ 均量 ×門檻 且收在區間上緣 — 主力大單買入")
alertcondition(bigSell, "⑧ 主力大單賣出日", "{{ticker}} 成交量 ≥ 均量 ×門檻 且收在區間下緣 — 主力大單賣出")
'''
(P / NAMES["a"][0]).write_text(a, encoding="utf-8")

# ═══════════════════════════════ R6-B ═══════════════════════════════
b = (P / NAMES["b"][1]).read_text(encoding="utf-8")
b = common(b, "b")
b = must(b, "overlay = false, max_labels_count = 300)", "overlay = false, max_labels_count = 300, max_lines_count = 200)", "B 宣告")
b = must(b, 'grid   = input.int(11, "解析度 (格數, 建議奇數 9–13；pane 較矮用小值)", minval = 9, maxval = 21, group = grpK)',
            'grid   = input.int(21, "解析度 (格數, 奇數；21 = 高解析，pane 較矮用 13–15)", minval = 9, maxval = 41, step = 2, group = grpK)', "B grid")
b = must(b, "//  ⚠ 時鐘是格子陣列，pane 太矮會被壓扁 —— 請把本 pane 往下拖高（約 250px 以上）\n//     才會呈現正圓；或把「解析度」調小（9–11 格）。",
            "//  ⚠ 時鐘是格子陣列，pane 太矮會被壓扁 —— 請把本 pane 往下拖高（約 300px 以上）\n"
            "//     才會呈現正圓；或把「解析度」調小（13–15 格）。\n"
            "//  R6：新增 MACD 頂背馳 / 底背馳（M1 ④），時鐘解析度提高、已走過的弧段以亮色顯示。", "B 檔頭")

DIV_INPUTS = '''grpDv = "M1 ④ 背馳 (頂 / 底)"
showDiv = input.bool(true, "顯示頂背馳 / 底背馳", group = grpDv)
divSrc  = input.string("柱狀圖", "背馳依據", options = ["柱狀圖", "MACD 線"], group = grpDv)
lbL     = input.int(5, "轉折左側確認根數", minval = 1, maxval = 20, group = grpDv)
lbR     = input.int(3, "轉折右側確認根數 (越小越早、越易誤判)", minval = 1, maxval = 10, group = grpDv)
divMin  = input.int(5,  "兩個轉折最少相隔 (日)", minval = 1, group = grpDv)
divMax  = input.int(60, "兩個轉折最多相隔 (日)", minval = 5, group = grpDv)
divLine = input.bool(true, "日線圖上畫背馳連線", group = grpDv)

'''
b = must(b, "// ── ⑦ 版面（四支 R6 腳本", DIV_INPUTS + "// ── ⑦ 版面（四支 R6 腳本", "B 背馳輸入")

OLD_CYCLE_TAIL = '''    el = bar_index - cs + 1
    au = array.size(ul) > 0 ? array.avg(ul) : defLen
    ad = array.size(dl) > 0 ? array.avg(dl) : defLen
    [m, s, h, u, fl, rs, el, au, ad, ll]

[macdL, sigLine, hist, up, flip, rising, elapsed, avgUp, avgDn, lastLen] =
     request.security(syminfo.tickerid, cycTF, f_cycle(), lookahead = barmerge.lookahead_off)
'''
NEW_CYCLE_TAIL = '''    el = bar_index - cs + 1
    au = array.size(ul) > 0 ? array.avg(ul) : defLen
    ad = array.size(dl) > 0 ? array.avg(dl) : defLen
    // ── 背馳（同樣在日線環境計算）：常規背馳
    //    底背馳 = 價格更低的低點，但振盪器 (零軸下) 低點抬高；頂背馳 = 價格更高的高點，但振盪器 (零軸上) 高點降低
    o    = divSrc == "柱狀圖" ? h : m
    plF  = not na(ta.pivotlow(o, lbL, lbR))
    phF  = not na(ta.pivothigh(o, lbL, lbR))
    oL   = o[lbR]
    oH   = o[lbR]
    pvL  = low[lbR]
    pvH  = high[lbR]
    prevOL = ta.valuewhen(plF, oL, 1)
    prevPL = ta.valuewhen(plF, pvL, 1)
    prevBL = ta.valuewhen(plF, bar_index - lbR, 1)
    prevOH = ta.valuewhen(phF, oH, 1)
    prevPH = ta.valuewhen(phF, pvH, 1)
    prevBH = ta.valuewhen(phF, bar_index - lbR, 1)
    distL = bar_index - lbR - prevBL
    distH = bar_index - lbR - prevBH
    bull = plF and oL < 0 and oL > prevOL and pvL < prevPL and distL >= divMin and distL <= divMax
    bear = phF and oH > 0 and oH < prevOH and pvH > prevPH and distH >= divMin and distH <= divMax
    [m, s, h, u, fl, rs, el, au, ad, ll, bull, bear, oL, oH, prevOL, prevOH, distL, distH]

[macdL, sigLine, hist, up, flip, rising, elapsed, avgUp, avgDn, lastLen,
     bullRaw, bearRaw, divOL, divOH, divPrevOL, divPrevOH, divDistL, divDistH] =
     request.security(syminfo.tickerid, cycTF, f_cycle(), lookahead = barmerge.lookahead_off)
'''
b = must(b, OLD_CYCLE_TAIL, NEW_CYCLE_TAIL, "B 週期引擎尾段")

DIV_DRAW = '''
// ── M1 背馳繪圖（訊號在轉折確認後 lbR 根才出現，標籤回貼到轉折那根）──
onCycTF = timeframe.period == cycTF
bullDiv = showDiv and bullRaw and newDay
bearDiv = showDiv and bearRaw and newDay
divOff  = onCycTF ? -lbR : 0
plotshape(bullDiv ? divOL : na, "底背馳", shape.labelup,   location.absolute, color.new(cUp, 0),
     text = "底背馳", textcolor = color.white, size = size.small, offset = divOff)
plotshape(bearDiv ? divOH : na, "頂背馳", shape.labeldown, location.absolute, color.new(cDn, 0),
     text = "頂背馳", textcolor = color.white, size = size.small, offset = divOff)
if divLine and onCycTF and bullDiv
    line.new(bar_index - lbR - int(divDistL), divPrevOL, bar_index - lbR, divOL, color = color.new(cUp, 0), width = 2)
if divLine and onCycTF and bearDiv
    line.new(bar_index - lbR - int(divDistH), divPrevOH, bar_index - lbR, divOH, color = color.new(cDn, 0), width = 2)

// Pine 沒有 math.atan2，自行實作（回傳弧度，範圍 -π..π）
f_atan2(y, x) =>
    x > 0 ? math.atan(y / x) :
     x < 0 ? (y >= 0 ? math.atan(y / x) + math.pi : math.atan(y / x) - math.pi) :
     (y > 0 ? math.pi / 2 : y < 0 ? -math.pi / 2 : 0.0)

// ── M1 時鐘 (table) ──'''
b = must(b, "\n// ── M1 時鐘 (table) ──", DIV_DRAW, "B 背馳繪圖")

OLD_CLOCK = b[b.index("    activeCol = up ? cUp : cDn"):b.index("    statTxt = ")]
NEW_CLOCK = '''    activeCol = up ? cUp : cDn
    dateTxt = str.format_time(time, "MM/dd", tz)
    table.cell(clk, 0, 0, phaseTxt + "  " + dateTxt, width = cellW, height = hdrH, text_color = color.white, bgcolor = color.new(activeCol, 10),
         text_size = size.small, text_halign = text.align_center)

    // 高解析度時鐘：環厚、指針寬、圓心半徑都隨格數放大；12/3/6/9 刻度；已走過的弧段亮色
    c     = (grid - 1) / 2.0            // 圓心索引
    r     = c - 0.5                     // 圓環半徑
    ringW = math.max(0.55, grid / 22.0) // 環半厚 (格)
    handW = math.max(0.45, grid / 34.0) // 指針半寬 (格)
    ctrR  = math.max(0.6,  grid / 16.0) // 圓心半徑 (格)
    th = math.toradians(theta)
    ux = math.sin(th)                   // 指針方向單位向量 (x 向右, y 向下)
    uy = -math.cos(th)
    startA = up ? 270.0 : 90.0          // 本周期起點：上昇 9 點鐘、下跌 3 點鐘
    swept  = theta - startA
    swept := swept < 0 ? swept + 360 : swept   // 本周期已走過的角度 0–180

    for i = 0 to grid - 1               // 欄 (x)
        for j = 0 to grid - 1           // 列 (y)
            dx = i - c
            dy = j - c
            d  = math.sqrt(dx * dx + dy * dy)
            ang = math.todegrees(f_atan2(dx, -dy))     // 順時針、12 點鐘 = 0°
            ang := ang < 0 ? ang + 360 : ang
            rel = ang - startA
            rel := rel < 0 ? rel + 360 : rel           // 相對本周期起點的角度
            inCur    = rel < 180                       // 屬於本周期那一半環
            done     = inCur and rel <= swept          // 已走過
            topHalf  = ang >= 270 or ang < 90
            isRing   = math.abs(d - r) <= ringW
            isTick   = isRing and (math.abs(dx) <= 0.5 or math.abs(dy) <= 0.5)
            along    = dx * ux + dy * uy
            perp     = math.abs(dx * uy - dy * ux)
            onHand   = along >= 0 and along <= r - ringW - 0.4 and perp <= handW
            isCenter = d <= ctrR
            inner    = d < r - ringW - 0.4 and d > r - ringW - 1.6   // 環內側一圈 (放刻度數字)

            cellBg = color.new(color.black, 100)
            cellTx = ""
            if isCenter
                cellBg := color.new(color.gray, 20)
            else if onHand
                cellBg := cHand
            else if isTick
                cellBg := color.new(color.white, 0)
            else if isRing
                halfCol = topHalf ? cUp : cDn
                cellBg := color.new(halfCol, done ? 0 : inCur ? 55 : 82)
            else if inner and grid >= 15
                if math.abs(dx) <= 0.5
                    cellTx := dy < 0 ? "12" : "6"
                else if math.abs(dy) <= 0.5
                    cellTx := dx < 0 ? "9" : "3"

            table.cell(clk, i, j + 1, cellTx, width = cellW, height = cellH,
                 bgcolor = cellBg, text_color = color.new(color.gray, 0), text_size = size.tiny,
                 text_halign = text.align_center, text_valign = text.align_center)

'''
b = b.replace(OLD_CLOCK, NEW_CLOCK)
b = b.rstrip("\n") + '''
alertcondition(bullDiv, "M1 底背馳", "{{ticker}} 日線 MACD 底背馳：價格創低但動能抬高 — 留意反轉向上")
alertcondition(bearDiv, "M1 頂背馳", "{{ticker}} 日線 MACD 頂背馳：價格創高但動能降低 — 留意反轉向下")
'''
(P / NAMES["b"][0]).write_text(b, encoding="utf-8")

# ═══════════════════════════════ R6-C ═══════════════════════════════
c = (P / NAMES["c"][1]).read_text(encoding="utf-8")
c = common(c, "c")
c = must(c, 'showVcp = input.bool(true, "顯示明細面板 (本 pane 右側)", group = grpW)\n',
            'showVcp = input.bool(true, "顯示明細面板 (本 pane 右側)", group = grpW)\n'
            'lblSz   = input.string("中", "等級標籤字級 (R6：預設放大一倍)", options = ["小", "中", "大"], group = grpW)\n'
            'f_lblSz(s) => s == "小" ? size.small : s == "大" ? size.large : size.normal\n', "C 字級輸入")
c = must(c, '''         color = color.new(gCol, 15), textcolor = color.white, size = size.tiny)''',
            '''         color = color.new(gCol, 15), textcolor = color.white, size = f_lblSz(lblSz))''', "C 標籤字級")
(P / NAMES["c"][0]).write_text(c, encoding="utf-8")

# ═══════════════════════════════ R6-D ═══════════════════════════════
d = (P / NAMES["d"][1]).read_text(encoding="utf-8")
d = common(d, "d")
OLD_D_PLOT = d[d.index("certCol = certTotal >= certAlert"):d.index('bgcolor(hlOk ? color.new(#3FB68B, 92) : na, title = "一底高於一底 結構")') + len('bgcolor(hlOk ? color.new(#3FB68B, 92) : na, title = "一底高於一底 結構")')]
NEW_D_PLOT = '''// ── 曲線：只有「高確定性」(總分 ≥ 門檻) 的區段著色；其餘灰色、無填色、無背景 ──
hiCert  = certTotal >= certAlert
certCol = hiCert ? color.new(#3FB68B, 0) : color.new(#8B98A5, 35)
pCert = plot(certTotal, "確定性總分", color = certCol, linewidth = 2)
pThr  = plot(certAlert, "高確定性分界 (門檻)", color = color.new(#3FB68B, 30), linewidth = 1)
fill(pCert, pThr, color = hiCert ? color.new(#3FB68B, 70) : na, title = "高確定性區 (曲線 ≥ 門檻)")
bgcolor(hiCert ? color.new(#3FB68B, 88) : na, title = "高確定性背景")
plotshape(hiCert and not hiCert[1] ? certTotal : na, "進入高確定性", shape.labelup, location.absolute,
     color.new(#3FB68B, 0), text = "高確定", textcolor = color.white, size = size.small)
plot(showParts ? cBreak * 100 : na, "突破 25%", color = color.new(color.green, 45))
plot(showParts ? cRetr  * 100 : na, "回升 10%", color = color.new(color.lime, 45))
plot(showParts ? cTime  * 100 : na, "守底 15%", color = color.new(color.blue, 45))
plot(showParts ? cDv    * 100 : na, "量縮 15%", color = color.new(color.purple, 45))
plot(showParts ? cContr * 100 : na, "收縮 10%", color = color.new(color.orange, 45))
plot(showParts ? cRs    * 100 : na, "RS 10%",   color = color.new(color.red, 45))
plot(showParts ? cMa    * 100 : na, "均線 15%", color = color.new(color.gray, 45))
hline(50, "50", color = color.new(color.gray, 60))
bgcolor(showHLbg and hlOk ? color.new(#3FB68B, 94) : na, title = "一底高於一底 結構 (預設關閉)")'''
d = d.replace(OLD_D_PLOT, NEW_D_PLOT)
d = must(d, 'showParts = input.bool(false, "同時畫出 7 個分項細線", group = grpW)\n',
            'showParts = input.bool(false, "同時畫出 7 個分項細線", group = grpW)\n'
            'showHLbg  = input.bool(false, "一底高於一底 結構背景 (淡綠；R6 預設關閉)", group = grpW)\n', "D 輸入")
d = must(d, '''    hdrCol = certTotal >= certAlert ? color.new(#3FB68B, 10) :
             certTotal >= 50 ? color.new(#E5B15C, 10) : color.new(#6B7885, 10)''',
            '''    hdrCol = hiCert ? color.new(#3FB68B, 10) : color.new(#6B7885, 10)   // 只有高確定性才上色''', "D 表頭色")
(P / NAMES["d"][0]).write_text(d, encoding="utf-8")

# ═══════════════════════════════ 檢查 ═══════════════════════════════
for k, (new, _) in NAMES.items():
    t = (P / new).read_text(encoding="utf-8")
    decl = len(re.findall(r"^(?:indicator|strategy)\(", t, re.M))
    title = re.search(r'^(?:indicator|strategy)\("([^"]+)"', t, re.M).group(1)
    print(f"{new:44s} decl={decl} lines={t.count(chr(10)):4d} title={title!r} R5-left={'R5' in t}")
print("TS", TS_TITLE, TS_FILE)
