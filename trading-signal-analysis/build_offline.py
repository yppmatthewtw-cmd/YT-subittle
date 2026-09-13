# -*- coding: utf-8 -*-
"""
產生完全自包含的離線版 HTML（ross_toolkit_offline.html）。
合併: 使用指南 + 三層看板 + 入市/賣出圖表(base64內嵌) + 83條規則庫(可搜尋) + Pine腳本(一鍵複製)
執行:  python3 build_offline.py
"""
import base64, csv, json, html, pathlib

ROOT = pathlib.Path(__file__).parent

# ---- 讀取素材 ----
img_b64 = base64.b64encode((ROOT / "charts/ross_entry_exit_chart.png").read_bytes()).decode()
win_b64 = base64.b64encode((ROOT / "case-study/dcfc_win_day.png").read_bytes()).decode()
red_b64 = base64.b64encode((ROOT / "case-study/dcfc_red_day.png").read_bytes()).decode()

with open(ROOT / "data/ross_rules.csv", encoding="utf-8-sig") as f:
    rows = list(csv.reader(f))
rules = [dict(zip(["vid", "factor", "metric", "threshold", "causal", "outcome"], r))
         for r in rows[1:]]

pines = {p.name: p.read_text(encoding="utf-8") for p in sorted((ROOT / "pine").glob("*.pine"))}

dashboard = (ROOT / "dashboard.html").read_text(encoding="utf-8")
# 取出看板的 <style> 與主體（去掉開頭註解與 title，因為離線版有自己的外框）
style_start = dashboard.index("<style>")
style_end = dashboard.index("</style>") + len("</style>")
dash_style = dashboard[style_start:style_end]
body_start = dashboard.index("<h1>")
dash_body = dashboard[body_start:]

pine_blocks = "\n".join(
    f"""<details class="pinebox"><summary><b>{name}</b>
      <button class="copybtn" onclick="copyPine(event,'{name}')">複製</button></summary>
      <pre id="pine-{name}">{html.escape(code)}</pre></details>"""
    for name, code in pines.items())

page = f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ross Momentum 交易工具包（離線完整版）</title>
{dash_style}
<style>
  nav{{position:sticky; top:0; z-index:9; background:var(--card); border:1px solid var(--line);
      border-radius:12px; padding:10px 14px; margin-bottom:20px; display:flex; gap:6px; flex-wrap:wrap}}
  nav a{{text-decoration:none; color:var(--ink); font-size:13.5px; padding:6px 12px; border-radius:8px}}
  nav a:hover{{background:var(--bg)}}
  section{{scroll-margin-top:70px}}
  .guide h3{{margin:18px 0 6px; font-size:15px}}
  .guide p, .guide li{{font-size:13.5px; color:var(--ink); margin-bottom:6px}}
  .guide ol, .guide ul{{padding-left:22px}}
  img.chart{{width:100%; border:1px solid var(--line); border-radius:10px}}
  .pinebox{{border:1px solid var(--line); border-radius:10px; margin-bottom:10px; overflow:hidden}}
  .pinebox summary{{padding:10px 14px; cursor:pointer; font-size:13.5px; background:var(--bg)}}
  .pinebox pre{{padding:14px; font-size:12px; overflow-x:auto; background:#0f172a; color:#e2e8f0;
      line-height:1.5}}
  .copybtn{{float:right; border:1px solid var(--line); background:var(--card); color:var(--ink);
      border-radius:6px; padding:2px 10px; font-size:12px; cursor:pointer}}
  #ruleSearch{{margin-bottom:10px}}
  #rulesTbl td{{vertical-align:top; font-size:12.5px}}
  #rulesTbl td:first-child{{white-space:nowrap; color:var(--ink2)}}
  .rule-out{{white-space:nowrap}}
</style>
</head>
<body>

<nav>
  <a href="#guide">📖 使用指南</a>
  <a href="#dash">📊 三層看板</a>
  <a href="#chart">📈 入市/賣出圖表</a>
  <a href="#case">⚖️ 成敗案例 DCFC</a>
  <a href="#rules">📚 規則庫 (83條)</a>
  <a href="#pine">📣 Pine 警報腳本</a>
</nav>

<section id="guide" class="layer guide">
  <h2>📖 使用指南：來不及看盤如何及時買賣</h2>
  <p>核心思路：<b>機器盯盤、人只在盤前準備＋收到推播後 30 秒決策</b>。每天約 20 分鐘人工。</p>
  <h3>每日流程</h3>
  <ol>
    <li><b>盤前 6:30 前</b>（規則 #36/#37）：掃描器篩「缺口>4% + Float&lt;10M + RVOL>5x」→ 在下方「層一」輸入候選股自動評分，只留 4/5、5/5。</li>
    <li><b>掛條件單</b>：「層三」計算器算出 OCO 括號單（入場 Buy Stop-Limit＋止損 Sell Stop＋分批止盈），盤前掛入券商後即使不看盤也會自動執行。</li>
    <li><b>盤中只處理推播</b>：TradingView 設好下方三支 Pine 腳本的警報。收到「MACD 轉紅燈」「放量跌破 VWAP」推播才需要手動處理。</li>
    <li><b>風控自動化</b>：達日最大虧損強制停止（#47）、峰值回吐 50% 收工（#48）— 層三會自動亮紅燈。</li>
  </ol>
  <h3>自動化三個層級</h3>
  <ul>
    <li><b>半自動（建議起點）</b>：盤前掛 OCO 括號單，警報只做否決用。</li>
    <li><b>警報驅動</b>：推播 → 券商 App 一鍵下單（預設倉位模板）。</li>
    <li><b>全自動</b>：TradingView Webhook → Alpaca/IBKR API 下單；務必先模擬盤一個月，並把冷市縮倉（#33/#34）與熔斷做進程式。</li>
  </ul>
  <h3>買入訊號特徵摘要</h3>
  <ul>
    <li><b>入市① Gap &amp; Go</b>：破盤前高 1–2 美分；量>5x、MACD 綠燈、價>VWAP、9:30–9:45 窗口；止損＝突破K線低點（#10/#24/#30/#68）</li>
    <li><b>入市② Bull Flag 首次回踩</b>：回踩&lt;前波20%、回踩量&lt;突破量50%、有下影線、守住EMA9，首根創新高K線進場；止損＝旗形低點（#13/#15）</li>
  </ul>
  <h3>賣出訊號特徵摘要</h3>
  <ul>
    <li>延伸棒長上影＋離VWAP>10% → 減半倉（#3/#60）；整數關口/第二延伸棒 → 再減半（#53）</li>
    <li>放量跌破旗形低點＋MACD轉負 → 全部出清（#16/#24）；高點回落>20% 即 Back-side 不再做多（#76）</li>
  </ul>
</section>

<section id="dash">
{dash_body.replace('<h1>', '<h1 id="dashTitle">')}
</section>

<section id="chart" class="layer">
  <h2>📈 Ross 典型交易日：入市點與賣出點</h2>
  <div class="hint">模擬低流通量 Gap &amp; Go 交易日（1分鐘K線＋成交量＋MACD）。藍框=入市訊號，紅框=賣出訊號，灰區=Back-side 禁區。</div>
  <img class="chart" alt="Ross 典型交易日入市賣出點標註圖" src="data:image/png;base64,{img_b64}">
</section>

<section id="case" class="layer">
  <h2>⚖️ 成功日 vs 失敗日 對照案例：DCFC (Tritium)</h2>
  <div class="hint">同一隻股票、同一個白宮消息事件窗口（2022/2/8–10）：一天 +$12k、一天轉紅。失敗日的每個價位均出自 Ross 在《Red Day Lessons》中的自述。詳細分析見 case-study/README.md。</div>
  <img class="chart" alt="成功日 +12k" src="data:image/png;base64,{win_b64}">
  <br><br>
  <img class="chart" alt="失敗日 紅日" src="data:image/png;base64,{red_b64}">
  <div style="overflow-x:auto"><table>
    <thead><tr><th>維度</th><th>✅ 成功日</th><th>⛔ 失敗日</th></tr></thead>
    <tbody>
      <tr><td>消息階段</td><td>第 1 天（未 price-in）</td><td>第 2 天（已 price-in，#51）</td></tr>
      <tr><td>入場位置</td><td>盤前高突破位，貼近 VWAP</td><td>離 VWAP >10% 的延伸段（$10.50 FOMO）</td></tr>
      <tr><td>倉位</td><td>計劃內</td><td>誤買 9,000 股（#67/#80）</td></tr>
      <tr><td>虧損處理</td><td>—</td><td>$10.30/$10.40 向下攤平（#43）</td></tr>
      <tr><td>出場</td><td>延伸棒分批止盈（#53/#60）</td><td>反彈 $10.85 認賠（正確執行 #61，避開 -$27k）</td></tr>
      <tr><td>根因</td><td>賺夠收工（#48）</td><td>冷市踩不住煞車（#34）</td></tr>
    </tbody>
  </table></div>
</section>

<section id="rules" class="layer">
  <h2>📚 Logic Analysis 規則庫（83 條）</h2>
  <div class="hint">來源: Logic Analysis (Opus Warrior) 2026.03.26。輸入關鍵字即時過濾（如 VWAP、Float、MACD、止損、心理）。</div>
  <input id="ruleSearch" placeholder="🔍 搜尋規則…" oninput="filterRules()">
  <div style="overflow-x:auto">
  <table id="rulesTbl"><thead><tr>
    <th>#</th><th>影片</th><th>因子</th><th>指標</th><th>門檻</th><th>因果鏈</th><th>結論</th>
  </tr></thead><tbody></tbody></table>
  </div>
</section>

<section id="pine" class="layer">
  <h2>📣 TradingView Pine 警報腳本（v5）</h2>
  <div class="hint">展開 → 複製 → 貼到 TradingView Pine Editor → 加入圖表 → 在「警報」對話框選取對應 alertcondition，通知勾選 App 推播。</div>
  {pine_blocks}
</section>

<footer>Ross Momentum 交易工具包 · 離線完整版 · 僅供教育用途，不構成投資建議。</footer>

<script>
const RULES = {json.dumps(rules, ensure_ascii=False)};
function renderRules(list){{
  document.querySelector('#rulesTbl tbody').innerHTML = list.map((r,i)=>
    `<tr><td>${{r.idx}}</td><td>${{r.vid}}</td><td><b>${{r.factor}}</b></td>`+
    `<td>${{r.metric}}</td><td>${{r.threshold}}</td><td>${{r.causal}}</td>`+
    `<td class="rule-out">${{r.outcome.split(':')[0]}}</td></tr>`).join('');
}}
RULES.forEach((r,i)=>r.idx=i+1);
function filterRules(){{
  const q = document.getElementById('ruleSearch').value.trim().toLowerCase();
  renderRules(!q ? RULES : RULES.filter(r =>
    Object.values(r).join(' ').toLowerCase().includes(q)));
}}
renderRules(RULES);
function copyPine(ev,name){{
  ev.preventDefault(); ev.stopPropagation();
  navigator.clipboard.writeText(document.getElementById('pine-'+name).textContent)
    .then(()=>{{ev.target.textContent='已複製 ✓'; setTimeout(()=>ev.target.textContent='複製',1500)}});
}}
</script>
</body>
</html>"""

out = ROOT / "ross_toolkit_offline.html"
out.write_text(page, encoding="utf-8")
print(f"saved {out.name}  ({out.stat().st_size/1024:.0f} KB)")
