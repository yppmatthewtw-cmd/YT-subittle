# -*- coding: utf-8 -*-
"""
MACD Cycle Clock 掃描 R1 —— 錨點改為「轉勢點」(6 點鐘 = 柱狀圖最負點)。

時鐘四個正點對應四個真實 MACD 事件（不再是純時間內插）：
    3 點鐘  柱狀圖由正轉負          (轉負)
    6 點鐘  柱狀圖最負點            (轉勢點) ← 本表最高分
    9 點鐘  柱狀圖由負轉正          (轉正)
   12 點鐘  柱狀圖最正點            (見頂)

指針角度：
  下跌周期‧仍在探底 (今日=本周期新低)   90° → 180°，以 elapsed / (預期/2) 內插
  下跌周期‧已過轉勢點                 180° → 270°，以柱狀圖自谷底回升比例內插
  上昇周期‧仍在攻頂 (今日=本周期新高)  270° → 360°，以 elapsed / (預期/2) 內插
  上昇周期‧已過頂                      0° → 90°，以柱狀圖自峰值回落比例內插

輸出：clock_rank2.json  (評分以 6 點鐘為節點)
"""
import gzip, csv, json, statistics, collections

REPO = "/home/user/yppmatthewtw-cmd/vcp-watchlist/data/yahoo"
LONG = f"{REPO}/eod_2025-09-01_2026-09-09.csv.gz"
SHORT = f"{REPO}/eod_2026-08-25_2026-09-11.csv.gz"
SCRATCH = "/tmp/claude-0/-home-user-YT-subittle/0bd65ef0-0bef-5829-9a6f-f0a46d2d96cd/scratchpad"

tk = json.load(open(f"{SCRATCH}/tickers.json"))
WANT = set(tk["union"])

bars = collections.defaultdict(dict)
for path in (LONG, SHORT):
    with gzip.open(path, "rt") as f:
        for r in csv.DictReader(f):
            s = r["symbol"].strip().upper()
            if s not in WANT:
                continue
            try:
                c, v = float(r["close"]), float(r["volume"] or 0)
            except (ValueError, TypeError):
                continue
            if c > 0:
                bars[s][r["date"]] = (c, v)

alldates = sorted({d for m in bars.values() for d in m})
LASTDAY = alldates[-1]
print(f"loaded {len(bars)} symbols | {alldates[0]} → {LASTDAY} ({len(alldates)} days)")


def ema(vals, span):
    k = 2.0 / (span + 1)
    out, e = [], None
    for v in vals:
        e = v if e is None else v * k + e * (1 - k)
        out.append(e)
    return out


def macd_hist(cl, f=12, s=26, sg=9):
    line = [a - b for a, b in zip(ema(cl, f), ema(cl, s))]
    sig = ema(line, sg)
    return line, sig, [a - b for a, b in zip(line, sig)]


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


# 市場基準
_r = []
for _s, _m in bars.items():
    _d = sorted(_m)
    if len(_d) >= 22:
        _c = [_m[x][0] for x in _d]
        _r.append(_c[-1] / _c[-22] - 1)
mkt21 = statistics.median(_r) if _r else 0.0
print(f"market median 21d: {mkt21*100:+.2f}% (n={len(_r)})")

rows, bad = [], []
for sym in sorted(WANT):
    m = bars.get(sym)
    if not m:
        bad.append({"sym": sym, "err": "無日線資料"}); continue
    ds = sorted(m)
    cl = [m[d][0] for d in ds]
    vo = [m[d][1] for d in ds]
    if len(cl) < 80:
        bad.append({"sym": sym, "err": f"歷史不足 ({len(cl)} 日)"}); continue

    line, sigl, hist = macd_hist(cl)
    n = len(hist)

    # ── 週期切分 ──
    ups, dns, start = [], [], 0
    for i in range(1, n):
        if (hist[i] >= 0) != (hist[i - 1] >= 0):
            (ups if hist[i - 1] >= 0 else dns).append(i - start)
            start = i
    up = hist[-1] >= 0
    elapsed = n - start
    avgUp = statistics.mean(ups[-8:]) if ups else 12.0
    avgDn = statistics.mean(dns[-8:]) if dns else 12.0
    expected = avgUp if up else avgDn

    # ── 本周期的極值 = 轉勢點 (跌) / 見頂點 (升) ──
    seg = hist[start:]
    ext = min(seg) if not up else max(seg)
    ext_i = start + (seg.index(ext))
    since_ext = (n - 1) - ext_i                  # 距極值幾根 K 線；0 = 今日就是極值
    # 極值之後連續同向根數
    run = 0
    for i in range(n - 1, ext_i, -1):
        if (hist[i] > hist[i - 1]) if not up else (hist[i] < hist[i - 1]):
            run += 1
        else:
            break

    h = hist[-1]
    # 自極值回復比例 (0 = 還在極值, 1 = 已到零軸)
    recov = clamp((h - ext) / (0 - ext)) if ext != 0 else 1.0

    # ── 事件錨定的時鐘角度 ──
    half = max(expected / 2.0, 1.0)
    if not up:
        if since_ext == 0:                        # 仍在探底：3 點 → 6 點
            theta = 90 + 90 * clamp(elapsed / half)
        else:                                     # 已過轉勢點：6 點 → 9 點
            theta = 180 + 90 * recov
    else:
        if since_ext == 0:                        # 仍在攻頂：9 點 → 12 點
            theta = 270 + 90 * clamp(elapsed / half)
        else:                                     # 已見頂：12 點 → 3 點
            theta = (0 + 90 * recov)
    theta %= 360
    hh = int(theta / 30) % 12
    hh = 12 if hh == 0 else hh
    mm = int((theta % 30) / 30 * 60)

    amp = max(abs(x) for x in hist[-120:]) or 1e-9
    line_up = line[-1] > line[-2] if n >= 2 else False
    line_run = 0
    for i in range(n - 1, 0, -1):
        if line[i] > line[i - 1]:
            line_run += 1
        else:
            break

    # ══════════ 評分：以 6 點鐘 (轉勢點) 為節點，指針越接近 180° 分數越高 ══════════
    # A 相位 45 —— 直接由時鐘角度與 6 點鐘的距離決定（非對稱：剛過谷底 > 尚未見底）
    if not up:
        # theta 由 90° (3 點, 剛轉負) 順時針走到 270° (9 點, 轉正)，節點在 180°
        if theta < 150:      A = 10 + 20 * ((theta - 90) / 60)      # 3:00–5:00 探底初中期
        elif theta < 180:    A = 30 + 15 * ((theta - 150) / 30)     # 5:00–6:00 探底末期
        elif theta <= 220:   A = 45.0                               # 6:00–7:20 剛過轉勢點 ← 節點
        elif theta <= 250:   A = 45 - 13 * ((theta - 220) / 30)     # 7:20–8:20 回升中段
        else:                A = 32 - 10 * ((theta - 250) / 20)     # 8:20–9:00 逼近轉正
    else:
        A = max(2.0, 14 - 1.6 * elapsed)                            # 已轉正：節點早已過去

    # B 轉勢確認 25 —— 這個底可不可信（連續回升根數 / MACD 線上翹 / 未破新低）
    if not up and since_ext > 0:
        B = min(14.0, 3.5 * run) + (7.0 if line_up else 0.0) + 4.0
    elif not up:
        B = 4.0 if line_up else 0.0                                              # 仍在探底，尚未確認
    else:
        B = 5.0 * clamp((5 - elapsed) / 5)

    # C 底部品質 15 —— 谷底夠深（反轉空間大）+ MACD 線連續上翹根數
    depth = clamp(abs(ext) / amp)
    C = (9.0 * depth + min(6.0, 1.5 * line_run)) if not up else min(4.0, 1.0 * line_run)

    # D 價格確認 15 —— 價 > EMA9/21、RS 勝市場、量縮
    e9, e21 = ema(cl, 9)[-1], ema(cl, 21)[-1]
    e50 = ema(cl, 50)[-1] if len(cl) >= 50 else e21
    ret21 = cl[-1] / cl[-22] - 1 if len(cl) >= 22 else 0.0
    rs21 = ret21 - mkt21
    v10 = statistics.mean(vo[-10:]) if len(vo) >= 10 else 0
    v50 = statistics.mean(vo[-50:]) if len(vo) >= 50 else v10
    vr = v10 / v50 if v50 > 0 else 1.0
    D = (5 if cl[-1] > e9 else 0) + (4 if cl[-1] > e21 else 0) + \
        (3 if rs21 > 0 else 0) + (3 if vr < 1.0 else 0)

    score = round(A + B + C + D, 1)
    hi52, lo52 = max(cl[-252:]), min(cl[-252:])
    rows.append({
        "sym": sym, "close": round(cl[-1], 2),
        "chg1d": round((cl[-1] / cl[-2] - 1) * 100, 2),
        "up": up, "elapsed": int(elapsed), "expected": round(expected, 1),
        "clock": f"{hh}:{mm:02d}", "theta": round(theta, 1),
        "since_ext": int(since_ext), "ext": round(ext, 4), "recov": round(recov * 100, 0),
        "run": run, "line_run": line_run, "depth": round(depth * 100, 0),
        "hist": round(h, 4),
        "A": round(A, 1), "B": round(B, 1), "C": round(C, 1), "D": round(D, 1), "score": score,
        "e9": cl[-1] > e9, "e21": cl[-1] > e21, "e50": cl[-1] > e50,
        "rs21": round(rs21 * 100, 1), "vr": round(vr, 2),
        "offhigh": round((cl[-1] - hi52) / hi52 * 100, 1),
        "chg21": round(ret21 * 100, 1),
    })

rows.sort(key=lambda r: -r["score"])
for i, r in enumerate(rows, 1):
    r["rank"] = i
json.dump({"lastday": LASTDAY, "rows": rows, "missing": bad},
          open(f"{SCRATCH}/clock_rank2.json", "w"), ensure_ascii=False)

print(f"scored {len(rows)} | missing {len(bad)}")
print("\n轉勢點 (6 點鐘) TOP 20：")
print(f"{'#':>3} {'代號':<6}{'分':>6} {'時鐘':>6} {'周期':<4}{'距轉勢':>7}{'回升%':>6}{'連升':>4}{'底深%':>6} {'hist':>9}{'谷底':>9}")
for r in rows[:20]:
    print(f"{r['rank']:>3} {r['sym']:<6}{r['score']:>6.1f} {r['clock']:>6} "
          f"{'升' if r['up'] else '跌':<4}{r['since_ext']:>6}日{r['recov']:>5.0f}%{r['run']:>4}"
          f"{r['depth']:>6.0f} {r['hist']:>9.4f}{r['ext']:>9.4f}")
