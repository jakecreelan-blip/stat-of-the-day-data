"""
Stat of the Day -- NBA bot
============================

Pulls 20 advanced NBA stats (10 offense, 10 defense) from the NBA's
own stats API via the nba_api package. Mirrors the structure of the
baseball bot: writes nba_stats_data.json (latest) plus a dated
nba_history/YYYY-MM-DD.json archive + nba_history/index.json.

SETUP:
    pip install nba_api pandas
    python nba_stat_bot.py

This script is defensive: it prints the columns it actually receives
from each table, and skips (rather than crashes on) any stat whose
expected column isn't found -- so if the NBA API changes a column
name, we'll see exactly what to fix.
"""

import os
import json
import datetime
import traceback
from nba_api.stats.endpoints import leaguedashplayerstats

MIN_MINUTES = 20   # per game
MIN_GP = 20        # games played


def current_season():
    today = datetime.date.today()
    if today.month >= 10:
        return f"{today.year}-{str(today.year + 1)[2:]}"
    return f"{today.year - 1}-{str(today.year)[2:]}"


SEASON = current_season()


def get_name(row):
    return row["PLAYER_NAME"]


def leader_low_avg(df, value_col, lower_is_better=False):
    sorted_df = df.sort_values(value_col, ascending=lower_is_better)
    best = sorted_df.iloc[0]
    worst = sorted_df.iloc[-1]
    avg = round(float(df[value_col].mean()), 4)
    return (
        {"player": get_name(best), "value": round(float(best[value_col]), 4)},
        {"player": get_name(worst), "value": round(float(worst[value_col]), 4)},
        avg,
    )


def process_columns(df, mapping, lower_is_better_map):
    out = {}
    for col, key in mapping:
        if col not in df.columns:
            print(f"  [skip] column '{col}' not available")
            continue
        valid = df.dropna(subset=[col])
        if valid.empty:
            print(f"  [skip] no valid rows for '{col}'")
            continue
        leader, coldest, avg = leader_low_avg(valid, col, lower_is_better=lower_is_better_map.get(key, False))
        out[key] = {"leader": leader, "coldest": coldest, "average": avg}
        print(f"  -> {key}: leader={leader}, coldest={coldest}, avg={avg}")
    return out


def fetch_table(measure_type, label):
    print(f"Fetching {label} ({measure_type}) for {SEASON}...")
    res = leaguedashplayerstats.LeagueDashPlayerStats(
        season=SEASON,
        measure_type_detailed_defense=measure_type,
        per_mode_detailed="PerGame",
        season_type_all_star="Regular Season",
        timeout=60,
    )
    df = res.get_data_frames()[0]
    print(f"  Got {len(df)} players. Columns: {list(df.columns)}")
    return df


def main():
    output = {
        "season": SEASON,
        "updated": datetime.date.today().isoformat(),
        "offense": {},
        "defense": {},
    }

    try:
        adv = fetch_table("Advanced", "Advanced")
        base = fetch_table("Base", "Base")

        # Merge on PLAYER_ID, keep MIN/GP from one table for filtering
        merged = adv.merge(base, on="PLAYER_ID", suffixes=("", "_base"))

        if "MIN" in merged.columns and "GP" in merged.columns:
            merged = merged[(merged["MIN"] >= MIN_MINUTES) & (merged["GP"] >= MIN_GP)]
            print(f"\n{len(merged)} players with >= {MIN_MINUTES} MIN/game and >= {MIN_GP} GP")

        # PLAYER_NAME may have a suffix after merging -- normalize
        if "PLAYER_NAME" not in merged.columns:
            for c in merged.columns:
                if c.startswith("PLAYER_NAME"):
                    merged["PLAYER_NAME"] = merged[c]
                    break

        # ---- OFFENSE (10) ----
        offense_mapping = [
            ("PTS", "pts"),
            ("TS_PCT", "ts"),
            ("EFG_PCT", "efg"),
            ("USG_PCT", "usg"),
            ("AST_PCT", "ast_pct"),
            ("AST_TO", "ast_to"),
            ("FG3_PCT", "fg3_pct"),
            ("FT_PCT", "ft_pct"),
            ("PLUS_MINUS", "plus_minus"),
            ("PIE", "pie"),
        ]
        offense_lower = {}  # all higher-is-better
        print("\n[Offense]")
        output["offense"] = process_columns(merged, offense_mapping, offense_lower)

        # ---- DEFENSE (10) ----
        defense_mapping = [
            ("DEF_RATING", "def_rating"),
            ("DREB_PCT", "dreb_pct"),
            ("OREB_PCT", "oreb_pct"),
            ("REB_PCT", "reb_pct"),
            ("STL", "stl"),
            ("BLK", "blk"),
            ("NET_RATING", "net_rating"),
            ("TOV", "tov"),
            ("PACE", "pace"),
            ("PF", "pf"),
        ]
        defense_lower = {
            "def_rating": True,
            "tov": True,
            "pf": True,
        }
        print("\n[Defense]")
        output["defense"] = process_columns(merged, defense_mapping, defense_lower)

    except Exception:
        print("  [error] NBA data fetch failed:")
        traceback.print_exc()

    today_str = datetime.date.today().isoformat()

    with open("nba_stats_data.json", "w") as f:
        json.dump(output, f, indent=2)
    print("\nWrote nba_stats_data.json")
    print("  offense keys:", list(output["offense"].keys()))
    print("  defense keys:", list(output["defense"].keys()))

    os.makedirs("nba_history", exist_ok=True)
    with open(f"nba_history/{today_str}.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"Wrote nba_history/{today_str}.json")

    index_path = "nba_history/index.json"
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
    print(f"Updated nba_history/index.json ({len(index['dates'])} day(s) total)")


if __name__ == "__main__":
    main()
