# -*- coding: utf-8 -*-
"""
R5 版面補丁：四支腳本的資訊框統一寬度、右緣對齊、撐滿各自 pane 的高度。

原理：Pine 的 table.cell(width, height) 以「% 圖表寬」「% pane 高」計算。
四個 pane 共用同一圖表寬度 → 同一個 boxW % 就是同一像素寬；
每個 table 的列高加總 = boxH %（預設 100）→ 撐滿該 pane。
所有框固定貼右 (position.*_right) → 右緣自然對齊。

用法：先跑 split_r5.py 產生 R5 四件套，再跑本腳本。
"""
import re, pathlib

P = pathlib.Path(__file__).parent

LAYOUT_INPUTS = '''
// ── ⑦ 版面（四支 R5 腳本請設同一 boxW，四個資訊框即等寬、右緣對齊）──
grpL   = "⑦ 版面 (四個 pane 統一)"
boxW   = input.float(18, "資訊框寬度 (% 圖表寬；四支腳本設同值)", minval = 8, maxval = 45, step = 0.5, group = grpL)
boxH   = input.float(100, "資訊框高度 (% 本 pane 高；100 = 撐滿)", minval = 30, maxval = 100, step = 5, group = grpL)
boxPos = input.string("右中", "垂直位置 (高度 <100 時才有差別)", options = ["右上", "右中", "右下"], group = grpL)
f_boxPos(s) => s == "右上" ? position.top_right : s == "右下" ? position.bottom_right : position.middle_right
'''


def split_args(s, start):
    """從 s[start] (緊接 '(' 之後) 開始，回傳頂層逗號切出的各引數 (文字, 起, 迄) 與右括號位置。"""
    depth, i, args, seg_start, in_str, q = 0, start, [], start, False, ""
    while i < len(s):
        ch = s[i]
        if in_str:
            if ch == "\\":
                i += 2
                continue
            if ch == q:
                in_str = False
        elif ch in "\"'":
            in_str, q = True, ch
        elif ch in "([":
            depth += 1
        elif ch in ")]":
            if depth == 0:
                args.append((s[seg_start:i], seg_start, i))
                return args, i
            depth -= 1
        elif ch == "," and depth == 0:
            args.append((s[seg_start:i], seg_start, i))
            seg_start = i + 1
        i += 1
    raise ValueError("unbalanced parens")


def size_cells(src, table_name, col_widths, row_h_expr):
    """為 table_name 的每個 table.cell(...) 呼叫，在第 4 個引數 (text) 之後插入 width/height。
    col_widths: 以欄索引為 key 的 Pine 運算式字串。既有的 width=/height= 會被移除後重加。"""
    out, pos = [], 0
    pat = re.compile(r"table\.cell\(\s*" + re.escape(table_name) + r"\s*,")
    for m in pat.finditer(src):
        args, close = split_args(src, m.end())
        if len(args) < 4:
            continue
        col = args[0][0].strip()          # args[0] = 欄, args[1] = 列 (表名已被 regex 吃掉)
        try:
            w = col_widths[int(col)]
        except (ValueError, KeyError):
            w = col_widths.get("var", "boxW")     # 迴圈變數 (時鐘格子) 用整體公式
        # 移除既有的 width= / height= 具名引數
        # args[0..2] = 欄, 列, 文字；其後為具名引數
        kept = [a for a in args[3:] if not re.match(r"\s*(width|height)\s*=", a[0])]
        rebuilt = (src[m.start():m.end()] + ",".join(a[0] for a in args[:3]) +
                   f", width = {w}, height = {row_h_expr}" +
                   "".join("," + a[0] for a in kept) + ")")
        out.append(src[pos:m.start()])
        out.append(rebuilt)
        pos = close + 1
    out.append(src[pos:])
    return "".join(out)


def anchor_right(src, table_name):
    """把 table.new(position.xxx, ...) 的位置改為 f_boxPos(boxPos)。"""
    return re.sub(r"(table\.new\()\s*position\.\w+\s*,",
                  r"\1f_boxPos(boxPos),", src, count=1) if table_name else src


def insert_inputs(src, marker_regex):
    """在第一個符合 marker 的行之前插入版面輸入區塊。"""
    m = re.search(marker_regex, src, re.M)
    assert m, f"marker not found: {marker_regex}"
    return src[:m.start()] + LAYOUT_INPUTS.lstrip("\n") + "\n" + src[m.start():]


# ─────────────────────────── R5-A 主圖狀態框 (tbl 2×9) ───────────────────────────
a = (P / "combo_r5a_main.pine").read_text(encoding="utf-8")
a = insert_inputs(a, r"^// ── M2 指標 ──")
a = anchor_right(a, "tbl")
a = a.replace("// M2 狀態面板 (右上角；M1 時鐘預設在左上角，互不重疊)", "// M2 狀態面板 (貼右；寬度/高度/位置由 ⑦ 版面 決定，與 R5-B/C/D 對齊)")
a = size_cells(a, "tbl", {0: "boxW * 0.55", 1: "boxW * 0.45"}, "boxH / 9")
(P / "combo_r5a_main.pine").write_text(a, encoding="utf-8")

# ─────────────────────────── R5-B 時鐘 (clk grid×(grid+2)) ───────────────────────────
b = (P / "combo_r5b_macd_clock.pine").read_text(encoding="utf-8")
b = insert_inputs(b, r"^// ── M1 日線週期引擎")
# 時鐘格子尺寸改由 boxW / boxH 推導，原本的 cellW / cellH 輸入改為註解說明
b = re.sub(r'^cellW\s*=\s*input\.float\([^\n]*\n', '', b, flags=re.M)
b = re.sub(r'^cellH\s*=\s*input\.float\([^\n]*\n', '', b, flags=re.M)
b = re.sub(r'^posOpt\s*=\s*input\.string\([^\n]*\n', '', b, flags=re.M)   # 位置改由 ⑦ 版面 boxPos 決定
b = b.replace(
    'tpos = posOpt == "右上" ? position.top_right : posOpt == "右中" ? position.middle_right :\n'
    '       posOpt == "右下" ? position.bottom_right : posOpt == "左上" ? position.top_left :\n'
    '       posOpt == "左中" ? position.middle_left : position.bottom_left',
    '// 時鐘尺寸由 ⑦ 版面 的 boxW / boxH 推導：上下各一列文字 (hdrH%)，中間 grid 列平均分配\n'
    'hdrH  = 6.0\n'
    'cellW = boxW / grid\n'
    'cellH = (boxH - 2 * hdrH) / grid\n'
    'tpos  = f_boxPos(boxPos)')
assert "tpos  = f_boxPos(boxPos)" in b, "R5-B tpos block not replaced"
# 上下文字列：合併儲存格，只需給高度
b = size_cells(b, "clk", {"var": "cellW", 0: "cellW"}, "cellH")
# 上方狀態列 / 下方統計列 (col 0, row 0 / row grid+1) 用 hdrH
b = re.sub(r'(table\.cell\(clk, 0, 0, phaseTxt, width = cellW, height = )cellH', r'\1hdrH', b)
b = re.sub(r'(table\.cell\(clk, 0, grid \+ 1, statTxt, width = cellW, height = )cellH', r'\1hdrH', b)
(P / "combo_r5b_macd_clock.pine").write_text(b, encoding="utf-8")

# ─────────────────────────── R5-C VCP 明細 (tV 2×9) ───────────────────────────
c = (P / "combo_r5c_vcp.pine").read_text(encoding="utf-8")
c = insert_inputs(c, r"^f_clamp01\(x\)")
c = anchor_right(c, "tV")
c = size_cells(c, "tV", {0: "boxW * 0.45", 1: "boxW * 0.55"}, "boxH / 9")
(P / "combo_r5c_vcp.pine").write_text(c, encoding="utf-8")

# ─────────────────────────── R5-D 確定性 7 項 (tD 3×9) ───────────────────────────
d = (P / "combo_r5d_cert.pine").read_text(encoding="utf-8")
d = insert_inputs(d, r"^f_clamp01\(x\)")
d = anchor_right(d, "tD")
d = size_cells(d, "tD", {0: "boxW * 0.40", 1: "boxW * 0.38", 2: "boxW * 0.22"}, "boxH / 9")
(P / "combo_r5d_cert.pine").write_text(d, encoding="utf-8")

# ─────────────────────────── 檢查 ───────────────────────────
for f in ["combo_r5a_main.pine", "combo_r5b_macd_clock.pine", "combo_r5c_vcp.pine", "combo_r5d_cert.pine"]:
    t = (P / f).read_text(encoding="utf-8")
    cells = re.findall(r"table\.cell\((\w+),", t)
    sized = re.findall(r"table\.cell\(\w+,[^\n]*width = ", t)
    decl = len(re.findall(r"^(?:indicator|strategy)\(", t, re.M))
    print(f"{f:28s} cells={len(cells):3d} sized={len(sized):3d} "
          f"boxW={'boxW' in t} f_boxPos={'f_boxPos(boxPos)' in t} decl={decl}")
