"""
Stat of the Day -- daily data bot (v6)
=======================================

New in v6:
  - Adds a full PITCHING section (10 stats measuring what pitchers
    ALLOW -- lower is better), using the pitcher-side equivalents of
    the same Baseball Savant data sources already used for hitting.
  - Output structure is now nested: {"hitting": {...}, "pitching": {...}}
    instead of one flat "stats" dict.
  - Still writes stats_data.json (latest) AND history/YYYY-MM-DD.json
    (dated archive) + history/index.json.

SETUP:
    pip install pybaseball pandas
    python mlb_stat_bot.py
"""

import os
import json
import datetime
import traceback
from pybaseball import (
    statcast_batter_expected_stats,
    statcast_batter_exitvelo_barrels,
    statcast_pitcher_expected_stats,
    statcast_pitcher_exitvelo_barrels,
)

YEAR = datetime.date.today().year

MIN_PA_BAT = 200
MIN_BBE_BAT = 100
MIN_PA_PIT = 150
MIN_BBE_PIT = 75


def get_name(row):
    for col in ["player_name", "name", "Name"]:
        if col in row and isinstance(row[col], str):
            return row[col]
    if "last_name, first_name" in row:
        last, first = str(row["last_name, first_name"]).split(",")
        return f"{first.strip()} {last.strip()}"
    return "Unknown player"


def leader_low_avg(df, value_col, lower_is_better=False):
    sorted_df = df.sort_values(value_col, ascending=lower_is_better)
    best = sorted_df.iloc[0]
    worst = sorted_df.iloc[-1]
    avg = round(float(df[value_col].mean()), 3)
    return (
        {"player": get_name(best), "value": round(float(best[value_col]), 3)},
        {"player": get_name(worst), "value": round(float(worst[value_col]), 3)},
        avg,
    )


def process_columns(df, mapping, lower_is_better=False):
    """mapping: list of (savant_column_name, output_key)"""
    out = {}
    for col, key in mapping:
        if col in df.columns and not df.empty:
            leader, coldest, avg = leader_low_avg(df, col, lower_is_better=lower_is_better)
            out[key] = {"leader": leader, "coldest": coldest, "average": avg}
            print(f"  -> {key}: leader={leader}, coldest={coldest}, avg={avg}")
        else:
            print(f"  [skip] column '{col}' not available")
    return out


def main():
    output = {
        "season": YEAR,
        "updated": datetime.date.today().isoformat(),
        "hitting": {},
        "pitching": {},
    }

    # ---------------- HITTING ----------------
    try:
        print(f"[Hitting] Fetching {YEAR} expected stats...")
        exp_df = statcast_batter_expected_stats(YEAR)
        print(f"  Got {len(exp_df)} players")
        if "pa" in exp_df.columns:
            exp_df = exp_df[exp_df["pa"] >= MIN_PA_BAT]
            print(f"  {len(exp_df)} with >= {MIN_PA_BAT} PA")
        output["hitting"].update(process_columns(
            exp_df,
            [("woba", "woba"), ("est_woba", "xwoba"), ("est_ba", "xba"), ("est_slg", "xslg")],
            lower_is_better=False,
        ))
    except Exception:
        print("  [error] hitting expected stats failed:")
        traceback.print_exc()

    try:
        print(f"\n[Hitting] Fetching {YEAR} exit velocity / barrels...")
        ev_df = statcast_batter_exitvelo_barrels(YEAR)
        print(f"  Got {len(ev_df)} players")
        if "attempts" in ev_df.columns:
            ev_df = ev_df[ev_df["attempts"] >= MIN_BBE_BAT]
            print(f"  {len(ev_df)} with >= {MIN_BBE_BAT} BBE")
        output["hitting"].update(process_columns(
            ev_df,
            [
                ("brl_percent", "barrel"),
                ("ev95percent", "hardhit"),
                ("avg_hit_speed", "avgev"),
                ("max_hit_speed", "maxev"),
                ("anglesweetspotpercent", "sweetspot"),
                ("avg_distance", "avgdist"),
            ],
            lower_is_better=False,
        ))
    except Exception:
        print("  [error] hitting exit velo / barrels failed:")
        traceback.print_exc()

    # ---------------- PITCHING (lower = better, since these are ALLOWED) ----------------
    try:
        print(f"\n[Pitching] Fetching {YEAR} expected stats allowed...")
        pexp_df = statcast_pitcher_expected_stats(YEAR)
        print(f"  Got {len(pexp_df)} pitchers")
        print(f"  Columns: {list(pexp_df.columns)}")
        pa_col = "pa" if "pa" in pexp_df.columns else ("bf" if "bf" in pexp_df.columns else None)
        if pa_col:
            pexp_df = pexp_df[pexp_df[pa_col] >= MIN_PA_PIT]
            print(f"  {len(pexp_df)} with >= {MIN_PA_PIT} {pa_col}")
        output["pitching"].update(process_columns(
            pexp_df,
            [("woba", "woba"), ("est_woba", "xwoba"), ("est_ba", "xba"), ("est_slg", "xslg")],
            lower_is_better=True,
        ))
    except Exception:
        print("  [error] pitching expected stats failed:")
        traceback.print_exc()

    try:
        print(f"\n[Pitching] Fetching {YEAR} exit velocity / barrels allowed...")
        pev_df = statcast_pitcher_exitvelo_barrels(YEAR)
        print(f"  Got {len(pev_df)} pitchers")
        print(f"  Columns: {list(pev_df.columns)}")
        if "attempts" in pev_df.columns:
            pev_df = pev_df[pev_df["attempts"] >= MIN_BBE_PIT]
            print(f"  {len(pev_df)} with >= {MIN_BBE_PIT} BBE")
        output["pitching"].update(process_columns(
            pev_df,
            [
                ("brl_percent", "barrel"),
                ("ev95percent", "hardhit"),
                ("avg_hit_speed", "avgev"),
                ("max_hit_speed", "maxev"),
                ("anglesweetspotpercent", "sweetspot"),
                ("avg_distance", "avgdist"),
            ],
            lower_is_better=True,
        ))
    except Exception:
        print("  [error] pitching exit velo / barrels failed:")
        traceback.print_exc()

    today_str = datetime.date.today().isoformat()

    with open("stats_data.json", "w") as f:
        json.dump(output, f, indent=2)
    print("\nWrote stats_data.json")
    print("  hitting keys:", list(output["hitting"].keys()))
    print("  pitching keys:", list(output["pitching"].keys()))

    os.makedirs("history", exist_ok=True)
    with open(f"history/{today_str}.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"Wrote history/{today_str}.json")

    index_path = "history/index.json"
    if os.path.exists(index_path):
        with open(index_path) as f:
            index = json.load(f)
    else:
        index = {"dates": []}

    if today_str not in index["dates"]:
        index["dates"].append(today_str)
        index["dates"].sort()

    with open(index_path, "w") as f:
        json.dump(index, f, indent=2)
    print(f"Updated history/index.json ({len(index['dates'])} day(s) total)")


if __name__ == "__main__":
    main()
