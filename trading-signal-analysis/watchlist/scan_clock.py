# -*- coding: utf-8 -*-
"""
MACD Cycle Clock 掃描：對三份 watchlist 的所有 ticker 計算日線 MACD 週期時鐘相位，
以「接近由負轉正」(下跌周期尾段 → 快要上昇) 為最高分重新排名。

資料：VCP-watchlist repo 的 Yahoo EOD 日線 (2025-09-01 → 2026-09-10)
輸出：/scratchpad/clock_rank.json
"""
import gzip, csv, json, math, statistics, collections

REPO = "/home/user/yppmatthewtw-cmd/vcp-watchlist/data/yahoo"
LONG = f"{REPO}/eod_2025-09-01_2026-09-09.csv.gz"
SHORT = f"{REPO}/eod_2026-08-25_2026-09-11.csv.gz"
SCRATCH = "/tmp/claude-0/-home-user-YT-subittle/0bd65ef0-0bef-5829-9a6f-f0a46d2d96cd/scratchpad"

tk = json.load(open(f"{SCRATCH}/tickers.json"))
WANT = set(tk["union"]) | {"SPY"}

# ── 讀取並合併日線 ──
bars = collections.defaultdict(dict)          # sym -> {date: (close, volume)}
for path in (LONG, SHORT):                    # 後讀的覆蓋先讀的
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
print(f"loaded {len(bars)} symbols | calendar {alldates[0]} → {LASTDAY} ({len(alldates)} days)")


def ema(vals, span):
    k = 2.0 / (span + 1)
    out, e = [], None
    for v in vals:
        e = v if e is None else v * k + e * (1 - k)
        out.append(e)
    return out


def macd_hist(closes, f=12, s=26, sg=9):
    line = [a - b for a, b in zip(ema(closes, f), ema(closes, s))]
    sig = ema(line, sg)
    return line, sig, [a - b for a, b in zip(line, sig)]


def cycles(hist):
    """回傳 (up, elapsed, avgUp, avgDn, lens) — 與 Pine 的 f_cycle 相同語意。"""
    ups, dns = [], []
    start = 0
    for i in range(1, len(hist)):
        if (hist[i] >= 0) != (hist[i - 1] >= 0):
            (ups if hist[i - 1] >= 0 else dns).append(i - start)
            start = i
    up = hist[-1] >= 0
    elapsed = len(hist) - 1 - start + 1
    avgUp = statistics.mean(ups[-8:]) if ups else 12.0
    avgDn = statistics.mean(dns[-8:]) if dns else 12.0
    return up, elapsed, avgUp, avgDn


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


# ── 市場基準 (RS)：SPY 不在個股 EOD 宇宙內，改用全體掃描標的的 21 日報酬中位數
#    （與 VCP-watchlist 的 rs21 = 個股報酬 − 市場中位數 同一做法）
_r = []
for _s, _m in bars.items():
    _ds = sorted(_m)
    if len(_ds) >= 22:
        _c = [_m[x][0] for x in _ds]
        _r.append(_c[-1] / _c[-22] - 1)
spy_ret21 = statistics.median(_r) if _r else 0.0
print(f"market median 21d return: {spy_ret21*100:+.2f}%  (n={len(_r)})")

rows = []
for sym in sorted(set(tk["union"])):
    m = bars.get(sym)
    if not m:
        rows.append({"sym": sym, "err": "無日線資料"})
        continue
    ds = sorted(m)
    cl = [m[d][0] for d in ds]
    vo = [m[d][1] for d in ds]
    if len(cl) < 80:
        rows.append({"sym": sym, "err": f"歷史不足 ({len(cl)} 日)"})
        continue

    line, sig, hist = macd_hist(cl)
    up, elapsed, avgUp, avgDn = cycles(hist)
    expected = avgUp if up else avgDn
    prog = elapsed / expected if expected > 0 else 1.0
    theta = (270 + 180 * min(prog, 0.97)) if up else (90 + 180 * min(prog, 0.97))
    theta %= 360
    # 時鐘時間字串 (12 點 = 0°)
    hh = int(theta / 30) % 12
    hh = 12 if hh == 0 else hh
    mm = int((theta % 30) / 30 * 60)

    h = hist[-1]
    slope3 = (hist[-1] - hist[-4]) / 3 if len(hist) >= 4 else 0.0
    rising_n = 0
    for i in range(len(hist) - 1, 0, -1):
        if hist[i] > hist[i - 1]:
            rising_n += 1
        else:
            break
    # 距離零軸幾根 K 線 (以近 3 日斜率外推)
    if not up and slope3 > 1e-9:
        bars2zero = -h / slope3
    elif up and slope3 < -1e-9:
        bars2zero = -h / slope3          # 上昇周期中轉負所需 (負面訊號，僅供顯示)
    else:
        bars2zero = float("inf")

    # 標準化：hist 相對於近 120 日的振幅
    amp = max(abs(x) for x in hist[-120:]) or 1e-9
    hnorm = h / amp

    # ── A 相位分 (0–45)：時鐘在哪 ──
    if not up:
        if prog < 0.30:
            A = 5 + 20 * (prog / 0.30)                 # 剛轉跌 (3–4 點)
        elif prog < 0.80:
            A = 25 + 15 * ((prog - 0.30) / 0.50)       # 中段 (5–7 點)
        elif prog <= 1.60:
            A = 45                                      # 尾段 (8–9 點) ← 最高
        else:
            A = max(30.0, 45 - 8 * (prog - 1.60))       # 嚴重超時：結構可能已壞
    else:
        if elapsed <= 3:
            A = 34                                      # 剛由負轉正 (9–10 點)
        elif prog < 0.40:
            A = 24 - 10 * (prog / 0.40)
        elif prog < 0.80:
            A = 12 - 8 * ((prog - 0.40) / 0.40)
        else:
            A = 2.0

    # ── B 零軸收斂分 (0–25)：預估幾根 K 轉正 ──
    if not up:
        B = 25 * clamp((8 - bars2zero) / 7) if slope3 > 0 else 0.0
    else:
        B = 25 if elapsed <= 2 else 25 * clamp((10 - elapsed) / 8) * 0.6

    # ── C 動能轉向分 (0–15)：連續回升根數 + 已離低點 ──
    trough = min(hist[max(0, len(hist) - int(elapsed) - 1):]) if elapsed >= 1 else h
    off_trough = clamp((h - trough) / (abs(trough) + 1e-9)) if trough < 0 else 0.0
    C = min(9.0, 3.0 * rising_n) + 6.0 * off_trough

    # ── D 價格 / 趨勢確認分 (0–15) ──
    e9 = ema(cl, 9)[-1]
    e21 = ema(cl, 21)[-1]
    e50 = ema(cl, 50)[-1] if len(cl) >= 50 else e21
    ret21 = cl[-1] / cl[-22] - 1 if len(cl) >= 22 else 0.0
    rs21 = ret21 - spy_ret21
    v10 = statistics.mean(vo[-10:]) if len(vo) >= 10 else 0
    v50 = statistics.mean(vo[-50:]) if len(vo) >= 50 else v10
    vr = v10 / v50 if v50 > 0 else 1.0
    D = (5 if cl[-1] > e9 else 0) + (4 if cl[-1] > e21 else 0) + \
        (3 if rs21 > 0 else 0) + (3 if vr < 1.0 else 0)

    score = round(A + B + C + D, 1)
    hi52 = max(cl[-252:]); lo52 = min(cl[-252:])
    rows.append({
        "sym": sym, "close": round(cl[-1], 2),
        "chg1d": round((cl[-1] / cl[-2] - 1) * 100, 2),
        "up": up, "elapsed": int(elapsed), "expected": round(expected, 1),
        "prog": round(prog * 100, 0), "clock": f"{hh}:{mm:02d}", "theta": round(theta, 1),
        "hist": round(h, 4), "hnorm": round(hnorm, 3), "slope3": round(slope3, 5),
        "rising_n": rising_n, "b2z": (round(bars2zero, 1) if bars2zero != float("inf") else None),
        "A": round(A, 1), "B": round(B, 1), "C": round(C, 1), "D": round(D, 1), "score": score,
        "e9": cl[-1] > e9, "e21": cl[-1] > e21, "e50": cl[-1] > e50,
        "rs21": round(rs21 * 100, 1), "vr": round(vr, 2),
        "offhigh": round((cl[-1] - hi52) / hi52 * 100, 1),
        "abovelow": round((cl[-1] - lo52) / lo52 * 100, 1),
        "chg21": round(ret21 * 100, 1),
        "days": len(cl),
    })

ok = [r for r in rows if "err" not in r]
bad = [r for r in rows if "err" in r]
ok.sort(key=lambda r: -r["score"])
for i, r in enumerate(ok, 1):
    r["rank"] = i
json.dump({"lastday": LASTDAY, "rows": ok, "missing": bad,
           "src": {k: v for k, v in tk.items() if k != "union"}},
          open(f"{SCRATCH}/clock_rank.json", "w"), ensure_ascii=False)

print(f"scored {len(ok)} | missing {len(bad)}: {[b['sym'] for b in bad][:20]}")
print("\n下跌周期尾段 (快要上昇) TOP 20：")
print(f"{'#':>3} {'代號':<6}{'分':>6} {'時鐘':>6} {'周期':<5}{'已走/預期':>10}{'進度':>6}{'轉正':>6} {'hist':>9} {'連升':>4}")
for r in ok[:20]:
    print(f"{r['rank']:>3} {r['sym']:<6}{r['score']:>6.1f} {r['clock']:>6} "
          f"{'升' if r['up'] else '跌':<5}{r['elapsed']:>4}/{r['expected']:<5.1f}{r['prog']:>5.0f}%"
          f"{(str(r['b2z']) if r['b2z'] is not None else '–'):>6} {r['hist']:>9.4f} {r['rising_n']:>4}")
