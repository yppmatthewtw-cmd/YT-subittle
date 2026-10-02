# -*- coding: utf-8 -*-
"""r10 的版本敘述：寫成 env 檔給 csv_to_xlsx.py / build_r7_scan_html.py 讀。所有數字由資料算出。"""
import os, sys, json, shlex, glob
import pandas as pd

S = "/tmp/claude-0/-home-user-YT-subittle/0bd65ef0-0bef-5829-9a6f-f0a46d2d96cd/scratchpad"
SNAPD = "/home/user/yppmatthewtw-cmd/10ma-watchlist/data/snapshots"
MPJ = "/home/user/yppmatthewtw-cmd/10ma-watchlist/data/screen_hm23.json"
sys.path.insert(0, S)
from scan_r7 import _files

b = pd.read_csv(f"{S}/base_r10.csv"); u = pd.read_csv(f"{S}/universe_r10.csv")
p9 = pd.read_csv(f"{S}/r9keep/base_r9.csv")
tk = json.load(open(f"{S}/scan_tickers.json")); tk9 = json.load(open(f"{S}/scan_tickers_r9.json"))
mp = json.load(open(MPJ))
BASE = b.date.max()
PANEL_N = os.environ.get("PANEL_N", "?")

# ── 各日 Yahoo 官方日線覆蓋（與 load() 同一組檔案；tail / intraday / 盤中路線不算）──
fr = []
for f in _files():
    bn = os.path.basename(f)
    if "tail" in bn or "intraday" in bn:
        continue
    d = pd.read_csv(f)
    if "route" in d.columns:
        d = d[~d.route.astype(str).str.contains("hourly|intraday|quote", case=False, na=False)]
    fr.append(d[d.date >= "2026-09-14"][["symbol", "date", "close"]])
y = pd.concat(fr).dropna(subset=["close"])
y["symbol"] = y.symbol.astype(str).str.upper().str.strip()
y = y.sort_values("date").drop_duplicates(["symbol", "date"], keep="last")
cov = y.groupby("date").symbol.nunique().to_dict()
full_n = max(cov.values())
ycl = {dd: g.set_index("symbol").close for dd, g in y.groupby("date")}

# ── 快照日期稽核（獨立於 load() 再算一次）：每份快照與哪一天的 Yahoo 收盤吻合 ──
audit = {}
for f in sorted(glob.glob(f"{SNAPD}/*.csv")):
    lab = os.path.basename(f)[:-4]
    if lab < "2026-09-14":
        continue
    sn = pd.read_csv(f, usecols=["symbol", "lastsale"])
    px = pd.Series(pd.to_numeric(sn.lastsale.astype(str).str.replace(r"[$,]", "", regex=True), errors="coerce").values,
                   index=sn.symbol.astype(str).str.upper().str.strip())
    px = px[~px.index.duplicated()]
    best, bestf = None, 0.0
    for dd, yc in ycl.items():
        if not (pd.Timestamp(lab) - pd.Timedelta(days=7) <= pd.Timestamp(dd) <= pd.Timestamp(lab)):
            continue
        c = px.index.intersection(yc.index)
        if len(c) < 200:
            continue
        fr_ = float(((px[c] / yc[c] - 1).abs() < 5e-4).mean())
        if fr_ > bestf:
            best, bestf = dd, fr_
    audit[lab] = (best, bestf)
mislab = {k: v for k, v in audit.items() if v[0] is not None and v[1] >= 0.9 and v[0] != k}
mis_txt = "、".join(f"{k[5:]}.csv 實為 {v[0][5:]} 收盤（{v[1]:.0%} 吻合）" for k, v in mislab.items())

used = set(b.symbol_used)
# 以 Nasdaq 收盤補值、落在 watchlist 名字上的日子（快取：面板載入約 1–2 分鐘）
cache = f"{S}/r10_gapfill.json"
if not os.path.exists(cache):
    os.environ["USE_SNAP"] = "0"
    import scan_r7
    pn = scan_r7.load(verbose=False)
    gf = pn[(pn.prio == 1) & pn.symbol.isin(used)]
    _p0 = pn[pn.prio == 0].sort_values(["symbol", "date"])
    _p0 = _p0.assign(v20=_p0.groupby("symbol").volume.transform(lambda v: v.shift(1).rolling(20, min_periods=10).median()))
    _last = _p0[_p0.date == pn.date.max()]
    vr = float((_last.volume / _last.v20).median())
    nfix_last = int(sum(1 for s_, ds in scan_r7.OHLC_FIX.items() if pn.date.max() in ds))
    nlast = int((pn.date == pn.date.max()).sum())
    json.dump({"fills": {s_: sorted(str(x.date()) for x in g.date) for s_, g in gf.groupby("symbol")},
               "stale": scan_r7.STALE_SNAPS, "relabel": scan_r7.SNAP_RELABEL,
               "counts": pn.groupby("symbol").size().to_dict(), "vr": vr, "nfix_last": nfix_last, "nlast": nlast,
               "wl_fix": sorted(s_ for s_ in used if pn.date.max() in scan_r7.OHLC_FIX.get(s_, ()))}, open(cache, "w"))
gc = json.load(open(cache))
gapfill = gc["fills"]
gf_txt = "、".join(k + "（" + "、".join(x[5:] for x in v) + "）" for k, v in gapfill.items())

days = [d_ for d_ in sorted(cov) if d_ >= "2026-09-22"]
# 00:07–00:12 UTC 的重抓：Yahoo 在整理期間把 10-01 撤回，與面板使用的前一次抓取比較
refetch, _cmp = {}, []
FIRST = {"vcp-watchlist": "4705389", "10ma-watchlist": "663f926", "20mawarchlist": "12fb28f"}
NAME = {"vcp-watchlist": "VCP", "10ma-watchlist": "10MA", "20mawarchlist": "20MA"}
for repo, f, pre in (("vcp-watchlist", "eod_2025-09-01_2026-10-02.csv.gz", "eod2/vcp_"),
                     ("10ma-watchlist", "eod_2025-12-26_2026-10-02.csv.gz", "eod/10ma_"),
                     ("20mawarchlist", "eod_2025-09-01_2026-10-02.csv.gz", "eod/20ma_")):
    try:
        nw = pd.read_csv(f"/home/user/{repo}/data/yahoo/{f}"); od = pd.read_csv(f"{S}/{pre}{f}")
        m_ = od[od.date == BASE].merge(nw[nw.date == BASE], on="symbol", suffixes=("_o", "_n"))
        refetch[repo] = (int((od.date == BASE).sum()), int((nw.date == BASE).sum()))
        _cmp.append(m_)
    except Exception:
        pass
_m = pd.concat(_cmp) if _cmp else pd.DataFrame(columns=["symbol"])
_rc = _m.assign(cchg=((_m.close_n / _m.close_o - 1).abs() > 1e-4) if len(_m) else False,
                rchg=(((_m.high_n - _m.low_n) / (_m.high_o - _m.low_o) - 1).abs() > 0.005) if len(_m) else False)
rf_n = _m.symbol.nunique() if len(_m) else 0
rf_c = sorted(set(_rc.symbol[_rc.cchg])) if len(_m) else []
rf_r = sorted(set(_rc.symbol[_rc.rchg])) if len(_m) else []
data = (f"本版資料：再次觸發三個 repo 的 GitHub Actions（fetch_yahoo_eod ×3、fetch_eod_snapshot）抓到 10-01 23:18–23:23 UTC（美東 10-01 收盤後約 3.3 小時）。"
        f"Yahoo 這次給了 09-25 到 10-01 每一天的日線，連 r9 時的 09-22 缺口也已回補："
        + "、".join(f"{d_[5:]} {cov[d_]:,}" for d_ in days)
        + f" 檔（完整交易日約 {full_n:,} 檔）。六項條件的基準推進到 {BASE} 官方收盤。"
        f"{BASE[5:]} 的收盤與成交量已是收盤後的完整值（各檔當日成交量 ÷ 自身前 20 日中位數，再取中位數 = {gc['vr']:.2f}）；"
        f"但高低價仍是 Yahoo 的暫定值：{gc['nlast']:,} 根中有 {gc['nfix_last']} 根的開盤或收盤落在高低區間外（之前幾次剛收盤就抓的最後一根也是如此，"
        "下一次抓取時約一半名字的振幅會被修正、收盤幾乎不動）。載入器把這些 K 棒的高低價放寬到至少包住開與收"
        + (f"，watchlist 中受影響的 {len(gc['wl_fix'])} 檔在「資料警示」欄註明" if gc["wl_fix"] else "")
        + "；②（波動指數斜率）與 ⑥ 用到最後一根的真實波幅，修訂後可能變動。"
        + (("10-02 00:07–00:12 UTC 再抓一次想取得定案的高低價，結果 Yahoo 在整理期間把 10-01 撤回："
            + "、".join(f"{NAME[k]} 鏡像 {v[0]:,} → {v[1]:,} 檔" for k, v in refetch.items())
            + f"；仍有 10-01 的 {rf_n} 個名字中，收盤變動 {len(rf_c)} 檔{('（' + '、'.join(rf_c) + '）') if rf_c else ''}、"
            f"振幅變動 >0.5% 的 {len(rf_r)} 檔{('（' + '、'.join(rf_r) + '）') if rf_r else ''}。所以本版沿用第一次的完整抓取（"
            + "、".join(f"{k} commit {FIRST[k]}" for k in refetch)
            + f"），{len(refetch)} 個 repo 目前同名檔案都已被重抓覆蓋、只剩少數名字的 10-01。")
           if refetch else "")
        + (f"10MA repo 的 Nasdaq 快照有標錯日期的情形：{mis_txt}；載入器逐份與 Yahoo 官方收盤比對後已改標或略過，所以 10-01 沒有可用的 Nasdaq 快照，"
           "10-01 的收盤只有 Yahoo 一個來源。" if mislab else "")
        + (f"Yahoo 個別缺漏、以當日 Nasdaq 收盤補成只有收盤的一根：{gf_txt}。" if gapfill else "Watchlist 名字沒有任何一天需要用 Nasdaq 收盤補。"))

warn = b[b.data_warn.fillna("") != ""]
stale_rows = b[b.date < BASE]
_grp = {}
for r in warn.itertuples():
    for part in str(r.data_warn).split("；"):
        key = part.split("（")[0] if part.endswith("已放寬校正）") else part
        _grp.setdefault(key, []).append(r.ticker)
warn_txt = "；".join(f"{k}{'（開/收落在高低區間外，已放寬校正）' if k.endswith('暫定值') else ''}：{'、'.join(v)}" for k, v in _grp.items())
panel = (f"面板：三個鏡像合併 {PANEL_N} 檔，同一檔同一天多份資料時取抓取窗口較新的檔；60 分鐘線彙總成的 intraday 檔不是官方收盤，只作墊底。"
         f"{int((b.date == BASE).sum())} / {len(b)} 檔最後一根落在 {BASE[5:]}"
         + (f"；{'、'.join(f'{r.ticker}（停在 {r.date[5:]}：Yahoo 沒有它的 {BASE[5:]} 日線，{BASE[5:]} 又沒有日期正確的 Nasdaq 快照可補，表中標「舊」）' for r in stale_rows.itertuples())}" if len(stale_rows) else "")
         + "。"
         + (f"資料警示（{len(warn)} 檔，按內容分組）：{warn_txt}。" if len(warn) else ""))

# ── 來源範圍 ──
u10 = set().union(*map(set, tk.values())); u9 = set().union(*map(set, tk9.values()))
gone = sorted(u9 - u10); new_ = sorted(u10 - u9)
t1 = [r["sym"] for r in mp["rows"] if int(r["tier"]) == 1]
scope = (f"掃描 {len(u10)} 檔 = 五份成品去重："
         + "、".join(f"{k} {len(v)}" for k, v in tk.items())
         + f"。chat 1 的最新成品已由 R21 動能回調換成 R23 熱錢回落 20MA（09-29 的 R22 是 R21 規則的重掃，10-01 的 R23 改用新準則），"
         f"所以只在 R21 上的 {len(gone)} 檔不再列入 watchlist 掃描（其中 {len(set(gone) & set(u.ticker))} 檔流動性達標、仍在加掃範圍內，"
         f"加掃六項全中 {int(u[u.ticker.isin(gone)].score.eq(6).sum())} 檔）；新加入 R23 各層名單共 {len(new_)} 檔。"
         f"{len(b)} 檔全部掃到，0 檔缺資料。")

# ── 與 r9 對照 ──
s9 = set(p9[p9.score == 6].ticker); s10 = set(b[b.score == 6].ticker)
out_gone = sorted((s9 - s10) - set(b.ticker))
fix = (f"r10 的變動：(1) chat 1 改用 R23（{mp['meta']['last_date']} 收盤）：第一梯隊 {len(t1)} 檔（{'、'.join(t1)}）算命中；"
       f"第二梯隊 {len(mp['rows']) - len(t1)}、差一項 {len(mp['near_miss'])}、熱錢板塊 {len(mp['hot'])} 檔只掃描、不算命中"
       f"（三份名單互有重疊；來源榜單標籤依 第一梯隊 > 第二梯隊 > 差一項 > 熱錢板塊 去重，所以標籤數是 "
       f"{len(tk.get('HM_R23_第二梯隊', []))} / {len(tk.get('HM_R23_差一項', []))} / {len(tk.get('HM_R23_熱錢板塊', []))}）。"
       f"(1b) 加息 R2 受惠名單補回 Agilent（A）：之前從工作簿抽代號時把單字母代號漏掉，受惠名單一直是 19 檔，實際是 20 檔（r5 起的來源榜單標籤、r6 起的 chat 命中都受影響）。"
       "(2) 載入器新增快照日期稽核：每份 Nasdaq 快照先和 Yahoo 官方收盤逐檔比對，吻合更早日子的改標、和任何一天都對不上的不使用。"
       "(3) chat 1 repo 新增的 intraday_*_60m 檔（60 分鐘線彙總）列為最低優先，不會蓋掉官方日線。"
       f"(4) 六項基準由 r9 的 09-24 推進到 {BASE[5:]}，附「與 r9 對照」：r9 六項全中 {len(s9)} 檔 → 本版 {len(s10)} 檔，"
       f"延續 {len(s9 & s10)}、新進 {len(s10 - s9)}、退出 {len(s9 - s10)}"
       + (f"（其中 {'、'.join(out_gone)} 已不在來源榜單）" if out_gone else "") + "。")
html = ("r10：條件與 r3–r9 相同。" + data + " " + panel + "<br>" + scope + "<br>" + fix)

rm = b[b.ticker != b.symbol_used]
_cnt = gc["counts"]
remap = (f"{len(rm)} 檔重對應：" + "、".join(f"{r.ticker}→{r.symbol_used}（{_cnt.get(r.symbol_used, '?')} 根"
                                            + (f"，{r.ticker} {_cnt[r.ticker]} 根" if r.ticker in _cnt else "") + "）" for r in rm.itertuples())
         if len(rm) else "0 檔重對應")
mk = mp["meta"]["universe"]
mkt = (f"這不是全市場：chat 1 的 R23 漏斗（{mp['meta']['last_date']}）美股可報價普通股 {mk['yahoo_current']:,} 檔、"
       f"通過流動性等門檻的合資格股 {mk['liq']:,} 檔。")
env = {"BASIS_NOTE": f"Yahoo 日線 OHLC；{BASE[5:]} 收盤與成交量為定值、高低價為 Yahoo 暫定值", "REMAP_NOTE": remap, "MKT_NOTE": mkt, "DATA_NOTE": data, "PANEL_NOTE": panel, "FIX_NOTE": fix, "SCOPE_NOTE": scope, "HTML_NOTE": html}
with open(f"{S}/notes_r10.env", "w") as f:
    for k, v in env.items():
        f.write(f"export {k}={shlex.quote(v)}\n")          # shlex：避免 bash 把 $1、$2 當變數展開

# ── 來源分頁 ──
_others = set().union(*[set(v) for k, v in tk.items() if not k.startswith("HM_R23")])
r23_extra_new = (set(tk.get("HM_R23_第二梯隊", [])) | set(tk.get("HM_R23_差一項", [])) | set(tk.get("HM_R23_熱錢板塊", []))) - _others - set(t1)
src = pd.read_csv(f"{S}/src_rows_r9.csv")
src = src[src.Session != "價格資料"]
i1 = src.index[src.Session.str.startswith("chat 1")][0]
src.loc[i1, ["Repo / 取得方式", "最新成品", "成品基準日", "取用檔數"]] = [
    "10MA-watchlist（branch claude/20ma-uptrend-watchlist-pages-pa7hmf，commit 84356ad；R23 起改為熱錢回落 20MA）",
    "reports/10MA_watchlistGit_R23.00_claudefable51xhigh_10.01_1724.xlsx（數值取自 data/screen_hm23.json）",
    mp["meta"]["last_date"],
    f"第一梯隊 {len(t1)}（+ 第二梯隊 {len(mp['rows']) - len(t1)}、差一項 {len(mp['near_miss'])}、熱錢板塊 {len(mp['hot'])} 只掃描；"
    f"標籤去重後 {len(tk.get('HM_R23_第二梯隊', [])) + len(tk.get('HM_R23_差一項', [])) + len(tk.get('HM_R23_熱錢板塊', []))} 檔，"
    f"其中 {len(r23_extra_new)} 檔不在其他成品內、是新增掃描）"]
src.loc[src.Session == "五份成品去重", "取用檔數"] = str(len(u10))
i2 = src.index[src.Session.str.startswith("chat 2")][0]
src.loc[i2, "Repo / 取得方式"] = "VCP-watchlist（branch claude/vcp-watch-list-z9z66i；R22 = commit 426f365，之後只有資料 commit）"
src.loc[src.Session == "加掃", ["Repo / 取得方式", "最新成品", "成品基準日", "取用檔數"]] = [
    f"三個 repo 的 Yahoo 鏡像併集 {PANEL_N} 檔",
    f"收盤 ≥ $2、20 日 (收盤×量) 平均 ≥ 300 萬美元、歷史 ≥ 80 根、最後一根在 {BASE[5:]}、同證券不同寫法只留一個", BASE, str(len(u))]
_irh = src.index[src["最新成品"].astype(str).str.contains("RateHike")]
if len(_irh):
    src.loc[_irh[0], "取用檔數"] = (f"受惠 {len(tk['RateHike_R2_受惠'])} / 迴避 {len(tk['RateHike_R2_迴避'])}"
                                   + (f" / 索引另加 {len(tk['RateHike_R2_索引'])}" if tk.get("RateHike_R2_索引") else ""))
src.loc[len(src)] = ["價格資料", "三個 repo 的 fetch_yahoo_eod（10-01 23:18–23:23 UTC）＋ 10MA fetch_eod_snapshot（逐份與 Yahoo 收盤核對日期）",
                     f"Yahoo 日線 OHLC 至 {BASE}（{BASE[5:]} 收盤與量為定值、高低價為暫定值；09-22 已由 Yahoo 回補）", BASE, PANEL_N]
src.to_csv(f"{S}/src_rows_r10.csv", index=False, encoding="utf-8-sig")
print(json.dumps({"cov": {k: v for k, v in cov.items() if k >= "2026-09-22"}, "audit": audit, "loader_stale": gc["stale"], "loader_relabel": gc["relabel"],
                  "gapfill": gapfill, "gone": len(gone), "new": len(new_), "six9": len(s9), "six10": len(s10),
                  "keep": sorted(s9 & s10), "newin": sorted(s10 - s9), "out": sorted(s9 - s10),
                  "uni": len(u), "u6": int((u.score == 6).sum()), "warn": warn.ticker.tolist(), "stale": stale_rows.ticker.tolist()}, ensure_ascii=False))
