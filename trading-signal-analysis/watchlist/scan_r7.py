# -*- coding: utf-8 -*-
"""
R7 A–G 六條件掃描（日線）— 以 Python 重現 r7a/b/c/e/g 的預設參數計算。
資料：vcp-watchlist repo 的 Yahoo 日線鏡像（至 2026-09-16 收盤）。
"""
import json, glob, math, sys
import numpy as np, pandas as pd

S = "/tmp/claude-0/-home-user-YT-subittle/0bd65ef0-0bef-5829-9a6f-f0a46d2d96cd/scratchpad"
FILES = [f"{S}/eod/eod_2025-09-01_2026-09-09.csv.gz",
         f"{S}/eod/eod_2026-09-01_2026-09-15.csv.gz",
         f"{S}/eod/eod_2026-09-02_2026-09-17.csv.gz",
         f"{S}/eod/eod_2026-09-04_2026-09-17.csv.gz"]
NEAR_ATR = 1.0          # criteria 6：|close − line| ≤ 1.0 × ATR14 算「附近」
NEAR_PCT = 3.0          # 或 ≤ 3%（兩者取其一即可）
VOL_MIN = 75.0          # criteria 3：R7-H 波動指數 ≥ 75
VA, VB = -3.381, 1.892  # R7-H 校準係數（20 日 ≥10% 回撤）

# ───────────────────────── Pine 等價工具 ─────────────────────────
def ema(s, n):  return s.ewm(span=n, adjust=False).mean()
def sma(s, n):  return s.rolling(n).mean()
def rma(s, n):  return s.ewm(alpha=1 / n, adjust=False).mean()
def atr(df, n=14):
    tr = pd.concat([df.high - df.low, (df.high - df.close.shift()).abs(), (df.low - df.close.shift()).abs()], axis=1).max(axis=1)
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

# ───────────────────────── R7-B MACD 時鐘 ─────────────────────────
def macd_clock(close, fast=12, slow=26, sig=9, lookN=8, defLen=12):
    m = ema(close, fast) - ema(close, slow); s = ema(m, sig); h = (m - s).values
    n = len(h); up = h >= 0
    cs = 0; ul = []; dl = []
    theta = np.full(n, np.nan); prog = np.full(n, np.nan); elapsed = np.zeros(n, int)
    for i in range(n):
        if i > 0 and up[i] != up[i - 1]:
            L = i - cs
            a = ul if up[i - 1] else dl
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
    return m.values, s.values, h, up, theta, prog, elapsed

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
    sdP = lr.rolling(sdLen).std(ddof=1) * 100          # ta.stdev 亦為樣本標準差
    volD = wAtr * atrP + (1 - wAtr) * sdP
    p = 1 / (1 + np.exp(-(a + b * np.log(volD))))
    return 100 * (1 - p), atrP, sdP, volD

# ───────────────────────── 主掃描 ─────────────────────────
def load():
    fr = [pd.read_csv(f) for f in FILES]
    d = pd.concat(fr).drop_duplicates(["symbol", "date"], keep="last")
    d["date"] = pd.to_datetime(d["date"])
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
    alt = {t: t.replace(".", "-") for t in universe}
    rows = []; missing = []
    for t in universe:
        s = t if t in have else (alt[t] if alt[t] in have else None)
        if s is None: missing.append(t); continue
        df = d[d.symbol == s]
        r = scan_one(t, df)
        if r is None: missing.append(t); continue
        r["lists"] = "+".join(src[t]); rows.append(r)
    out = pd.DataFrame(rows).sort_values(["score", "c5_days", "theta"], ascending=[False, True, False])
    out.to_csv(f"{S}/scan_r7_result.csv", index=False, encoding="utf-8-sig")
    json.dump({"missing": missing, "n": len(rows), "lastday": str(d.date.max().date())}, open(f"{S}/scan_r7_meta.json", "w"))
    print("scanned", len(rows), "missing", len(missing), missing[:30])
    print(out.score.value_counts().sort_index())
    print(out[out.score >= 5].head(40).to_string())
