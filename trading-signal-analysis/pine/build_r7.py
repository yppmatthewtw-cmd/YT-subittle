# -*- coding: utf-8 -*-
"""
R7 八件套：由最新的 R6 四件套 + maojie 兩支原型 + Livermore + 波動指數重新整併、統一命名。

    R7-A  主圖 (overlay)   EMA9 帶寬策略 + 進出場 + 狀態面板     ← R6-A 原樣（策略與價格重心分開）
    R7-B  下方 pane ①      MACD 柱狀圖 + 週期時鐘 + 背馳 + 升破前頂/跌破前底   ← R6-B 原樣
    R7-C  下方 pane ②      VCP 指數 + 標準化成交量柱             ← R6-C 原樣
    R7-D  下方 pane ③      確定性指數 (高確定性著色)             ← R6-D 原樣
    R7-E  主圖 (overlay)   價格重心：VWAP / 錨定 / 滾動 / POC 重心 + 成本帶 + 訊號   ← maojie_price_gravity_r1
    R7-F  下方 pane ④      買賣力度：1 分鐘近似主動買賣 → 力度 / 累積力度 / 結構低點    ← maojie_buy_sell_force
    R7-G  主圖 (overlay)   Livermore 最低阻力線：樞紐點結構 + Market Key + 放量/跟進     ← livermore_least_resistance
    R7-H  下方 pane ⑤      波動指數：絕對波動水準 → 未來 20/40 日大幅回撤機率 (高 = 平靜)   ← volatility_index

用法：python3 build_r7.py   → r7a_main(mm.dd_hh.mm).pine … r7h_volidx(mm.dd_hh.mm).pine
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
    ("g", f"r7g_livermore({TS_FILE}).pine",  P / "livermore_least_resistance.pine",            "R7-G Livermore Least-Resistance", "R7-G Livermore"),
    ("h", f"r7h_volidx({TS_FILE}).pine",     P / "volatility_index.pine",                      "R7-H Volatility Index",      "R7-H VolIdx"),
]
NEWNAMES = {k: out for k, out, *_ in SPEC}

HEADER_TABLE = f'''//  R7 八件套 —— 每支各佔一個 pane；策略 (A) 與價格重心 (E) 分開，可各自加減：
//     R7-A  主圖 (overlay)   EMA9 帶寬策略 + 進出場 + 狀態面板                {NEWNAMES["a"]}
//     R7-B  下方 pane ①      MACD 柱狀圖 + 週期時鐘 + 背馳 + 升破前頂/跌破前底  {NEWNAMES["b"]}
//     R7-C  下方 pane ②      VCP 指數 + 標準化成交量柱                         {NEWNAMES["c"]}
//     R7-D  下方 pane ③      確定性指數 (高確定性著色)                         {NEWNAMES["d"]}
//     R7-E  主圖 (overlay)   價格重心 (VWAP / 錨定 / 滾動 / POC) + 成本帶 + 訊號  {NEWNAMES["e"]}
//     R7-F  下方 pane ④      買賣力度 (1 分鐘近似主動買賣) + 結構低點 + 防守位   {NEWNAMES["f"]}
//     R7-G  主圖 (overlay)   Livermore 最低阻力線：樞紐點結構 + Market Key 六欄 + 放量/跟進濾網  {NEWNAMES["g"]}
//     R7-H  下方 pane ⑤      波動指數：絕對波動水準 → 未來 20/40 日大幅回撤機率 (高 = 平靜 = 不易大跌)  {NEWNAMES["h"]}
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
    # 檔頭的四件套說明 → 七件套
    src = re.sub(r"//  R6 套件 —— [^\n]*\n(?://     R6-[ABCD][^\n]*\n){4}//  四支的計算邏輯與 R4 逐字相同[^\n]*\n",
                 HEADER_TABLE, src, count=1)
    assert "R7 八件套" in src, "檔頭未替換"
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


def convert_g(src):
    src = retitle(src, r"Livermore Least-Resistance r\d", "R7-G Livermore Least-Resistance", "R7-G Livermore")
    src = src.replace("//  Livermore 最低阻力線 (Line of Least Resistance) r1 —— 主圖 overlay，中短線版：只畫「一條線」",
                      f"//  版本 r7({TS_TITLE})\n//  R7-G  主圖：Livermore 最低阻力線 (Line of Least Resistance)\n//\n" + HEADER_TABLE + "//")
    return src


def convert_h(src):
    src = retitle(src, r"波動指數 Volatility Index r\d", "R7-H Volatility Index", "R7-H VolIdx")
    src = src.replace("//  波動指數 (Volatility Index) r0 —— 下方 pane，0–100，越高 = 越平靜 = 未來大幅下跌的機會越小",
                      f"//  版本 r7({TS_TITLE})\n//  R7-H  下方 pane：波動指數 (Volatility Index)，0–100，越高 = 越平靜 = 未來大幅下跌的機會越小\n//\n" + HEADER_TABLE + "//")
    assert "R7 八件套" in src, "H 檔頭未替換"
    return src


def convert_f(src):
    src = retitle(src, r"買賣力度 Buy/Sell Force r0", "R7-F Buy/Sell Force", "R7-F Force")
    src = src.replace("//  買賣力度 (Buy / Sell Force) —— 推論重建猫姐「買賣力道」的公開版 r0（下方 pane）",
                      f"//  版本 r7({TS_TITLE})\n//  R7-F  下方 pane：買賣力度 (Buy / Sell Force) —— 推論重建猫姐「買賣力道」\n//\n" + HEADER_TABLE + "//")
    return src


# ═══════════ 版面統一後處理：狀態列瘦身 + 備註框透明 + 文字加粗 ═══════════
def _close_paren(t, i):
    """t[i] 是 '(' 之後第一個字元；回傳對應右括號位置（跳過字串）。"""
    depth, q = 0, None
    while i < len(t):
        ch = t[i]
        if q:
            if ch == "\\":
                i += 2
                continue
            if ch == q:
                q = None
        elif ch in "\"'":
            q = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            if depth == 0:
                return i
            depth -= 1
        i += 1
    raise ValueError("unbalanced")


def add_kw(t, call_re, kw):
    """對每個符合 call_re 的呼叫，若尚無該具名引數，就在右括號前補上 ', kw'。"""
    out, pos = [], 0
    key = kw.split("=")[0].strip()
    for m in re.finditer(call_re, t):
        if m.start() < pos:
            continue
        close = _close_paren(t, m.end())
        body = t[m.end():close]
        out.append(t[pos:close])
        if not re.search(r"\b" + key + r"\s*=", body):
            out.append(", " + kw)
        pos = close
    out.append(t[pos:])
    return "".join(out)


BOLD = "text_formatting = text.format_bold"


def soften_boxes(src):
    # ⓪ 全套升到 Pine v6：粗體 (text_formatting = text.format_bold) 只有 v6 才有；v5 會報「no argument text_formatting」
    src = src.replace("//@version=5", "//@version=6\n// R7 全套為 Pine v6（備註框 / 資訊框粗體字 text_formatting 需要 v6）", 1)
    # ① plotshape / plotchar 不上狀態列（否則每個訊號都在標題列印一串 0.0000）
    src = add_kw(src, r"(?<![\w.])plotshape\(", "display = display.pane")
    src = add_kw(src, r"(?<![\w.])plotchar\(", "display = display.pane")
    # ② 所有備註框 (label) 與資訊框 (table) 文字加粗
    src = add_kw(src, r"(?<![\w.])label\.new\(", BOLD)
    src = add_kw(src, r"(?<![\w.])table\.cell\(", BOLD)
    # ③ 備註框底色改為近乎透明（f_note 共用 helper）
    src = src.replace("color = color.new(col, 40)", "color = color.new(col, 88)")
    # ④ 資訊框深色表頭 → 透明 + 黑字（白字在透明底上看不見）
    for dark in ("#374151", "#3FB68B", "#6B7885", "gCol"):
        src = src.replace(f"color.new({dark}, 10)", f"color.new({dark}, 88)")
    src = re.sub(r"(table\.cell\([^\n]*?)text_color = color\.white", r"\1text_color = color.black", src)
    # ⑤ 資訊框內的highlight 底色一律更淡（只動明確是 bgcolor / 顏色變數的那幾行）
    def lighten(m):
        line = m.group(0)
        if "cellBg" in line or "activeCol" in line or "clk" in line:   # 時鐘格子是圖形，不動
            return line
        return re.sub(r", (30|55|60|65|70)\)", ", 88)", line)
    src = re.sub(r"^.*(bgcolor =|Col = |Col := ).*$", lighten, src, flags=re.M)
    return src


for key, out, srcfile, title, short in SPEC:
    s = srcfile.read_text(encoding="utf-8")
    if key in "abcd":
        s = convert_r6(s, title, short)
        if key == "b":
            s = fix_clock_width(s)
    elif key == "e":
        s = convert_e(s)
    elif key == "g":
        s = convert_g(s)
    elif key == "h":
        s = convert_h(s)
    else:
        s = convert_f(s)
    s = soften_boxes(s)
    (P / out).write_text(s, encoding="utf-8")
    decl = len(re.findall(r"^(?:indicator|strategy)\(", s, re.M))
    bad_alert = [l for l in s.splitlines() if l.startswith("alertcondition(") and "str.tostring" in l]
    t = re.search(r'^(?:indicator|strategy)\("([^"]+)", shorttitle = "([^"]+)"', s, re.M)
    print(f"{out:34s} decl={decl} non-const-alert={len(bad_alert)} lines={s.count(chr(10)):4d} title={t.group(1)!r} short={t.group(2)!r}")
print("TS", TS_TITLE)
