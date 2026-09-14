# -*- coding: utf-8 -*-
"""
由最新的 R6-A (combo_a_main_r6(*).pine) 產生 R7：EMA9 帶寬策略 + 價格重心 (MODULE 4) 合併在同一支主圖策略。

價格重心的線、成本帶、訊號全部畫在策略本身的價格座標上（與 K 線同一 pane、同一價格軸），
所以拖動價格軸放大 / 縮小 K 線時，重心線、成本帶會等比例跟著縮放；標準版獨立指標若被放到
「新價格軸 / 無軸」就不會同步，這是合併的主要目的。

用法：python3 build_r7.py   → r7_ema9_bw_gravity(mm.dd_hh.mm).pine
"""
import re, pathlib, datetime, zoneinfo, glob

P = pathlib.Path(__file__).parent
TZ = zoneinfo.ZoneInfo("Asia/Taipei")
now = datetime.datetime.now(TZ)
TS_TITLE = now.strftime("%m:%d_%H:%M")
TS_FILE  = now.strftime("%m.%d_%H.%M")
OUT = f"r7_ema9_bw_gravity({TS_FILE}).pine"

srcs = sorted(glob.glob(str(P / "combo_a_main_r6(*).pine")))
assert srcs, "找不到 R6-A"
a = pathlib.Path(srcs[-1]).read_text(encoding="utf-8")


def must(src, old, new, what):
    assert old in src, f"[{what}] 找不到：{old[:60]!r}"
    return src.replace(old, new, 1)


# ── 標題 / 檔頭 ──
a = re.sub(r'^strategy\("R6-A EMA9 BW \(main\) r6\([^)]*\)", shorttitle = "R6-A EMA9-BW",',
           f'strategy("R7 EMA9-BW-Gravity r7({TS_TITLE})", shorttitle = "R7 EMA9-BW-Gravity",', a, count=1, flags=re.M)
assert "R7 EMA9-BW-Gravity" in a, "標題未替換"
a = re.sub(r"^//  版本 r6\([^)]*\)\n//  R6-A  主圖：EMA9 Band Width Strategy",
           f"//  版本 r7({TS_TITLE})\n//  R7  主圖：EMA9 Band Width Strategy + 價格重心 (MODULE 4)", a, count=1, flags=re.M)
a = must(a, "//  本檔內容：MODULE 2（EMA9 中線 ± 帶寬、擠壓突破 / 回踩進場、風控出場）。",
            "//  本檔內容：MODULE 2（EMA9 中線 ± 帶寬、擠壓突破 / 回踩進場、風控出場）\n"
            "//           + MODULE 4 價格重心（當日 / 錨定 / 滾動 VWAP 或 POC；成本帶 ±kσ；斜率 / 穩定度 / 距離；\n"
            "//             上升 / 下跌最低阻力、定錨、假跌破 訊號）。重心與 K 線畫在同一價格軸，縮放同步。", "檔頭")

# ── ⑥ 模組整合：加入 M4 過濾開關 ──
a = must(a, '''minCert       = input.float(0, "M3：確定性總分 ≥ 此值才做多 (0 = 不過濾)", minval = 0, maxval = 100, step = 5, group = grpI, display = display.none)
''', '''minCert       = input.float(0, "M3：確定性總分 ≥ 此值才做多 (0 = 不過濾)", minval = 0, maxval = 100, step = 5, group = grpI, display = display.none)
useGravity    = input.bool(false, "M4：多單只在重心上移 / 定錨且價在重心上；空單只在重心下移且價在重心下", group = grpI, display = display.none)
''', "⑥ 整合")

# ── MODULE 4 輸入：放在 ⑦ 版面 之前 ──
M4_INPUTS = '''// ── ⑨ MODULE 4：價格重心（推論重建猫姐「重心指標」）──
grpG    = "⑨ 價格重心 (MODULE 4)"
showGrav = input.bool(true, "顯示重心線 / 成本帶 / 訊號", group = grpG, display = display.none)
gMode   = input.string("滾動 VWAP", "重心模式", options = ["當日 VWAP", "錨定 VWAP", "滾動 VWAP", "POC 成交量分佈"], group = grpG, display = display.none)
gSrc    = input.source(hlc3, "重心價格來源", group = grpG, display = display.none)
gAnchTF = input.timeframe("W", "錨定時間框 (錨定 VWAP 模式)", group = grpG, display = display.none)
gLenN   = input.int(30, "滾動長度 N (滾動 VWAP / POC)", minval = 5, maxval = 400, group = grpG, display = display.none)
gBins   = input.int(40, "POC 分箱數", minval = 10, maxval = 100, group = grpG, display = display.none)
gK      = input.float(1.0, "成本帶寬 (± k σ，成交量加權)", minval = 0.25, maxval = 3, step = 0.25, group = grpG, display = display.none)
gSlopeM = input.int(5, "斜率 / 穩定度窗口 M (根)", minval = 2, maxval = 50, group = grpG, display = display.none)
gStabThr= input.float(0.5, "穩定：M 根位移 ≤ 此 ATR 倍數", minval = 0.1, maxval = 3, step = 0.1, group = grpG, display = display.none)
gTrendThr = input.float(0.8, "上移 / 下移：M 根位移 ≥ 此 ATR 倍數", minval = 0.2, maxval = 5, step = 0.1, group = grpG, display = display.none)
gFakeM  = input.int(3, "假跌破：跌破後幾根內收回", minval = 1, maxval = 10, group = grpG, display = display.none)
gAtrLen = input.int(14, "重心用 ATR 長度", minval = 5, group = grpG, display = display.none)

'''
a = must(a, "// ── ⑦ 版面（四支 R6 腳本", M4_INPUTS + "// ── ⑦ 版面（四支 R6 腳本", "M4 輸入")

# ── MODULE 4 計算：放在 M2 訊號之前（訊號要用 gLongOK / gShortOK 過濾）──
M4_CALC = '''// ── MODULE 4 計算：價格重心 ──
gAtr   = ta.atr(gAtrLen)
gVol   = nz(volume, 0.0)                     // 無成交量標的 (指數) → 退回均價
gSma   = ta.sma(gSrc, gLenN)
gVwapDay = nz(ta.vwap(gSrc, timeframe.change("D")), gSma)
gVwapAnc = nz(ta.vwap(gSrc, timeframe.change(gAnchTF)), gSma)
gSumPV = math.sum(gSrc * gVol, gLenN)
gSumV  = math.sum(gVol, gLenN)
gVwapRoll = gSumV > 0 ? gSumPV / gSumV : gSma
gHiN = ta.highest(high, gLenN)
gLoN = ta.lowest(low, gLenN)
f_gPoc() =>
    step = (gHiN - gLoN) / gBins
    var vols = array.new_float(gBins, 0.0)
    array.fill(vols, 0.0)
    ok = bar_index >= gLenN and not na(step) and step > 0 and gSumV > 0
    if ok
        for i = 0 to gLenN - 1
            b = int(math.min(gBins - 1, math.max(0, (nz(gSrc[i], gLoN) - gLoN) / step)))
            array.set(vols, b, array.get(vols, b) + nz(volume[i], 0.0))
    idx = ok ? array.indexof(vols, array.max(vols)) : 0
    ok ? gLoN + (idx + 0.5) * step : gSma
gPoc = f_gPoc()
gravity = gMode == "當日 VWAP" ? gVwapDay : gMode == "錨定 VWAP" ? gVwapAnc : gMode == "滾動 VWAP" ? gVwapRoll : gPoc

gDev2  = math.sum(gVol * math.pow(gSrc - gravity, 2), gLenN)
gSigma = gSumV > 0 ? math.sqrt(gDev2 / gSumV) : gAtr
gSigma := na(gSigma) or gSigma <= 0 ? gAtr : gSigma
gUpper = gravity + gK * gSigma
gLower = gravity - gK * gSigma

gShift  = gAtr > 0 ? (gravity - gravity[gSlopeM]) / gAtr : 0.0   // M 根位移 (ATR 倍數)
gStable = math.abs(gShift) <= gStabThr
gUp     = gShift >= gTrendThr
gDn     = gShift <= -gTrendThr
gDist   = gSigma > 0 ? (close - gravity) / gSigma : 0.0          // 價格距重心 (σ)
gAbove  = close > gravity
gPathUp = gUp and gAbove                                          // 上升最低阻力
gPathDn = gDn and not gAbove                                      // 下跌最低阻力
gAnchor = gStable and math.abs(gDist) <= gK                       // 定錨：重心穩、價在成本帶內
gBrokeDn = ta.crossunder(close, gravity)
gBrokeUp = ta.crossover(close, gravity)
gBarsBD  = ta.barssince(gBrokeDn)
gBarsBU  = ta.barssince(gBrokeUp)
gFakeBD  = gBrokeUp and gBarsBD <= gFakeM and gBarsBD > 0          // 假跌破收回
gFakeBU  = gBrokeDn and gBarsBU <= gFakeM and gBarsBU > 0          // 假突破跌回
gLongOK  = not useGravity or ((gUp or gAnchor) and gAbove)
gShortOK = not useGravity or (gDn and not gAbove)

'''
a = must(a, "// ── M2 訊號 ──", M4_CALC + "// ── M2 訊號 ──", "M4 計算")
a = must(a, "and dailyLongOK and notLateOK and vcpOK and certOK\n", "and dailyLongOK and notLateOK and vcpOK and certOK and gLongOK\n", "longSig 過濾")
a = must(a, "and dailyShortOK and notLateOK\n", "and dailyShortOK and notLateOK and gShortOK\n", "shortSig 過濾")

# ── MODULE 4 繪圖：與 K 線同一價格軸 ──
M4_PLOT = '''// ── MODULE 4 繪圖：重心線 / 成本帶 / 訊號（與 K 線同一價格軸，縮放同步）──
gCol = gUp ? color.new(#26a69a, 0) : gDn ? color.new(#ef5350, 0) : color.new(#f59e0b, 0)
pGrav = plot(showGrav ? gravity : na, "M4 價格重心", color = gCol, linewidth = 3, display = display.pane + display.data_window + display.price_scale)
pGU   = plot(showGrav ? gUpper : na, "M4 成本帶上緣", color = color.new(color.gray, 60), linewidth = 1, display = display.pane + display.data_window)
pGL   = plot(showGrav ? gLower : na, "M4 成本帶下緣", color = color.new(color.gray, 60), linewidth = 1, display = display.pane + display.data_window)
fill(pGU, pGL, color = gAnchor ? color.new(#f59e0b, 90) : color.new(color.gray, 95), title = "M4 成本帶 (黃 = 定錨中)")
plot(gShift, "M4 重心 M 根位移 (ATR)", display = display.data_window)
plot(gDist,  "M4 價格距重心 (σ)",      display = display.data_window)
plotshape(showGrav and gPathUp and not gPathUp[1], "M4 重心上移 (上升最低阻力)", shape.triangleup,   location.belowbar, color.new(#26a69a, 0), size = size.tiny, text = "重心上移", textcolor = #26a69a)
plotshape(showGrav and gPathDn and not gPathDn[1], "M4 重心下移 (下跌最低阻力)", shape.triangledown, location.abovebar, color.new(#ef5350, 0), size = size.tiny, text = "重心下移", textcolor = #ef5350)
plotshape(showGrav and gAnchor and not gAnchor[1], "M4 定錨開始", shape.diamond, location.belowbar, color.new(#f59e0b, 0), size = size.tiny)
if showGrav and gFakeBD
    [gl1, gn1] = f_note(bar_index, low, low - gAtr * 0.8, "假跌破 收回重心", #26a69a, false)
if showGrav and gFakeBU
    [gl2, gn2] = f_note(bar_index, high, high + gAtr * 0.8, "假突破 跌回重心", #ef5350, true)

'''
a = must(a, "// M2 狀態面板 (貼右；", M4_PLOT + "// M2 狀態面板 (貼右；", "M4 繪圖")

# ── 狀態面板 10 列 → 12 列 ──
a = must(a, "table.new(f_boxPos(boxPos), 2, 10,", "table.new(f_boxPos(boxPos), 2, 12,", "表格列數")
a = a.replace("boxH / 10", "boxH / 12")
ROWS = '''    gStateTxt = gPathUp ? "上升最低阻力" : gPathDn ? "下跌最低阻力" : gAnchor ? "定錨 (主力未走)" : gStable ? "走平" : "位移中"
    gStateCol = gPathUp ? color.new(#26a69a, 60) : gPathDn ? color.new(#ef5350, 60) : gAnchor ? color.new(#f59e0b, 60) : na
    table.cell(tbl, 0, 10, "價格重心 (M4 · " + gMode + ")", width = boxW * 0.55, height = boxH / 12, text_size = size.small)
    table.cell(tbl, 1, 10, str.tostring(gravity, format.mintick) + " · " + gStateTxt + (useGravity ? " ·過濾中" : ""), width = boxW * 0.45, height = boxH / 12, text_size = size.small, bgcolor = gStateCol)
    table.cell(tbl, 0, 11, "重心位移 / 價距重心", width = boxW * 0.55, height = boxH / 12, text_size = size.small)
    table.cell(tbl, 1, 11, str.tostring(gShift, "+#.##") + " ATR / " + str.tostring(gDist, "+#.##") + " σ", width = boxW * 0.45, height = boxH / 12, text_size = size.small,
         text_color = gAbove ? #26a69a : #ef5350)

// ── M2 警報 ──'''
a = must(a, "\n// ── M2 警報 ──", "\n" + ROWS, "表格新增列")
a = a.rstrip("\n") + '''
alertcondition(gPathUp and not gPathUp[1], "M4 重心上移 · 上升最低阻力", "{{ticker}} 價格重心上移且價在重心上 — 上升最低阻力")
alertcondition(gPathDn and not gPathDn[1], "M4 重心下移 · 下跌最低阻力", "{{ticker}} 價格重心下移且價在重心下 — 下跌最低阻力")
alertcondition(gAnchor and not gAnchor[1], "M4 重心定錨", "{{ticker}} 價格重心走平且價在成本帶內 — 主力未走")
alertcondition(gFakeBD, "M4 假跌破收回重心", "{{ticker}} 跌破價格重心後數根內收回 — 洗盤嫌疑")
alertcondition(gFakeBU, "M4 假突破跌回重心", "{{ticker}} 突破價格重心後數根內跌回 — 誘多嫌疑")
'''
a = a.replace("R6-A", "R7").replace("(與 R6-B/C/D 對齊)", "(與 R6-B/C/D 對齊；R6-B/C/D 不變)")
(P / OUT).write_text(a, encoding="utf-8")

decl = len(re.findall(r"^(?:indicator|strategy)\(", a, re.M))
bad_alert = [l for l in a.splitlines() if l.startswith("alertcondition(") and "str.tostring" in l]
print(f"{OUT}: lines={a.count(chr(10))} decl={decl} non-const-alert={len(bad_alert)} "
      f"gLongOK={'and gLongOK' in a} rows12={'2, 12' in a} boxH/12={a.count('boxH / 12')}")
