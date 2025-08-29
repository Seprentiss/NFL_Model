import pandas as pd
import main
import scipy.stats as st
import math
import numpy as np


def save_to_csv(file_name, results):
    df = pd.DataFrame(results)
    df.to_csv(file_name, index=False)
    print(f"Data saved to {file_name}")

def CalcSpread(week, season, home_team, away_team, home_net, away_net,htvar,atvar, hfa):
    np.random.seed(42)

    vegas_data = pd.read_csv(f"{season} Vegas Lines/Vegas_Lines_Week_{week}.csv")

    # Extract data from the selected row
    home_team_dvoa = home_net + hfa
    home_team_variance = htvar
    away_team_dvoa = away_net
    away_team_variance = atvar

    # Update the diffplot data with the new mean and variance
    updated_x1 = np.random.normal(home_team_dvoa, np.sqrt(home_team_variance), 10_000)
    updated_x2 = np.random.normal(away_team_dvoa, np.sqrt(away_team_variance), 10_000)

    avg_plays = 153/2
    for i in range(len(updated_x1)):
        if updated_x1[i] < 0:
            updated_x1[i] = round(avg_plays * (updated_x1[i]))
        else:
            updated_x1[i] = round(avg_plays * (updated_x1[i]))

    for i in range(len(updated_x2)):
        if updated_x2[i] < 0:
            updated_x2[i] = round(avg_plays * (updated_x2[i]))
        else:
            updated_x2[i] = round(avg_plays * (updated_x2[i]))

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

    vegas_data['Team'] = vegas_data['Team'].apply(main.getTeamAbvShortName)

    vegas_mean = float(vegas_data[vegas_data["Team"] == home_team]["Spread"].iloc[0]) * -1

    combined_samples = np.rint((rounded_samples * .35 + vegas_mean * .65))

    mean = np.mean(combined_samples)

    cpev = pd.read_csv("Cover Prob EV.csv")

    # mean = np.mean(rounded_samples)

    # Calculation and fancy output
    if mean > 0:
        if vegas_mean > 0:
            hw_hl = f"My Model Projects {home_team} to Win by {round(mean * 2) / 2} - Vegas has {home_team} as a {vegas_mean} Point Favorite"
        else:
            hw_hl = f"My Model Projects {home_team} to Win by {round(mean * 2) / 2} - Vegas has {away_team} as a {-1*vegas_mean} Point Favorite"
    else:
        if vegas_mean < 0:
            hw_hl = f"My Model Projects {away_team} to Win by {round(mean * 2) / 2} - Vegas has {away_team} as a {vegas_mean} Point Favorite"
        else:
            hw_hl = f"My Model Projects {away_team} to Win by {round(mean * -2) / 2} - Vegas has {home_team} as a {vegas_mean} Point Favorite"
    # Home Team Favorite in both


    # Fancy output
    # print("┌" + "─" * 85 + "┐")
    # print(f"│ Expected Value for Betting Spread ( Only Bet + EV ): {ev_percentage}%".ljust(85) + " │")
    # print("├" + "─" * 85 + "┤")
    # print(f"│ {hw_hl}".ljust(85) + " │")
    # print("└" + "─" * 85 + "┘")

    print("┌" + "─" * 85 + "┐")
    print("├" + "─" * 85 + "┤")
    print(f"│ {hw_hl}".ljust(85) + " │")
    print("└" + "─" * 85 + "┘")

    return {
        "Week": week,
        "Season": season,
        "Home Team": home_team,
        "Away Team": away_team,
        "Home Team Projected Spread": -1*mean,
        "Home Team Vegas Spread": -1*vegas_mean,
        "Home Team Spread Std": np.std(combined_samples)
    }
season = 2024

weeks = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22]
for week in weeks:
    results = []
    data = pd.read_csv(f"{season} Weekly Predictions/Week {week} Predictions_Full_Season.csv")
    for i in range(len(data)):
        spread_result = CalcSpread(week, 2024, data["Home Team"].iloc[i], data["Away Team"].iloc[i], data['Home Team Str Mean'].iloc[i],
                                   data['Away Team Str Mean'].iloc[i],data['Home Team Str Var'].iloc[i],data['Away Team Str Var'].iloc[i],
                                   data['HFA'].iloc[i])

        results.append(spread_result)

    save_to_csv(f"2024 Weekly Predictions/Week {week} Predictions_Full_Season_Spread_Testing_Unadjusted.csv", results)