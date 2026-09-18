# -*- coding: utf-8 -*-
"""產生 MACD Cycle Clock 排名 R1 —— 以 6 點鐘「轉勢點」為節點。"""
import json, html, math

S = "/tmp/claude-0/-home-user-YT-subittle/0bd65ef0-0bef-5829-9a6f-f0a46d2d96cd/scratchpad"
d = json.load(open(f"{S}/clock_rank2.json"))
meta = json.load(open(f"{S}/meta.json"))
rows, missing, lastday = d["rows"], d["missing"], d["lastday"]


def tier(r):
    t = r["theta"]
    if r["up"]:
        return "E"
    if t < 150:
        return "F"
    if t < 180:
        return "B"
    if t <= 220:
        return "A"
    if t <= 250:
        return "C"
    return "D"


TIERS = [
    ("A", "轉勢點 6:00–7:20", "柱狀圖谷底已過、回升確認中 —— 指針正在 6 點鐘節點附近，本表最高分段", "#16a34a"),
    ("B", "探底末段 5:00–6:00", "仍在創本周期新低，但已走到預期中點附近 —— 轉勢隨時發生，尚未確認", "#d97706"),
    ("C", "回升中段 7:20–8:20", "自谷底回升 44–78% —— 轉勢已確認但已走一段", "#0891b2"),
    ("D", "逼近轉正 8:20–9:00", "回升 78%+ ，即將穿越零軸 —— 動能修復大半，進場點已不便宜", "#64748b"),
    ("E", "已轉正（上昇周期）", "柱狀圖已為正 —— 轉勢點早已過去，非本表目標", "#94a3b8"),
    ("F", "探底初中段 3:00–5:00", "剛轉負不久、仍在下探 —— 距 6 點鐘節點還早，最不宜進場", "#dc2626"),
]
TC = {t[0]: t[3] for t in TIERS}
for r in rows:
    r["tier"] = tier(r)

TV = "https://www.tradingview.com/chart/?symbol="


def clock_svg(theta, up, tier_, size=28):
    """時鐘圖示：上半綠 / 下半紅 + 6 點鐘節點刻度 + 指針。"""
    c, rr = size / 2, size / 2 - 3
    a = math.radians(theta)
    x, y = c + rr * 0.74 * math.sin(a), c - rr * 0.74 * math.cos(a)
    gu = "#16a34a" if up else "#c7e8d5"
    gd = "#f3c7c2" if up else "#dc2626"
    node = "#16a34a" if tier_ == "A" else "#94a3b8"
    return (f'<svg class="clk" viewBox="0 0 {size} {size}" width="{size}" height="{size}" aria-hidden="true">'
            f'<path d="M {c-rr} {c} A {rr} {rr} 0 0 1 {c+rr} {c}" fill="none" stroke="{gu}" stroke-width="2.6"/>'
            f'<path d="M {c+rr} {c} A {rr} {rr} 0 0 1 {c-rr} {c}" fill="none" stroke="{gd}" stroke-width="2.6"/>'
            f'<line x1="{c}" y1="{c+rr-4}" x2="{c}" y2="{c+rr+2.4}" stroke="{node}" stroke-width="2.4"/>'
            f'<line x1="{c}" y1="{c}" x2="{x:.1f}" y2="{y:.1f}" stroke="#eab308" stroke-width="2.2" stroke-linecap="round"/>'
            f'<circle cx="{c}" cy="{c}" r="1.5" fill="#475569"/></svg>')


def chips(r):
    m = meta.get(r["sym"], {})
    return "".join(f'<i class="src {cls}">{l}</i>'
                   for l, cls in (("AI", "ai"), ("10MA", "tm"), ("CW", "cw"))
                   if l in m.get("lists", []))


def fnum(v, fmt="{:+.1f}"):
    if v is None:
        return '<span class="mut">–</span>'
    return f'<span class="{"up" if v > 0 else ("dn" if v < 0 else "")}">{fmt.format(v)}</span>'


def row_html(r):
    m = meta.get(r["sym"], {})
    nm, sec = html.escape(m.get("name", ""))[:26], html.escape(m.get("sector", ""))[:14]
    tcol = TC[r["tier"]]
    if r["up"]:
        turn = '<span class="mut">已轉正</span>'
    elif r["since_ext"] == 0:
        turn = '<span class="dn">探底中</span>'
    else:
        turn = f'{r["since_ext"]} 日前'
    vcp, cert, aif = m.get("vcp"), m.get("cert"), m.get("aiflow")
    return f'''<tr data-tier="{r['tier']}">
<td class="num" data-v="{-r['rank']}">{r['rank']}</td>
<td class="tk"><a href="{TV}{r['sym']}" target="_blank" rel="noopener">{r['sym']}</a>{chips(r)}</td>
<td class="nm">{nm}<small>{sec}</small></td>
<td class="tr" data-v="{r['score']}"><span class="tier" style="--tc:{tcol}">{r['tier']}</span></td>
<td class="ck" data-v="{-abs(r['theta']-180)}">{clock_svg(r['theta'], r['up'], r['tier'])}<b>{r['clock']}</b></td>
<td class="num" data-v="{-(r['since_ext'] if not r['up'] else 99)}">{turn}</td>
<td class="num" data-v="{r['recov'] if not r['up'] else 999}">{r['recov']:.0f}%<small class="mut">連升 {r['run']}</small></td>
<td class="num" data-v="{r['ext']}">{r['ext']:+.3f}<small class="mut">深 {r['depth']:.0f}%</small></td>
<td class="num" data-v="{r['hist']}">{r['hist']:+.3f}</td>
<td class="cy {'u' if r['up'] else 'd'}" data-v="{r['elapsed'] if not r['up'] else -r['elapsed']}">
  <b>{'升' if r['up'] else '跌'}</b> {r['elapsed']}/{r['expected']:.1f} 日</td>
<td class="sc" data-v="{r['score']}"><span class="bar"><i style="width:{r['score']}%"></i></span><b>{r['score']:.1f}</b></td>
<td class="num sub" data-v="{r['A']}">{r['A']:.0f}</td>
<td class="num sub" data-v="{r['B']}">{r['B']:.0f}</td>
<td class="num sub" data-v="{r['C']}">{r['C']:.0f}</td>
<td class="num sub" data-v="{r['D']}">{r['D']:.0f}</td>
<td class="num" data-v="{r['close']}">{r['close']:.2f}<small class="{'up' if r['chg1d']>0 else 'dn'}">{r['chg1d']:+.1f}%</small></td>
<td class="num" data-v="{r['chg21']}">{fnum(r['chg21'])}%</td>
<td class="num" data-v="{r['offhigh']}">{r['offhigh']:.1f}%</td>
<td class="num" data-v="{r['rs21']}">{fnum(r['rs21'])}</td>
<td class="num" data-v="{r['vr']}">{r['vr']:.2f}</td>
<td class="tr" data-v="{'ABCDE'.index(vcp) if vcp else 9}">{f'<b class="g{vcp}">{vcp}</b>' if vcp else '<span class="mut">–</span>'}</td>
<td class="num" data-v="{cert if cert is not None else -1}">{f'{cert:.1f}' if cert is not None else '<span class="mut">–</span>'}</td>
<td class="num" data-v="{aif if aif is not None else -9}">{fnum(aif, "{:+.2f}") if aif is not None else '<span class="mut">–</span>'}</td>
<td class="ma">{'✓' if r['e9'] else '·'}{'✓' if r['e21'] else '·'}{'✓' if r['e50'] else '·'}</td>
</tr>'''


counts = {t[0]: sum(1 for r in rows if r["tier"] == t[0]) for t in TIERS}
body = "\n".join(row_html(r) for r in rows)
miss = "、".join(m["sym"] for m in missing)

page = f'''<title>MACD 轉勢點時鐘排名 R1</title>
<style>
:root{{color-scheme:light dark;
 --bg:#f6f7f5;--panel:#fff;--ink:#16202b;--mut:#64748b;--line:#e2e6e3;--head:#eef1ed;--hover:#f2f5f1;
 --up:#16a34a;--dn:#dc2626;--acc:#b07b24;--accs:#f6ecd8;--bar:#0891b2;}}
@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{
 --bg:#0d1218;--panel:#141c24;--ink:#e3e9ee;--mut:#8b98a5;--line:#25313c;--head:#1a232c;--hover:#1b242e;
 --up:#3fb68b;--dn:#e0705f;--acc:#e5b15c;--accs:#2b2417;--bar:#38bdf8;}}}}
:root[data-theme=dark]{{
 --bg:#0d1218;--panel:#141c24;--ink:#e3e9ee;--mut:#8b98a5;--line:#25313c;--head:#1a232c;--hover:#1b242e;
 --up:#3fb68b;--dn:#e0705f;--acc:#e5b15c;--accs:#2b2417;--bar:#38bdf8;}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);
 font:15px/1.55 "Avenir Next","Segoe UI","PingFang TC","Microsoft JhengHei",system-ui,sans-serif}}
.wrap{{max-width:1620px;margin:0 auto;padding-block:22px 60px;padding-inline:18px}}
header{{border-bottom:3px solid var(--ink);padding-bottom:12px;display:flex;flex-wrap:wrap;gap:8px 16px;align-items:baseline}}
h1{{font-size:25px;margin:0;text-wrap:balance}} h1 em{{font-style:normal;color:var(--acc)}}
.meta{{flex-basis:100%;color:var(--mut);font-size:12.5px}} .meta b{{color:var(--ink)}}
.sw{{margin-left:auto;display:inline-flex;gap:4px;background:var(--panel);border:1.5px solid var(--acc);
 border-radius:99px;padding:3px 4px}}
.sw button{{font:inherit;font-size:12px;font-weight:600;color:var(--mut);background:none;border:0;
 border-radius:99px;padding:4px 11px;cursor:pointer}}
.sw button[aria-pressed=true]{{background:var(--acc);color:var(--bg)}}
.rule{{background:var(--panel);border:1px solid var(--line);border-left:4px solid var(--acc);
 border-radius:7px;padding:14px 17px;margin:16px 0;font-size:13.5px}}
.rule h3{{margin:0 0 7px;font-size:14.5px}}
.rule code{{background:var(--accs);color:var(--acc);padding:1px 5px;border-radius:3px;font-size:12px}}
.dial{{display:flex;flex-wrap:wrap;gap:18px;align-items:center;margin-top:11px}}
.dial figure{{margin:0;flex:none}}
.nodes{{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:7px;flex:1;min-width:280px}}
.nodes div{{background:var(--head);border-radius:5px;padding:6px 11px;font-size:12px;line-height:1.35}}
.nodes small{{display:block;font-size:10.5px;margin-top:1px}}
.nodes b{{color:var(--acc)}} .nodes.hit{{}}
.formula{{display:flex;flex-wrap:wrap;gap:8px;margin-top:11px}}
.formula span{{background:var(--head);border:1px solid var(--line);border-radius:5px;padding:4px 10px;font-size:12.5px}}
.formula b{{color:var(--acc)}}
.tiers{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:9px;margin:16px 0}}
.tc{{background:var(--panel);border:1px solid var(--line);border-left:4px solid var(--tc);border-radius:7px;padding:9px 13px}}
.tc h4{{margin:0;font-size:13px}} .tc h4 i{{font-style:normal;color:var(--tc);font-weight:800;margin-right:4px}}
.tc p{{margin:3px 0 0;color:var(--mut);font-size:11.5px;line-height:1.45}}
.tc b{{float:right;font-size:17px;color:var(--tc);font-variant-numeric:tabular-nums}}
.filters{{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:14px 0 8px}}
.filters button{{font:inherit;font-size:12.5px;font-weight:600;background:var(--panel);color:var(--ink);
 border:1px solid var(--line);border-radius:6px;padding:5px 12px;cursor:pointer}}
.filters button[aria-pressed=true]{{background:var(--ink);color:var(--bg);border-color:var(--ink)}}
.filters input{{font:inherit;font-size:13px;padding:5px 10px;border:1px solid var(--line);
 border-radius:6px;background:var(--panel);color:var(--ink);min-width:150px}}
.filters .n{{color:var(--mut);font-size:12.5px;margin-left:auto}}
.tblwrap{{overflow-x:auto;border:1px solid var(--line);border-radius:8px;background:var(--panel)}}
table{{border-collapse:collapse;width:100%;font-size:13px}}
th{{background:var(--head);text-align:left;padding:6px 8px;font-size:11px;text-transform:uppercase;
 letter-spacing:.03em;color:var(--mut);white-space:nowrap;position:sticky;top:0;cursor:pointer;user-select:none}}
th small{{display:block;font-size:9.5px;letter-spacing:0;text-transform:none;font-weight:400}}
th:hover{{color:var(--ink);background:var(--hover)}}
th::after{{content:"⇅";opacity:.4;margin-left:3px;font-size:9px}}
th[data-dir=desc]::after{{content:"▼";opacity:1;color:var(--acc)}}
th[data-dir=asc]::after{{content:"▲";opacity:1;color:var(--acc)}}
td{{padding:5px 8px;border-top:1px solid var(--line);vertical-align:middle;white-space:nowrap}}
tbody tr:hover{{background:var(--hover)}}
td.num,th.num{{text-align:right;font-variant-numeric:tabular-nums;
 font-family:"SF Mono",Consolas,ui-monospace,monospace;font-size:12px}}
td small{{display:block;font-size:9.5px;line-height:1.3}}
td.tk a{{font-weight:700;color:var(--acc);text-decoration:none;border-bottom:1px solid transparent}}
td.tk a:hover{{border-bottom-color:var(--acc)}}
.src{{display:inline-block;font-style:normal;font-size:8.5px;font-weight:700;border-radius:3px;
 padding:0 3px;margin-left:3px;vertical-align:1px}}
.src.ai{{background:#7c3aed;color:#fff}} .src.tm{{background:#0891b2;color:#fff}} .src.cw{{background:#94a3b8;color:#fff}}
td.nm{{color:var(--mut);font-size:12px;max-width:190px;overflow:hidden;text-overflow:ellipsis}}
td.nm small{{font-size:9.5px;opacity:.8}}
.tier{{display:inline-block;min-width:20px;text-align:center;font-weight:800;font-size:12px;
 color:#fff;background:var(--tc);border-radius:4px;padding:1px 6px}}
td.ck b{{font-size:11.5px;margin-left:4px;vertical-align:4px;font-variant-numeric:tabular-nums}}
.clk{{vertical-align:middle}}
td.cy{{font-size:11.5px;font-variant-numeric:tabular-nums}}
td.cy b{{font-size:12px}} td.cy.u b{{color:var(--up)}} td.cy.d b{{color:var(--dn)}}
td.sc b{{font-size:13px;font-variant-numeric:tabular-nums;margin-left:5px}}
.bar{{display:inline-block;width:52px;height:6px;border-radius:3px;background:var(--line);vertical-align:middle}}
.bar i{{display:block;height:6px;border-radius:3px;background:var(--bar)}}
td.sub{{color:var(--mut);font-size:11px}}
.up{{color:var(--up)}} .dn{{color:var(--dn)}} .mut{{color:var(--mut)}}
td.tr{{text-align:center}}
.gA{{background:var(--up)}} .gB{{background:#5ca3d6}} .gC{{background:#6b7885}}
.gD{{background:#94a3b8}} .gE{{background:var(--acc)}}
td.tr b{{display:inline-block;min-width:17px;border-radius:3px;color:#fff;font-size:11px;padding:0 4px}}
td.ma{{letter-spacing:2px;color:var(--up);font-size:12px}}
footer{{margin-top:26px;border-top:1px solid var(--line);padding-top:14px;color:var(--mut);font-size:12.5px}}
footer h3{{color:var(--ink);font-size:14px;margin:0 0 7px}}
footer li{{margin:4px 0}}
.warn{{border-left:3px solid var(--dn);padding-left:11px;margin-top:11px}}
:focus-visible{{outline:2px solid var(--acc);outline-offset:2px}}
@media(prefers-reduced-motion:reduce){{*{{transition:none!important;animation:none!important}}}}
@media(max-width:640px){{h1{{font-size:20px}} .sw{{margin-left:0}}}}
</style>
<div class="wrap">
<header>
  <h1>MACD <em>轉勢點</em> 時鐘排名 <em>R1</em></h1>
  <div class="sw" role="group" aria-label="主題">
    <button type="button" data-m="auto" aria-pressed="true">系統</button>
    <button type="button" data-m="light" aria-pressed="false">☀️ 淺色</button>
    <button type="button" data-m="dark" aria-pressed="false">🌙 深色</button>
  </div>
  <span class="meta">節點＝時鐘 <b>6 點鐘</b>（MACD 柱狀圖最負點）｜指針越接近 180°，分數越高｜
  來源：AI Sector R8 · 10MA Uptrend R15 · Combined Watchlist R17｜
  掃描 <b>{len(rows)}</b> 檔（union {len(rows)+len(missing)}，{len(missing)} 檔無日線資料）｜
  資料基準 <b>{lastday}</b> 收盤（Yahoo 日線）｜產生 2026.09.11 21:52 HKT｜Opus5;high</span>
</header>

<div class="rule">
  <h3>節點定義：時鐘四個正點 ＝ 四個真實 MACD 事件</h3>
  這一版把指針角度改成<b>事件錨定</b>（不再是純時間內插）：谷底出現前，指針由 3 點走向 6 點；
  谷底出現後，指針由 6 點走向 9 點，位置＝柱狀圖自谷底回升到零軸的比例。
  因此<b>「柱狀圖剛過最負點、開始回升」就落在 6 點鐘</b>，正是圖中藍色垂直線的位置 —— 本表給最高分。
  <div class="dial">
    <figure>{clock_svg(196, False, "A", 108)}</figure>
    <div class="nodes">
      <div><b>3 點鐘</b> 柱狀圖由正轉負<small class="mut">跌勢開始</small></div>
      <div><b>6 點鐘</b> 柱狀圖最負點 ← 節點<small class="mut">轉勢點 · 動能反轉的一刻</small></div>
      <div><b>9 點鐘</b> 柱狀圖由負轉正<small class="mut">上一版的舊節點</small></div>
      <div><b>12 點鐘</b> 柱狀圖最正點<small class="mut">見頂</small></div>
    </div>
  </div>
  <div class="formula">
    <span><b>A 相位 45</b> 指針與 180° 的距離（6:00–7:20 滿分）</span>
    <span><b>B 轉勢確認 25</b> 連續回升根數 · MACD 線上翹 · 未破新低</span>
    <span><b>C 底部品質 15</b> 谷底深度（相對 120 日振幅）· 線連續上翹</span>
    <span><b>D 價格確認 15</b> 價 &gt; EMA9/21 · RS21 勝市場中位 · 量縮</span>
  </div>
</div>

<div class="tiers">
{"".join(f'<div class="tc" style="--tc:{c}"><b>{counts[k]}</b><h4><i>{k}</i>{n}</h4><p>{desc}</p></div>' for k, n, desc, c in TIERS)}
</div>

<div class="filters">
  <button data-f="all" aria-pressed="true">全部</button>
  {"".join(f'<button data-f="{k}" aria-pressed="false">{k} · {counts[k]}</button>' for k, _, _, _ in TIERS)}
  <input id="q" placeholder="🔍 搜尋代號 / 名稱 / 產業">
  <span class="n" id="cnt"></span>
</div>

<div class="tblwrap"><table>
<thead><tr>
<th class="num">#</th><th>代號</th><th>名稱 / 產業</th><th>級</th>
<th>時鐘<small>指針位置</small></th>
<th class="num">距轉勢點<small>谷底在幾日前</small></th>
<th class="num">回升<small>自谷底 / 連升</small></th>
<th class="num">谷底值<small>深度 %</small></th><th class="num">現值<small>Hist</small></th>
<th>周期<small>已走/預期</small></th>
<th class="num">分數<small>0–100</small></th>
<th class="num">A<small>相位</small></th><th class="num">B<small>確認</small></th>
<th class="num">C<small>底質</small></th><th class="num">D<small>價格</small></th>
<th class="num">收盤<small>{lastday[5:]}</small></th><th class="num">21日</th><th class="num">距高</th>
<th class="num">RS21<small>vs 市場中位</small></th><th class="num">量比<small>10d/50d</small></th>
<th>VCP<small>R17</small></th><th class="num">確定性<small>R17</small></th>
<th class="num">AI流<small>5日</small></th><th>均線<small>9/21/50</small></th>
</tr></thead>
<tbody id="tb">
{body}
</tbody></table></div>

<footer>
  <h3>方法與限制</h3>
  <ul>
    <li><b>與上一版（9 點鐘節點）的差別</b>：舊版把「柱狀圖穿越零軸」當節點，排出來的都是已經回升 80–95% 的股票；
      本版改以<b>柱狀圖最負點</b>為節點，抓的是動能反轉的<b>第一刻</b>，進場更早、空間更大，
      但<b>確認度也更低</b> —— 谷底是事後才能確定的，今日看似的谷底可能被明天的新低取代。</li>
    <li><b>週期引擎已驗證</b>：MACD 12/26/9、柱狀圖穿越零軸為周期切換、最近 8 段同類周期均長為「預期長度」，
      與 Pine 腳本 <code>combo_cycle_clock_ema9bw_r3</code> 的 MODULE 1 一致；對照 TradingView 實跑，
      MET 的「第 3/預期 8.8 日」完全吻合。</li>
    <li><b>資料</b>：Yahoo Finance 日線（2025-09-02 → {lastday}，258 個交易日），取自 VCP-watchlist repo 的本地 EOD 存檔。
      VCP 等級與確定性欄取自 Combined Watchlist R17 同一基準日；AI 流欄為 AI Sector R8 的 5 日資金流向。
      RS21 ＝ 個股 21 日報酬 − 全體掃描標的中位數（−0.88%）；本地存檔只含個股不含指數 ETF。</li>
    <li><b>「探底中」不等於低分</b>：B 級（5:00–6:00）今日仍在創新低，指針還沒走到節點，
      但距離節點只差幾日 —— 這批是「明天可能就是轉勢點」的觀察名單，不是已經可以進場的名單。</li>
    <li><b>{len(missing)} 檔無資料</b>：{miss} —— 多為外國 ADR，不在本地 EOD 存檔的美股宇宙內。</li>
  </ul>
  <div class="warn">本表為技術面排序工具，不是投資建議。MACD 谷底只代表<b>下跌動能開始減弱</b>，
  不代表價格見底 —— 下跌趨勢中的動能背離常只帶來反彈而非反轉，且谷底要到事後才能確定。
  實際進場請配合原榜單的 VCP 形態、確定性與個股催化劑，並以價格結構（EMA9/21、前低）設好停損。</div>
</footer>
</div>

<script>
(function(){{
 var root=document.documentElement, sw=[].slice.call(document.querySelectorAll('.sw button'));
 function paint(m){{ m==='auto'?root.removeAttribute('data-theme'):root.setAttribute('data-theme',m);
   sw.forEach(function(b){{b.setAttribute('aria-pressed', b.dataset.m===m);}});
   try{{localStorage.setItem('clk2-theme',m)}}catch(e){{}} }}
 var sv='auto'; try{{sv=localStorage.getItem('clk2-theme')||'auto'}}catch(e){{}}
 paint(sv); sw.forEach(function(b){{b.onclick=function(){{paint(b.dataset.m)}}}});

 var tb=document.getElementById('tb'), all=[].slice.call(tb.rows),
     cnt=document.getElementById('cnt'), q=document.getElementById('q'), filt='all';
 function apply(){{
   var s=(q.value||'').trim().toLowerCase(), n=0;
   all.forEach(function(tr){{
     var ok=(filt==='all'||tr.dataset.tier===filt) && (!s||tr.textContent.toLowerCase().indexOf(s)>=0);
     tr.hidden=!ok; if(ok) n++;
   }});
   cnt.textContent='顯示 '+n+' / '+all.length+' 檔';
 }}
 [].slice.call(document.querySelectorAll('.filters button')).forEach(function(b){{
   b.onclick=function(){{ filt=b.dataset.f;
     [].slice.call(document.querySelectorAll('.filters button')).forEach(function(x){{
       x.setAttribute('aria-pressed', x===b);}});
     apply(); }};
 }});
 q.oninput=apply; apply();

 [].slice.call(document.querySelectorAll('th')).forEach(function(th,i){{
   th.onclick=function(){{
     var dir=th.dataset.dir==='desc'?'asc':'desc';
     [].slice.call(document.querySelectorAll('th')).forEach(function(x){{x.removeAttribute('data-dir')}});
     th.dataset.dir=dir;
     all.slice().sort(function(a,b){{
       var av=a.cells[i].dataset.v, bv=b.cells[i].dataset.v;
       if(av===undefined||bv===undefined){{ av=a.cells[i].textContent; bv=b.cells[i].textContent;
         return dir==='desc'?bv.localeCompare(av):av.localeCompare(bv); }}
       return dir==='desc'?parseFloat(bv)-parseFloat(av):parseFloat(av)-parseFloat(bv);
     }}).forEach(function(r){{tb.appendChild(r)}});
   }};
 }});
}})();
</script>'''

out = "/home/user/YT-subittle/trading-signal-analysis/watchlist/macd_clock_rank.html"
open(out, "w", encoding="utf-8").write(page)
print(f"saved {out} ({len(page)/1024:.0f} KB)")
print("tiers:", counts)
