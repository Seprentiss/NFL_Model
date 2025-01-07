import pandas as pd
import main
import scipy.stats as st
import math
import numpy as np


def save_to_csv(file_name, results):
    df = pd.DataFrame(results)
    df.to_csv(file_name, index=False)
    print(f"Data saved to {file_name}")

def CalcWinner(data, last_season_data, week, season, home_team, away_team, home_net, away_net, hfa):
    homev = main.teamVarPP(data, last_season_data, home_team,
                           weeks_played=week, season=season)
    awayv = main.teamVarPP(data, last_season_data, away_team,
                           weeks_played=week, season=season)
    mean = (home_net + hfa) - away_net
    sd = math.sqrt((homev + awayv))
    z = (0 - mean) / sd
    htwp = (1 - st.norm.cdf(z))

    atwp = 1 - htwp

    print("┌" + "─" * 50 + "┐")
    print(f"│ WEEK {week}: {home_team}: {round(htwp * 100)}%  {away_team}: {round(atwp * 100)}%".ljust(50) + " │")
    print("└" + "─" * 50 + "┘")

    return {
        "Week": week,
        "Season": season,
        "Home Team": home_team,
        "Away Team": away_team,
        "Home Win %": round(htwp * 100),
        "Away Win %": round(atwp * 100),
        "Home Team Str Mean": home_net,
        "Home Team Str Var": homev,
        "Away Team Str Mean": away_net,
        "Away Team Str Var": awayv,
        "HFA": hfa
    }


def CalcSpread(data, last_season_data, week, season, home_team, away_team, home_net, away_net, hfa):
    np.random.seed(42)

    vegas_data = pd.read_csv(f"2024 Vegas Lines/Vegas_Lines_Week_{week}.csv")

    # Extract data from the selected row
    home_team_dvoa = home_net + hfa
    home_team_variance = main.teamVarPP(data, last_season_data, home_team,
                                        weeks_played=week, season=season)
    away_team_dvoa = away_net
    away_team_variance = main.teamVarPP(data, last_season_data, away_team,
                                        weeks_played=week, season=season)

    # Update the diffplot data with the new mean and variance
    updated_x1 = np.random.normal(home_team_dvoa, np.sqrt(home_team_variance), 10_000)
    updated_x2 = np.random.normal(away_team_dvoa, np.sqrt(away_team_variance), 10_000)

    avg_plays = 153
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
    if vegas_mean > 0:
        if mean > 0:
            ev = (sum(cpev[(cpev["spread_line"] == round(-mean * 2) / 2) & (cpev["result"] < -vegas_mean)][
                          "normalized_modeled_prob"]) +
                  sum(cpev[(cpev["spread_line"] == round(-mean * 2) / 2) & (cpev["result"] > -vegas_mean)][
                          "normalized_modeled_prob"]) * -1.1) / 1.1
        else:
            ev = (sum(cpev[(cpev["spread_line"] == round(-mean * 2) / 2) & (cpev["result"] > -vegas_mean)][
                          "normalized_modeled_prob"]) +
                  sum(cpev[(cpev["spread_line"] == round(-mean * 2) / 2) & (cpev["result"] < -vegas_mean)][
                          "normalized_modeled_prob"]) * -1.1) / 1.1
    else:
        if mean > 0:
            ev = (sum(cpev[(cpev["spread_line"] == round(mean * 2) / 2) & (cpev["result"] > vegas_mean)][
                          "normalized_modeled_prob"]) +
                  sum(cpev[(cpev["spread_line"] == round(mean * 2) / 2) & (cpev["result"] < vegas_mean)][
                          "normalized_modeled_prob"]) * -1.1) / 1.1
        else:
            ev = (sum(cpev[(cpev["spread_line"] == round(mean * 2) / 2) & (cpev["result"] < vegas_mean)][
                          "normalized_modeled_prob"]) +
                  sum(cpev[(cpev["spread_line"] == round(mean * 2) / 2) & (cpev["result"] > vegas_mean)][
                          "normalized_modeled_prob"]) * -1.1) / 1.1

    ev_percentage = round(ev * 100)

    # Fancy output
    # print("┌" + "─" * 85 + "┐")
    # print(f"│ Expected Value for Betting Spread ( Only Bet + EV ): {ev_percentage}%".ljust(85) + " │")
    # print("├" + "─" * 85 + "┤")
    # print(f"│ {hw_hl}".ljust(85) + " │")
    # print("└" + "─" * 85 + "┘")

    print("┌" + "─" * 85 + "┐")
    if ev > 0:
        print(f"│ \033[32mExpected Value for Betting Spread ( Only Bet + EV ): {ev_percentage}%\033[0m".ljust(94) + " │")  # Green text for the first line
    else:
        print(f"│ \033[31mExpected Value for Betting Spread ( Only Bet + EV ): {ev_percentage}%\033[0m".ljust(94) + " │")
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
        "Expected Value (%)": ev_percentage,
        "Home Team Spread Std": np.std(combined_samples)
    }


season = 2024

schedule_data = pd.read_csv(f"Data/NFL_SCHEDULE_{season}.csv")
url = f'https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{season-1}.csv'

data = pd.read_csv(url, low_memory=True)

last_season_data = pd.read_csv(f"Data/play_by_play_{season - 1}.csv")

vegas = pd.read_csv(f"NFL Vegas Win Totals {season}.csv")

print("data_loaded")

weeks = [18]
results = []

Total_Wins = 0
Total_Loses = 0
for week in weeks:
    Week_Wins = 0
    Week_Loses = 0
    hfa = main.hfa(data, last_season_data, weeks_played=week)
    print(f"HFA: {hfa}")
    week_data = schedule_data[schedule_data["Week"] == week]
    # print(week_data)
    for i in range(len(week_data)):
        home_team = main.getTeamAbv(week_data["HomeTm"].iloc[i])
        away_team = main.getTeamAbv(week_data["VisTm"].iloc[i])

        last_season = pd.read_csv(f"Team Stats/{season - 1}/{22}/Net_Ratings.csv")

        """BYE WEEKS"""
        """Preliminary number want to check more seasons. Only 5 so far maybe last 10"""
        # -0.0080468
        # too small

        """QB ADJ"""

        if week == 1:
            home_net = ((last_season[home_team].iloc[0] * 2 / 3) * .35) + (
                        ((vegas[vegas["Team"] == home_team]["Vegas Wins"].iloc[0] - 8.3641) / 33.146) * .65)
            away_net = ((last_season[away_team].iloc[0] * 2 / 3) * .35) + (
                        ((vegas[vegas["Team"] == away_team]["Vegas Wins"].iloc[0] - 8.3641) / 33.146) * .65)
        elif week < 14:
            net = pd.read_csv(f"Team Stats/{season}/{week - 1}/Net_Ratings.csv")

            last_season = pd.read_csv(f"Team Stats/{season - 1}/{22}/Net_Ratings.csv")
            home_net = (net[home_team].iloc[0] * ((week - 1) / 13)) + (
                        ((last_season[home_team].iloc[0] * 2 / 3) * .35) + (
                            ((vegas[vegas["Team"] == home_team]["Vegas Wins"].iloc[0] - 8.3641) / 33.146) * .65)) * (
                                   1 - ((week - 1) / 13))
            away_net = (net[away_team].iloc[0] * ((week - 1) / 13)) + (
                        ((last_season[away_team].iloc[0] * 2 / 3) * .35) + (
                            ((vegas[vegas["Team"] == away_team]["Vegas Wins"].iloc[0] - 8.3641) / 33.146) * .65)) * (
                                   1 - ((week - 1) / 13))

        else:
            home_net = pd.read_csv(f"Team Stats/{season}/{week - 1}/Net_Ratings.csv")[home_team].iloc[0]
            away_net = pd.read_csv(f"Team Stats/{season}/{week - 1}/Net_Ratings.csv")[away_team].iloc[0]

        QB_adj = {"ATL":-0.00504188034,"CLE":-0.02286752136,"PHI":-0.06409743589,"IND":-0.0072068376,"MIA":-0.05824786324,"BUF":-0.12082307692,"KC":-0.07854102564,"LA":-0.00577435897,"SF":-0.07786153846}
        # QB_adj = {}
        if home_team in QB_adj:
            home_net+= QB_adj[home_team]
        if away_team in QB_adj:
            away_net+= QB_adj[away_team]

        if week > 21:
            hfa = 0

        if home_team not in []:
            win_result = CalcWinner(data, last_season_data, week, season, home_team, away_team, home_net, away_net, hfa)
            spread_result = CalcSpread(data, last_season_data, week, season, home_team, away_team, home_net, away_net, hfa)
        else:
            win_result = CalcWinner(data, last_season_data, week, season, home_team, away_team, home_net, away_net, 0)
            spread_result = CalcSpread(data, last_season_data, week, season, home_team, away_team, home_net, away_net,
                                       0)

        combined_result = {**win_result, **spread_result}

        results.append(combined_result)

    save_to_csv(f"2024 Weekly Predictions/Week {week} Predictions_Full_Season.csv", results)

    #     if (home_net > away_net):
    #         if home_team == main.getTeamAbv(week_data["Winner/tie"].iloc[i]):
    #             Total_Wins += 1
    #             Week_Wins += 1
    #             print(f"Home Net: {home_net} Away Net: {away_net}) 1")
    #         else:
    #             Total_Loses += 1
    #             Week_Loses += 1
    #             print(f"Home Net: {home_net} Away Net: {away_net}) 0 ")
    #     else:
    #         if away_team == main.getTeamAbv(week_data["Winner/tie"].iloc[i]):
    #             Total_Wins += 1
    #             Week_Wins += 1
    #             print(f"Home Net: {home_net} Away Net: {away_net}) 1")
    #         else:
    #             Total_Loses += 1
    #             Week_Loses += 1
    #             print(f"Home Net: {home_net} Away Net: {away_net}) 0")
    #
    # print(f"Total W/L :{Total_Wins} - {Total_Loses} ( {Total_Wins / (Total_Wins + Total_Loses):.2f} )% \n "
    #       f"Week W/L :{Week_Wins} - {Week_Loses} ( {Week_Wins / (Week_Wins + Week_Loses):.2f} )% ")
