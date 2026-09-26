# -*- coding: utf-8 -*-
"""從各份 watchlist 工作簿 / HTML 抽出全部 ticker，輸出 {榜單名: [ticker]} JSON。

支援：
  AI_Sector_watchlist_R*.xlsx      成分股資金流 Constituents 的「代號」
  SubSector_flow_watchlist_R*.xlsx 總表 All 的「成分股 1..N」
  Combined_Watchlist_R*.xlsx       各分頁的「代號」
  10MA_uptrend_watchlist_R*.xlsx   總表的「代號」
用法：python3 extract_tickers.py out.json file1.xlsx file2.xlsx …
"""
import sys, json, re, os
import pandas as pd

TICK = re.compile(r"^[A-Z][A-Z0-9.\-]{0,6}$")
BAD = {"NAN", "NONE", "NA", "N/A", "TICKER"}


def label(path):
    b = os.path.basename(path)
    for k, tag in (("AI_Sector", "AI"), ("SubSector", "SubSector"), ("Combined", "Combined"), ("10MA", "10MA")):
        if k in b:
            v = re.search(r"R(\d+(?:\.\d+)?)", b)
            return f"{tag}_R{v.group(1).split('.')[0]}" if v else tag
    return os.path.splitext(b)[0][:20]


def header_row(df, keys):
    for i in range(min(15, len(df))):
        vals = [str(v).strip().replace("\n", "") for v in df.iloc[i].values]
        if any(v in keys for v in vals):
            return i
    return None


def from_book(path):
    xl = pd.ExcelFile(path)
    out = set()
    for sh in xl.sheet_names:
        df = xl.parse(sh, header=None)
        h = header_row(df, {"代號", "Ticker", "ticker"})
        if h is None:
            h2 = header_row(df, {"成分股1"})
            if h2 is None:
                continue
            cols = [j for j, v in enumerate(df.iloc[h2]) if str(v).replace("\n", "").startswith("成分股")]
            for _, r in df.iloc[h2 + 1:].iterrows():
                for j in cols:
                    v = str(r.iloc[j]).strip().upper()
                    if TICK.match(v) and v not in BAD:
                        out.add(v)
            continue
        cols = [j for j, v in enumerate(df.iloc[h]) if str(v).strip().replace("\n", "") in ("代號", "Ticker", "ticker")]
        for _, r in df.iloc[h + 1:].iterrows():
            for j in cols:
                v = str(r.iloc[j]).strip().upper()
                if TICK.match(v) and v not in BAD:
                    out.add(v)
    return sorted(out)


if __name__ == "__main__":
    out, files = sys.argv[1], sys.argv[2:]
    res = {}
    for f in files:
        res[label(f)] = from_book(f)
        print(f"{label(f):16s} {len(res[label(f)]):4d}  {res[label(f)][:8]}")
    uni = sorted(set().union(*res.values()))
    print("UNION", len(uni))
    json.dump(res, open(out, "w"), indent=1)
