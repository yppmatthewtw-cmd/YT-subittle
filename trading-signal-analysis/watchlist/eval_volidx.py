# -*- coding: utf-8 -*-
"""
波動指數 vs VCP 指數：哪個更能說明「未來 N 日大幅下跌機會減少」？
樣本：vcp-watchlist Yahoo 日線鏡像 2,979 檔 × 2025-09 → 2026-09-16。
指標全部用 Pine 可以逐根計算的方式（單一標的的時間序列，不做橫斷面）。
"""
import sys, json
import numpy as np, pandas as pd
sys.path.insert(0, "/tmp/claude-0/-home-user-YT-subittle/0bd65ef0-0bef-5829-9a6f-f0a46d2d96cd/scratchpad")
from scan_r7 import load, vcp_score, atr, sma, ema, rma

S = "/tmp/claude-0/-home-user-YT-subittle/0bd65ef0-0bef-5829-9a6f-f0a46d2d96cd/scratchpad/volidx"
HORIZONS = (10, 20, 40)
DROPS = (-8.0, -10.0, -15.0)
PR_LEN = 126   # 百分位回看（Pine ta.percentrank）

def prank(s, n):
    """ta.percentrank 等價：目前值在過去 n 根（含自己）中的百分位 0–100"""
    return s.rolling(n).apply(lambda w: (w[:-1] < w[-1]).mean() * 100, raw=True)

def features(df):
    c = df.close; h = df.high; l = df.low
    r = np.log(c / c.shift())
    f = pd.DataFrame(index=df.index)
    f["atrp"] = atr(df, 14) / c * 100                                  # ATR14 %
    f["rv20"] = r.rolling(20).std() * np.sqrt(252) * 100              # 已實現波動 20
    f["rv60"] = r.rolling(60).std() * np.sqrt(252) * 100
    sd = c.rolling(20).std(); f["bbw"] = 4 * sd / sma(c, 20) * 100    # BB(20,2) 帶寬 %
    f["dsd20"] = r.clip(upper=0).rolling(20).apply(lambda w: np.sqrt((w ** 2).mean()), raw=True) * np.sqrt(252) * 100
    f["mdrop20"] = -(r.rolling(20).min() * 100)                      # 20 日內最大單日跌幅 %
    f["rng20"] = (h.rolling(20).max() / l.rolling(20).min() - 1) * 100
    f["ctr"] = atr(df, 5) / atr(df, 20)                              # 收縮比 (<1 = 收縮)
    f["rvr"] = f.rv20 / f.rv60
    # 百分位（高 = 波動高）；指數 = 100 − 百分位（高 = 平靜）
    for k in ("atrp", "rv20", "bbw", "dsd20", "rng20"):
        f[f"pr_{k}"] = prank(f[k], PR_LEN)
    f["V_atr"] = 100 - f.pr_atrp
    f["V_rv"] = 100 - f.pr_rv20
    f["V_bbw"] = 100 - f.pr_bbw
    f["V_dsd"] = 100 - f.pr_dsd20
    f["V_comp"] = 0.30 * (100 - f.pr_atrp) + 0.25 * (100 - f.pr_bbw) + 0.25 * (100 - f.pr_dsd20) + 0.20 * (100 - f.pr_rng20)
    # 絕對水準版（不做百分位，可跨標的比較）：ATR% 4% → 50 分，2% → 75，8% → 0
    f["V_abs"] = (100 - f.atrp * 12.5).clip(0, 100)
    f["V_absrv"] = (100 - f.rv20 * 100 / 120).clip(0, 100)      # rv 60% → 50, 120% → 0
    # 綜合：絕對 + 相對各半
    f["V_mix"] = 0.5 * f.V_abs + 0.5 * f.V_comp
    vs, vg, vr = vcp_score(df)
    f["VCP"] = vs.values
    f["VCPg"] = vg
    return f

def forward(df):
    c = df.close.values; l = df.low.values; n = len(c)
    out = {}
    for H in HORIZONS:
        mdd = np.full(n, np.nan); ret = np.full(n, np.nan)
        for i in range(n - H):
            mdd[i] = (l[i + 1:i + 1 + H].min() / c[i] - 1) * 100
            ret[i] = (c[i + H] / c[i] - 1) * 100
        out[f"mdd{H}"] = mdd; out[f"ret{H}"] = ret
    return pd.DataFrame(out, index=df.index)

def auc(score, y):
    """AUC：score 越高 → y=1 (沒有大跌) 的機率越高？ 用秩和"""
    m = ~(np.isnan(score) | np.isnan(y)); s = score[m]; yy = y[m].astype(bool)
    n1 = yy.sum(); n0 = (~yy).sum()
    if n1 == 0 or n0 == 0: return np.nan
    rk = pd.Series(s).rank().values
    return (rk[yy].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)

if __name__ == "__main__":
    import os
    if os.path.exists(f"{S}/panel.pkl") and "--rebuild" not in sys.argv:
        X = pd.read_pickle(f"{S}/panel.pkl"); print("loaded panel", X.shape)
    else:
      d = load()
      rows = []
      syms = sorted(d.symbol.unique())
      for k, s in enumerate(syms):
          df = d[d.symbol == s].reset_index(drop=True)
          if len(df) < 200 or df.close.iloc[-1] < 2 or (df.volume.tail(60).mean() < 100_000): continue
          f = features(df); fw = forward(df)
          x = pd.concat([f, fw], axis=1)
          x["symbol"] = s; x["date"] = df.date
          x = x.iloc[PR_LEN + 20:]                 # 等百分位 / VCP 暖機
          x = x[~x.mdd10.isna()]
          rows.append(x)
          if k % 300 == 0: print(k, s, len(rows), flush=True)
      X = pd.concat(rows)
      X.to_pickle(f"{S}/panel.pkl")
      print("panel", X.shape, X.symbol.nunique(), X.date.min(), X.date.max())
    IDX = ["V_atr", "V_rv", "V_bbw", "V_dsd", "V_comp", "V_abs", "V_absrv", "V_mix", "VCP"]
    res = []
    for H in HORIZONS:
        for D in DROPS:
            y = (X[f"mdd{H}"].values > D).astype(float)          # 1 = 沒有大跌
            base = 1 - y.mean()
            for k in IDX:
                res.append(dict(H=H, drop=D, idx=k, AUC=auc(X[k].values, y), base_drop_rate=base))
    R = pd.DataFrame(res)
    piv = R.pivot_table(index="idx", columns=["H", "drop"], values="AUC").round(3)
    print(piv.to_string())
    piv.to_csv(f"{S}/auc_table.csv")
    # 十分位：大跌率
    dec = {}
    for k in IDX:
        q = pd.qcut(X[k].rank(method="first"), 10, labels=False) + 1
        g = X.groupby(q)
        dec[k] = pd.DataFrame({"drop10_20d": g.apply(lambda z: (z.mdd20 <= -10).mean() * 100),
                               "drop15_40d": g.apply(lambda z: (z.mdd40 <= -15).mean() * 100),
                               "ret20": g.ret20.mean(), "mdd20": g.mdd20.mean(), "n": g.size()}).round(2)
        print("\n==", k); print(dec[k].T.to_string())
    pd.concat(dec, axis=1).to_csv(f"{S}/deciles.csv")
    # 高分區（≥70）與 VCP 高分區（≥70）比較 + 兩者交叉
    for k in ("V_comp", "V_abs", "V_mix"):
        hi = X[k] >= 70; vh = X.VCP >= 70
        print(f"\n{k}>=70: n={hi.sum()} drop10/20d={(X.mdd20[hi] <= -10).mean()*100:.1f}%  | VCP>=70: n={vh.sum()} {(X.mdd20[vh] <= -10).mean()*100:.1f}%  | both: n={(hi&vh).sum()} {(X.mdd20[hi&vh] <= -10).mean()*100:.1f}%  | VCP>=70 & {k}<40: n={(vh&(X[k]<40)).sum()} {(X.mdd20[vh&(X[k]<40)] <= -10).mean()*100:.1f}%  | all: {(X.mdd20 <= -10).mean()*100:.1f}%")
    # 相關
    print("\ncorr V_comp vs VCP:", X[["V_comp", "V_abs", "VCP"]].corr(method="spearman").round(3).to_string())
