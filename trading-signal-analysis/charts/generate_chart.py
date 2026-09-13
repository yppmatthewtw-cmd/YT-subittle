# -*- coding: utf-8 -*-
"""
產生「Ross Cameron 典型 Gap & Go 交易日」教學圖表。

模擬一隻低流通量 (Low Float) 動能股在開盤後的 1 分鐘 K 線走勢，
並標註 Ross 典型的入市點 (Entry) 與賣出點 (Exit)，
每個訊號旁註明其特徵條件（來源：Logic Analysis 規則庫 ross_rules.csv）。

執行:  python3 generate_chart.py
輸出:  ross_entry_exit_chart.png
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch
import matplotlib.font_manager as fm

# ---- 中文字體 ----
plt.rcParams["font.family"] = ["WenQuanYi Zen Hei", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False

rng = np.random.default_rng(42)

# ---------------------------------------------------------------
# 1. 合成一個典型的低流通量 Gap & Go 交易日 (1 分鐘 K 線)
#    時間軸: 09:15 盤前 -> 10:30
#    劇本: 盤前有 FDA 消息缺口 +40%，開盤突破盤前高 -> 第一波拉升
#          -> Bull Flag 縮量回踩 -> 第二波拉升 -> 動能衰竭跌破 VWAP
# ---------------------------------------------------------------
anchors = [  # (分鐘索引, 價格)  09:15 = 0
    (0, 5.05), (5, 5.12), (10, 5.20), (14, 5.28),      # 盤前爬升, 盤前高 5.30
    (15, 5.10),                                          # 09:30 開盤小回
    (17, 5.18), (18, 5.35),                              # 突破盤前高 -> Entry 1
    (21, 5.70), (24, 6.00), (25, 6.20),                  # 第一波拉升 + 延伸棒
    (28, 6.00), (31, 5.95),                              # Bull Flag 縮量回踩
    (33, 6.15),                                          # 旗形突破 -> Entry 2
    (36, 6.55), (39, 6.85), (40, 7.00),                  # 第二波拉升
    (43, 6.80), (46, 6.70), (49, 6.55),                  # 第二旗形轉弱
    (52, 6.35), (56, 6.10), (60, 5.90),                  # 跌破旗形低點 -> 出清
    (65, 5.70), (70, 5.60), (75, 5.55),                  # Back-side 陰跌
]
n = anchors[-1][0] + 1
xs = np.arange(n, dtype=float)
ax_pts = np.array([a[0] for a in anchors], dtype=float)
ay_pts = np.array([a[1] for a in anchors])
close = np.interp(xs, ax_pts, ay_pts) + rng.normal(0, 0.015, n)
close[0] = 5.05

open_ = np.empty(n)
open_[0] = 5.00
open_[1:] = close[:-1] + rng.normal(0, 0.005, n - 1)
hi = np.maximum(open_, close) + np.abs(rng.normal(0, 0.02, n))
lo = np.minimum(open_, close) - np.abs(rng.normal(0, 0.02, n))
# 延伸棒 (25) 上影線、Dump 棒 (52) 放大
hi[25] += 0.10
hi[40] += 0.12
lo[52] -= 0.08

# 成交量: 盤前小 -> 開盤爆量 -> 回踩縮量 -> 突破放量 -> 衰減
vol = np.full(n, 12_000.0)
vol[:15] = rng.uniform(3_000, 9_000, 15)                       # 盤前
vol[15:20] = [60_000, 45_000, 55_000, 140_000, 90_000]         # 開盤+突破爆量
vol[20:26] = rng.uniform(60_000, 110_000, 6)                   # 第一波
vol[26:32] = rng.uniform(15_000, 28_000, 6)                    # 縮量回踩 (<突破量50%)
vol[32:36] = [30_000, 95_000, 70_000, 60_000]                  # 旗形突破放量
vol[36:42] = rng.uniform(45_000, 80_000, 6)                    # 第二波
vol[42:52] = rng.uniform(18_000, 35_000, 10)                   # 轉弱
vol[52] = 85_000                                               # 放量下殺
vol[53:] = rng.uniform(8_000, 20_000, n - 53)                  # 衰減

# VWAP (由盤前起累計)
typ = (hi + lo + close) / 3
vwap = np.cumsum(typ * vol) / np.cumsum(vol)

# EMA9 / EMA20
def ema(a, span):
    k = 2 / (span + 1)
    out = np.empty_like(a)
    out[0] = a[0]
    for i in range(1, len(a)):
        out[i] = a[i] * k + out[i - 1] * (1 - k)
    return out

ema9, ema20 = ema(close, 9), ema(close, 20)
macd_line = ema(close, 12) - ema(close, 26)
macd_sig = ema(macd_line, 9)
macd_hist = macd_line - macd_sig

# ---------------------------------------------------------------
# 2. 畫圖
# ---------------------------------------------------------------
UP, DN = "#16a34a", "#dc2626"          # 漲/跌 K 線
C_VWAP, C_E9, C_E20 = "#7c3aed", "#f59e0b", "#2563eb"
C_ENTRY, C_EXIT = "#2563eb", "#dc2626"
BG = "#ffffff"

fig = plt.figure(figsize=(16, 11), facecolor=BG)
gs = fig.add_gridspec(3, 1, height_ratios=[3.2, 0.9, 0.9], hspace=0.06)
axp = fig.add_subplot(gs[0])
axv = fig.add_subplot(gs[1], sharex=axp)
axm = fig.add_subplot(gs[2], sharex=axp)

# K 線
for i in range(n):
    c = UP if close[i] >= open_[i] else DN
    axp.plot([i, i], [lo[i], hi[i]], color=c, lw=0.9, zorder=2)
    axp.add_patch(Rectangle((i - 0.32, min(open_[i], close[i])), 0.64,
                            max(abs(close[i] - open_[i]), 0.004),
                            facecolor=c, edgecolor=c, lw=0.5, zorder=3))

axp.plot(xs, vwap, color=C_VWAP, lw=2.0, label="VWAP", zorder=4)
axp.plot(xs, ema9, color=C_E9, lw=1.4, label="EMA 9", zorder=4)
axp.plot(xs, ema20, color=C_E20, lw=1.4, label="EMA 20", zorder=4)

# 盤前高水平線
pm_high = hi[:15].max()
axp.hlines(pm_high, 0, 22, color="#64748b", lw=1.2, linestyle="--", zorder=1)
axp.text(0.3, pm_high + 0.04, f"盤前高點 ${pm_high:.2f}（突破觸發位）",
         fontsize=10, color="#475569")

# 開盤垂直線
axp.axvline(15, color="#94a3b8", lw=1, linestyle=":")
for a in (axp, axv, axm):
    a.set_facecolor(BG)
    for s in ("top", "right"):
        a.spines[s].set_visible(False)
    a.grid(axis="y", color="#e2e8f0", lw=0.7, zorder=0)

# ------- 入市 / 賣出 標註 -------
def entry(i, txt, dy_pt=-52):
    axp.annotate("▲", (i, lo[i] - 0.06), color=C_ENTRY, fontsize=15,
                 ha="center", va="top", zorder=6)
    axp.annotate(txt, (i, lo[i] - 0.10), xytext=(0, dy_pt),
                 textcoords="offset points", ha="center", va="top", fontsize=9.5,
                 color="#1e3a8a",
                 bbox=dict(boxstyle="round,pad=0.45", fc="#eff6ff", ec=C_ENTRY, lw=1.2),
                 arrowprops=dict(arrowstyle="-", color=C_ENTRY, lw=1))

def exit_(i, txt, dy_pt=42):
    axp.annotate("▼", (i, hi[i] + 0.05), color=C_EXIT, fontsize=15,
                 ha="center", va="bottom", zorder=6)
    axp.annotate(txt, (i, hi[i] + 0.09), xytext=(0, dy_pt),
                 textcoords="offset points", ha="center", va="bottom", fontsize=9.5,
                 color="#7f1d1d",
                 bbox=dict(boxstyle="round,pad=0.45", fc="#fef2f2", ec=C_EXIT, lw=1.2),
                 arrowprops=dict(arrowstyle="-", color=C_EXIT, lw=1))

entry(18, "入市①  Gap & Go 突破\n特徵: 破盤前高 + 量>5x\nMACD綠燈 + 價>VWAP\n止損: 突破K線低點", -28)
exit_(25, "賣出①  延伸棒減半倉\n特徵: 連漲後長上影\n離VWAP過遠(>10%)\n→ 先收一半利潤", 30)
entry(33, "入市②  Bull Flag 首次回踩\n特徵: 縮量回踩<前波20%\n有下影線 + 守住EMA9\n首根創新高K線進場", -60)
exit_(40, "賣出②  第二延伸棒\n特徵: 整數關口$7 +\n高潮量 + 長上影\n→ 再減半倉", 8)
exit_(52, "賣出③  出清\n特徵: 放量跌破旗形低點\nMACD轉負(紅燈)\n→ 全部出場", 36)

# Back-side 區域
axp.axvspan(56, n - 1, color="#f1f5f9", zorder=0)
axp.text(65, 6.9, "Back-side（後段）\n跌破VWAP + 高點回落>20%\n→ 不再做多，觀望",
         fontsize=10, color="#475569", ha="center",
         bbox=dict(boxstyle="round,pad=0.5", fc="#f8fafc", ec="#94a3b8", lw=1))

axp.set_ylim(3.95, 8.15)
axp.set_ylabel("價格 (USD)", fontsize=11)
axp.legend(loc="upper left", frameon=False, fontsize=10)
axp.set_title("Ross Cameron 典型交易日：入市點與賣出點及其訊號特徵\n"
              "(低流通量 <5M、FDA 消息催化、$2–$10 甜區 — 模擬 1 分鐘 K 線教學圖)",
              fontsize=14, pad=14)

# 成交量
vcolors = [UP if close[i] >= open_[i] else DN for i in range(n)]
axv.bar(xs, vol / 1000, color=vcolors, width=0.7, zorder=2)
axv.set_ylabel("成交量 (千股)", fontsize=10)
axv.annotate("突破爆量 (>5x)", (18, vol[18] / 1000), xytext=(30, -6),
             textcoords="offset points", fontsize=9, color="#334155", va="top",
             arrowprops=dict(arrowstyle="->", color="#334155", lw=0.9))
axv.annotate("回踩縮量 (<50%)", (29, 30), xytext=(28, 30),
             textcoords="offset points", fontsize=9, color="#334155",
             arrowprops=dict(arrowstyle="->", color="#334155", lw=0.9))

# MACD
axm.bar(xs, macd_hist, color=[UP if v >= 0 else DN for v in macd_hist],
        width=0.7, zorder=2, alpha=0.55)
axm.plot(xs, macd_line, color="#0f172a", lw=1.2, label="MACD")
axm.plot(xs, macd_sig, color="#f59e0b", lw=1.2, label="Signal")
axm.axhline(0, color="#94a3b8", lw=0.8)
axm.set_ylabel("MACD", fontsize=10)
axm.legend(loc="upper left", frameon=False, fontsize=9, ncol=2)
axm.text(20, max(macd_line) * 0.55, "綠燈區：MACD>0 才可做多", fontsize=9, color=UP)
axm.text(56, max(macd_line) * 0.55, "紅燈區：MACD<0 禁止做多", fontsize=9, color=DN)

# X 軸時間標籤
ticks = [0, 15, 30, 45, 60, 75]
labels = ["09:15", "09:30\n(開盤)", "09:45", "10:00", "10:15", "10:30"]
axm.set_xticks(ticks)
axm.set_xticklabels(labels, fontsize=10)
axm.set_xlim(-1.5, n + 0.5)
plt.setp(axp.get_xticklabels(), visible=False)
plt.setp(axv.get_xticklabels(), visible=False)

fig.align_ylabels()
fig.savefig(__file__.replace("generate_chart.py", "ross_entry_exit_chart.png"),
            dpi=150, bbox_inches="tight", facecolor=BG)
print("saved ross_entry_exit_chart.png")
