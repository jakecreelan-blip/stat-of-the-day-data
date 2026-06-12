"""
Stat of the Day -- daily data bot (v5)
=======================================

New in v5:
  - Each stat now also includes a "average" value (league average among
    qualified players), used for the small comparison chart.
  - The bot now also saves a DATED snapshot to history/YYYY-MM-DD.json
    every day (without overwriting previous days), plus updates
    history/index.json with the list of available dates. This builds
    an archive over time for "on this day" comparisons.

SETUP:
    pip install pybaseball pandas
    python mlb_stat_bot.py
"""

import os
import json
import datetime
import traceback
from pybaseball import statcast_batter_expected_stats, statcast_batter_exitvelo_barrels

YEAR = datetime.date.today().year

MIN_PA = 200
MIN_BBE = 100


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


def main():
    results = {}

    try:
        print(f"Fetching {YEAR} expected stats from Baseball Savant...")
        exp_df = statcast_batter_expected_stats(YEAR)
        print(f"  Got {len(exp_df)} players before filtering")

        if "pa" in exp_df.columns:
            exp_df = exp_df[exp_df["pa"] >= MIN_PA]
            print(f"  {len(exp_df)} players with at least {MIN_PA} PA")

        for col, key in [("woba", "woba"), ("est_woba", "xwoba"), ("est_ba", "xba"), ("est_slg", "xslg")]:
            if col in exp_df.columns and not exp_df.empty:
                leader, coldest, avg = leader_low_avg(exp_df, col)
                results[key] = {"leader": leader, "coldest": coldest, "average": avg}
                print(f"  -> {key}: leader={leader}, coldest={coldest}, avg={avg}")
            else:
                print(f"  [skip] column '{col}' not available")
    except Exception:
        print("  [error] expected stats fetch failed:")
        traceback.print_exc()

    try:
        print(f"\nFetching {YEAR} exit velocity / barrel data from Baseball Savant...")
        ev_df = statcast_batter_exitvelo_barrels(YEAR)
        print(f"  Got {len(ev_df)} players before filtering")

        if "attempts" in ev_df.columns:
            ev_df = ev_df[ev_df["attempts"] >= MIN_BBE]
            print(f"  {len(ev_df)} players with at least {MIN_BBE} batted ball events")

        for col, key in [
            ("brl_percent", "barrel"),
            ("ev95percent", "hardhit"),
            ("avg_hit_speed", "avgev"),
            ("max_hit_speed", "maxev"),
            ("anglesweetspotpercent", "sweetspot"),
            ("avg_distance", "avgdist"),
        ]:
            if col in ev_df.columns and not ev_df.empty:
                leader, coldest, avg = leader_low_avg(ev_df, col)
                results[key] = {"leader": leader, "coldest": coldest, "average": avg}
                print(f"  -> {key}: leader={leader}, coldest={coldest}, avg={avg}")
            else:
                print(f"  [skip] column '{col}' not available")
    except Exception:
        print("  [error] exit velo / barrels fetch failed:")
        traceback.print_exc()

    today_str = datetime.date.today().isoformat()
    output = {
        "season": YEAR,
        "updated": today_str,
        "stats": results,
    }

    # Main "latest" file (overwritten daily)
    with open("stats_data.json", "w") as f:
        json.dump(output, f, indent=2)
    print("\nWrote stats_data.json with keys:", list(results.keys()))

    # Dated archive snapshot (never overwritten)
    os.makedirs("history", exist_ok=True)
    with open(f"history/{today_str}.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"Wrote history/{today_str}.json")

    # Update index of available history dates
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
