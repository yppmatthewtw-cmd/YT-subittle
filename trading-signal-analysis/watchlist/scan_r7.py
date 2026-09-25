# -*- coding: utf-8 -*-
"""
R7 A–G 六條件掃描（日線）— 以 Python 重現 r7a/b/c/e/g 的預設參數計算。
資料：三個 watchlist repo 的 Yahoo 日線鏡像合併面板
      vcp-watchlist / 10ma-watchlist / 20mawarchlist 的 data/yahoo/*.csv.gz 全部併入，
      同一 symbol×date 以「官方 EOD 檔」優先，tail/hourly 盤中快照最後（且預設整天丟棄）。
"""
import re, json, glob, math, sys, os
import numpy as np, pandas as pd

S = "/tmp/claude-0/-home-user-YT-subittle/0bd65ef0-0bef-5829-9a6f-f0a46d2d96cd/scratchpad"
EOD_DIRS = [f"{S}/eod2", f"{S}/eod"]          # 依序搜尋，找到第一個有檔案的就用
# Nasdaq screener 收盤快照（只有收盤價與成交量，沒有盤中高低）。OHLC 鏡像還沒補到的交易日用它補。
SNAP_DIR = os.environ.get("SNAP_DIR", "/home/user/yppmatthewtw-cmd/10ma-watchlist/data/snapshots")
USE_SNAP = os.environ.get("USE_SNAP", "1") != "0"
NEAR_ATR = 1.0          # criteria 6：|close − line| ≤ 1.0 × ATR14 算「附近」
NEAR_PCT = 3.0          # 或 ≤ 3%（兩者取其一即可）
VOL_MIN = 75.0          # criteria 3：R7-H 波動指數 ≥ 75
VA, VB = -3.381, 1.892  # R7-H 校準係數（20 日 ≥10% 回撤）

# ───────────────────────── Pine 等價工具 ─────────────────────────
# Pine 的 ta.ema / ta.rma 都以「前 n 根的 SMA」作種子，種子形成前回傳 na。
# pandas 的 ewm 從第 0 根就有值 → 暖機段會有假訊號，所以這裡自己實作。
def _seeded(x, n, k, k1):
    v = np.asarray(x, dtype=float)
    out = np.full(len(v), np.nan)
    if len(v) < n or np.isnan(v[:n]).any():
        # 前面可能有 na（例如 MACD 線本身），從第一個連續 n 個非 na 開始
        ok = np.where(np.isfinite(v))[0]
        if len(ok) < n:
            return out
        st = ok[0]
    else:
        st = 0
    seed = v[st:st + n]
    if np.isnan(seed).any():
        return out
    out[st + n - 1] = seed.mean()
    for i in range(st + n, len(v)):
        out[i] = v[i] * k + out[i - 1] * k1 if np.isfinite(v[i]) else out[i - 1]
    return out


def pine_ema(x, n):
    k = 2.0 / (n + 1)
    return _seeded(x, n, k, 1 - k)


def pine_rma(x, n):
    k = 1.0 / n
    return _seeded(x, n, k, 1 - k)


def ema(s, n):  return pd.Series(pine_ema(np.asarray(s, dtype=float), n), index=getattr(s, "index", None))
def sma(s, n):  return s.rolling(n).mean()
def rma(s, n):  return pd.Series(pine_rma(np.asarray(s, dtype=float), n), index=getattr(s, "index", None))
def atr(df, n=14):
    """ta.atr = ta.rma(ta.tr, n)。
    只有收盤價的快照棒（O=H=L=C）沒有盤中高低，真實波幅會被系統性低估 → ATR 被壓低 →
    波動指數被抬高、斜率假性轉正。這種棒一律不更新 ATR（沿用前一根），而不是餵它一個偏低的 TR。"""
    tr = pd.concat([df.high - df.low, (df.high - df.close.shift()).abs(), (df.low - df.close.shift()).abs()], axis=1).max(axis=1)
    if "route" in df.columns:
        synth = df["route"].astype(str).eq("snapshot-close").values
    else:
        synth = ((df.high == df.low) & (df.low == df.close)).values
    tr = tr.mask(pd.Series(synth, index=tr.index))
    return rma(tr, n)

def pivot_high(x, L, R):
    """ta.pivothigh 等價：回傳在 bar i (確認 bar) 的 pivot 值 = x[i-R]，其他 NaN"""
    v = x.values; n = len(v); out = np.full(n, np.nan)
    for i in range(L + R, n):
        c = v[i - R]
        if np.isnan(c): continue
        win = v[i - R - L:i + 1]
        if c == np.nanmax(win) and (win[:L] < c).all() and (win[L + 1:] <= c).all():
            out[i] = c
    return out

def pivot_low(x, L, R):
    v = x.values; n = len(v); out = np.full(n, np.nan)
    for i in range(L + R, n):
        c = v[i - R]
        if np.isnan(c): continue
        win = v[i - R - L:i + 1]
        if c == np.nanmin(win) and (win[:L] > c).all() and (win[L + 1:] >= c).all():
            out[i] = c
    return out

def _jump_warn(df, n=60, lim=0.6, vmul=3.0):
    """最近 n 根內單日漲跌超過 lim（60%）、而且當天成交量沒有放大（< 前 20 根中位數的 vmul 倍）
    → 多半是未調整的分割／重組，不是真實行情，指標值不可信。
    真實的暴漲暴跌（例如 MRNA 08-19 +177%，量放大 46 倍）不標。"""
    r = df.close.pct_change()
    med = df.volume.shift(1).rolling(20, min_periods=5).median()
    sus = (r.abs() > lim) & ~(df.volume >= vmul * med)
    sus = sus.tail(n)
    if sus.any():
        k = r[sus[sus].index].abs().idxmax()
        return f"單日 {r[k] * 100:+.0f}%（{df.date[k].strftime('%m-%d')}）且量未放大，疑似未調整分割/重組"
    return ""

# ───────────────────────── R7-B MACD 時鐘 ─────────────────────────
def macd_clock(close, fast=12, slow=26, sig=9, lookN=8, defLen=12, drop_first_cycle=True):
    """r7b_macd_clock 的週期時鐘。
    ema() 已是 Pine 式（SMA 種子、種子前回 na），所以柱狀圖在前 (slow-1)+(sig-1) 根自然是 na，
    r7b 的 fl (翻轉偵測) 在那段期間不會記錄任何週期。若改用 pandas ewm，暖機段會在零軸上下亂穿、
    把假週期推進 ul/dl，污染平均週期長度 → 進度 → 指針角度。
    另外丟掉「第一段」：含第一根有效柱的那一段在視窗起點之前就開始了，長度被截斷。
    只丟這一段；另一方向的第一段是完整週期，要留著（TradingView 圖上載入長歷史，最近 lookN 段都是完整週期）。"""
    m = ema(close, fast) - ema(close, slow); s_ = ema(m, sig); h = (m - s_).values.astype(float)
    n = len(h); up = h >= 0
    valid = np.isfinite(h)
    cs = int(np.argmax(valid)) if valid.any() else 0
    ul = []; dl = []; seen_any = False
    theta = np.full(n, np.nan); prog = np.full(n, np.nan); elapsed = np.zeros(n, int)
    for i in range(n):
        if not valid[i]:
            continue
        if valid[i - 1] and up[i] != up[i - 1]:
            L = i - cs
            a = ul if up[i - 1] else dl
            first = not seen_any
            seen_any = True
            if not (drop_first_cycle and first):   # 第一段被視窗起點截斷，不算
                a.append(L)
                if len(a) > lookN: a.pop(0)
            cs = i
        el = i - cs + 1
        au = np.mean(ul) if ul else defLen
        ad = np.mean(dl) if dl else defLen
        exp_ = au if up[i] else ad
        p = min(el / exp_, 0.97)
        t = (270 + 180 * p) if up[i] else (90 + 180 * p)
        theta[i] = t - 360 if t >= 360 else t
        prog[i] = el / exp_; elapsed[i] = el
    return m.values, s_.values, h, up, theta, prog, elapsed


def clock_txt(theta):
    hrs = theta / 30.0
    hh = int(hrs) % 12; mm = int(round((hrs - int(hrs)) * 60))
    if mm == 60: hh = (hh + 1) % 12; mm = 0
    return f"{hh if hh else 12}:{mm:02d}"

# ───────────────────────── R7-C VCP 分數 ─────────────────────────
def vcp_score(df):
    c = df.close; v = df.volume
    n = len(c); idx = np.arange(n)
    hi52 = c.rolling(252).max(); lo52 = c.rolling(252).min()
    hiN = c.expanding().max(); loN = c.expanding().min()
    hiY = hi52.fillna(hiN); loY = lo52.fillna(loN)
    offHigh = (hiY - c) / hiY * 100
    aboveLow = np.where(loY > 0, (c - loY) / loY * 100, 0.0)
    ma50 = sma(c, 50); ma200 = sma(c, 200)
    has50 = ma50.notna(); has200 = ma200.notna()
    a50raw = has50 & (c > ma50)
    a200 = np.where(has200, c > ma200, np.where(has50, a50raw & (offHigh <= 25), (aboveLow >= 25) & (offHigh <= 20)))
    cross = np.where(has200, np.where(has50, ma50 > ma200, a200), a200)
    a50 = np.where(has50, a50raw, a200)
    trendOK = a50 & a200 & cross & (aboveLow >= 30) & (offHigh <= 25)
    c1 = np.where(idx >= 21, (c / c.shift(21) - 1) * 100, 0.0)
    c3 = np.where(idx >= 63, (c / c.shift(63) - 1) * 100, c1)
    c6 = np.where(idx >= 126, (c / c.shift(126) - 1) * 100, 0.0)
    c1y = np.where(idx >= 252, (c / c.shift(252) - 1) * 100, 0.0)
    rng = (c.rolling(21).max() / c.rolling(21).min() - 1) * 100
    tight = (np.abs(c1) <= 7) & (rng <= 12)
    extended = c1 > 15
    v50 = sma(v, 50); v10 = sma(v, 10)
    vr = np.where(v50 > 0, v10 / v50, 1.0)
    s = 10.0 * a200 + 10.0 * a50 + 5.0 * cross + 5.0 * (aboveLow >= 30)
    s = s + np.maximum(0, 15 * (1 - np.minimum(offHigh, 25) / 25)) + np.maximum(0, 15 * (1 - np.minimum(np.abs(c1), 15) / 15))
    s = s + np.minimum(10, np.maximum(0, c6) / 5) + np.minimum(10, np.maximum(0, c1y) / 10)
    s = s + np.where(vr < 0.95, 10.0, 0.0) + np.where((offHigh <= 5) & tight, 5.0, 0.0)
    s = np.minimum(s, 100.0)
    g = np.full(n, 3)
    g = np.where(extended, 4, g)
    g = np.where(~extended & trendOK & (offHigh <= 10) & tight, 0, g)
    g = np.where(~extended & ~(trendOK & (offHigh <= 10) & tight) & (offHigh <= 4) & (c1 > 8), 4, g)
    cond2 = ~extended & ~(trendOK & (offHigh <= 10) & tight) & ~((offHigh <= 4) & (c1 > 8))
    g = np.where(cond2 & trendOK & (offHigh <= 20) & (c3 > -5), 1, g)
    cond3 = cond2 & ~(trendOK & (offHigh <= 20) & (c3 > -5))
    g = np.where(cond3 & (a200 | (aboveLow >= 20)) & (offHigh <= 30) & (c1 > -10), 2, g)
    return pd.Series(s, index=c.index), g, vr

GRADE = {0: "A 待突破", 1: "B 上升結構", 2: "C 基底修復", 3: "D 趨勢弱", 4: "E 延伸"}

# ───────────────────────── R7-G Livermore 最低阻力線 ─────────────────────────
def livermore_line(df, lbL=3, lbR=2, brkPct=0.0, boxLen=10, rangeMult=2.5, mkRev=2.0, mkConf=1.0, atrLen=14):
    hi = df.high.values; lo = df.low.values; c = df.close.values; n = len(c)
    a = atr(df, atrLen).values
    ph = pivot_high(df.high, lbL, lbR); pl = pivot_low(df.low, lbL, lbR)
    ph1 = ph2 = pl1 = pl2 = np.nan
    structDir = 0; prevStruct = 0
    mk = 0; mkTrend = 0; colExt = np.nan; lastUT = lastDT = lastNR = lastNRe = np.nan
    lr = np.nan
    lrLine = np.full(n, np.nan); lrDirA = np.zeros(n, int); structA = np.zeros(n, int); mkA = np.zeros(n, int); mkTrA = np.zeros(n, int); inBoxA = np.zeros(n, bool)
    hiBox = pd.Series(hi).rolling(boxLen).max().values; loBox = pd.Series(lo).rolling(boxLen).min().values
    for i in range(n):
        if not np.isnan(ph[i]): ph2, ph1 = ph1, ph[i]
        if not np.isnan(pl[i]): pl2, pl1 = pl1, pl[i]
        hh = ph1 > ph2; lh = ph1 < ph2; hl = pl1 > pl2; ll = pl1 < pl2
        # crossover / crossunder（需前一根在另一側）
        lvU = ph1 * (1 + brkPct / 100) if not np.isnan(ph1) else np.nan
        lvD = pl1 * (1 - brkPct / 100) if not np.isnan(pl1) else np.nan
        brkUp = i > 0 and not np.isnan(lvU) and c[i] > lvU and c[i - 1] <= lvU
        brkDn = i > 0 and not np.isnan(lvD) and c[i] < lvD and c[i - 1] >= lvD
        prevStruct = structDir
        if hh and hl: structDir = 1
        elif lh and ll: structDir = -1
        if brkUp: structDir = 1
        if brkDn: structDir = -1
        # Market Key
        cc = c[i]
        revAmt = (colExt if not np.isnan(colExt) else cc) * mkRev / 100
        confAmt = cc * mkConf / 100
        if np.isnan(colExt):
            colExt = cc; mk = 1; mkTrend = 1
        elif mk == 1:
            if cc > colExt: colExt = cc
            elif cc <= colExt - revAmt: lastUT = colExt; mk = -2; colExt = cc
        elif mk == -1:
            if cc < colExt: colExt = cc
            elif cc >= colExt + revAmt: lastDT = colExt; mk = 2; colExt = cc
        elif mk == -2:
            if cc < colExt:
                colExt = cc
                if (not np.isnan(lastDT) and cc < lastDT) or (not np.isnan(lastNRe) and cc < lastNRe - confAmt):
                    mk = -1; mkTrend = -1
            elif cc >= colExt + revAmt:
                lastNRe = colExt; colExt = cc
                if not np.isnan(lastUT) and cc > lastUT: mk = 1; mkTrend = 1
                elif not np.isnan(lastNR) and cc < lastNR: mk = 3
                else: mk = 2
        elif mk == 2:
            if cc > colExt:
                colExt = cc
                if (not np.isnan(lastUT) and cc > lastUT) or (not np.isnan(lastNR) and cc > lastNR + confAmt):
                    mk = 1; mkTrend = 1
            elif cc <= colExt - revAmt:
                lastNR = colExt; colExt = cc
                if not np.isnan(lastDT) and cc < lastDT: mk = -1; mkTrend = -1
                elif not np.isnan(lastNRe) and cc > lastNRe: mk = -3
                else: mk = -2
        elif mk == 3:
            if cc > colExt:
                colExt = cc
                if not np.isnan(lastUT) and cc > lastUT: mk = 1; mkTrend = 1
                elif not np.isnan(lastNR) and cc > lastNR: mk = 2
            elif cc <= colExt - revAmt:
                colExt = cc; mk = -2 if (not np.isnan(lastNRe) and cc < lastNRe) else -3
        elif mk == -3:
            if cc < colExt:
                colExt = cc
                if not np.isnan(lastDT) and cc < lastDT: mk = -1; mkTrend = -1
                elif not np.isnan(lastNRe) and cc < lastNRe: mk = -2
            elif cc >= colExt + revAmt:
                colExt = cc; mk = 2 if (not np.isnan(lastNR) and cc > lastNR) else 3
        inBox = (not np.isnan(hiBox[i]) and not np.isnan(a[i]) and (hiBox[i] - loBox[i]) < a[i] * rangeMult and not brkUp and not brkDn)
        # 線
        upC1 = pl1 if (not np.isnan(pl1) and pl1 < cc) else np.nan
        upC2 = lastNRe if (not np.isnan(lastNRe) and lastNRe < cc) else np.nan
        upCand = upC2 if np.isnan(upC1) else (upC1 if np.isnan(upC2) else max(upC1, upC2))
        dnC1 = ph1 if (not np.isnan(ph1) and ph1 > cc) else np.nan
        dnC2 = lastNR if (not np.isnan(lastNR) and lastNR > cc) else np.nan
        dnCand = dnC2 if np.isnan(dnC1) else (dnC1 if np.isnan(dnC2) else min(dnC1, dnC2))
        if structDir == 1:
            lr = upCand if (prevStruct != 1 or np.isnan(lr)) else (lr if np.isnan(upCand) else max(lr, upCand))
        elif structDir == -1:
            lr = dnCand if (prevStruct != -1 or np.isnan(lr)) else (lr if np.isnan(dnCand) else min(lr, dnCand))
        lrLine[i] = lr; structA[i] = structDir; mkA[i] = mk; mkTrA[i] = mkTrend; inBoxA[i] = inBox
        lrDirA[i] = 0 if inBox else (1 if (structDir == 1 and mkTrend == 1) else (-1 if (structDir == -1 and mkTrend == -1) else 0))
    return lrLine, lrDirA, structA, mkA, mkTrA, inBoxA

MK = {1: "UT", 2: "自然反彈", 3: "次級反彈", -1: "DT", -2: "自然回檔", -3: "次級回檔", 0: "—"}

# ───────────────────────── R7-H 波動指數 ─────────────────────────
def vol_index(df, atrLen=14, sdLen=60, wAtr=0.5, a=VA, b=VB):
    """r7h_volidx 等價：volD = ½ ATR14/close% + ½ 60 日對數報酬 stdev%；指數 = 100 × (1 − logistic(a + b·ln volD))"""
    c = df.close
    atrP = atr(df, atrLen) / c * 100
    lr = np.log(c / c.shift())
    sdP = lr.rolling(sdLen).std(ddof=0) * 100          # Pine ta.stdev 預設 biased=true → 母體標準差（除以 N）
    volD = wAtr * atrP + (1 - wAtr) * sdP
    # Pine: volD > 0 ? logistic : na（完全停牌/零波動的標的回 na，不會被當成 100 分）
    pos = volD.where(volD > 0)
    p = 1 / (1 + np.exp(-(a + b * np.log(pos))))
    return 100 * (1 - p), atrP, sdP, volD

# ───────────────────────── 主掃描 ─────────────────────────
def _files():
    """三個鏡像目錄全部讀，不是只讀第一個有檔案的。
    同名檔（同一份鏡像被複製到兩個目錄）只取一次；同一 symbol×date 的重複由 load() 依 prio 去重。"""
    seen, out = set(), []
    for d in EOD_DIRS:
        for f in sorted(glob.glob(f"{d}/*.csv.gz")):
            b = os.path.basename(f)
            if b in seen:
                continue
            seen.add(b)
            out.append(f)
    if not out:
        raise SystemExit("找不到日線鏡像 csv.gz")
    return out


STALE_SNAPS = []   # load() 判定為過期、未使用的快照日期


def load(verbose=True):
    """合併所有鏡像檔；同一 symbol×date 取優先度最高的來源。
    prio 0 = 官方 EOD（有 OHLC）
    prio 1 = Nasdaq 收盤快照（只有收盤與成交量；O=H=L=C，當日真實波幅會略為低估）
    prio 2 = tail / hourly 盤中快照（不是收盤，永遠只作墊底）"""
    frames = []
    for f in _files():
        b = os.path.basename(f)
        d = pd.read_csv(f)
        d.columns = [c.strip() for c in d.columns]
        route = d["route"].astype(str) if "route" in d.columns else pd.Series(["eod"] * len(d))
        keep = [c for c in ("symbol", "date", "open", "high", "low", "close", "adj_close", "volume") if c in d.columns]
        d = d[keep].copy()
        d["route"] = route.values
        # 鏡像檔名的最後一個日期 = 抓取窗口的終點；同一 symbol×date 同優先度時取較新的檔
        # （舊檔裡的「當日」可能是收盤前抓到的半日值，新檔才是正式收盤）
        _ds = re.findall(r"\d{4}-\d{2}-\d{2}", b)
        d["fend"] = _ds[-1] if _ds else "0000-00-00"
        d["prio"] = 0
        d.loc[d["route"].str.contains("hourly|intraday|quote", case=False, na=False), "prio"] = 2
        if "tail" in b:
            d.loc[d["prio"] == 0, "prio"] = 2
        frames.append(d)
    d0 = pd.concat(frames, ignore_index=True)
    d0["symbol"] = d0["symbol"].astype(str).str.upper().str.strip()
    d0["date"] = pd.to_datetime(d0["date"])
    d0 = d0.dropna(subset=["close"])
    # OHLC 鏡像的最後一個「完整」交易日：之後的日子才用收盤快照補，且只補鏡像本來就有的標的，
    # 否則快照那 7,100 檔的寬universe 會把覆蓋率基準抬高、反而把歷史交易日判成不完整。
    ohlc = d0[d0.prio == 0]
    cov0 = ohlc.groupby("date").symbol.nunique()
    last_full = cov0[cov0 >= 0.5 * cov0.max()].index.max() if len(cov0) else None
    known = set(ohlc.symbol.unique())
    # 缺口日：在最後完整日之前、但 OHLC 覆蓋不到一半的交易日（例如 Yahoo 始終沒出齊的 2026-09-22）。
    # 整天丟掉會讓序列把前後兩日當成相鄰，所以一律用 Nasdaq 收盤快照補成「只有收盤」的一根（有 Yahoo 日線的照用 Yahoo）。
    # 最後完整日之後的日子，仍只在 USE_SNAP=1 時才用快照補。
    holes = set(cov0[(cov0 < 0.5 * cov0.max()) & (cov0.index < last_full)].index) if len(cov0) else set()
    # 完整交易日（≤ 最後完整日）上個別缺漏的名字（例如 Yahoo 沒給 HUBB 09-24）也用當日收盤快照補，
    # 但只補該日前後 7 天內仍有 OHLC 的名字，避免把已下市、代號被重用的公司接到舊序列後面。
    last_ohlc = ohlc.groupby("symbol").date.max()
    if os.path.isdir(SNAP_DIR) and last_full is not None:
        snaps = []
        prev_px = None                      # 上一份快照的收盤（偵測「過期快照」用）
        for f in sorted(glob.glob(f"{SNAP_DIR}/*.csv")):
            dt = pd.Timestamp(os.path.basename(f)[:-4])
            # 過期快照：與上一份快照的收盤 ≥90% 逐檔相同 → 其實是前一交易日的資料（例如 10MA repo 的 2026-09-24.csv
            # 與 09-23.csv 完全相同），不可當成當天收盤。
            try:
                _raw = pd.read_csv(f, usecols=["symbol", "lastsale"])
                _px = pd.Series(pd.to_numeric(_raw.lastsale.astype(str).str.replace(r"[$,]", "", regex=True), errors="coerce").values,
                                index=_raw.symbol.astype(str).str.upper().str.strip())
                _px = _px[~_px.index.duplicated()]
            except Exception:
                _px = None
            if _px is not None and prev_px is not None:
                _c = _px.index.intersection(prev_px.index)
                if len(_c) and (_px[_c] == prev_px[_c]).mean() >= 0.9:
                    STALE_SNAPS.append(str(dt.date()))
                    if verbose:
                        print(f"snapshot {dt.date()}: 與上一份快照 {(_px[_c] == prev_px[_c]).mean():.1%} 相同 → 過期，不使用")
                    continue
            if _px is not None:
                prev_px = _px
            fill_gap = dt <= last_full and dt not in holes
            if not ((dt > last_full and USE_SNAP) or dt in holes or fill_gap):
                continue
            try:
                sn = pd.read_csv(f)
            except Exception:
                continue
            if "symbol" not in sn.columns or "lastsale" not in sn.columns:
                continue
            px = pd.to_numeric(sn["lastsale"].astype(str).str.replace(r"[$,]", "", regex=True), errors="coerce")
            vol = pd.to_numeric(sn.get("volume"), errors="coerce")
            sn = pd.DataFrame({"symbol": sn["symbol"].astype(str).str.upper().str.strip(), "date": dt,
                               "open": px, "high": px, "low": px, "close": px, "adj_close": px, "volume": vol})
            sn = sn[sn.symbol.isin(known)].dropna(subset=["close"])
            if fill_gap or dt in holes:
                have_day = set(ohlc.symbol[ohlc.date == dt])
                recent = set(last_ohlc.index[last_ohlc >= dt - pd.Timedelta(days=7)])
                sn = sn[~sn.symbol.isin(have_day) & sn.symbol.isin(recent)]
            sn["route"] = "snapshot-close"
            sn["prio"] = 1
            sn["fend"] = str(dt.date())
            snaps.append(sn)
            if verbose:
                print(f"snapshot {dt.date()}{'（缺口日）' if dt in holes else ('（補個別缺漏）' if fill_gap else '')}: +{len(sn)} 檔收盤（無盤中高低）")
        if snaps:
            d0 = pd.concat([d0] + snaps, ignore_index=True)
    frames = [d0]
    d = pd.concat(frames, ignore_index=True)
    d["symbol"] = d["symbol"].astype(str).str.upper().str.strip()
    d["date"] = pd.to_datetime(d["date"])
    d = d.dropna(subset=["close"])
    d = (d.sort_values(["symbol", "date", "prio", "fend"], ascending=[True, True, True, False], kind="mergesort")
          .drop_duplicates(["symbol", "date"], keep="first"))
    # 覆蓋率只算「收盤級」資料（prio 0/1）；盤中快照不能算一個完整交易日
    off = d[d.prio <= 1]
    cov = off.groupby("date").symbol.nunique()
    full = cov[cov >= 0.5 * cov.max()].index
    dropped = sorted(str(pd.Timestamp(x).date()) for x in d.date.unique() if pd.Timestamp(x) not in set(full))
    if dropped and verbose:
        det = {str(k.date()): int(v) for k, v in cov.items() if k not in full}
        print("partial sessions dropped:", dropped, "close-grade rows:", det)
    d = d[d.date.isin(full)]
    if verbose:
        last = d.date.max()
        mix = d[d.date == last].prio.value_counts().to_dict()
        print(f"panel: {len(d):,} rows  {d.symbol.nunique():,} symbols  {d.date.min().date()} .. {last.date()}  "
              f"(最後一根來源 prio 分佈 {mix}；1 = 收盤快照，無盤中高低)")
    return d.sort_values(["symbol", "date"])


def scan_one(sym, df):
    df = df.reset_index(drop=True)
    if len(df) < 60: return None
    c = df.close; hlc3 = (df.high + df.low + df.close) / 3
    a14 = atr(df, 14)
    # R7-E 滾動 VWAP 30 (hlc3)
    vol = df.volume.fillna(0)
    sumPV = (hlc3 * vol).rolling(30).sum(); sumV = vol.rolling(30).sum()
    grav = np.where(sumV > 0, sumPV / sumV, sma(hlc3, 30))
    grav = pd.Series(grav, index=df.index)
    vidx, atrP, sdP, volD = vol_index(df)
    vs, vg, vr = vcp_score(df)
    m, s, h, up, theta, prog, elapsed = macd_clock(c)
    lr, lrDir, st, mk, mkTr, inBox = livermore_line(df)
    i = len(df) - 1
    A = a14.iloc[i]
    g_e = grav.iloc[i] - grav.iloc[i - 1]; g_e5 = (grav.iloc[i] - grav.iloc[i - 5]) / A if A > 0 else np.nan
    g_vi = vidx.iloc[i] - vidx.iloc[i - 1]
    g_v = vs.iloc[i] - vs.iloc[i - 1]
    # criteria 5：首根淺紅 = 今日 hist<0 且 hist 回升，昨日仍在加深（深紅）
    lightRed = (h < 0) & (h > np.roll(h, 1)); darkRedPrev = np.roll(h, 1) < np.roll(h, 2)
    first_lr = lightRed & darkRedPrev & (np.roll(h, 1) < 0)
    first_lr[:2] = False
    lr_days = np.nan
    for k in range(0, 15):
        if first_lr[i - k]: lr_days = k; break
    # 今日仍是淺紅（連續淺紅未中斷）才算「已過峰值」
    still_light = bool(lightRed[i])
    trough = np.nanmin(h[max(0, i - 40):i + 1]) if h[i] < 0 else np.nan
    dE = (c.iloc[i] - grav.iloc[i]); dG = (c.iloc[i] - lr[i]) if not np.isnan(lr[i]) else np.nan
    near = lambda d: (not np.isnan(d)) and (abs(d) <= NEAR_ATR * A or abs(d) / c.iloc[i] * 100 <= NEAR_PCT)
    r = dict(
        ticker=sym, date=df.date.iloc[i].strftime("%Y-%m-%d"), close=round(c.iloc[i], 2), atr=round(A, 2),
        c1=bool(g_e > 0), grav=round(grav.iloc[i], 2), grav_slope=round(g_e, 3), grav_shift5atr=round(g_e5, 2),
        c2=bool(g_vi > 0), volidx=round(vidx.iloc[i], 1), volidx_slope=round(g_vi, 2), volidx_prev=round(vidx.iloc[i - 1], 1),
        c3=bool(vidx.iloc[i] >= VOL_MIN), atr_pct=round(atrP.iloc[i], 2), sd60_pct=round(sdP.iloc[i], 2),
        vcp=round(vs.iloc[i], 1), vcp_slope=round(g_v, 1), vcp_grade=GRADE[int(vg[i])],
        c4=bool(180 <= theta[i] <= 300), clock=clock_txt(theta[i]), theta=round(theta[i], 1), cycle="跌" if not up[i] else "升",
        cyc_prog=round(prog[i] * 100, 0), cyc_days=int(elapsed[i]),
        c5=bool((not np.isnan(lr_days)) and lr_days <= 2 and still_light), c5_days=lr_days, hist=round(h[i], 4), hist_prev=round(h[i - 1], 4), hist_trough=round(trough, 4) if not np.isnan(trough) else np.nan,
        still_light=still_light,
        c6=bool(near(dE)), dist_grav_pct=round(dE / c.iloc[i] * 100, 2), dist_grav_atr=round(dE / A, 2) if A > 0 else np.nan,
        lr_line=round(lr[i], 2) if not np.isnan(lr[i]) else np.nan,
        dist_lr_pct=round(dG / c.iloc[i] * 100, 2) if not np.isnan(dG) else np.nan, dist_lr_atr=round(dG / A, 2) if (A > 0 and not np.isnan(dG)) else np.nan,
        turnover20_m=round(float((c * df.volume).tail(20).mean() / 1e6), 1),
        data_warn=_jump_warn(df),
        bar_src=("收盤快照" if ("prio" in df.columns and int(df.prio.iloc[i]) == 1) else "OHLC"),
        lr_dir={1: "↑", -1: "↓", 0: "—"}[int(lrDir[i])], struct={1: "HH/HL", -1: "LH/LL", 0: "—"}[int(st[i])], mk=MK[int(mk[i])], inBox=bool(inBox[i]),
        bars=len(df),
    )
    r["score"] = sum(int(r[k]) for k in ("c1", "c2", "c3", "c4", "c5", "c6"))
    return r

if __name__ == "__main__":
    tk = json.load(open(f"{S}/scan_tickers.json"))
    src = {}
    for k, v in tk.items():
        for t in v: src.setdefault(t, []).append(k)
    universe = sorted(src)
    d = load()
    d["symbol"] = d["symbol"].str.upper()
    have = set(d.symbol.unique())
    # 代號寫法對齊：鏡像裡同時存在 BRK/A、BRK/B、BRK.B、BF/A、BF.B、MOG.A 等寫法，
    # watchlist 可能寫成 BRK-B / BRK.B。逐一試點、槓、斜線三種分隔，取「資料最長」的那個。
    counts = d.groupby("symbol").size()

    def resolve(t):
        cands = {t}
        for a in ".-/":
            for b in ".-/":
                if a in t:
                    cands.add(t.replace(a, b))
        cands = [c for c in cands if c in have]
        return max(sorted(cands), key=lambda c: (counts[c], "/" in c)) if cands else None

    rows = []; missing = []
    for t in universe:
        s = resolve(t)
        if s is None: missing.append(t); continue
        df = d[d.symbol == s]
        r = scan_one(t, df)
        if r is None: missing.append(t); continue
        r["symbol_used"] = s
        r["lists"] = "+".join(src[t]); rows.append(r)
    out = pd.DataFrame(rows).sort_values(["score", "c5_days", "theta"], ascending=[False, True, False])
    out.to_csv(f"{S}/scan_r7_result.csv", index=False, encoding="utf-8-sig")
    json.dump({"missing": missing, "n": len(rows), "lastday": str(d.date.max().date())}, open(f"{S}/scan_r7_meta.json", "w"))
    print("scanned", len(rows), "missing", len(missing), missing[:30])
    remap = [(r["ticker"], r["symbol_used"]) for r in rows if r["ticker"] != r["symbol_used"]]
    if remap: print("symbol remapped:", remap)
    assert len(missing) + len(rows) == len(universe), "有 ticker 既沒掃到也沒列進 missing"
    print(out.score.value_counts().sort_index())
    print(out[out.score >= 5].head(40).to_string())
