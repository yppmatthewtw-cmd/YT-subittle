# -*- coding: utf-8 -*-
"""r9 的版本敘述：寫成 env 檔給 csv_to_xlsx.py / build_r7_scan_html.py 讀。所有數字由資料算出。"""
import os, sys, json, shlex
import pandas as pd

S = "/tmp/claude-0/-home-user-YT-subittle/0bd65ef0-0bef-5829-9a6f-f0a46d2d96cd/scratchpad"
SNAPD = "/home/user/yppmatthewtw-cmd/10ma-watchlist/data/snapshots"
MPJ = "/home/user/yppmatthewtw-cmd/10ma-watchlist/data/screen_mp21.json"
sys.path.insert(0, S)
from scan_r7 import _files

b = pd.read_csv(f"{S}/base_r9.csv"); u = pd.read_csv(f"{S}/universe_r9.csv")
p8 = pd.read_csv(f"{S}/r8keep/base_r8.csv")
tk = json.load(open(f"{S}/scan_tickers.json")); tk8 = json.load(open(f"{S}/scan_tickers_r8.json"))
mp = json.load(open(MPJ))
BASE = b.date.max()
n6 = int((b.score == 6).sum())

# ── 各日 Yahoo 完整日線覆蓋（與 load() 同一組檔案；tail 與盤中路線不算）──
fr = []
for f in _files():
    if "tail" in os.path.basename(f):
        continue
    d = pd.read_csv(f)
    if "route" in d.columns:
        d = d[~d.route.astype(str).str.contains("hourly|intraday|quote", case=False, na=False)]
    fr.append(d[d.date >= "2026-09-18"][["symbol", "date", "close"]])
y = pd.concat(fr).dropna(subset=["close"])
y["symbol"] = y.symbol.astype(str).str.upper().str.strip()
y = y.drop_duplicates(["symbol", "date"])
cov = y.groupby("date").symbol.nunique().to_dict()
full_n = max(cov.values())

def _snap(dt):
    sn = pd.read_csv(f"{SNAPD}/{dt}.csv")
    sn["px"] = pd.to_numeric(sn.lastsale.astype(str).str.replace(r"[$,]", "", regex=True), errors="coerce")
    sn["symbol"] = sn.symbol.astype(str).str.upper().str.strip()
    return sn.drop_duplicates("symbol").set_index("symbol").px
# 過期快照：與前一份快照逐檔相同（10MA repo 的 2026-09-24.csv 就是 09-23 的資料）
p23, p24 = _snap("2026-09-23"), _snap("2026-09-24")
_c = p23.index.intersection(p24.index)
same24 = float((p23[_c] == p24[_c]).mean())
stale24 = same24 >= 0.9
chk = {}
for dt in ("2026-09-22", "2026-09-23", "2026-09-24"):
    fp = f"{SNAPD}/{dt}.csv"
    if not os.path.exists(fp) or (dt == "2026-09-24" and stale24):
        continue
    sn = pd.read_csv(fp)
    sn["px"] = pd.to_numeric(sn.lastsale.astype(str).str.replace(r"[$,]", "", regex=True), errors="coerce")
    sn["symbol"] = sn.symbol.astype(str).str.upper().str.strip()
    m = y[y.date == dt].merge(sn[["symbol", "px"]], on="symbol")
    dc = (m.close / m.px - 1).abs() * 100
    chk[dt] = (len(m), float(dc.max()) if len(m) else 0.0, int((dc > 0.05).sum()))
used = set(b.symbol_used)
# 完整交易日上個別缺漏、以 Nasdaq 收盤補的 watchlist 名字（快取：面板載入約 1 分鐘）
cache = f"{S}/r9_gapfill.json"
if not os.path.exists(cache):
    os.environ["USE_SNAP"] = "0"
    import scan_r7
    pn = scan_r7.load(verbose=False)
    gf = pn[(pn.prio == 1) & (pn.date != "2026-09-22") & pn.symbol.isin(used)]
    json.dump({s_: sorted(str(x.date()) for x in g.date) for s_, g in gf.groupby("symbol")}, open(cache, "w"))
gapfill = json.load(open(cache))
gf_txt = "、".join(k + "（" + "、".join(x[5:] for x in v) + "）" for k, v in gapfill.items())
wl_y22 = len(used & set(y[y.date == "2026-09-22"].symbol))
sn22 = pd.read_csv(f"{SNAPD}/2026-09-22.csv"); sn22s = set(sn22.symbol.astype(str).str.upper().str.strip())
wl_hole = len(used - set(y[y.date == "2026-09-22"].symbol))
wl_hole_nas = len((used - set(y[y.date == "2026-09-22"].symbol)) & sn22s)

data = (f"本版資料：再次觸發三個 repo 的 GitHub Actions（fetch_yahoo_eod ×3、fetch_eod_snapshot）抓到 09-25 01:3x UTC（美東 09-24 收盤後約 5.5 小時）。"
        f"Yahoo 這次出齊了 09-23（{cov.get('2026-09-23', 0):,} 檔）與 09-24（{cov.get('2026-09-24', 0):,} 檔）的完整日線，"
        f"六項條件的基準推進到 {BASE} 官方收盤（完整 OHLC）。"
        f"09-22 則成了永久缺口：Yahoo 始終只出了 {cov.get('2026-09-22', 0):,} 檔（完整交易日約 {full_n:,} 檔；chat 1 的 R21 也記錄了同一個缺口）。"
        f"整天丟掉會讓 09-21 直接接 09-23、指標錯位，所以 09-22 用 10MA repo 的 Nasdaq 官方收盤快照補成「只有收盤」的一根（O=H=L=C）；"
        f"掃描的 {len(b)} 檔中 {wl_y22} 檔 09-22 有 Yahoo 完整日線照用，其餘 {wl_hole} 檔用 Nasdaq 收盤（{wl_hole_nas} 檔在快照內）。"
        + (f"完整交易日上 Yahoo 個別缺漏的名字也用當日 Nasdaq 收盤補：{gf_txt}。" if gapfill else "")
        + "這根只有收盤的 K 棒沒有盤中高低：ATR14 略過它的真實波幅（沿用前一日的值，不會被偏低的 TR 拉低，但也少了 09-22 的真實波幅），"
          "60 日報酬標準差照常計入 09-22 的收盤，重心線在這一根用收盤代替 hlc3。"
        + (f"注意：10MA repo 的「2026-09-24」Nasdaq 快照與 09-23 的快照 {same24:.0%} 逐檔相同，價格等於 09-23 收盤，是過期資料；"
           "載入器已偵測並略過它（09-24 一律用 Yahoo 日線）。" if stale24 else "")
        + "兩個來源重疊的收盤逐檔比對：" + "、".join(f"{k[5:]} {v[0]:,} 檔最大差 {v[1]:.3f}%" for k, v in chk.items())
        + f"，差 >0.05% 合計 {sum(v[2] for v in chk.values())} 檔。")

warn = b[b.data_warn.fillna("") != ""]
panel = (f"面板：三個鏡像合併 {os.environ.get('PANEL_N', '?')} 檔（10MA repo 自 09-24 起把抓取清單擴大為所有 ≥$1 的普通股，面板比 r8 的 3,097 檔大），"
         f"同一檔同一天多份資料時取抓取窗口較新的檔。{int((b.date == BASE).sum())} / {len(b)} 檔最後一根落在 {BASE[5:]}"
         + (f"；{'、'.join(f'{r.ticker}（停在 {r.date[5:]}：Yahoo 沒有它的 {BASE[5:]} 日線，當天的 Nasdaq 快照又是過期的，表中標「舊」）' for r in b[b.date < BASE].itertuples())}" if (b.date < BASE).any() else "")
         + "。"
         + (f"資料警示：{'、'.join(f'{r.ticker}（{r.data_warn}）' for r in warn.itertuples())}，指標值不可信。" if len(warn) else ""))

# ── 來源範圍 ──
u9 = set().union(*map(set, tk.values())); u8 = set().union(*map(set, tk8.values()))
only20 = sorted(u8 - u9)
scope = (f"掃描 {len(u9)} 檔 = 五份成品去重："
         + "、".join(f"{k} {len(v)}" for k, v in tk.items())
         + f"。chat 1 的最新成品已由 10MA R20 換成 R21 動能回調（R21 起取代 R20 的篩選），所以 R20 不再列入："
         f"只在 R20 上的 {len(only20)} 檔不再列入 watchlist 掃描；其中 {len(set(only20) & set(u.ticker))} 檔流動性達標、仍在加掃範圍內"
         f"（加掃六項全中 {int(u[u.ticker.isin(only20)].score.eq(6).sum())} 檔，完整分數見 _加掃.csv）。新加入 R21 總表與差一項共 {len(u9 - u8)} 檔。"
         f"{len(b)} 檔全部掃到，0 檔缺資料。")

# ── 與 r8 對照 ──
s8 = set(p8[p8.score == 6].ticker); s9 = set(b[b.score == 6].ticker)
fix = (f"r9 的變動：(1) chat 1 改用 R21（{mp['meta']['last_date']} 收盤，總表 {len(mp['rows'])} 檔，差一項 {len(mp['near_miss'])} 檔只掃描不算命中）。"
       f"(2) 載入器新增兩條補值規則：最後完整日之前、OHLC 覆蓋不到一半的「缺口日」（本版只有 09-22），以及完整交易日上個別名字的缺漏，"
       f"若有 Nasdaq 收盤快照就補成只有收盤的一根；只補該日之前 7 天內有 Yahoo 日線的名字，避免把已下市、代號被重用的公司接上舊序列。"
       f"另外，快照若與前一份快照逐檔相同就判定為過期、不使用。"
       f"(3) 六項基準由 r8 的 09-21 推進到 {BASE[5:]}，最新一日是完整 OHLC，所以不再需要「收盤快照更新」分頁，改附「與 r8 對照」："
       f"r8 六項全中 {len(s8)} 檔 → 本版 {len(s9)} 檔，延續 {len(s8 & s9)}、新進 {len(s9 - s8)}、退出 {len(s8 - s9)}"
       + (f"（其中 {'、'.join(sorted((s8 - s9) - set(b.ticker)))} 只在 R20 上，本版已不在來源榜單）" if (s8 - s9) - set(b.ticker) else "") + "。")
off = u[(u.score == 6) & (~u.ticker.isin(set(b.ticker)))]
html = ("r9：條件與 r3–r8 相同。" + data + " " + panel + "<br>" + scope + "<br>" + fix)
rm = b[b.ticker != b.symbol_used]
_cnt = {}
if len(rm):
    import scan_r7 as _s7
    _pn = _s7.load(verbose=False) if "pn" not in globals() else pn
    _cnt = _pn.groupby("symbol").size().to_dict()
remap = (f"{len(rm)} 檔重對應：" + "、".join(f"{r.ticker}→{r.symbol_used}（{_cnt.get(r.symbol_used, '?')} 根"
                                            + (f"，{r.ticker} {_cnt[r.ticker]} 根" if r.ticker in _cnt else "") + "）" for r in rm.itertuples())
         if len(rm) else "0 檔重對應")
mk = mp["meta"]["universe"]
mkt = (f"這不是全市場：chat 1 的 R21 漏斗（{mp['meta']['last_date']}）美股可報價普通股 {mk['yahoo_current']:,} 檔、"
       f"通過流動性等門檻的合資格股 {mk['liq']:,} 檔。")
env = {"REMAP_NOTE": remap, "MKT_NOTE": mkt, "DATA_NOTE": data, "PANEL_NOTE": panel, "FIX_NOTE": fix, "SCOPE_NOTE": scope, "HTML_NOTE": html}
with open(f"{S}/notes_r9.env", "w") as f:
    for k, v in env.items():
        f.write(f"export {k}={shlex.quote(v)}\n")          # shlex：避免 bash 把 $1、$2 當變數展開

# ── 來源分頁 ──
src = pd.read_csv(f"{S}/src_rows_r8.csv")
src = src[src.Session != "價格資料"]
i1 = src.index[src.Session.str.startswith("chat 1")][0]
src.loc[i1, ["Repo / 取得方式", "最新成品", "成品基準日", "取用檔數"]] = [
    "10MA-watchlist（branch claude/20ma-uptrend-watchlist-pages-pa7hmf，commit 75dce35；R21 起改為高動能回到 20MA）",
    "reports/20MA_momentum_pullback_watchlistGit_R21.00_claudeopus55xhigh_09.25_0034.xlsx（數值取自 data/screen_mp21.json）",
    mp["meta"]["last_date"], f"{len(mp['rows'])}（+ 差一項 {len(mp['near_miss'])} 只掃描）"]
src.loc[src.Session == "五份成品去重", "取用檔數"] = str(len(u9))
src.loc[src.Session == "加掃", ["Repo / 取得方式", "最新成品", "成品基準日", "取用檔數"]] = [
    f"三個 repo 的 Yahoo 鏡像併集 {os.environ.get('PANEL_N', '?')} 檔",
    f"收盤 ≥ $2、20 日 (收盤×量) 平均 ≥ 300 萬美元、歷史 ≥ 80 根、最後一根在 {BASE[5:]}、同證券不同寫法只留一個", BASE, str(len(u))]
_irh = src.index[src["最新成品"].astype(str).str.contains("RateHike")]
if len(_irh):
    src.loc[_irh[0], "取用檔數"] = (f"受惠 {len(tk['RateHike_R2_受惠'])} / 迴避 {len(tk['RateHike_R2_迴避'])}"
                                   + (f" / 索引另加 {len(tk['RateHike_R2_索引'])}" if tk.get("RateHike_R2_索引") else ""))
src.loc[len(src)] = ["價格資料", "三個 repo 的 fetch_yahoo_eod（09-25 01:3x UTC）＋ 10MA fetch_eod_snapshot（09-22 缺口補收盤）",
                     f"完整 OHLC 至 {BASE}；09-22 為缺口日，Yahoo 沒有的名字用 Nasdaq 官方收盤", BASE, os.environ.get("PANEL_N", "?")]
src.to_csv(f"{S}/src_rows_r9.csv", index=False, encoding="utf-8-sig")
print(json.dumps({"stale24": stale24, "same24": same24, "cov": cov, "chk": chk, "wl_y22": wl_y22, "wl_hole": wl_hole, "wl_hole_nas": wl_hole_nas, "only20": len(only20),
                  "six8": len(s8), "six9": len(s9), "keep": sorted(s8 & s9), "new": sorted(s9 - s8), "out": sorted(s8 - s9),
                  "uni": len(u), "u6": int((u.score == 6).sum()), "off": len(off), "warn": warn.ticker.tolist()}, ensure_ascii=False))
