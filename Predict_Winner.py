import pandas as pd
import main
import scipy.stats as st
import math
import numpy as np

def CalcWinner(data,last_season_data,week,season,home_team, away_team, home_net, away_net,hfa):

    homev = main.teamVarPP(data,last_season_data, home_team,
                           weeks_played=week, season=season)
    awayv = main.teamVarPP(data,last_season_data, away_team,
                           weeks_played=week, season=season)
    mean = (home_net+hfa) - away_net
    sd = math.sqrt((homev + awayv))
    z = (0 - mean) / sd
    htwp = (1 - st.norm.cdf(z))

    atwp = 1 - htwp

    print(f"WEEK {week}: {home_team}: {(htwp * 100):.1f}%  {away_team}: {(atwp * 100):.1f}%")

def CalcSpread(data,last_season_data,week,season,home_net,away_net,hfa):
    np.random.seed(42)

    # Extract data from the selected row
    home_team_dvoa = home_net + hfa
    home_team_variance = main.teamVarPP(data,last_season_data, home_team,
                           weeks_played=week, season=season)
    away_team_dvoa = away_net
    away_team_variance = main.teamVarPP(data,last_season_data, away_team,
                           weeks_played=week, season=season)

    # Update the diffplot data with the new mean and variance
    updated_x1 = np.random.normal(home_team_dvoa, np.sqrt(home_team_variance), 10_000)
    updated_x2 = np.random.normal(away_team_dvoa, np.sqrt(away_team_variance), 10_000)

    avg_points = 21.77
    for i in range(len(updated_x1)):
        if updated_x1[i] < 0:
            updated_x1[i] = round(avg_points * (1 + updated_x1[i]))
        else:
            updated_x1[i] = round(avg_points * (1 + updated_x1[i]))

    for i in range(len(updated_x2)):
        if updated_x2[i] < 0:
            updated_x2[i] = round(avg_points * (1 + updated_x2[i]))
        else:
            updated_x2[i] = round(avg_points * (1 + updated_x2[i]))

    diff = updated_x1 - updated_x2

    margins = pd.read_csv("NFL_Margins.csv")

    data = np.array([])
    for i in range(len(margins)):
        tot = margins["MARGIN"].iloc[i]
        freq = margins["FREQ"].iloc[i]
        for j in range(freq):
            data = np.append(data, tot)

    # Parameters for the second normal distribution
    mu1, std1 = np.mean(diff), np.std(diff)

    # Number of samples
    num_samples = 10_000

    # Generate samples from the first and second distributions
    dist1_samples = np.random.choice(data, size=int(num_samples * 0.25), replace=True)
    dist2_samples = np.random.normal(mu1, std1, int(num_samples * 0.75))

    dist2_samples = [round(element) for element in dist2_samples]

    # Assign weights to the distributions
    weight_dist1 = 0.25
    weight_dist2 = 0.75

    # Combine the samples based on weights
    weighted_samples = np.concatenate([
        np.random.choice(dist1_samples, size=int(num_samples * weight_dist1)),
        np.random.choice(dist2_samples, size=int(num_samples * weight_dist2))
    ])

    rounded_samples = np.rint(weighted_samples)
    # Create a histogram trace

    # vegas_mean = float(vegas_data[vegas_data["Team"] == ht.split(" ")[-1]]["Spread"].iloc[0]) * -1

    # combined_samples = np.rint((rounded_samples * .4 + vegas_mean * .6))

    # mean = np.mean(combined_samples)

    mean = rounded_samples
    if mean < 0:
        hw_hl = f" The {home_team} Lose by {round(mean * 2) / 2 * -1}"
        # print(np.mean(combined_samples < vegas_mean))
    else:
        hw_hl = f" The {away_team} Win by {round(mean * 2) / 2}"
        # print(np.mean(combined_samples > vegas_mean))

    print(hw_hl)

season = 2023


schedule_data = pd.read_csv(f"Data/NFL_SCHEDULE_{season}.csv")
url = f'https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{season}.csv'

data = pd.read_csv(url, low_memory=True)

last_season_data = pd.read_csv(f"Data/play_by_play_{season-1}.csv")

vegas = pd.read_csv("NFL Vegas Win Totals 2023.csv")

print("data_loaded")

weeks = [2,3,4,5,6,7,8,9,10]

for week in weeks:
    hfa = main.hfa(data,last_season_data,weeks_played=week)
    print(f"HFA: {hfa}")
    week_data = schedule_data[schedule_data["Week"] == week]
    print(week_data)
    for i in range(len(week_data)):
        home_team = main.getTeamAbv(week_data["HomeTm"].iloc[i])
        away_team = main.getTeamAbv(week_data["VisTm"].iloc[i])

        last_season = pd.read_csv(f"Team Stats/{season - 1}/{23}/Net_Ratings.csv")

        """BYE WEEKS"""
        """Preliminary number want to check more seasons. Only 5 so far maybe last 10"""
        # -0.0080468
        #too small

        """QB ADJ"""


        if week == 1:
            home_net = ((last_season[home_team].iloc[0] * 2 / 3) * .35) + (((vegas[vegas["Team"] == home_team]["Vegas Wins"].iloc[0] - 8.3641 ) / 33.146 ) *.65)
            away_net = ((last_season[away_team].iloc[0] * 2 / 3) * .35) + (((vegas[vegas["Team"] == away_team]["Vegas Wins"].iloc[0] - 8.3641 ) / 33.146 ) *.65)
        elif week < 14:
            net = pd.read_csv(f"Team Stats/{season}/{week - 1}/Net_Ratings.csv")

            last_season = pd.read_csv(f"Team Stats/{season-1}/{23}/Net_Ratings.csv")
            print((net[home_team].iloc[0]*((week-1)/13)) , (((last_season[home_team].iloc[0] * 2 / 3) * .35) + (((vegas[vegas["Team"] == home_team]["Vegas Wins"].iloc[0] - 8.3641 ) / 33.146 ) *.65)) * (1-((week-1)/13)))
            home_net = (net[home_team].iloc[0]*((week-1)/13)) + (((last_season[home_team].iloc[0] * 2 / 3) * .35) + (((vegas[vegas["Team"] == home_team]["Vegas Wins"].iloc[0] - 8.3641 ) / 33.146 ) *.65)) * (1-((week-1)/13))
            print((net[away_team].iloc[0] * ((week - 1) / 13)), (((last_season[away_team].iloc[0] * 2 / 3) * .35) + (
                        ((vegas[vegas["Team"] == away_team]["Vegas Wins"].iloc[0] - 8.3641) / 33.146) * .65)) * (
                              1 - ((week - 1) / 13)))
            away_net = (net[away_team].iloc[0]*((week-1)/13)) + (((last_season[away_team].iloc[0] * 2 / 3) * .35) + (((vegas[vegas["Team"] == away_team]["Vegas Wins"].iloc[0] - 8.3641 ) / 33.146 ) *.65)) * (1-((week-1)/13))

        else:
            home_net = pd.read_csv(f"Team Stats/{season}/{week-1}/Net_Ratings.csv")[home_team].iloc[0]
            away_net = pd.read_csv(f"Team Stats/{season}/{week-1}/Net_Ratings.csv")[away_team].iloc[0]

        if week > 21:
            hfa = 0

        CalcWinner(data,last_season_data,week,season,home_team,away_team, home_net, away_net,hfa)
        print(f"Home Net: {home_net} Away Net: {away_net})")

    print("")
