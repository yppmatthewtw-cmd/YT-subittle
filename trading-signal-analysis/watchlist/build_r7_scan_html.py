# -*- coding: utf-8 -*-
"""R7 A–G 六項條件掃描 → HTML 列表。輸入 scan_r7_result.csv（由 scan_r7.py 產生）。"""
import sys, json, html, datetime
import pandas as pd
from zoneinfo import ZoneInfo

S = "/tmp/claude-0/-home-user-YT-subittle/0bd65ef0-0bef-5829-9a6f-f0a46d2d96cd/scratchpad"
OUT_DIR = "/home/user/YT-subittle/trading-signal-analysis/watchlist"
d = pd.read_csv(f"{S}/scan_r7_result.csv")
meta = json.load(open(f"{S}/scan_r7_meta.json"))
now = datetime.datetime.now(ZoneInfo("Asia/Taipei"))
stamp = now.strftime("%m_%d; %H.%M")     # 檔名（冒號不能用於檔名 → 點）
stamp_t = now.strftime("%m_%d; %H:%M")   # 標題
TV = "https://www.tradingview.com/chart/Q1c5VWwD/?symbol="
import os
VER = os.environ.get("VER", "r7")
BD = os.environ.get("BASE_DAY", "09-16")   # 六項條件基準日（最新完整 OHLC）
SD = os.environ.get("SNAP_DAY", "09-17")   # 收盤快照日（只重算 ①④⑤⑥）
HTML_NOTE = os.environ.get("HTML_NOTE", "")
_U = os.environ.get("UPDATE_CSV", "")
SNAP_META = (f' · 另以 <b>{SD} Nasdaq 收盤快照</b>更新 ①④⑤⑥（快照無盤中高低，②③ 不能重算）'
             if (_U and os.path.exists(_U)) else "")   # 本版資料敘述（每版由呼叫端帶入）

CRIT = [
    ("c1", "① 重心線向上", "r7e_gravity 線（滾動 VWAP 30，hlc3）最新一根斜率 > 0"),
    ("c2", "② 波動指數向上", "r7h_volidx（0–100，高 = 平靜）最新一根斜率 > 0"),
    ("c3", "③ 波動指數 ≥ 75", "r7h_volidx 數值 ≥ 75（分隔線 80 之下一級；校準樣本 20 日內 ≥10% 回撤約 13%）"),
    ("c4", "④ 時鐘 6–10 點", "r7b_macd_clock 指針在 180°–300°：日線下跌周期已走 ≥ 50%，或上昇周期剛起步（9–10 點）"),
    ("c5", "⑤ 淺紅第 1–3 根", "MACD 柱狀圖 < 0 且回升（淺紅 #ffcdd2）已連續 1–3 根、中間未再加深 = 下跌動能峰值剛過"),
    ("c6", "⑥ 價格貼近重心線", "收盤距 r7e 重心線 ≤ 1.0 × ATR14 或 ≤ 3%（以收盤價為分母）"),
]
CK = [c[0] for c in CRIT]
NC = len(CK)

def esc(x): return html.escape(str(x))
def f2(x, n=2):
    try:
        if pd.isna(x): return "—"
        return f"{x:,.{n}f}"
    except Exception: return "—"
def sgn(x, n=2, suf=""):
    if pd.isna(x): return "—"
    cls = "pos" if x > 0 else ("neg" if x < 0 else "")
    return f'<span class="{cls}">{x:+.{n}f}{suf}</span>'
def tick(b): return '<span class="ok">✓</span>' if b else '<span class="no">✗</span>'
def lrday(r):
    if pd.isna(r.c5_days): return '<span class="mut">—</span>'
    k = int(r.c5_days)
    if r.still_light and k <= 2: return f'<b class="ok">淺紅第 {k + 1} 根</b>'
    if r.still_light: return f'<span class="warn">淺紅第 {k + 1} 根</span>'
    return f'<span class="mut">{k} 日前 · 已中斷</span>'

def row(r, i, mark=None):
    fails = [k for k in CK if not r[k]]
    stale = r.date < meta["lastday"]
    tk = f'<a href="{TV}{esc(r.ticker)}" target="_blank" rel="noopener">{esc(r.ticker)}</a>'
    if stale: tk += f' <span class="stale" title="鏡像最後一根 {r.date}">舊 {r.date[5:]}</span>'
    if isinstance(r.get("data_warn"), str) and r.get("data_warn"): tk += f' <span class="stale" title="{esc(r.data_warn)}">資料?</span>'
    cells = [
        f'<td class="rk">{i}</td>',
        f'<td class="tk">{tk}<span class="lst">{esc(r.lists).replace("+", " · ")}</span></td>',
        f'<td class="nums">{f2(r.close)}</td>',
        f'<td class="nums sc">{int(r.score)}/{NC}' + (f'<span class="miss">缺 {" ".join(k[1] for k in fails)}</span>' if fails and len(fails) <= 2 else "") + '</td>',
        f'<td class="cr">{tick(r.c1)}<span class="sub">重心 {f2(r.grav)} {sgn(r.grav_slope, 3)}<br>5 根位移 {sgn(r.grav_shift5atr, 2)} ATR</span></td>',
        f'<td class="cr">{tick(r.c2)}<span class="sub">VolIdx {f2(r.volidx, 1)} {sgn(r.volidx_slope, 2)}<br>前值 {f2(r.volidx_prev, 1)}</span></td>',
        f'<td class="cr">{tick(r.c3)}<span class="sub"><b>{f2(r.volidx, 1)}</b> {"≥ 75" if r.c3 else "< 75"}<br>ATR {f2(r.atr_pct, 2)}% · σ60 {f2(r.sd60_pct, 2)}%</span></td>',
        f'<td class="cr">{tick(r.c4)}<span class="sub"><b>{esc(r.clock)}</b> {esc(r.cycle)}周期 第 {int(r.cyc_days)} 日<br>進度 {int(r.cyc_prog)}%</span></td>',
        f'<td class="cr">{tick(r.c5)}<span class="sub">{lrday(r)}<br>Hist {f2(r["hist"], 3)} ← {f2(r["hist_prev"], 3)}</span></td>',
        f'<td class="cr">{tick(r.c6)}<span class="sub">距重心 {sgn(r.dist_grav_pct, 2, "%")}<br>({sgn(r.dist_grav_atr, 2)} ATR)</span></td>',
        f'<td class="mut sm">20 日均額 {f2(r.turnover20_m, 1)}M · {int(r.bars)} 根<br>VCP {f2(r.vcp, 1)} {esc(r.vcp_grade)}<br>{esc(r.struct)} · {esc(r.mk)} · 阻力線 {f2(r.lr_line)} ({sgn(r.dist_lr_pct, 1, "%")})</td>',
    ]
    return f'<tr data-score="{int(r.score)}" data-tk="{esc(r.ticker)}">' + "".join(cells) + "</tr>"

HEAD = """<tr><th>#</th><th>Ticker · 來源榜單</th><th>收盤</th><th>命中</th>
<th>① 重心線斜率</th><th>② 波動指數斜率</th><th>③ 波動指數 ≥ 75</th><th>④ MACD 時鐘</th><th>⑤ 柱狀圖 淺紅</th><th>⑥ 距重心線</th><th>參考：VCP · 結構 · 最低阻力線</th></tr>"""

def table(df, start=1):
    if df.empty: return '<p class="empty">— 無 —</p>'
    return '<table><thead>' + HEAD + '</thead><tbody>' + "".join(row(r, i) for i, (_, r) in enumerate(df.iterrows(), start)) + '</tbody></table>'

strict = d[d.score == NC].sort_values(["c5_days", "volidx"], ascending=[True, False])
cats = [(k, strict[strict.c5_days == k]) for k in (0, 1, 2)]   # ⑤ 淺紅第 1 / 2 / 3 根 分類
five = d[d.score == NC - 1].copy()
five["fail"] = five.apply(lambda r: [k for k in CK if not r[k]][0], axis=1)
five = five.sort_values(["fail", "theta"], ascending=[True, False])
allrows = d.sort_values(["score", "c5_days", "theta"], ascending=[False, True, False])
missing = meta["missing"]
meta["lastday"] = str(d.date.max())          # 以本表自己的最後收盤日為準
stale = d[d.date < meta["lastday"]].ticker.tolist()
n_src = json.load(open(f"{S}/scan_tickers.json"))
UNI = os.environ.get("UNIVERSE_CSV", "")
udf = pd.read_csv(UNI) if (UNI and os.path.exists(UNI)) else None
uhit = None
if udf is not None:
    uhit = udf[(udf.score == NC) & (~udf.ticker.isin(set(d.ticker)))].sort_values(["c5_days", "volidx"], ascending=[True, False]).copy()
    uhit["lists"] = "榜外"
UPD = os.environ.get("UPDATE_CSV", "")
mupd = pd.read_csv(UPD) if (UPD and os.path.exists(UPD)) else None

def _row_names(df):
    return " · ".join(df.ticker.astype(str))

upd_html = ""
if mupd is not None:
    still = mupd[(mupd.score == NC) & mupd.four_17]
    lost  = mupd[(mupd.score == NC) & (~mupd.four_17)]
    fresh = mupd[(mupd.score != NC) & mupd.four_17 & mupd.c2 & mupd.c3].sort_values("volidx", ascending=False)
    upd_html = (
        f'<h2>{SD} 收盤更新 <span class="n">{BD} 六項全中 {len(still) + len(lost)} 檔中，{len(still)} 檔在 {SD} 收盤下 ①④⑤⑥ 仍成立</span></h2>'
        + f'<div class="note">{SD} 只有 Nasdaq 收盤快照（沒有盤中高低），②③ 波動指數無法重算，所以這一段只看 ①④⑤⑥。<br>'
        + '<b>仍成立（%d）</b>：%s<br>' % (len(still), _row_names(still))
        + '<b>已失效（%d，多數是 ⑤ 淺紅中斷）</b>：%s<br>' % (len(lost), _row_names(lost))
        + f'<b>{SD} 新符合（{len(fresh)}，①④⑤⑥ 成立且 {BD} 的 ②③ 也過）</b>：{_row_names(fresh)}</div>')

# 與上版對照（可選）
PREV = os.environ.get("PREV_CSV", ""); PV = os.environ.get("PREV_VER", "上版"); PD_ = os.environ.get("PREV_DAY", "")
if PREV and os.path.exists(PREV):
    _pv = pd.read_csv(PREV); _p6 = set(_pv[_pv.score == NC].ticker); _c6 = list(strict.ticker)
    _cur = d.set_index("ticker")
    _keep = [t for t in _c6 if t in _p6]; _new = [t for t in _c6 if t not in _p6]
    _out = [t for t in _pv[_pv.score == NC].ticker if t not in set(_c6)]
    def _why(t):
        if t not in _cur.index: return f"{esc(t)}（已不在來源榜單）"
        r = _cur.loc[t]; m = "".join(k[1][0] for k in CRIT if not r[k[0]])
        return f"{esc(t)}（{int(r.score)}/{NC}，缺 {m}）"
    upd_html += (f'<h2>與 {PV} 對照 <span class="n">{PV}（{PD_} 基準）六項全中 {len(_p6)} 檔 → 本版（{BD} 基準）{len(_c6)} 檔</span></h2>'
                 f'<div class="note"><b>延續（{len(_keep)}）</b>：{" · ".join(map(esc, _keep)) or "—"}<br>'
                 f'<b>新進（{len(_new)}）</b>：{" · ".join(map(esc, _new)) or "—"}<br>'
                 f'<b>退出（{len(_out)}）</b>：{" · ".join(_why(t) for t in _out) or "—"}</div>')

CH = os.environ.get("CHATHITS_CSV", "")
chd = pd.read_csv(CH) if (CH and os.path.exists(CH)) else None
chat_html = ""
if chd is not None:
    SHORT = {"chat1 動能回調 R21": "①動能", "chat2 Combined R22": "②VCP", "chat3 SubSector R12": "③子板塊", "chat3 AI Sector R13": "③AI", "chat3 加息 R2": "③加息"}

    def chrow(r):
        tags = "".join(f'<em class="src">{esc(SHORT.get(x.strip(), x.strip()))}</em>' for x in str(r.hits).split("｜"))
        warn = ' <em class="warn">⚠ 迴避</em>' if str(r.avoid).strip() not in ("", "nan") else ""
        return ('<tr data-n="%d" data-s="%d" data-tk="%s"><td><a href="%s%s" target="_blank">%s</a>%s</td>'
                '<td class="c">%d</td><td>%s</td><td class="c">%d/6</td><td class="miss">%s</td>'
                '<td class="c">%s</td><td class="c">%s</td><td class="c">%s</td><td class="c">%s</td><td class="d">%s</td></tr>') % (
            int(r.n_hit), int(r.score), esc(r.ticker), TV, esc(r.ticker), esc(r.ticker), warn,
            int(r.n_hit), tags, int(r.score), esc(r["miss"]),
            f2(r.volidx, 1), esc(r.clock), esc(r.c5_cat), f2(r.dist_grav_pct), esc(str(r.detail))[:180])

    n3, n2, n1 = [int((chd.n_hit == k).sum()) for k in (3, 2, 1)]
    _bj = CH[:-4] + "_both.json"         # chat_hits.py 另寫的「同時六項全中」名單
    _bjd = json.load(open(_bj)) if os.path.exists(_bj) else {}
    both = _bjd.get("both", []); SY = _bjd.get("sys", {}); _bav = set(_bjd.get("both_avoid", []))
    _six = set(strict.ticker)
    both = [t for t in strict.ticker if t in set(both)] + [t for t in both if t not in _six]
    chat_html = (
        '<h2>Chat 1–3 命中、六項未全中 <span class="n">%d 檔</span></h2>' % len(chd)
        + '<div class="note">三個 session 的成品各自用自己那套準則選中、但本掃描六項條件未全中的名字。'
          '命中規則一律採用來源成品自己寫明的通過標記：<br>'
          f'<b>chat 1</b> 動能回調 R21：在總表（1/2/3/6 個月動能至少一個排前 10%% 且回到上升中的 20MA；差一項 {SY.get("mp_nm", "?")} 檔只掃描）→ {SY.get("10ma", "?")} 檔　'
          f'<b>chat 2</b> Combined R22：線上 ≥1 且三榜有頂級（VCP A/B、Weinstein 2A、Pre-breakout A）→ {SY.get("comb", "?")}/{SY.get("comb_all", "?")} 檔　'
          f'<b>chat 3</b> SubSector R12：所屬子板塊 5 日分 ≥70 且斜率 &gt;0 → {SY.get("ss", "?")}/{SY.get("ss_all", "?")} 個子板塊；'
          f'AI Sector R13：所屬小群組 5 日分 ≥70 且個股 5 日強度 &gt;0 → {SY.get("ai", "?")} 檔；'
          f'加息 R2：受惠名單 {SY.get("rh", "?")} 檔（迴避名單 {SY.get("avoid", "?")} 檔不算命中，另標 ⚠）<br>'
          'chat 1–3 合共命中 %d 檔，其中 %d 檔同時六項全中（%s），餘下 %d 檔列於下表；'
          '本掃描六項全中的 %d 檔裡有 %d 檔是 chat 準則沒有選中的%s。'
          '同時命中 3 套 %d 檔、2 套 %d 檔、1 套 %d 檔。</div>' % (
              len(chd) + len(both), len(both), " · ".join(t + (" ⚠迴避" if t in _bav else "") for t in both) or "—", len(chd),
              len(strict), len(strict) - len(both),
              (("（其中 " + "、".join(t for t in _bjd.get("six_avoid", []) if t not in set(both)) + " 在加息清單「迴避」）")
               if [t for t in _bjd.get("six_avoid", []) if t not in set(both)] else ""), n3, n2, n1)
        + '<div class="filters"><span class="mut">命中系統 ≥</span>'
        + "".join('<button data-cn="%d" class="%s">%d</button>' % (k, "on" if k == 1 else "", k) for k in (1, 2, 3))
        + '<span class="mut" style="margin-left:14px">六項 ≥</span>'
        + "".join('<button data-cs="%d" class="%s">%d</button>' % (k, "on" if k == 0 else "", k) for k in range(0, 6))
        + '<input id="chq" placeholder="搜 Ticker…" size="14"></div>'
        + '<div id="chat"><table><thead><tr><th>Ticker</th><th>套數</th><th>命中哪幾套</th><th>六項</th><th>欠缺</th>'
          '<th>波動指數</th><th>時鐘</th><th>淺紅</th><th>距重心 %</th><th>命中內容（來源原話）</th></tr></thead><tbody>'
        + "".join(chrow(r) for _, r in chd.iterrows()) + '</tbody></table></div>')

crit_html = "".join(f'<li><b>{esc(t)}</b><span>{esc(dsc)}</span></li>' for _, t, dsc in CRIT)
src_html = " · ".join(f"{esc(k)} {len(v)} 檔" for k, v in n_src.items())

doc = f"""<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>R7_six_criteria_scan_{VER} ({stamp_t})</title>
<style>
:root{{color-scheme:light dark;--bg:#f6f7f5;--panel:#fff;--ink:#16202b;--mut:#64748b;--line:#e2e6e3;--head:#eef1ed;--hover:#f2f5f1;
 --up:#16a34a;--dn:#dc2626;--warn:#b45309;--acc:#b07b24;--accs:#f6ecd8;--okbg:#e8f6ee;}}
@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{--bg:#0d1218;--panel:#141c24;--ink:#e3e9ee;--mut:#8b98a5;--line:#25313c;--head:#1a232c;--hover:#1b242e;
 --up:#3fb68b;--dn:#e0705f;--warn:#e5b15c;--acc:#e5b15c;--accs:#2b2417;--okbg:#14261d;}}}}
:root[data-theme=dark]{{--bg:#0d1218;--panel:#141c24;--ink:#e3e9ee;--mut:#8b98a5;--line:#25313c;--head:#1a232c;--hover:#1b242e;
 --up:#3fb68b;--dn:#e0705f;--warn:#e5b15c;--acc:#e5b15c;--accs:#2b2417;--okbg:#14261d;}}
em.src{{font-style:normal;font-size:11px;background:var(--head);border:1px solid var(--line);border-radius:4px;padding:1px 5px;margin-right:3px;color:var(--mut)}}
em.warn{{font-style:normal;font-size:11px;color:var(--dn);font-weight:700}}
td.miss{{letter-spacing:1px;color:var(--dn);font-weight:700}} td.d{{font-size:12px;color:var(--mut);max-width:520px}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 "Avenir Next","Segoe UI","PingFang TC","Microsoft JhengHei",system-ui,sans-serif}}
.wrap{{max-width:1680px;margin:0 auto;padding:20px 16px 60px}}
header{{border-bottom:3px solid var(--ink);padding-bottom:10px;display:flex;flex-wrap:wrap;gap:6px 14px;align-items:baseline}}
h1{{font-size:24px;margin:0}} h1 em{{font-style:normal;color:var(--acc)}} .meta{{flex-basis:100%;color:var(--mut);font-size:12.5px}} .meta b{{color:var(--ink)}}
.sw{{margin-left:auto;display:inline-flex;gap:4px;background:var(--panel);border:1.5px solid var(--acc);border-radius:99px;padding:3px 4px}}
.sw button{{font:inherit;font-size:12px;font-weight:600;color:var(--mut);background:none;border:0;border-radius:99px;padding:3px 10px;cursor:pointer}} .sw button.on{{background:var(--acc);color:#fff}}
h3{{font-size:14.5px;margin:16px 0 6px;display:flex;gap:8px;align-items:baseline}} h3 .n{{font-size:12.5px;color:var(--mut);font-weight:500}}
h2{{font-size:17px;margin:26px 0 8px;display:flex;gap:10px;align-items:baseline}} h2 .n{{font-size:13px;color:var(--mut);font-weight:500}}
.crit{{list-style:none;margin:10px 0 0;padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:6px 14px}}
.crit li{{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:7px 10px;font-size:12.5px}} .crit b{{display:block;margin-bottom:2px}} .crit span{{color:var(--mut)}}
.note{{background:var(--accs);border-left:4px solid var(--acc);padding:8px 12px;border-radius:6px;font-size:13px;margin-top:12px}}
table{{width:100%;border-collapse:collapse;background:var(--panel);border:1px solid var(--line);font-size:12.5px}}
th{{background:var(--head);text-align:left;padding:7px 8px;border-bottom:2px solid var(--line);white-space:nowrap;position:sticky;top:0;z-index:1;font-size:12px}}
td{{padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}} tr:hover td{{background:var(--hover)}}
td.rk{{color:var(--mut);width:34px}} td.tk a{{font-weight:700;color:var(--ink);text-decoration:none;font-size:14px}} td.tk a:hover{{color:var(--acc)}}
.lst{{display:block;color:var(--mut);font-size:11px}} .nums{{font-variant-numeric:tabular-nums;white-space:nowrap}}
.sc{{font-weight:700}} .miss{{display:block;font-weight:500;font-size:11px;color:var(--dn)}}
.cr .ok{{color:var(--up);font-weight:800;font-size:15px}} .cr .no{{color:var(--dn);font-weight:800;font-size:15px}}
.sub{{display:block;color:var(--mut);font-size:11.5px;white-space:nowrap}} .sub b{{color:var(--ink)}}
.pos{{color:var(--up)}} .neg{{color:var(--dn)}} .warn{{color:var(--warn);font-weight:600}} .mut{{color:var(--mut)}} .sm{{font-size:11.5px;white-space:nowrap}}
.stale{{font-size:10px;color:var(--warn);border:1px solid var(--warn);border-radius:4px;padding:0 4px;margin-left:4px;vertical-align:middle}}
.empty{{background:var(--panel);border:1px dashed var(--line);border-radius:8px;padding:14px;color:var(--mut);text-align:center}}
.filters{{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}} .filters button{{font:inherit;font-size:12px;border:1px solid var(--line);background:var(--panel);color:var(--ink);border-radius:99px;padding:3px 10px;cursor:pointer}}
.filters button.on{{background:var(--ink);color:var(--bg);border-color:var(--ink)}} .filters input{{font:inherit;font-size:12px;border:1px solid var(--line);border-radius:6px;padding:3px 8px;background:var(--panel);color:var(--ink)}}
.tags{{display:flex;flex-wrap:wrap;gap:4px;font-size:12px}} .tags span{{background:var(--panel);border:1px solid var(--line);border-radius:4px;padding:1px 6px}}
@media (max-width:720px){{.sub{{white-space:normal}} th,td{{padding:5px 5px}}}}
</style></head><body><div class="wrap">
<header><h1>R7 A–H <em>六項條件掃描</em> {VER} ({stamp_t})</h1>
<div class="sw"><button data-t="light">☀️ 淺色</button><button data-t="dark">🌙 深色</button></div>
<div class="meta">日線 · 六項條件基準 <b>{esc(meta["lastday"])} 官方收盤（完整 OHLC）</b>{SNAP_META} · 價格面板為三個 repo 的 Yahoo 鏡像合併（Yahoo 直連在本機被 proxy 封鎖，鏡像由各 repo 的 GitHub Actions 抓取）· 來源 5 份成品：{src_html} · 去重 <b>{len(d) + len(missing)} 檔</b>，可算 <b>{len(d)}</b>，無資料 {len(missing)} · 產生 {now.strftime("%Y.%m.%d %H:%M")} 台北 · 規則以 r7b/e/h 預設參數在 Python 重現</div></header>

<ul class="crit">{crit_html}</ul>
<div class="note">{HTML_NOTE}六項全中 <b>{len(strict)} 檔</b>。</div>

{upd_html}

<h2>六項全中（{BD} 基準） <span class="n">{len(strict)} 檔 · 按 ⑤ 淺紅根數分三類，類內依波動指數由高至低</span></h2>
{"".join(f'<h3>淺紅第 {k + 1} 根 <span class="n">{len(g)} 檔</span></h3>{table(g)}' for k, g in cats)}

<h2>差一項 <span class="n">{NC - 1}/{NC} · {len(five)} 檔 · 按缺少的條件分組</span></h2>
{table(five)}

{f'<h2>加掃：watchlist 以外的六項全中 <span class="n">{len(uhit)} 檔 · 合併面板中流動性達標的 {len(udf):,} 檔</span></h2>' + (f'<div class="note">{esc(os.environ.get("MKT_NOTE", ""))}</div>' if os.environ.get("MKT_NOTE") else '') + table(uhit) if uhit is not None else ''}

<h2>全部 {len(d)} 檔 <span class="n">按命中數排序 · 可篩選</span></h2>
<div class="filters"><span class="mut">命中 ≥</span>{"".join(f'<button data-min="{k}" class="{"on" if k == 0 else ""}">{k}</button>' for k in range(0, NC + 1))}
<input id="q" placeholder="搜 Ticker…" size="14"></div>
<div id="all">{table(allrows)}</div>

{chat_html}

<h2>無法計算 <span class="n">{len(missing)} 檔無日線鏡像（多為 ADR／外國掛牌／.B 股）· {len(stale)} 檔最後一根早於基準日</span></h2>
<div class="tags">{"".join(f"<span>{esc(t)}</span>" for t in missing)}</div>
<p class="mut" style="font-size:12px">最後一根早於基準日（表中標「舊」）：{" · ".join(stale) or "無"}</p>
</div>
<script>
const root=document.documentElement,sw=document.querySelectorAll('.sw button');
function setT(t){{root.dataset.theme=t;sw.forEach(b=>b.classList.toggle('on',b.dataset.t===t));try{{localStorage.setItem('r7theme',t)}}catch(e){{}}}}
sw.forEach(b=>b.onclick=()=>setT(b.dataset.t));
try{{const s=localStorage.getItem('r7theme');if(s)setT(s);else sw.forEach(b=>b.classList.toggle('on',(b.dataset.t==='dark')===matchMedia('(prefers-color-scheme:dark)').matches))}}catch(e){{}}
let minS=0,q='';const rows=[...document.querySelectorAll('#all tbody tr')];
function apply(){{rows.forEach(r=>{{r.style.display=(+r.dataset.score>=minS&&r.dataset.tk.includes(q))?'':'none'}})}}
document.querySelectorAll('.filters button[data-min]').forEach(b=>b.onclick=()=>{{minS=+b.dataset.min;document.querySelectorAll('.filters button[data-min]').forEach(x=>x.classList.toggle('on',x===b));apply()}});
document.getElementById('q').oninput=e=>{{q=e.target.value.trim().toUpperCase();apply()}};
const chBox=document.getElementById('chat');
if(chBox){{
 let cn=1,cs=0,cq='';const crows=[...chBox.querySelectorAll('tbody tr')];
 const capply=()=>crows.forEach(r=>{{r.style.display=(+r.dataset.n>=cn&&+r.dataset.s>=cs&&r.dataset.tk.includes(cq))?'':'none'}});
 document.querySelectorAll('button[data-cn]').forEach(b=>b.onclick=()=>{{cn=+b.dataset.cn;document.querySelectorAll('button[data-cn]').forEach(x=>x.classList.toggle('on',x===b));capply()}});
 document.querySelectorAll('button[data-cs]').forEach(b=>b.onclick=()=>{{cs=+b.dataset.cs;document.querySelectorAll('button[data-cs]').forEach(x=>x.classList.toggle('on',x===b));capply()}});
 document.getElementById('chq').oninput=e=>{{cq=e.target.value.trim().toUpperCase();capply()}};
}}
</script></body></html>"""

out = f"{OUT_DIR}/R7_six_criteria_scan_{VER} ({stamp}).html"
open(out, "w", encoding="utf-8").write(doc)
d.to_csv(f"{OUT_DIR}/R7_six_criteria_scan_{VER} ({stamp}).csv", index=False, encoding="utf-8-sig")
print(out, len(doc))
