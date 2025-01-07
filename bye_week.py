import pandas as pd
import main
import scipy.stats as st
import math
import main
# year = 2019
for year in [2023,2022,2021,2020,2019]:
    data = pd.read_csv(f"https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{year}.csv")

    bye_weeks = pd.read_csv("bye_weeks.csv")
    total_diff = 0
    for week in bye_weeks.columns:
        w = week.split(" ")[1]
        # print(w)

        try:
            index = int(2023 - year)
            all_teams = bye_weeks[week].iloc[index].split(",")
            for t in (all_teams):
                team = t.strip()
                team_name = team
                # print(team_name)
                week_to_look_for = int(w)+1
                week_data = data[(data["week"] == week_to_look_for)]

                team_data = week_data[(week_data['home_team'] == team_name) | (week_data['away_team'] == team_name)]
                team_data = team_data[team_data['side_of_field'].notna()]

                for i in range(len(team_data)):
                    if team_data["defteam"].iloc[i] == team:
                        team_data["epa"].iloc[i] = team_data["epa"].iloc[i] * -1

                total_diff += sum(team_data['epa'])/len(team_data) - pd.read_csv("Team Stats/2023/22/Net_Ratings.csv")[team_name]


        except:
            continue

    print(total_diff/32)


# bye_weeks["Week 5"].iloc[0].split(",")