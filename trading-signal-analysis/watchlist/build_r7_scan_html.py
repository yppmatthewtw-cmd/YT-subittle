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

CRIT = [
    ("c1", "① 重心線向上", "r7e_gravity 線（滾動 VWAP 30，hlc3）最新一根斜率 > 0"),
    ("c2", "② 波動指數向上", "r7h_volidx（0–100，高 = 平靜）最新一根斜率 > 0"),
    ("c3", "③ 波動指數 ≥ 75", "r7h_volidx 數值 ≥ 75（分隔線 80 之下一級；校準樣本 20 日內 ≥10% 回撤約 13%）"),
    ("c4", "④ 時鐘 6–10 點", "r7b_macd_clock 指針在 180°–300°：日線下跌周期已走 ≥ 50%，或上昇周期剛起步（9–10 點）"),
    ("c5", "⑤ 淺紅第 1–3 根", "MACD 柱狀圖 < 0 且回升（淺紅 #ffcdd2）已連續 1–3 根、中間未再加深 = 下跌動能峰值剛過"),
    ("c6", "⑥ 價格貼近重心線", "收盤距 r7e 重心線 ≤ 1.0 × ATR14 或 ≤ 3%"),
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
stale = d[d.date < meta["lastday"]].ticker.tolist()
n_src = json.load(open(f"{S}/scan_tickers.json"))
import os
UNI = os.environ.get("UNIVERSE_CSV", "")
udf = pd.read_csv(UNI) if (UNI and os.path.exists(UNI)) else None
uhit = None
if udf is not None:
    uhit = udf[(udf.score == NC) & (~udf.ticker.isin(set(d.ticker)))].sort_values(["c5_days", "volidx"], ascending=[True, False]).copy()
    uhit["lists"] = "watchlist 外"

crit_html = "".join(f'<li><b>{esc(t)}</b><span>{esc(dsc)}</span></li>' for _, t, dsc in CRIT)
src_html = " · ".join(f"{esc(k)} {len(v)} 檔" for k, v in n_src.items())

doc = f"""<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>R7_six_criteria_scan_r5 ({stamp_t})</title>
<style>
:root{{color-scheme:light dark;--bg:#f6f7f5;--panel:#fff;--ink:#16202b;--mut:#64748b;--line:#e2e6e3;--head:#eef1ed;--hover:#f2f5f1;
 --up:#16a34a;--dn:#dc2626;--warn:#b45309;--acc:#b07b24;--accs:#f6ecd8;--okbg:#e8f6ee;}}
@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{--bg:#0d1218;--panel:#141c24;--ink:#e3e9ee;--mut:#8b98a5;--line:#25313c;--head:#1a232c;--hover:#1b242e;
 --up:#3fb68b;--dn:#e0705f;--warn:#e5b15c;--acc:#e5b15c;--accs:#2b2417;--okbg:#14261d;}}}}
:root[data-theme=dark]{{--bg:#0d1218;--panel:#141c24;--ink:#e3e9ee;--mut:#8b98a5;--line:#25313c;--head:#1a232c;--hover:#1b242e;
 --up:#3fb68b;--dn:#e0705f;--warn:#e5b15c;--acc:#e5b15c;--accs:#2b2417;--okbg:#14261d;}}
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
<header><h1>R7 A–H <em>六項條件掃描</em> r5 ({stamp_t})</h1>
<div class="sw"><button data-t="light">☀️ 淺色</button><button data-t="dark">🌙 深色</button></div>
<div class="meta">日線 · 數據基準 <b>{esc(meta["lastday"])} 收盤</b>（三個 repo 的 Yahoo 鏡像合併；Yahoo 直連在本機被封鎖）· 附件 4 份：{src_html} · 去重 <b>{len(d) + len(missing)} 檔</b>，可算 <b>{len(d)}</b>，無資料 {len(missing)} · 產生 {now.strftime("%Y.%m.%d %H:%M")} 台北 · 規則以 r7b/e/h 預設參數在 Python 重現</div></header>

<ul class="crit">{crit_html}</ul>
<div class="note">r5：條件與 r3/r4 相同，但 ticker 直接取自三個 watchlist repo 的最新成品（10MA R20 · Combined R22 · SubSector R12 + AI R13），價格面板由三個 repo 的 Yahoo 鏡像合併（3,097 檔）。條件：① 只看重心線；② ③ 改用 R7-H 波動指數（斜率 > 0、數值 ≥ 75）；⑥ 只看重心線；MA20 與 EMA21 全部刪除；⑤ 全中名單按淺紅第 1 / 2 / 3 根分開排列。六項全中 <b>{len(strict)} 檔</b>。</div>

<h2>六項全中 <span class="n">{len(strict)} 檔 · 按 ⑤ 淺紅根數分三類，類內依波動指數由高至低</span></h2>
{"".join(f'<h3>淺紅第 {k + 1} 根 <span class="n">{len(g)} 檔</span></h3>{table(g)}' for k, g in cats)}

<h2>差一項 <span class="n">{NC - 1}/{NC} · {len(five)} 檔 · 按缺少的條件分組</span></h2>
{table(five)}

{f'<h2>全市場加掃：watchlist 以外的六項全中 <span class="n">{len(uhit)} 檔 · 合併面板 {len(udf)} 檔流動性達標股票中</span></h2>' + table(uhit) if uhit is not None else ''}

<h2>全部 {len(d)} 檔 <span class="n">按命中數排序 · 可篩選</span></h2>
<div class="filters"><span class="mut">命中 ≥</span>{"".join(f'<button data-min="{k}" class="{"on" if k == 0 else ""}">{k}</button>' for k in range(0, NC + 1))}
<input id="q" placeholder="搜 Ticker…" size="14"></div>
<div id="all">{table(allrows)}</div>

<h2>無法計算 <span class="n">{len(missing)} 檔無日線鏡像（多為 ADR／外國掛牌／.B 股）· {len(stale)} 檔鏡像停在 09-14</span></h2>
<div class="tags">{"".join(f"<span>{esc(t)}</span>" for t in missing)}</div>
<p class="mut" style="font-size:12px">鏡像停在 09-14（表中標「舊」）：{" · ".join(stale)}</p>
</div>
<script>
const root=document.documentElement,sw=document.querySelectorAll('.sw button');
function setT(t){{root.dataset.theme=t;sw.forEach(b=>b.classList.toggle('on',b.dataset.t===t));try{{localStorage.setItem('r7theme',t)}}catch(e){{}}}}
sw.forEach(b=>b.onclick=()=>setT(b.dataset.t));
try{{const s=localStorage.getItem('r7theme');if(s)setT(s);else sw.forEach(b=>b.classList.toggle('on',(b.dataset.t==='dark')===matchMedia('(prefers-color-scheme:dark)').matches))}}catch(e){{}}
let minS=0,q='';const rows=[...document.querySelectorAll('#all tbody tr')];
function apply(){{rows.forEach(r=>{{r.style.display=(+r.dataset.score>=minS&&r.dataset.tk.includes(q))?'':'none'}})}}
document.querySelectorAll('.filters button').forEach(b=>b.onclick=()=>{{minS=+b.dataset.min;document.querySelectorAll('.filters button').forEach(x=>x.classList.toggle('on',x===b));apply()}});
document.getElementById('q').oninput=e=>{{q=e.target.value.trim().toUpperCase();apply()}};
</script></body></html>"""

out = f"{OUT_DIR}/R7_six_criteria_scan_r5 ({stamp}).html"
open(out, "w", encoding="utf-8").write(doc)
d.to_csv(f"{OUT_DIR}/R7_six_criteria_scan_r5 ({stamp}).csv", index=False, encoding="utf-8-sig")
print(out, len(doc))
