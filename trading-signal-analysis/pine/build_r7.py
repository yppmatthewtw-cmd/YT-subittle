# -*- coding: utf-8 -*-
"""
R7 六件套：由最新的 R6 四件套 + maojie 兩支原型重新整併、統一命名。

    R7-A  主圖 (overlay)   EMA9 帶寬策略 + 進出場 + 狀態面板     ← R6-A 原樣（策略與價格重心分開）
    R7-B  下方 pane ①      MACD 柱狀圖 + 週期時鐘 + 背馳 + 升破前頂/跌破前底   ← R6-B 原樣
    R7-C  下方 pane ②      VCP 指數 + 標準化成交量柱             ← R6-C 原樣
    R7-D  下方 pane ③      確定性指數 (高確定性著色)             ← R6-D 原樣
    R7-E  主圖 (overlay)   價格重心：VWAP / 錨定 / 滾動 / POC 重心 + 成本帶 + 訊號   ← maojie_price_gravity_r1
    R7-F  下方 pane ④      買賣力度：1 分鐘近似主動買賣 → 力度 / 累積力度 / 結構低點    ← maojie_buy_sell_force

用法：python3 build_r7.py   → r7a_main(mm.dd_hh.mm).pine … r7f_force(mm.dd_hh.mm).pine
"""
import re, pathlib, datetime, zoneinfo, glob

P = pathlib.Path(__file__).parent
MJ = P.parent / "maojie" / "pine"
TZ = zoneinfo.ZoneInfo("Asia/Taipei")
now = datetime.datetime.now(TZ)
TS_TITLE = now.strftime("%m:%d_%H:%M")
TS_FILE  = now.strftime("%m.%d_%H.%M")


def latest(pattern):
    fs = sorted(glob.glob(pattern))
    assert fs, f"找不到 {pattern}"
    return pathlib.Path(fs[-1])


# (輸出檔名, 來源, 舊標題正則, 新標題, 新短標題)
SPEC = [
    ("a", f"r7a_main({TS_FILE}).pine",       latest(str(P / "combo_a_main_r6(*).pine")),       "R7-A EMA9 BW (main)",        "R7-A EMA9-BW"),
    ("b", f"r7b_macd_clock({TS_FILE}).pine", latest(str(P / "combo_b_macd_clock_r6(*).pine")), "R7-B MACD + Cycle Clock",    "R7-B MACD Clock"),
    ("c", f"r7c_vcp({TS_FILE}).pine",        latest(str(P / "combo_c_vcp_r6(*).pine")),        "R7-C VCP Score",             "R7-C VCP"),
    ("d", f"r7d_cert({TS_FILE}).pine",       latest(str(P / "combo_d_cert_r6(*).pine")),       "R7-D Certainty 7",           "R7-D Cert7"),
    ("e", f"r7e_gravity({TS_FILE}).pine",    MJ / "maojie_price_gravity_r1.pine",              "R7-E Price Gravity",         "R7-E Gravity"),
    ("f", f"r7f_force({TS_FILE}).pine",      MJ / "maojie_buy_sell_force.pine",                "R7-F Buy/Sell Force",        "R7-F Force"),
]
NEWNAMES = {k: out for k, out, *_ in SPEC}

HEADER_TABLE = f'''//  R7 六件套 —— 每支各佔一個 pane；策略 (A) 與價格重心 (E) 分開，可各自加減：
//     R7-A  主圖 (overlay)   EMA9 帶寬策略 + 進出場 + 狀態面板                {NEWNAMES["a"]}
//     R7-B  下方 pane ①      MACD 柱狀圖 + 週期時鐘 + 背馳 + 升破前頂/跌破前底  {NEWNAMES["b"]}
//     R7-C  下方 pane ②      VCP 指數 + 標準化成交量柱                         {NEWNAMES["c"]}
//     R7-D  下方 pane ③      確定性指數 (高確定性著色)                         {NEWNAMES["d"]}
//     R7-E  主圖 (overlay)   價格重心 (VWAP / 錨定 / 滾動 / POC) + 成本帶 + 訊號  {NEWNAMES["e"]}
//     R7-F  下方 pane ④      買賣力度 (1 分鐘近似主動買賣) + 結構低點 + 防守位   {NEWNAMES["f"]}
//  六支的「⑦ 版面 boxW」設同一值即等寬貼右。R7-E 框預設右上 (高 40%)；同時載入 R7-A 時請把 R7-A 的框改 右下 / 高度 60。
'''


def retitle(src, old_title_re, new_title, new_short):
    src, n = re.subn(r'^(strategy|indicator)\("' + old_title_re + r'[^"]*", shorttitle = "[^"]*"',
                     lambda m: f'{m.group(1)}("{new_title} r7({TS_TITLE})", shorttitle = "{new_short}"', src, count=1, flags=re.M)
    assert n == 1, f"標題未替換: {old_title_re}"
    return src


def fix_clock_width(src):
    """R7-B：table 每格有固定內距，時鐘 21 欄累積後比其他框寬 (右緣對齊、左緣突出)。
    以 clkWfix / clkHfix (% 圖表寬 / % pane 高) 從 boxW / boxH 扣除後再平分給格子。"""
    src = src.replace('boxPos = input.string("右中", "垂直位置 (高度 <100 時才有差別)", options = ["右上", "右中", "右下"], group = grpL, display = display.none)\n',
                      'boxPos = input.string("右中", "垂直位置 (高度 <100 時才有差別)", options = ["右上", "右中", "右下"], group = grpL, display = display.none)\n'
                      'clkWfix = input.float(1.2, "時鐘寬度補正 (% 圖表寬；時鐘比其他框寬就調大、窄就調小)", minval = 0, maxval = 6, step = 0.1, group = grpL, display = display.none)\n'
                      'clkHfix = input.float(3.0, "時鐘高度補正 (% pane 高；時鐘超出 pane 就調大)", minval = 0, maxval = 20, step = 0.5, group = grpL, display = display.none)\n', 1)
    src = src.replace("cellW = boxW / grid\ncellH = (boxH - 2 * hdrH) / grid",
                      "cellW = (boxW - clkWfix) / grid            // 扣除格子內距累積的寬度，使時鐘與其他框等寬、左右緣對齊\n"
                      "cellH = (boxH - 2 * hdrH - clkHfix) / grid", 1)
    assert "clkWfix" in src and "(boxW - clkWfix) / grid" in src, "B 時鐘寬度補正未套用"
    return src


def convert_r6(src, new_title, new_short):
    """R6-A/B/C/D → R7：換標題、版本、檔頭檔案表；計算與畫法不變。"""
    src = retitle(src, r"R6-[ABCD] ", new_title, new_short)
    src = re.sub(r"^//  版本 r6\([^)]*\)", f"//  版本 r7({TS_TITLE})", src, count=1, flags=re.M)
    # 檔頭的四件套說明 → 六件套
    src = re.sub(r"//  R6 套件 —— [^\n]*\n(?://     R6-[ABCD][^\n]*\n){4}//  四支的計算邏輯與 R4 逐字相同[^\n]*\n",
                 HEADER_TABLE, src, count=1)
    assert "R7 六件套" in src, "檔頭未替換"
    src = src.replace("R6-A", "R7-A").replace("R6-B", "R7-B").replace("R6-C", "R7-C").replace("R6-D", "R7-D")
    src = src.replace("四支 R6 腳本", "六支 R7 腳本").replace("R6 預設", "R7 預設").replace("R6：", "R7：").replace("（R6 預設關閉）", "（R7 預設關閉）")
    return src


def convert_e(src):
    src = retitle(src, r"價格重心 Price Gravity r1", "R7-E Price Gravity", "R7-E Gravity")
    src = src.replace("//  價格重心 (Price Gravity) —— 推論重建猫姐「重心指標」的公開版 r1（r0 因 alertcondition 訊息非常數而無法編譯）",
                      f"//  版本 r7({TS_TITLE})\n//  R7-E  主圖：價格重心 (Price Gravity) —— 推論重建猫姐「重心指標」\n//\n" + HEADER_TABLE + "//")
    # 資訊框：預設左上，避免與 R7-A 右側狀態框重疊；位置選項加入左側
    src = src.replace('boxPos = input.string("右上", "位置", options = ["右上", "右中", "右下"], group = grpL, display = display.none)',
                      'boxPos = input.string("右上", "位置 (與其他 R7 框同貼右；若與 R7-A 狀態框重疊，把 R7-A 改 右下 / 高度 60)", options = ["右上", "右中", "右下", "左上", "左中", "左下"], group = grpL, display = display.none)')
    src = src.replace('f_boxPos(s) => s == "右上" ? position.top_right : s == "右下" ? position.bottom_right : position.middle_right',
                      'f_boxPos(s) => s == "左上" ? position.top_left : s == "左中" ? position.middle_left : s == "左下" ? position.bottom_left :\n'
                      '     s == "右上" ? position.top_right : s == "右下" ? position.bottom_right : position.middle_right')
    assert 'position.top_left' in src, "E 版面未替換"
    return src


def convert_f(src):
    src = retitle(src, r"買賣力度 Buy/Sell Force r0", "R7-F Buy/Sell Force", "R7-F Force")
    src = src.replace("//  買賣力度 (Buy / Sell Force) —— 推論重建猫姐「買賣力道」的公開版 r0（下方 pane）",
                      f"//  版本 r7({TS_TITLE})\n//  R7-F  下方 pane：買賣力度 (Buy / Sell Force) —— 推論重建猫姐「買賣力道」\n//\n" + HEADER_TABLE + "//")
    return src


for key, out, srcfile, title, short in SPEC:
    s = srcfile.read_text(encoding="utf-8")
    if key in "abcd":
        s = convert_r6(s, title, short)
        if key == "b":
            s = fix_clock_width(s)
    elif key == "e":
        s = convert_e(s)
    else:
        s = convert_f(s)
    (P / out).write_text(s, encoding="utf-8")
    decl = len(re.findall(r"^(?:indicator|strategy)\(", s, re.M))
    bad_alert = [l for l in s.splitlines() if l.startswith("alertcondition(") and "str.tostring" in l]
    t = re.search(r'^(?:indicator|strategy)\("([^"]+)", shorttitle = "([^"]+)"', s, re.M)
    print(f"{out:34s} decl={decl} non-const-alert={len(bad_alert)} lines={s.count(chr(10)):4d} title={t.group(1)!r} short={t.group(2)!r}")
print("TS", TS_TITLE)
