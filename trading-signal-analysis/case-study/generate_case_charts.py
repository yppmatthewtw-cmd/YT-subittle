# -*- coding: utf-8 -*-
"""
DCFC (Tritium) 成功日 vs 失敗日 對照圖表。

圖A 成功日 (+$12k)：依公開事件（2022/2/8-9 田納西建廠 + 白宮點名，兩日 +39.5%/+34.3%）
     重構的「第一天消息日正確打法」示意圖。
圖B 失敗日 (紅日)：依 Ross 在 Red Day Lessons 中自述的真實價位重構：
     halt $8.42 → FOMO 追高 $10.50 買 9,000 股 → $10.95 halt 前賣出 (+$4,500)
     → $11.50 加回(均價 $11.32) → 高點 $11.90 → 跌至 VWAP 攤平 $10.30/$10.40
     → 反彈 $10.85 出場 → 若持有至 $8.30 = -$3/股。

執行: python3 generate_case_charts.py
輸出: dcfc_win_day.png / dcfc_red_day.png
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

plt.rcParams["font.family"] = ["WenQuanYi Zen Hei", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["text.parse_math"] = False
UP, DN = "#16a34a", "#dc2626"
C_VWAP = "#7c3aed"
rng = np.random.default_rng(7)


def make_ohlc(anchors, noise=0.012):
    n = anchors[-1][0] + 1
    xs = np.arange(n, dtype=float)
    close = np.interp(xs, [a[0] for a in anchors], [a[1] for a in anchors])
    close += rng.normal(0, noise, n)
    open_ = np.empty(n); open_[0] = close[0]; open_[1:] = close[:-1]
    hi = np.maximum(open_, close) + np.abs(rng.normal(0, .02, n))
    lo = np.minimum(open_, close) - np.abs(rng.normal(0, .02, n))
    return xs, open_, hi, lo, close


def draw(ax, xs, o, h, l, c, halts=()):
    for i in range(len(xs)):
        if any(a <= i < b for a, b in halts):
            continue
        col = UP if c[i] >= o[i] else DN
        ax.plot([i, i], [l[i], h[i]], color=col, lw=.9, zorder=2)
        ax.add_patch(Rectangle((i - .32, min(o[i], c[i])), .64,
                     max(abs(c[i] - o[i]), .004), fc=col, ec=col, lw=.5, zorder=3))
    for a, b in halts:
        ax.axvspan(a, b, color="#cbd5e1", alpha=.55, zorder=1)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color="#e2e8f0", lw=.7, zorder=0)


def note(ax, x, y, txt, up, color, dy=40):
    m, fc, ec = ("▼", "#fef2f2", DN) if not up else ("▲", "#eff6ff", "#2563eb")
    if color: ec = color
    ax.annotate(m, (x, y + (.05 if not up else -.05)), color=ec, fontsize=14,
                ha="center", va="bottom" if not up else "top", zorder=6)
    ax.annotate(txt, (x, y + (.09 if not up else -.09)),
                xytext=(0, dy if not up else -dy), textcoords="offset points",
                ha="center", va="bottom" if not up else "top", fontsize=9,
                color="#0f172a",
                bbox=dict(boxstyle="round,pad=.4", fc=fc, ec=ec, lw=1.2),
                arrowprops=dict(arrowstyle="-", color=ec, lw=1), zorder=6)


def vwap_of(h, l, c, v):
    t = (h + l + c) / 3
    return np.cumsum(t * v) / np.cumsum(v)


# ══════════════ 圖A 成功日 (+$12k, 示意重構) ══════════════
A = [(0, 6.60), (6, 6.80), (12, 6.95), (14, 7.00), (15, 6.85), (17, 6.95),
     (18, 7.08), (21, 7.45), (24, 7.80), (27, 7.58), (30, 7.60), (31, 7.88),
     (34, 8.15), (38, 8.42), (41, 8.30), (45, 8.55), (50, 8.35), (58, 8.10),
     (66, 8.25), (75, 8.15)]
xs, o, h, l, c = make_ohlc(A)
h[24] += .06; h[38] += .08
v = np.concatenate([rng.uniform(4, 10, 15), [55, 40, 95, 130, 80], rng.uniform(50, 90, 6),
                    rng.uniform(14, 24, 5), [26, 70, 60], rng.uniform(35, 60, 7),
                    rng.uniform(12, 30, 34)]) * 1000
v = np.resize(v, len(xs))
vw = vwap_of(h, l, c, v)

fig, (ax, axv) = plt.subplots(2, 1, figsize=(15, 8.6), sharex=True,
                              gridspec_kw={"height_ratios": [3.3, .9], "hspace": .06})
draw(ax, xs, o, h, l, c)
ax.plot(xs, vw, color=C_VWAP, lw=2, label="VWAP")
ax.hlines(7.00, 0, 20, color="#64748b", lw=1.2, ls="--")
ax.text(.4, 7.05, "盤前高點 $7.00", fontsize=9.5, color="#475569")
ax.axvline(15, color="#94a3b8", lw=1, ls=":")
ax.text(1.2, 7.42, "盤前消息：田納西建廠＋白宮點名\n（政策級催化 = 消息質量高 #39）",
        fontsize=9, color="#334155",
        bbox=dict(boxstyle="round,pad=.4", fc="#f8fafc", ec="#94a3b8"))
note(ax, 18, l[18], "入場①  Gap&Go 破盤前高\n量>5x·綠燈·價>VWAP ✓\n止損=突破K線低點 (#10)", True, None, 46)
note(ax, 24, h[24], "延伸棒賣半倉 +$0.70/股\n恐懼不提早·目標位預設 (#60)", False, None, 30)
note(ax, 31, l[31], "入場②  旗形首次縮量回踩\n首根新高K線 (#13/#15)", True, None, 40)
note(ax, 38, h[38], "第二延伸棒全部出清\n整數關口前 · 不戀戰 (#53)", False, None, 34)
ax.text(60, 8.75, "之後不再追（已收工保利潤 #48）\n約 7,000 股 × 平均 +$1.6 ≈ +$12k",
        fontsize=9.5, color="#166534", ha="center",
        bbox=dict(boxstyle="round,pad=.5", fc="#f0fdf4", ec="#16a34a"))
ax.set_ylim(6.1, 9.15); ax.set_ylabel("價格 (USD)")
ax.legend(loc="upper left", frameon=False, fontsize=9)
ax.set_title("圖A · 成功日：DCFC +$12k — 消息第一天、紀律化 Gap & Go\n"
             "(依公開事件重構之示意圖；Warrior Trading「$DCFC +$12k」 2022年2月)",
             fontsize=13, pad=12)
axv.bar(xs, v / 1000, color=[UP if c[i] >= o[i] else DN for i in range(len(xs))], width=.7)
axv.set_ylabel("量 (千股)")
for s in ("top", "right"): axv.spines[s].set_visible(False)
axv.set_xticks([0, 15, 30, 45, 60, 75])
axv.set_xticklabels(["09:15", "09:30\n(開盤)", "09:45", "10:00", "10:15", "10:30"])
fig.savefig(__file__.replace("generate_case_charts.py", "dcfc_win_day.png"),
            dpi=150, bbox_inches="tight", facecolor="#fff")
plt.close(fig)

# ══════════════ 圖B 失敗日 (紅日, 依自述價位重構) ══════════════
B = [(0, 8.20), (2, 8.42),                       # 開盤急拉 -> halt#1 @8.42
     (7, 9.15), (10, 9.90), (11, 10.30),          # 恢復續拉
     (12, 10.50), (14, 10.95),                    # FOMO入場10.50 -> halt#2 @10.95
     (19, 11.50), (21, 11.55), (23, 11.90),       # 恢復11.50加倉, 高點11.90
     (26, 11.30), (29, 10.80), (33, 10.35),       # 崩回VWAP
     (36, 10.45), (38, 10.85),                    # 攤平後反彈10.85
     (42, 10.40), (48, 9.90), (55, 9.55),         # 出場後續跌
     (63, 8.90), (70, 8.30), (75, 8.45)]          # flush 8.30
xs, o, h, l, c = make_ohlc(B, noise=.02)
halts = [(3, 7), (15, 19)]
h[23] += .1; l[70] -= .06
v = np.concatenate([[90, 120, 140], np.zeros(4), [110, 95, 100, 120, 150, 130, 160],
                    np.zeros(4), [140, 90, 80, 110, 60, 70, 90, 120, 95, 60, 55, 50, 45, 65],
                    rng.uniform(25, 55, 40)]) * 1000
v = np.resize(v, len(xs)); v[v == 0] = 1
vw = vwap_of(h, l, c, v)

fig, (ax, axv) = plt.subplots(2, 1, figsize=(15, 9.2), sharex=True,
                              gridspec_kw={"height_ratios": [3.3, .9], "hspace": .06})
draw(ax, xs, o, h, l, c, halts)
ax.plot(xs, vw, color=C_VWAP, lw=2, label="VWAP")
for (a, b), lab in zip(halts, ["Halt① $8.42", "Halt③ $10.95"]):
    ax.text((a + b) / 2, 7.35, lab, fontsize=8.5, color="#475569", ha="center", rotation=90)
note(ax, 12, l[12], "✗ FOMO 追高 $10.50\n誤買 9,000 股（超大倉位）\n已離VWAP>15%·追第二天消息\n(#60 情緒 / #67 滑價 / #51 Day2)", True, DN, 52)
note(ax, 14, h[14], "※ $10.95 halt 前賣出 +$4,500\n（僥倖獲利 — 但強化了壞習慣）", False, "#d97706", 26)
note(ax, 20, l[20], "✗ $11.50 加回 (均價$11.32)\n接近頂部·延伸過度\n(#76 追後段)", True, DN, 40)
note(ax, 23, h[23], "當日高點 $11.90\n（他的加倉幾乎買在最高）", False, None, 30)
note(ax, 33, l[33], "✗ 跌至VWAP攤平 $10.30/$10.40\n(#43 攤平=典型錯誤)", True, DN, 46)
note(ax, 38, h[38], "反彈 $10.85 全部出場\n高位倉 -$0.47/股 → 當日轉紅\n(原本 +$1,000 → 紅日)", False, None, 34)
ax.annotate("若不停損持到 $8.30：\n-$3/股 × 9,000 = -$27,000\n（Ross:「這種回撤你絕不想抱」）",
            (70, l[70]), xytext=(-30, -66), textcoords="offset points",
            fontsize=9.5, color="#7f1d1d", ha="center",
            bbox=dict(boxstyle="round,pad=.5", fc="#fef2f2", ec=DN, lw=1.4),
            arrowprops=dict(arrowstyle="->", color=DN))
ax.set_ylim(7.2, 13.0); ax.set_ylabel("價格 (USD)")
ax.legend(loc="upper left", frameon=False, fontsize=9)
ax.set_title("圖B · 失敗日：DCFC 紅日 — FOMO 追高、頂部加倉、VWAP 攤平\n"
             "(依 Ross 於 Red Day Lessons 自述之真實價位重構；灰帶 = 熔斷暫停)",
             fontsize=13, pad=12)
axv.bar(xs, v / 1000, color=[UP if c[i] >= o[i] else DN for i in range(len(xs))], width=.7)
axv.set_ylabel("量 (千股)")
for s in ("top", "right"): axv.spines[s].set_visible(False)
axv.set_xticks([0, 15, 30, 45, 60, 75])
axv.set_xticklabels(["09:30", "09:45", "10:00", "10:15", "10:30", "10:45"])
fig.savefig(__file__.replace("generate_case_charts.py", "dcfc_red_day.png"),
            dpi=150, bbox_inches="tight", facecolor="#fff")
print("saved dcfc_win_day.png, dcfc_red_day.png")
