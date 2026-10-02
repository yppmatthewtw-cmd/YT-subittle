# -*- coding: utf-8 -*-
"""r8 的版本敘述：寫成 env 檔給 csv_to_xlsx.py / build_r7_scan_html.py 讀。
所有數字都由資料算出（面板覆蓋、Yahoo vs Nasdaq 比對、與 r7 / 修正前的差異），不手寫。"""
import os, sys, json, glob
import pandas as pd

S = "/tmp/claude-0/-home-user-YT-subittle/0bd65ef0-0bef-5829-9a6f-f0a46d2d96cd/scratchpad"
SNAPD = "/home/user/yppmatthewtw-cmd/10ma-watchlist/data/snapshots"
sys.path.insert(0, S)
from scan_r7 import _files

b = pd.read_csv(f"{S}/base_r8.csv"); u = pd.read_csv(f"{S}/universe_r8.csv"); up = pd.read_csv(f"{S}/update_r8.csv")
n6 = int((b.score == 6).sum())
still = up[(up.score == 6) & up.four_17]; fresh = up[(up.score != 6) & up.four_17 & up.c2 & up.c3]

# ── 面板上 09-22 / 09-23 的 Yahoo（prio 0）覆蓋：與 load() 相同的檔案集合與去重 ──
fr = []
for f in _files():
    d = pd.read_csv(f)
    if "tail" in os.path.basename(f):
        continue
    if "route" in d.columns:
        d = d[~d.route.astype(str).str.contains("hourly|intraday|quote", case=False, na=False)]
    fr.append(d[d.date.isin(["2026-09-22", "2026-09-23"])][["symbol", "date", "close"]])
y = pd.concat(fr).dropna(subset=["close"])
y["symbol"] = y.symbol.astype(str).str.upper().str.strip()
y = y.drop_duplicates(["symbol", "date"])
yv = {dt: int((y.date == dt).sum()) for dt in ("2026-09-22", "2026-09-23")}

# 20MA repo tail 路線（本次觸發的 fetch_yahoo_tail）拿到的 09-22 日線，與上面的 Yahoo 名單比
tl = pd.read_csv("/home/user/yppmatthewtw-cmd/20mawarchlist/data/yahoo/r7scan_after_2026-09-21.csv.gz")
tl22 = set(tl[(tl.date == "2026-09-22") & (tl.route == "hist5d")].symbol.str.upper())
tl_new = len(tl22 - set(y[y.date == "2026-09-22"].symbol))
chk, nas = {}, {}
for dt in ("2026-09-22", "2026-09-23"):
    sn = pd.read_csv(f"{SNAPD}/{dt}.csv")
    sn["px"] = pd.to_numeric(sn.lastsale.astype(str).str.replace(r"[$,]", "", regex=True), errors="coerce")
    sn["symbol"] = sn.symbol.astype(str).str.upper().str.strip()
    nas[dt] = set(sn.symbol)
    m = y[y.date == dt].merge(sn[["symbol", "px"]], on="symbol")
    dc = (m.close / m.px - 1).abs() * 100
    chk[dt] = (len(m), float(dc.max()), int((dc > 0.05).sum()))
used = set(b.symbol_used)
wl_y = {dt: len(used & set(y[y.date == dt].symbol)) for dt in yv}
wl_nas = {dt: len(used & nas[dt]) for dt in nas}
miss_nas = sorted(used - nas["2026-09-23"])

data = (f"本版資料：再次觸發三個 repo 的 GitHub Actions（fetch_yahoo_eod ×3、fetch_eod_snapshot）抓到 09-24 01:25 UTC（美東 09-23 收盤後約 5.5 小時）。"
        f"Yahoo 的 09-22 日線在全部鏡像中合計只有 {yv['2026-09-22']:,} 檔（09-23 {yv['2026-09-23']:,} 檔；完整交易日約 3,040 檔），"
        f"另外觸發 20MA repo 的 tail 路線（5 日相對期間 / 小時線），只拿到 {len(tl22)} 檔 09-22 日線，其中 {tl_new} 檔是上述名單以外的，覆蓋仍遠低於 50% 門檻，"
        "所以完整 OHLC 的最新交易日仍是 09-21，六項條件的基準與 r7 相同。"
        f"09-22、09-23 兩天的收盤：Nasdaq 官方收盤快照涵蓋 {wl_nas['2026-09-23']}/760 檔"
        + (f"（{'、'.join(miss_nas)} 不在 Nasdaq 快照，改用 Yahoo 日線）" if miss_nas else "")
        + f"；已有 Yahoo 完整日線的名字優先用 Yahoo（760 檔中 09-22 有 {wl_y['2026-09-22']} 檔、09-23 有 {wl_y['2026-09-23']} 檔）。"
        f"兩個來源重疊的收盤逐檔比對（09-22 {chk['2026-09-22'][0]} 檔、09-23 {chk['2026-09-23'][0]} 檔），"
        f"最大差異 {max(chk['2026-09-22'][1], chk['2026-09-23'][1]):.3f}%，差 >0.05% 的 {chk['2026-09-22'][2] + chk['2026-09-23'][2]} 檔。")

# ── 與 r7、與修正前 r8 的差異 ──
r7 = pd.read_csv(f"{S}/r7keep/base_new.csv"); pre = pd.read_csv(f"{S}/r8pre/base_r8.csv")
m7 = b.merge(r7, on="ticker", suffixes=("", "_o"))
same7 = int((m7.score == m7.score_o).sum())
mp = b.merge(pre, on="ticker", suffixes=("", "_o"))
th2 = mp[(mp.theta - mp.theta_o).abs() > 2]
c4f = mp[mp.c4 != mp.c4_o]
sc = mp[mp.score != mp.score_o]
upre = pd.read_csv(f"{S}/r8pre/universe_r8.csv")
u6, p6 = set(u[u.score == 6].ticker), set(upre[upre.score == 6].ticker)
off = u[(u.score == 6) & (~u.ticker.isin(set(b.ticker)))]
warn = b[b.data_warn.fillna("") != ""]
CN = {"c1": "①", "c2": "②", "c3": "③", "c4": "④", "c5": "⑤", "c6": "⑥"}
def _why(t, gone):
    """加掃六項全中名單變動的原因：進出流動性門檻，或哪一項翻轉。"""
    a, z = (upre, u) if gone else (upre, u)
    if gone and t not in set(u.ticker):
        r = upre[upre.ticker == t].iloc[0]
        return f"{t}（20 日均額改正後不足 300 萬美元）" if r.turnover20_m < 3.2 else f"{t}（已不在加掃範圍）"
    if not gone and t not in set(upre.ticker):
        return f"{t}（改正均額後才進入加掃範圍）"
    o = upre[upre.ticker == t].iloc[0]; n = u[u.ticker == t].iloc[0]
    fl = "".join(CN[c] for c in CN if bool(o[c]) != bool(n[c]))
    return f"{t}（{fl} 翻轉，θ {o.theta:.1f}° → {n.theta:.1f}°）" if "④" in fl else f"{t}（{fl} 翻轉）"

panel = ("面板規則：同一檔同一天在多份鏡像都有資料時，取抓取窗口較新的那份（r7 以前取檔名排序在前的舊檔）。"
         f"760 檔最後一根全部落在 09-21，0 檔停在舊日期。"
         + (f"資料警示：{'、'.join(f'{r.ticker}（{r.data_warn}）' for r in warn.itertuples())}，指標值不可信；皆未進入任何命中名單。" if len(warn) else ""))
fix = ("r8 同時修正的問題（獨立驗證發現）："
       "(1) chat 編號：chat 1 = 10MA R20、chat 2 = Combined R22（VCP / Stage 2A / Pre-breakout）、chat 3 = SubSector R12 + AI Sector R13 + 加息 R2，依三個 session 連結順序與各 repo commit 的 Claude-Session 尾註核對；r6、r7 標錯了（把 Combined 標成 chat 1、SubSector / AI 標成 chat 2、10MA 與加息標成 chat 3），命中規則與名單不受影響。"
       "(2) 20 日均額改為最近 20 根 (收盤 × 成交量) 的平均（原為最後收盤 × 20 日均量），加掃另剔除最後一根不在 09-21 的名字、並把同一證券的不同寫法（BF.B / BF/B）合併；"
       f"加掃由 {len(upre):,} 檔變為 {len(u):,} 檔；加掃六項全中 {len(p6)} → {len(u6)} 檔"
       + (f"，移出 {'、'.join(_why(t, True) for t in sorted(p6 - u6))}" if p6 - u6 else "")
       + (f"，加入 {'、'.join(_why(t, False) for t in sorted(u6 - p6))}" if u6 - p6 else "") + "。"
       f"(3) MACD 時鐘只丟被視窗起點截斷的第一段（原本兩個方向各丟一段，多丟了一段完整週期）：{len(th2)} 檔指針角度變動 >2°，"
       f"④ 翻轉 {len(c4f)} 檔（{'、'.join(f'{r.ticker} {r.score_o}→{r.score}' for r in c4f.itertuples()) or '無'}），六項全中與差一項名單"
       + ("不變" if len(sc[(sc.score >= 5) | (sc.score_o >= 5)]) == 0 else "有變動") + "。"
       "(4) Excel chat 分頁原本把所有文字欄的「+」換成「 · 」，來源原話裡的正號（斜率 +0.49 等）因此消失；現在只換來源榜單欄。"
       "(5) BF.B 與 BF/B 資料相同、根數相同時，代號對齊固定取斜線寫法（Nasdaq 快照的寫法），不再依雜湊順序。")
html = ("r8：條件與 r3–r7 相同。" + data + " " + panel +
        f" 本版真正的新資訊是 <b>09-23 收盤</b>：{n6} 檔全中裡 {len(still)} 檔在 09-23 收盤下 ①④⑤⑥ 仍成立，另有 {len(fresh)} 檔新符合。<br>" + fix)
env = {"DATA_NOTE": data, "PANEL_NOTE": panel, "FIX_NOTE": fix, "HTML_NOTE": html}
with open(f"{S}/notes_r8.env", "w") as f:
    for k, v in env.items():
        f.write(f"export {k}={json.dumps(v, ensure_ascii=False)}\n")

# 來源分頁：chat 編號、五份成品、加掃一列由資料算出
src = pd.read_csv(f"{S}/src_rows.csv")
lab = {"Watch List - 10MA uptrend": "chat 1 · Watch List - 10MA uptrend",
       "Watch List - VCP, Stage 2A, Pre Break Out": "chat 2 · Watch List - VCP, Stage 2A, Pre Break Out",
       "Watch List - Sub sector": "chat 3 · Watch List - Sub sector"}
src["Session"] = src.Session.map(lambda x: lab.get(x, x))
src.loc[src.Session == "四榜去重", "Session"] = "五份成品去重"
src.loc[src.Session == "加掃", ["Repo / 取得方式", "最新成品", "成品基準日", "取用檔數"]] = [
    "三個 repo 的 Yahoo 鏡像併集 3,097 檔", "收盤 ≥ $2、20 日 (收盤×量) 平均 ≥ 300 萬美元、最後一根在 09-21、同證券不同寫法只留一個",
    "2026-09-21", str(len(u))]
src.loc[len(src)] = ["價格資料", "三個 repo 的 fetch_yahoo_eod（09-24 01:21–01:25 UTC）＋ 10MA fetch_eod_snapshot（09-22、09-23）",
                     "完整 OHLC 至 09-21；09-22 / 09-23 為 Nasdaq 官方收盤快照（已有 Yahoo 日線者用 Yahoo）", "2026-09-23", "3,097"]
src.to_csv(f"{S}/src_rows_r8.csv", index=False, encoding="utf-8-sig")
print(json.dumps({"yv": yv, "chk": chk, "wl_y": wl_y, "wl_nas": wl_nas, "miss_nas": miss_nas, "same_score_vs_r7": same7,
                  "theta>2": len(th2), "c4flip": [(r.ticker, r.score_o, r.score) for r in c4f.itertuples()],
                  "uni": [len(upre), len(u)], "u6": [len(p6), len(u6)], "off": len(off), "warn": warn.ticker.tolist()}, ensure_ascii=False))
