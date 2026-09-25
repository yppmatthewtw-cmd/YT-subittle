# -*- coding: utf-8 -*-
"""把三個 session（chat 1–3）各自「用自己那套準則選中」的 ticker 抽出來，
再對上 R7 六項條件掃描結果，輸出「沒中六項、但中了 chat 1–3」的名單。

命中規則一律採用來源成品自己寫明的通過標記，不另設門檻：

  chat 1  20MA_momentum_pullback_watchlist R21（10ma-watchlist，session_01U5TQY1…；R21 起取代 10MA R20）
          在「總表」= 1/2/3/6 個月動能至少一個排前 10% 且五項回調形態全過（data/screen_mp21.json）；
          「差一項」名單只掃描、不算命中。
  chat 2  Combined_Watchlist_R22（vcp-watchlist，session_01SVJ37W…）
          線上數 ≥ 1（至少一張榜顯示「線上」）且三榜中至少一個是該榜的頂級：
          VCP = A/B、Weinstein = 2A、Pre-breakout = A。
  chat 3a SubSector_flow_watchlist_R12（20mawarchlist，session_01W6xAAk…）
          成分股所屬子板塊的「5 日分數」≥ 70（0–100 橫截面百分位）且「斜率」> 0。
  chat 3b AI_Sector_watchlist_R13（同一 session）
          所屬 AI 小群組 5 日分數 ≥ 70，且該股「5 日強度 tf5」> 0。
  chat 3c 加息與地緣政治 3 日清單 R2（同一 session）
          「受惠」名單算命中；「迴避」名單不算，並另行標註。
（chat 編號依使用者給的三個 session 連結順序；各 repo 的 commit 尾註 Claude-Session 可對照。r6/r7 曾把編號標錯。）

用法：python3 chat_hits.py <base_scan.csv> <out.csv> [update_0917.csv]
"""
import sys, os, json, re
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
S = os.environ.get("SCRATCH", "/tmp/claude-0/-home-user-YT-subittle/0bd65ef0-0bef-5829-9a6f-f0a46d2d96cd/scratchpad")
DELIV = os.environ.get("DELIV", f"{S}/deliv")
FLOW_MIN = 70.0     # chat 3 子板塊／AI 小群組的 5 日分數門檻
base_csv, out_csv = sys.argv[1], sys.argv[2]
upd_csv = sys.argv[3] if len(sys.argv) > 3 else ""


def norm(t):
    return str(t).strip().upper().replace("/", ".").replace("-", ".")


def header_row(df, keys, lim=15):
    for i in range(min(lim, len(df))):
        vals = [str(v).strip().replace("\n", "") for v in df.iloc[i].values]
        if any(v in keys for v in vals):
            return i
    return None


hit = {}        # norm ticker -> {源: 說明}
strength = {}   # norm ticker -> {欄位: 值}


def mark(t, key, desc, **vals):
    k = norm(t)
    hit.setdefault(k, {})[key] = desc
    strength.setdefault(k, {}).update({x: v for x, v in vals.items() if pd.notna(v)})


# ── chat 2：Combined Watchlist R22 ──────────────────────────────────────────
c1f = sorted([f for f in os.listdir(DELIV) if f.startswith("Combined_Watchlist_R")])[-1]
c1 = pd.read_excel(f"{DELIV}/{c1f}", "4. 總表", header=0)
c1.columns = [str(c).replace("\n", "") for c in c1.columns]
n_c1 = 0
for _, r in c1.iterrows():
    tags = []
    if str(r.get("VCP")).strip() in ("A", "B"):
        tags.append("VCP " + str(r["VCP"]).strip())
    if str(r.get("Weinstein")).strip() == "2A":
        tags.append("Weinstein 2A")
    if str(r.get("Pre-breakout")).strip() == "A":
        tags.append("Pre-breakout A")
    onl = r.get("線上數")
    if tags and pd.notna(onl) and float(onl) >= 1:
        n_c1 += 1
        mark(r["代號"], "k_comb", "、".join(tags) + f"（線上 {int(onl)}/3）",
             comb_up=r.get("上升分數"), comb_sure=r.get("確定性總分"), comb_cat=r.get("催化"),
             name=r.get("名稱"), comb_grade="/".join("—" if pd.isna(r.get(k)) or str(r.get(k)).strip() == "" else str(r.get(k)).strip()
                                                     for k in ("VCP", "Weinstein", "Pre-breakout")))
print(f"chat2 {c1f}: {n_c1} / {len(c1)} 命中（線上 ≥1 且三榜有頂級）")

# ── chat 3a：SubSector flow R12 ─────────────────────────────────────────────
c2f = sorted([f for f in os.listdir(DELIV) if f.startswith("SubSector_flow_watchlist_R")])[-1]
raw = pd.read_excel(f"{DELIV}/{c2f}", "總表 All", header=None)
h = header_row(raw, {"名次"})
c2 = raw.iloc[h + 1:].copy()
c2.columns = [str(v).replace("\n", "") for v in raw.iloc[h]]
c2 = c2.dropna(subset=["名次"])
memb = [c for c in c2.columns if c.startswith("成分股")]
n_c2 = 0
for _, r in c2.iterrows():
    if not (float(r["5日分數"]) >= FLOW_MIN and float(r["斜率"]) > 0):
        continue
    n_c2 += 1
    for c in memb:
        t = str(r[c]).strip().upper()
        if not re.match(r"^[A-Z][A-Z0-9.\-/]{0,6}$", t) or t in ("NAN", "NONE"):
            continue
        mark(t, "k_ss", f'#{int(r["名次"])} {str(r["名稱"]).strip()}（5 日分 {float(r["5日分數"]):.0f}，斜率 {float(r["斜率"]):+.2f}）',
             ss_rank=int(r["名次"]), ss_score=round(float(r["5日分數"]), 1), ss_name=str(r["名稱"]).strip())
print(f"chat3a {c2f}: {n_c2} / {len(c2)} 個子板塊達標")

# ── chat 3b：AI Sector R13 ─────────────────────────────────────────────────
c3f = sorted([f for f in os.listdir(DELIV) if f.startswith("AI_Sector_watchlist_R")])[-1]
raw = pd.read_excel(f"{DELIV}/{c3f}", "總表 All", header=None)
h = header_row(raw, {"名次"})
ai = raw.iloc[h + 1:].copy()
ai.columns = [str(v).replace("\n", "") for v in raw.iloc[h]]
ai = ai.dropna(subset=["名次"])
gscore = {str(r["名稱"]).strip(): (float(r["5日分數"]), int(r["名次"]), str(r["English"]).split()[0]) for _, r in ai.iterrows()}
raw = pd.read_excel(f"{DELIV}/{c3f}", "成分股資金流 Constituents", header=None)
h = header_row(raw, {"代號"})
con = raw.iloc[h + 1:].copy()
con.columns = [str(v).replace("\n", "") for v in raw.iloc[h]]
con = con.dropna(subset=["代號"])
n_c3 = 0
for _, r in con.iterrows():
    g = gscore.get(str(r["所屬群組"]).strip())
    tf5 = r.get("5日強度 tf5")
    if g is None or pd.isna(tf5) or float(tf5) <= 0 or g[0] < FLOW_MIN:
        continue
    n_c3 += 1
    mark(r["代號"], "k_ai", f'{g[2]} {str(r["所屬群組"]).strip()} #{g[1]}（群組 5 日分 {g[0]:.0f}，個股強度 {float(tf5):+.3f}）',
         ai_group=f'{g[2]} {str(r["所屬群組"]).strip()}', ai_rank=g[1], ai_tf5=round(float(tf5), 4))
print(f"chat3b {c3f}: {n_c3} / {len(con)} 檔成分股命中")

# ── chat 1：高動能回到 20MA R21（R21 起取代 10MA R20）────────────────────────
# R21 工作簿的排名／分數全是公式（沒有快取值），所以讀同一 session 寫出的 screen_mp21.json。
MPJ = os.environ.get("MP_JSON", "/home/user/yppmatthewtw-cmd/10ma-watchlist/data/screen_mp21.json")
mp = json.load(open(MPJ))
WIN = {21: "1月", 42: "2月", 63: "3月", 126: "6月"}
for r in mp["rows"]:
    fl = "；".join(f[1] for f in r.get("flags", []) if isinstance(f, (list, tuple)) and len(f) > 1)
    mark(r["sym"], "k_10ma",
         f'總表 #{int(r["rank"])}（動能 {"/".join(WIN[w] for w in r["hits_w"])}，爆發潛力 {r["score"]:.1f}）',
         mp_rank=int(r["rank"]), mp_cov=int(r["hits"]), mp_win="/".join(WIN[w] for w in r["hits_w"]),
         mp_score=round(float(r["score"]), 1), mp_mom=round(float(r["mom"]), 1), mp_pq=round(float(r["pq"]), 1),
         mp_flag=fl, name=r.get("name"))
n_live = len(mp["rows"])
n_nm = len(mp.get("near_miss", []))
print(f"chat1 {os.path.basename(MPJ)}（{mp['meta']['last_date']}）: {n_live} 檔上總表（差一項 {n_nm} 檔只掃描、不算命中）")

# ── chat 3c：加息與地緣政治 3 日清單 R2 ─────────────────────────────────────
rh = json.load(open(f"{S}/ratehike_r2.json"))
for t in rh.get("benefit", []):
    mark(t, "k_rh", "加息／地緣政治 3 日清單：受惠", rh="受惠")
avoid = {norm(t) for t in rh.get("avoid", [])}
print(f"chat3c 加息 R2: 受惠 {len(rh.get('benefit', []))} 檔命中、迴避 {len(avoid)} 檔標註")

# ── 併回六項條件掃描 ────────────────────────────────────────────────────────
d = pd.read_csv(base_csv)
d["key"] = d.ticker.map(norm)
NC = 6
CN = {"c1": "①", "c2": "②", "c3": "③", "c4": "④", "c5": "⑤", "c6": "⑥"}
d["miss"] = d.apply(lambda r: "".join(CN[c] for c in CN if not r[c]), axis=1)
d["c5_cat"] = d.apply(lambda r: ("第 %d 根" % (int(r.c5_days) + 1)) if (pd.notna(r.c5_days) and r.still_light)
                      else ("已中斷" if pd.notna(r.c5_days) else "—"), axis=1)
d["hist_ok"] = d["bars"] >= 250

if upd_csv and os.path.exists(upd_csv):
    u = pd.read_csv(upd_csv)
    u["key"] = u.ticker.map(norm)
    d = d.merge(u[["key", "four_17", "close_17", "chg1d_pct", "clock_17"]], on="key", how="left")
else:
    d["four_17"] = pd.NA; d["close_17"] = pd.NA; d["chg1d_pct"] = pd.NA; d["clock_17"] = pd.NA

LBL = {"k_10ma": "chat1 動能回調 R21", "k_comb": "chat2 Combined R22", "k_ss": "chat3 SubSector R12",
       "k_ai": "chat3 AI Sector R13", "k_rh": "chat3 加息 R2"}
ORDER = ("k_10ma", "k_comb", "k_ss", "k_ai", "k_rh")
rows = []
for _, r in d.iterrows():
    h = hit.get(r["key"])
    if not h or r["score"] == NC:
        continue
    v = strength.get(r["key"], {})
    rows.append(dict(
        ticker=r["ticker"], name=v.get("name", ""),
        n_hit=len(h), hits=" ｜ ".join(LBL[k] for k in ORDER if k in h),
        detail=" ｜ ".join(h[k] for k in ORDER if k in h),
        avoid="⚠ 加息清單「迴避」" if r["key"] in avoid else "",
        comb_grade=v.get("comb_grade", ""), comb_up=v.get("comb_up"), comb_sure=v.get("comb_sure"),
        ss_rank=v.get("ss_rank"), ss_score=v.get("ss_score"), ss_name=v.get("ss_name", ""),
        ai_group=v.get("ai_group", ""), ai_rank=v.get("ai_rank"), ai_tf5=v.get("ai_tf5"),
        mp_rank=v.get("mp_rank"), mp_win=v.get("mp_win", ""), mp_score=v.get("mp_score"), mp_flag=v.get("mp_flag", ""),
        rh=v.get("rh", ""), catalyst=str(v.get("comb_cat", "") or "")[:60],
        score=r["score"], miss=r["miss"],
        close=r["close"], volidx=r["volidx"], volidx_slope=r["volidx_slope"], grav_slope=r["grav_slope"],
        clock=r["clock"], c5_cat=r["c5_cat"], dist_grav_pct=r["dist_grav_pct"],
        turnover20_m=r["turnover20_m"], bars=r["bars"], hist_ok=r["hist_ok"],
        vcp=r["vcp"], vcp_grade=r["vcp_grade"], struct=r["struct"],
        four_17=r["four_17"], close_17=r["close_17"], chg1d_pct=r["chg1d_pct"], clock_17=r["clock_17"],
        lists=r["lists"]))

o = pd.DataFrame(rows).sort_values(["score", "n_hit", "volidx"], ascending=[False, False, False])
o.to_csv(out_csv, index=False, encoding="utf-8-sig")
both = [r.ticker for _, r in d.iterrows() if r["score"] == NC and r["key"] in hit]
json.dump({"both": both, "n_chat_only": len(o),
           "sys": {"10ma": n_live, "mp_nm": n_nm, "comb": n_c1, "comb_all": len(c1), "ss": n_c2, "ss_all": len(c2), "ai": n_c3,
                   "rh": len(rh.get("benefit", [])), "avoid": len(avoid)}}, open(out_csv[:-4] + "_both.json", "w"), ensure_ascii=False)   # 給報表寫「同時六項全中」一句
print(f"\nchat 1–3 命中合共 {len(o) + len(both)} 檔，其中 {len(both)} 檔同時六項全中（{'、'.join(both)}）")
print(f"六項全中 {int((d.score == NC).sum())} 檔已排除；chat 1–3 命中但未過六項：{len(o)} 檔")
print("  命中系統數分佈:", o.n_hit.value_counts().sort_index().to_dict())
print("  六項命中數分佈:", o.score.value_counts().sort_index().to_dict())
print("  其中標註『迴避』:", int((o.avoid != "").sum()))
print(o.head(15)[["ticker", "n_hit", "score", "miss", "volidx", "clock", "c5_cat", "hits"]].to_string())
