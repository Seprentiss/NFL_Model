import main
import pandas as pd
import numpy as np

schedule_data = pd.read_csv("Data/NFL_SCHEDULE_2024.csv")

model_rmse = 0
vegas_rmse = 0
games=0
wins = 0
loses = 0
pushes = 0
for i in range(1,14):
    data = pd.read_csv(f"Week {i} Predictions_Full_Season.csv")

    week_data = schedule_data[schedule_data["Week"] == i]

    for j in range(len(week_data)):
        Home_team = week_data["HomeTm"].iloc[j]
        Home_team_abbr = main.getTeamAbv(Home_team)
        vegas_home_team_margin = data[data["Home Team"] == Home_team_abbr]["Home Team Vegas Spread"].iloc[0]*-1
        model_home_team_margin = data[data["Home Team"] == Home_team_abbr]["Home Team Projected Spread"].iloc[0]*-1

        if week_data["HomeTm"].iloc[j] == week_data["Winner/tie"].iloc[j]:
            actual_home_team_margin = week_data["PtsW"].iloc[j] - week_data["PtsL"].iloc[j]
        else:
            actual_home_team_margin = week_data["PtsL"].iloc[j] - week_data["PtsW"].iloc[j]

        vegas_rmse += (actual_home_team_margin - vegas_home_team_margin)**2
        model_rmse += (actual_home_team_margin - (round(model_home_team_margin * 2) / 2))**2

        # home team favored vegas
        if vegas_home_team_margin*-1 <= 0:
            if model_home_team_margin*-1 > vegas_home_team_margin*-1:
                if actual_home_team_margin*-1 > vegas_home_team_margin:
                    wins += 1
                elif actual_home_team_margin*-1 < vegas_home_team_margin:
                    loses += 1
                else:
                    pushes +=1
            if model_home_team_margin*-1 < vegas_home_team_margin*-1:
                if actual_home_team_margin*-1 < vegas_home_team_margin:
                    wins += 1
                elif actual_home_team_margin*-1 > vegas_home_team_margin:
                    loses += 1
                else:
                    pushes +=1
        # away team favored vegas

        else:
            if model_home_team_margin*-1 > vegas_home_team_margin*-1:
                if actual_home_team_margin*-1 > vegas_home_team_margin:
                    wins += 1
                elif actual_home_team_margin*-1 < vegas_home_team_margin:
                    loses += 1
                else:
                    pushes +=1






        print(f"Week {i} {vegas_home_team_margin} {model_home_team_margin} {actual_home_team_margin}" )
        games+=1
print(f"Vegas RMSE: {np.sqrt(vegas_rmse/games)} - Model RMSE: {np.sqrt(model_rmse/games)}")
print(wins,loses,pushes)