"""
Stat of the Day -- daily data bot (v4, 10 stats)
=================================================

Pulls 10 advanced/Statcast hitting stats from Baseball Savant via
pybaseball -- using the SAME two data sources as before, since both
tables contain more useful columns than we were using:

From statcast_batter_expected_stats:
  - wOBA, xwOBA, xBA, xSLG

From statcast_batter_exitvelo_barrels:
  - Barrel%, Hard-Hit%, Avg Exit Velocity, Max Exit Velocity,
    Sweet-Spot%, Avg Distance

SETUP:
    pip install pybaseball pandas
    python mlb_stat_bot.py
"""

import json
import datetime
import traceback
from pybaseball import statcast_batter_expected_stats, statcast_batter_exitvelo_barrels

YEAR = datetime.date.today().year

MIN_PA = 200    # plate appearances, for expected-stats table
MIN_BBE = 100   # batted ball events, for exit velo / barrels table


def get_name(row):
    for col in ["player_name", "name", "Name"]:
        if col in row and isinstance(row[col], str):
            return row[col]
    if "last_name, first_name" in row:
        last, first = str(row["last_name, first_name"]).split(",")
        return f"{first.strip()} {last.strip()}"
    return "Unknown player"


def leader_and_low(df, value_col, lower_is_better=False):
    sorted_df = df.sort_values(value_col, ascending=lower_is_better)
    best = sorted_df.iloc[0]
    worst = sorted_df.iloc[-1]
    return (
        {"player": get_name(best), "value": round(float(best[value_col]), 3)},
        {"player": get_name(worst), "value": round(float(worst[value_col]), 3)},
    )


def main():
    results = {}

    # --- Table 1: expected stats -> wOBA, xwOBA, xBA, xSLG ---
    try:
        print(f"Fetching {YEAR} expected stats from Baseball Savant...")
        exp_df = statcast_batter_expected_stats(YEAR)
        print(f"  Got {len(exp_df)} players before filtering")

        if "pa" in exp_df.columns:
            exp_df = exp_df[exp_df["pa"] >= MIN_PA]
            print(f"  {len(exp_df)} players with at least {MIN_PA} PA")

        for col, key in [("woba", "woba"), ("est_woba", "xwoba"), ("est_ba", "xba"), ("est_slg", "xslg")]:
            if col in exp_df.columns and not exp_df.empty:
                leader, coldest = leader_and_low(exp_df, col)
                results[key] = {"leader": leader, "coldest": coldest}
                print(f"  -> {key}: leader={leader}, coldest={coldest}")
            else:
                print(f"  [skip] column '{col}' not available")
    except Exception:
        print("  [error] expected stats fetch failed:")
        traceback.print_exc()

    # --- Table 2: exit velo / barrels -> Barrel%, Hard-Hit%, EV, max EV, sweet spot%, distance ---
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
                leader, coldest = leader_and_low(ev_df, col)
                results[key] = {"leader": leader, "coldest": coldest}
                print(f"  -> {key}: leader={leader}, coldest={coldest}")
            else:
                print(f"  [skip] column '{col}' not available")
    except Exception:
        print("  [error] exit velo / barrels fetch failed:")
        traceback.print_exc()

    output = {
        "season": YEAR,
        "updated": datetime.date.today().isoformat(),
        "stats": results,
    }

    with open("stats_data.json", "w") as f:
        json.dump(output, f, indent=2)

    print("\nWrote stats_data.json with keys:", list(results.keys()))


if __name__ == "__main__":
    main()
