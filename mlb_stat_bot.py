"""
Stat of the Day -- daily data bot (v3, Baseball Savant edition)
================================================================

Pulls advanced/Statcast stats from Baseball Savant via pybaseball:
  - xwOBA  (expected weighted on-base average)
  - Barrel% (rate of "perfectly struck" balls)
  - Hard-Hit% (rate of balls hit 95+ mph)

v3 change: filters by sample size OURSELVES after fetching the data,
since Savant's built-in minPA/minBBE parameters weren't reliably
filtering out small-sample outliers (e.g. a 0.78 "xwOBA" from a
player with almost no plate appearances).

SETUP:
    pip install pybaseball pandas
    python mlb_stat_bot.py
"""

import json
import datetime
import traceback
from pybaseball import statcast_batter_expected_stats, statcast_batter_exitvelo_barrels

YEAR = datetime.date.today().year

MIN_PA = 200    # plate appearances, for xwOBA
MIN_BBE = 100   # batted ball events, for barrel/hard-hit rate


def get_name(row):
    """Savant data often gives 'last_name, first_name' instead of a single Name column."""
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

    # --- xwOBA ---
    try:
        print(f"Fetching {YEAR} expected stats (xwOBA) from Baseball Savant...")
        xwoba_df = statcast_batter_expected_stats(YEAR)
        print(f"  Got {len(xwoba_df)} players before filtering")

        if "pa" in xwoba_df.columns:
            xwoba_df = xwoba_df[xwoba_df["pa"] >= MIN_PA]
            print(f"  {len(xwoba_df)} players with at least {MIN_PA} PA")

        xwoba_col = next((c for c in ["est_woba", "xwoba", "x_woba"] if c in xwoba_df.columns), None)
        if xwoba_col and not xwoba_df.empty:
            leader, coldest = leader_and_low(xwoba_df, xwoba_col, lower_is_better=False)
            results["xwoba"] = {"leader": leader, "coldest": coldest}
            print(f"  -> Leader: {leader}, Lowest: {coldest}")
        else:
            print("  [skip] no qualified rows or no xwOBA-like column found")
    except Exception:
        print("  [error] xwOBA fetch failed:")
        traceback.print_exc()

    # --- Barrel% and Hard-Hit% ---
    try:
        print(f"\nFetching {YEAR} exit velocity / barrel data from Baseball Savant...")
        ev_df = statcast_batter_exitvelo_barrels(YEAR)
        print(f"  Got {len(ev_df)} players before filtering")

        if "attempts" in ev_df.columns:
            ev_df = ev_df[ev_df["attempts"] >= MIN_BBE]
            print(f"  {len(ev_df)} players with at least {MIN_BBE} batted ball events")

        barrel_col = next((c for c in ["brl_percent", "barrel_batted_rate", "barrel%"] if c in ev_df.columns), None)
        if barrel_col and not ev_df.empty:
            leader, coldest = leader_and_low(ev_df, barrel_col, lower_is_better=False)
            results["barrel"] = {"leader": leader, "coldest": coldest}
            print(f"  -> Barrel% Leader: {leader}, Lowest: {coldest}")
        else:
            print("  [skip] no qualified rows or no Barrel%-like column found")

        hardhit_col = next((c for c in ["ev95percent", "hard_hit_percent", "hardhit_percent"] if c in ev_df.columns), None)
        if hardhit_col and not ev_df.empty:
            leader, coldest = leader_and_low(ev_df, hardhit_col, lower_is_better=False)
            results["hardhit"] = {"leader": leader, "coldest": coldest}
            print(f"  -> Hard-Hit% Leader: {leader}, Lowest: {coldest}")
        else:
            print("  [skip] no qualified rows or no Hard-Hit%-like column found")

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
