# -*- coding: utf-8 -*-
"""產生 MACD Cycle Clock 排名清單 HTML。"""
import json, html

S = "/tmp/claude-0/-home-user-YT-subittle/0bd65ef0-0bef-5829-9a6f-f0a46d2d96cd/scratchpad"
d = json.load(open(f"{S}/clock_rank.json"))
meta = json.load(open(f"{S}/meta.json"))
rows, missing, lastday = d["rows"], d["missing"], d["lastday"]


def tier(r):
    """依時鐘相位分級（不是純分數），A 為『接近由負轉正』。"""
    if not r["up"]:
        if r["prog"] >= 80 and (r["b2z"] is not None and r["b2z"] <= 6):
            return "A"                       # 下跌尾段 + 已在收斂 → 即將轉正
        if r["prog"] >= 80:
            return "C"                       # 尾段但尚未收斂
        if r["prog"] >= 50:
            return "C"
        return "E"                           # 下跌前中段
    if r["elapsed"] <= 3:
        return "B"                           # 剛由負轉正
    return "D" if r["prog"] < 60 else "F"    # 上昇早中段 / 尾段延伸


TIERS = [
    ("A", "即將由負轉正", "下跌周期已走 ≥80%，柱狀圖回升且預估 6 日內穿越零軸 —— 時鐘指針逼近 9 點鐘，本表最高分段", "#16a34a"),
    ("B", "剛由負轉正",   "上昇周期第 1–3 日，指針剛過 9 點 —— 轉折已發生，仍在起漲點",                       "#0891b2"),
    ("C", "下跌尾段醞釀", "下跌周期已走 50%+ 但柱狀圖尚未明確收斂 —— 需再觀察幾日",                          "#d97706"),
    ("D", "上昇早中段",   "上昇周期進度 <60% —— 已在上昇，非本表主要目標",                                   "#64748b"),
    ("F", "上昇尾段延伸", "上昇周期進度 ≥60% —— 指針逼近 3 點鐘，留意轉折",                                   "#94a3b8"),
    ("E", "剛轉入下跌",   "下跌周期 <50% —— 指針在 3–6 點鐘，最不宜進場",                                    "#dc2626"),
]
for r in rows:
    r["tier"] = tier(r)

TV = "https://www.tradingview.com/chart/?symbol="


def clock_svg(theta, up, size=26):
    """小時鐘圖示：上半綠 / 下半紅 + 指針。"""
    import math
    c, rr = size / 2, size / 2 - 2.5
    a = math.radians(theta)
    x, y = c + rr * 0.78 * math.sin(a), c - rr * 0.78 * math.cos(a)
    gu = "#16a34a" if up else "#bbf7d0"
    gd = "#fecaca" if up else "#dc2626"
    return (f'<svg class="clk" viewBox="0 0 {size} {size}" width="{size}" height="{size}" aria-hidden="true">'
            f'<path d="M {c-rr} {c} A {rr} {rr} 0 0 1 {c+rr} {c}" fill="none" stroke="{gu}" stroke-width="3"/>'
            f'<path d="M {c+rr} {c} A {rr} {rr} 0 0 1 {c-rr} {c}" fill="none" stroke="{gd}" stroke-width="3"/>'
            f'<line x1="{c}" y1="{c}" x2="{x:.1f}" y2="{y:.1f}" stroke="#eab308" stroke-width="2.2" stroke-linecap="round"/>'
            f'<circle cx="{c}" cy="{c}" r="1.6" fill="#334155"/></svg>')


def chips(r):
    m = meta.get(r["sym"], {})
    out = []
    for l, cls in (("AI", "ai"), ("10MA", "tm"), ("CW", "cw")):
        if l in m.get("lists", []):
            out.append(f'<i class="src {cls}">{l}</i>')
    return "".join(out)


def fnum(v, fmt="{:+.1f}", cls=True):
    if v is None:
        return '<span class="mut">–</span>'
    c = "up" if v > 0 else ("dn" if v < 0 else "")
    return f'<span class="{c if cls else ""}">{fmt.format(v)}</span>'


def row_html(r):
    m = meta.get(r["sym"], {})
    nm = html.escape(m.get("name", ""))[:26]
    sec = html.escape(m.get("sector", ""))[:14]
    cyc = "升" if r["up"] else "跌"
    tcol = dict((t[0], t[3]) for t in TIERS)[r["tier"]]
    b2z = f'{r["b2z"]:.1f} 日' if (r["b2z"] is not None and r["b2z"] <= 30 and not r["up"]) else \
          ('<span class="mut">已轉正</span>' if r["up"] else '<span class="mut">未收斂</span>')
    vcp = m.get("vcp")
    vcell = f'<b class="g{vcp}">{vcp}</b>' if vcp else '<span class="mut">–</span>'
    cert = m.get("cert")
    ccell = f'{cert:.1f}' if cert is not None else '<span class="mut">–</span>'
    aif = m.get("aiflow")
    acell = fnum(aif, "{:+.2f}") if aif is not None else '<span class="mut">–</span>'
    return f'''<tr data-tier="{r['tier']}">
<td class="num" data-v="{-r['rank']}">{r['rank']}</td>
<td class="tk"><a href="{TV}{r['sym']}" target="_blank" rel="noopener">{r['sym']}</a>{chips(r)}</td>
<td class="nm">{nm}<small>{sec}</small></td>
<td class="tr" data-v="{r['score']}"><span class="tier" style="--tc:{tcol}">{r['tier']}</span></td>
<td class="ck" data-v="{(360-r['theta']) if not r['up'] else (720-r['theta'])}">{clock_svg(r['theta'], r['up'])}<b>{r['clock']}</b></td>
<td class="cy {'u' if r['up'] else 'd'}" data-v="{r['prog'] if not r['up'] else -r['prog']}">
  <b>{cyc}</b> {r['elapsed']}/{r['expected']:.1f} 日<small>{r['prog']:.0f}%</small></td>
<td class="num" data-v="{-(r['b2z'] if r['b2z'] is not None and not r['up'] else 99)}">{b2z}</td>
<td class="num" data-v="{r['hist']}">{r['hist']:+.3f}<small class="{'up' if r['rising_n'] else 'mut'}">連升 {r['rising_n']}</small></td>
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
<td class="tr" data-v="{'ABCDE'.index(vcp) if vcp else 9}">{vcell}</td>
<td class="num" data-v="{cert if cert is not None else -1}">{ccell}</td>
<td class="num" data-v="{aif if aif is not None else -9}">{acell}</td>
<td class="ma">{'✓' if r['e9'] else '·'}{'✓' if r['e21'] else '·'}{'✓' if r['e50'] else '·'}</td>
</tr>'''


tier_counts = {t[0]: sum(1 for r in rows if r["tier"] == t[0]) for t in TIERS}
body = "\n".join(row_html(r) for r in rows)
miss = "、".join(m["sym"] for m in missing)

page = f'''<title>MACD Cycle Clock 排名</title>
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
.wrap{{max-width:1560px;margin:0 auto;padding:22px 18px 60px}}
header{{border-bottom:3px solid var(--ink);padding-bottom:12px;display:flex;flex-wrap:wrap;gap:8px 16px;align-items:baseline}}
h1{{font-size:25px;margin:0}} h1 em{{font-style:normal;color:var(--acc)}}
.meta{{flex-basis:100%;color:var(--mut);font-size:12.5px}} .meta b{{color:var(--ink)}}
.sw{{margin-left:auto;display:inline-flex;gap:4px;background:var(--panel);border:1.5px solid var(--acc);
 border-radius:99px;padding:3px 4px}}
.sw button{{font:inherit;font-size:12px;font-weight:600;color:var(--mut);background:none;border:0;
 border-radius:99px;padding:4px 11px;cursor:pointer}}
.sw button[aria-pressed=true]{{background:var(--acc);color:var(--bg)}}
.rule{{background:var(--panel);border:1px solid var(--line);border-left:4px solid var(--acc);
 border-radius:7px;padding:13px 16px;margin:16px 0;font-size:13.5px}}
.rule h3{{margin:0 0 6px;font-size:14.5px}}
.rule code{{background:var(--accs);color:var(--acc);padding:1px 5px;border-radius:3px;font-size:12px}}
.formula{{display:flex;flex-wrap:wrap;gap:8px;margin-top:9px}}
.formula span{{background:var(--head);border:1px solid var(--line);border-radius:5px;padding:4px 10px;font-size:12.5px}}
.formula b{{color:var(--acc)}}
.tiers{{display:grid;grid-template-columns:repeat(auto-fit,minmax(215px,1fr));gap:9px;margin:16px 0}}
.tc{{background:var(--panel);border:1px solid var(--line);border-left:4px solid var(--tc);border-radius:7px;padding:9px 13px}}
.tc h4{{margin:0;font-size:13.5px}} .tc h4 i{{font-style:normal;color:var(--tc);font-weight:800}}
.tc p{{margin:3px 0 0;color:var(--mut);font-size:11.5px;line-height:1.45}}
.tc b{{float:right;font-size:17px;color:var(--tc)}}
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
td.ck{{white-space:nowrap}} td.ck b{{font-size:11.5px;margin-left:4px;vertical-align:3px;font-variant-numeric:tabular-nums}}
.clk{{vertical-align:middle}}
td.cy b{{font-size:12px}} td.cy.u b{{color:var(--up)}} td.cy.d b{{color:var(--dn)}}
td.cy{{font-size:11.5px;font-variant-numeric:tabular-nums}} td.cy small{{color:var(--mut)}}
td.sc{{white-space:nowrap}} td.sc b{{font-size:13px;font-variant-numeric:tabular-nums;margin-left:5px}}
.bar{{display:inline-block;width:56px;height:6px;border-radius:3px;background:var(--line);vertical-align:middle}}
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
footer li{{margin:3px 0}}
.warn{{border-left:3px solid var(--dn);padding-left:11px;margin-top:11px}}
:focus-visible{{outline:2px solid var(--acc);outline-offset:2px}}
@media(prefers-reduced-motion:reduce){{*{{transition:none!important;animation:none!important}}}}
@media(max-width:640px){{h1{{font-size:20px}} .sw{{margin-left:0}}}}
</style>
<div class="wrap">
<header>
  <h1>MACD Cycle Clock <em>排名</em></h1>
  <div class="sw" role="group" aria-label="主題">
    <button type="button" data-m="auto" aria-pressed="true">系統</button>
    <button type="button" data-m="light" aria-pressed="false">☀️ 淺色</button>
    <button type="button" data-m="dark" aria-pressed="false">🌙 深色</button>
  </div>
  <span class="meta">以日線 MACD 週期時鐘相位重新排名｜<b>「接近由負轉正」= 最高分</b>｜
  來源：AI Sector R8 · 10MA Uptrend R15 · Combined Watchlist R17｜
  掃描 <b>{len(rows)}</b> 檔（union {len(rows)+len(missing)} 檔，{len(missing)} 檔無日線資料）｜
  資料基準 <b>{lastday}</b> 收盤（Yahoo 日線）｜Opus 5</span>
</header>

<div class="rule">
  <h3>計分邏輯（0–100）</h3>
  時鐘指針順時針轉：下跌周期由 <code>3 點 → 6 點 → 9 點</code>，走到 <b>9 點鐘</b>就是柱狀圖由負轉正的一刻。
  因此<b>「下跌周期尾段 + 柱狀圖正在收斂回零軸」給最高分</b>；已經轉正但仍在起漲點（9–10 點）次之；
  上昇中段之後遞減；剛轉入下跌（3–4 點）最低。
  <div class="formula">
    <span><b>A 相位 45</b> 指針位置：下跌 prog ≥80% 滿分</span>
    <span><b>B 收斂 25</b> 以近 3 日斜率外推，預估 ≤8 日穿零軸</span>
    <span><b>C 轉向 15</b> 連續回升根數 + 已離本周期低點</span>
    <span><b>D 確認 15</b> 價 &gt; EMA9/21 · RS21 &gt; 市場中位 · 量縮</span>
  </div>
</div>

<div class="tiers">
{"".join(f'<div class="tc" style="--tc:{c}"><b>{tier_counts[k]}</b><h4><i>{k}</i> {n}</h4><p>{desc}</p></div>' for k, n, desc, c in TIERS)}
</div>

<div class="filters">
  <button data-f="all" aria-pressed="true">全部</button>
  {"".join(f'<button data-f="{k}" aria-pressed="false">{k} · {n}</button>' for k, n, _, _ in TIERS)}
  <input id="q" placeholder="🔍 搜尋代號 / 名稱 / 產業">
  <span class="n" id="cnt"></span>
</div>

<div class="tblwrap"><table>
<thead><tr>
<th class="num">#</th><th>代號</th><th>名稱 / 產業</th><th>級</th>
<th>時鐘<small>指針位置</small></th><th>周期<small>已走/預期</small></th>
<th class="num">預估轉正<small>外推日數</small></th><th class="num">MACD Hist<small>連升根數</small></th>
<th class="num">分數<small>0–100</small></th>
<th class="num">A<small>相位</small></th><th class="num">B<small>收斂</small></th>
<th class="num">C<small>轉向</small></th><th class="num">D<small>確認</small></th>
<th class="num">收盤<small>9/10</small></th><th class="num">21日</th><th class="num">距高</th>
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
    <li><b>算法一致性已驗證</b>：本掃描以 Python 重現 Pine 腳本 <code>combo_cycle_clock_ema9bw_r3</code> 的 MODULE 1 週期引擎
      （MACD 12/26/9，柱狀圖穿越零軸為周期切換，取最近 8 段同類周期均長為「預期長度」）。
      對照 TradingView 實跑：<b>MET 下跌 34%、第 3/預期 8.8 日 — 完全吻合</b>；
      RVMD 第 9/預期 14.4 日 vs 畫面 14.1 日（TradingView 歷史較長，均值略異）。</li>
    <li><b>資料</b>：Yahoo Finance 日線（2025-09-02 → {lastday}，258 個交易日），取自 VCP-watchlist repo
      的本地 EOD 存檔。VCP 等級與確定性欄取自 Combined Watchlist R17 同一基準日；AI 流欄為 AI Sector R8 的 5 日資金流向。RS21 = 個股 21 日報酬 − 全體掃描標的中位數（−0.88%）；本地 EOD 存檔只含個股、不含 SPY 等指數 ETF，故以中位數作市場基準（同 VCP-watchlist 做法）。</li>
    <li><b>「預估轉正」是線性外推</b>：以最近 3 日柱狀圖斜率推算還要幾根 K 線穿越零軸，斜率為負或發散時顯示「未收斂」。
      這是估計值不是預測，實際轉正日可能提前或延後，尤其在消息驅動的個股上。</li>
    <li><b>下跌周期進度 &gt;160% 會扣分</b>：周期遠超歷史均長，通常代表趨勢結構已變（而非「快要轉正」），
      A 項由 45 分逐步降至 30 分。</li>
    <li><b>{len(missing)} 檔無資料</b>：{miss} —— 多為外國 ADR，不在本地 EOD 存檔的美股宇宙內。</li>
  </ul>
  <div class="warn">本表為技術面排序工具，不是投資建議。MACD 週期只反映動能相位，
  不含基本面、消息面與流動性判斷；「即將由負轉正」不保證價格會上漲，下跌趨勢中的動能收斂常只帶來反彈而非反轉。
  實際進場請配合原榜單的 VCP 形態、確定性與個股催化劑一併判斷。</div>
</footer>
</div>

<script>
(function(){{
 var root=document.documentElement, sw=[].slice.call(document.querySelectorAll('.sw button'));
 function paint(m){{ m==='auto'?root.removeAttribute('data-theme'):root.setAttribute('data-theme',m);
   sw.forEach(function(b){{b.setAttribute('aria-pressed', b.dataset.m===m);}});
   try{{localStorage.setItem('clk-theme',m)}}catch(e){{}} }}
 var sv='auto'; try{{sv=localStorage.getItem('clk-theme')||'auto'}}catch(e){{}}
 paint(sv); sw.forEach(function(b){{b.onclick=function(){{paint(b.dataset.m)}}}});

 var tb=document.getElementById('tb'), all=[].slice.call(tb.rows),
     cnt=document.getElementById('cnt'), q=document.getElementById('q'), filt='all';
 function apply(){{
   var s=(q.value||'').trim().toLowerCase(), n=0;
   all.forEach(function(tr){{
     var okT = filt==='all' || tr.dataset.tier===filt;
     var okQ = !s || tr.textContent.toLowerCase().indexOf(s)>=0;
     tr.hidden = !(okT&&okQ); if(!tr.hidden) n++;
   }});
   cnt.textContent = '顯示 '+n+' / '+all.length+' 檔';
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
     var dir = th.dataset.dir==='desc' ? 'asc' : 'desc';
     [].slice.call(document.querySelectorAll('th')).forEach(function(x){{x.removeAttribute('data-dir')}});
     th.dataset.dir=dir;
     var rs=all.slice().sort(function(a,b){{
       var av=a.cells[i].dataset.v, bv=b.cells[i].dataset.v;
       if(av===undefined||bv===undefined){{ av=a.cells[i].textContent; bv=b.cells[i].textContent;
         return dir==='desc'? bv.localeCompare(av): av.localeCompare(bv); }}
       return dir==='desc'? parseFloat(bv)-parseFloat(av) : parseFloat(av)-parseFloat(bv);
     }});
     rs.forEach(function(r){{tb.appendChild(r)}});
   }};
 }});
}})();
</script>'''

out = "/home/user/YT-subittle/trading-signal-analysis/watchlist/macd_clock_rank.html"
import os
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out, "w", encoding="utf-8").write(page)
print(f"saved {out} ({len(page)/1024:.0f} KB)")
print("tier counts:", tier_counts)
