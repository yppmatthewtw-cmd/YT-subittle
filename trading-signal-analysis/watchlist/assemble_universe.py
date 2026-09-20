# -*- coding: utf-8 -*-
"""把各來源的 ticker JSON 合成 scan_tickers.json（{榜單: [ticker]}），並印出交集統計。"""
import json, os, sys, glob
S = "/tmp/claude-0/-home-user-YT-subittle/0bd65ef0-0bef-5829-9a6f-f0a46d2d96cd/scratchpad"
mine = json.load(open(f"{S}/my_tickers.json"))          # 我自己抽的（分榜單）
agent = {os.path.basename(f)[:-5]: set(json.load(open(f))) for f in glob.glob(f"{S}/sources/*.json")}
out = {k: set(v) for k, v in mine.items()}
# 代理人抽到而我漏掉的，按來源補回
if "10MA" in agent:
    out.setdefault("10MA_R20", set()).update(agent["10MA"])
if "VCP" in agent:
    out.setdefault("Combined_R22", set()).update(agent["VCP"])
if "SubSectorAI" in agent:
    extra = agent["SubSectorAI"] - out.get("SubSector_R12", set()) - out.get("AI_R13", set())
    if extra:
        out.setdefault("SubSector_R12", set()).update(extra)
out = {k: sorted(v) for k, v in out.items()}
uni = sorted(set().union(*out.values()))
for k, v in out.items():
    print(f"{k:16s} {len(v):4d}")
print("UNION", len(uni))
json.dump(out, open(f"{S}/scan_tickers.json", "w"), indent=1)
